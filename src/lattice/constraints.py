from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from lattice import _engine
from lattice.model import (
    Assignment,
    BidirectionalConstraint,
    ConditionalConstraint,
    ForcedConstraint,
    ForwardDependencyConstraint,
    HigherOrderConstraint,
    InvalidPairConstraint,
    Model,
    NA_VALUE,
)

AssignmentRef = tuple[int, int]
PartialAssignment = dict[int, int]


class ConstraintError(ValueError):
    """Raised when compiled constraints are contradictory."""


class ConstraintEngine:
    """Compiles a model's constraints to the engine's primitives (invalid pairs,
    requirements, higher-order exclusions, forced interactions), checks the
    compiled closure for contradictions, and asks the Rust engine whether the
    model and its forced interactions are satisfiable. The Ruby gem's
    ConstraintEngine does the same, so both report the same errors."""

    def __init__(self, model: Model):
        self.model = model
        self.parameter_index = {parameter.name: index for index, parameter in enumerate(model.parameters)}
        self.value_index = {
            (parameter_index, value): value_index
            for parameter_index, parameter in enumerate(model.parameters)
            for value_index, value in enumerate(parameter.values)
        }
        self.invalid_pairs: dict[AssignmentRef, set[AssignmentRef]] = defaultdict(set)
        self.requires: dict[AssignmentRef, set[AssignmentRef]] = defaultdict(set)
        self.higher_order: list[tuple[tuple[AssignmentRef, ...], AssignmentRef]] = []
        self.forced_interactions: list[tuple[AssignmentRef, ...]] = []
        self._compile_constraints()
        self._compute_implied_pairs()
        self._validate_compiled_constraints()
        self.native = self.native_model(model.strength)
        self._satisfiable = self._check_feasibility()

    def conflicts(self, left: Assignment, right: Assignment) -> bool:
        return self._to_ref(right) in self.invalid_pairs.get(self._to_ref(left), set())

    def implied_requirements(self, assignment: Assignment) -> tuple[Assignment, ...]:
        refs = self.requires.get(self._to_ref(assignment), set())
        return tuple(sorted(self._from_ref(ref) for ref in refs))

    def satisfiable(self) -> bool:
        """Whether any row satisfies every constraint."""
        return self._satisfiable

    def can_complete(self, partial: PartialAssignment) -> bool:
        """Whether some valid row contains every assignment in `partial`."""
        return self.native.can_complete(sorted(partial.items()))

    def engine_constraints(self) -> dict:
        """The compiled constraints as the engine takes them: invalid pairs and
        requirements as sorted ((p, v), (q, w)) lists, higher-order exclusions
        and forced interactions in compile order."""
        return {
            "invalid_pairs": _pairs(self.invalid_pairs),
            "requires": _pairs(self.requires),
            "higher_order": [(list(antecedents), forbidden) for antecedents, forbidden in self.higher_order],
            "forced": [list(forced) for forced in self.forced_interactions],
        }

    def native_model(self, strength: int) -> "_engine.Model":
        compiled = self.engine_constraints()
        return _engine.Model(
            [len(parameter.values) for parameter in self.model.parameters],
            [list(parameter.normalized_weights) for parameter in self.model.parameters],
            strength,
            compiled["invalid_pairs"],
            compiled["requires"],
            compiled["higher_order"],
            compiled["forced"],
        )

    def _check_feasibility(self) -> bool:
        """Raises for the first impossible forced interaction; otherwise returns
        whether the model has any valid row."""
        try:
            self.native.feasibility()
        except _engine.ForcedInfeasible as error:
            forced = self.forced_interactions[error.args[0]]
            assignments = ", ".join(
                f"{self.model.parameters[parameter_index].name}={self.model.parameters[parameter_index].values[value_index]}"
                for parameter_index, value_index in forced
            )
            raise ConstraintError(f"Forced interaction is not feasible: {assignments}.") from None
        except _engine.NoValidAssignments:
            return False
        return True

    def _compile_constraints(self) -> None:
        for constraint in self.model.constraints:
            if isinstance(constraint, InvalidPairConstraint):
                self._add_invalid_pair(self._to_ref(constraint.if_assignment), self._to_ref(constraint.then_not))
                continue

            if isinstance(constraint, BidirectionalConstraint):
                left, right = constraint.pair
                left_ref = self._to_ref(left)
                right_ref = self._to_ref(right)
                self._add_requirement(left_ref, right_ref)
                self._add_requirement(right_ref, left_ref)
                self._exclude_other_values(left_ref, right_ref)
                self._exclude_other_values(right_ref, left_ref)
                continue

            if isinstance(constraint, ForwardDependencyConstraint):
                source_ref = self._to_ref(constraint.source)
                target_ref = self._to_ref(constraint.target)
                self._add_requirement(source_ref, target_ref)
                self._exclude_other_values(source_ref, target_ref)
                continue

            if isinstance(constraint, ConditionalConstraint):
                self._compile_conditional(constraint)
                continue

            if isinstance(constraint, ForcedConstraint):
                refs = tuple(self._to_ref(assignment) for assignment in constraint.assignments)
                self.forced_interactions.append(refs)
                continue

            if isinstance(constraint, HigherOrderConstraint):
                antecedents = tuple(self._to_ref(assignment) for assignment in constraint.if_all)
                forbidden = self._to_ref(constraint.then_not)
                self.higher_order.append((antecedents, forbidden))

    def _compile_conditional(self, constraint: ConditionalConstraint) -> None:
        parent_index = self.parameter_index[constraint.parent]
        child_index = self.parameter_index[constraint.parameter]
        parent = self.model.parameters[parent_index]
        child = self.model.parameters[child_index]
        applicable_values = set(constraint.applies_when)
        na_ref = (child_index, self.value_index[(child_index, NA_VALUE)])

        for parent_value_index, parent_value in enumerate(parent.values):
            parent_ref = (parent_index, parent_value_index)
            if parent_value in applicable_values:
                self._add_invalid_pair(parent_ref, na_ref)
                continue

            for child_value_index, child_value in enumerate(child.values):
                if child_value == NA_VALUE:
                    continue
                self._add_invalid_pair(parent_ref, (child_index, child_value_index))

    def _compute_implied_pairs(self) -> None:
        changed = True
        all_assignments = list(self._all_assignment_refs())
        while changed:
            changed = False

            for assignment in all_assignments:
                implied = set(self.requires.get(assignment, set()))
                for required in tuple(implied):
                    implied.update(self.requires.get(required, set()))
                if implied - self.requires.get(assignment, set()):
                    self.requires[assignment].update(implied)
                    changed = True

            for assignment in all_assignments:
                additions: set[AssignmentRef] = set()
                for conflicting in tuple(self.invalid_pairs.get(assignment, set())):
                    additions.update(self.requires.get(conflicting, set()))
                for required in tuple(self.requires.get(assignment, set())):
                    additions.update(self.invalid_pairs.get(required, set()))
                additions.discard(assignment)
                for addition in additions:
                    if addition not in self.invalid_pairs.get(assignment, set()):
                        self._add_invalid_pair(assignment, addition)
                        changed = True

    def _validate_compiled_constraints(self) -> None:
        for assignment in self._all_assignment_refs():
            if assignment in self.invalid_pairs.get(assignment, set()):
                readable = self._from_ref(assignment)
                raise ConstraintError(f"Constraint closure makes `{readable.parameter}={readable.value}` impossible.")

            for required in self.requires.get(assignment, set()):
                if assignment[0] == required[0] and assignment[1] != required[1]:
                    left = self._from_ref(assignment)
                    right = self._from_ref(required)
                    raise ConstraintError(
                        f"Constraint closure requires incompatible values `{left.parameter}={left.value}` and `{right.parameter}={right.value}`."
                    )
                if required in self.invalid_pairs.get(assignment, set()):
                    left = self._from_ref(assignment)
                    right = self._from_ref(required)
                    raise ConstraintError(
                        f"Constraint closure makes `{left.parameter}={left.value}` conflict with its own requirement `{right.parameter}={right.value}`."
                    )

    def _exclude_other_values(self, source: AssignmentRef, required: AssignmentRef) -> None:
        target_parameter = self.model.parameters[required[0]]
        for value_index in range(len(target_parameter.values)):
            if value_index == required[1]:
                continue
            self._add_invalid_pair(source, (required[0], value_index))

    def _add_invalid_pair(self, left: AssignmentRef, right: AssignmentRef) -> None:
        self.invalid_pairs[left].add(right)
        self.invalid_pairs[right].add(left)

    def _add_requirement(self, source: AssignmentRef, target: AssignmentRef) -> None:
        self.requires[source].add(target)

    def _all_assignment_refs(self) -> Iterable[AssignmentRef]:
        for parameter_index, parameter in enumerate(self.model.parameters):
            for value_index in range(len(parameter.values)):
                yield (parameter_index, value_index)

    def _to_ref(self, assignment: Assignment) -> AssignmentRef:
        parameter_index = self.parameter_index[assignment.parameter]
        value_index = self.value_index[(parameter_index, assignment.value)]
        return (parameter_index, value_index)

    def _from_ref(self, assignment: AssignmentRef) -> Assignment:
        parameter = self.model.parameters[assignment[0]]
        return Assignment(parameter=parameter.name, value=parameter.values[assignment[1]])


def _pairs(table: dict[AssignmentRef, set[AssignmentRef]]) -> list[tuple[AssignmentRef, AssignmentRef]]:
    return sorted((source, target) for source, targets in table.items() for target in targets)
