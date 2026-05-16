from __future__ import annotations

import random
from collections import defaultdict
from itertools import product
from typing import Iterable

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

try:  # pragma: no cover - optional dependency
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - optional dependency
    cp_model = None


AssignmentRef = tuple[int, int]
PartialAssignment = dict[int, int]


class ConstraintError(ValueError):
    """Raised when compiled constraints are contradictory."""


class ConstraintEngine:
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
        self._feasibility_cache: dict[tuple[tuple[int, int], ...], bool] = {}
        self._compile_constraints()
        self._compute_implied_pairs()
        self._validate_compiled_constraints()

    def conflicts(self, left: Assignment, right: Assignment) -> bool:
        return self._to_ref(right) in self.invalid_pairs.get(self._to_ref(left), set())

    def implied_requirements(self, assignment: Assignment) -> tuple[Assignment, ...]:
        refs = self.requires.get(self._to_ref(assignment), set())
        return tuple(sorted(self._from_ref(ref) for ref in refs))

    def can_complete(self, partial: PartialAssignment) -> bool:
        normalized = self._normalize_partial(dict(partial))
        if normalized is None:
            return False

        signature = tuple(sorted(normalized.items()))
        cached = self._feasibility_cache.get(signature)
        if cached is not None:
            return cached

        if cp_model is not None:
            result = self._can_complete_with_cp_sat(normalized)
        else:
            result = self._backtrack_complete(normalized, rng=None, failures=set()) is not None

        self._feasibility_cache[signature] = result
        return result

    def complete_assignment(self, partial: PartialAssignment, rng: random.Random | None = None) -> tuple[int, ...] | None:
        normalized = self._normalize_partial(dict(partial))
        if normalized is None:
            return None
        return self._backtrack_complete(normalized, rng=rng, failures=set())

    def is_complete_assignment_valid(self, row: tuple[int, ...]) -> bool:
        partial = {parameter_index: value_index for parameter_index, value_index in enumerate(row)}
        normalized = self._normalize_partial(partial)
        if normalized is None or len(normalized) != len(self.model.parameters):
            return False

        for antecedents, forbidden in self.higher_order:
            if all(normalized.get(param_index) == value_index for param_index, value_index in antecedents):
                if normalized.get(forbidden[0]) == forbidden[1]:
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

        for forced in self.forced_interactions:
            partial = {parameter_index: value_index for parameter_index, value_index in forced}
            if self.complete_assignment(partial, rng=None) is None:
                assignments = ", ".join(
                    f"{self.model.parameters[parameter_index].name}={self.model.parameters[parameter_index].values[value_index]}"
                    for parameter_index, value_index in forced
                )
                raise ConstraintError(f"Forced interaction is not feasible: {assignments}.")

    def _normalize_partial(self, partial: PartialAssignment) -> PartialAssignment | None:
        normalized = dict(partial)
        changed = True
        while changed:
            changed = False
            if not self._partial_consistent(normalized):
                return None
            for parameter_index, value_index in list(normalized.items()):
                for required_parameter, required_value in self.requires.get((parameter_index, value_index), set()):
                    current = normalized.get(required_parameter)
                    if current is None:
                        normalized[required_parameter] = required_value
                        changed = True
                        continue
                    if current != required_value:
                        return None
        if not self._partial_consistent(normalized):
            return None
        return normalized

    def _partial_consistent(self, partial: PartialAssignment) -> bool:
        for parameter_index, value_index in partial.items():
            for other_parameter, other_value in partial.items():
                if parameter_index == other_parameter and value_index != other_value:
                    return False
                if parameter_index == other_parameter:
                    continue
                if (other_parameter, other_value) in self.invalid_pairs.get((parameter_index, value_index), set()):
                    return False

        for antecedents, forbidden in self.higher_order:
            if all(partial.get(parameter_index) == value_index for parameter_index, value_index in antecedents):
                if partial.get(forbidden[0]) == forbidden[1]:
                    return False
        return True

    def _backtrack_complete(
        self,
        partial: PartialAssignment,
        rng: random.Random | None,
        failures: set[tuple[tuple[int, int], ...]],
    ) -> tuple[int, ...] | None:
        signature = tuple(sorted(partial.items()))
        if signature in failures:
            return None

        if len(partial) == len(self.model.parameters):
            row = tuple(partial[index] for index in range(len(self.model.parameters)))
            return row if self.is_complete_assignment_valid(row) else None

        next_parameter, values = self._next_parameter_values(partial)
        if next_parameter is None:
            failures.add(signature)
            return None

        for value in self._ordered_values(next_parameter, values, rng):
            candidate = dict(partial)
            candidate[next_parameter] = value
            normalized = self._normalize_partial(candidate)
            if normalized is None:
                continue
            result = self._backtrack_complete(normalized, rng=rng, failures=failures)
            if result is not None:
                return result

        failures.add(signature)
        return None

    def _next_parameter_values(self, partial: PartialAssignment) -> tuple[int | None, list[int]]:
        best_parameter: int | None = None
        best_values: list[int] = []
        best_size: int | None = None

        for parameter_index, parameter in enumerate(self.model.parameters):
            if parameter_index in partial:
                continue
            feasible: list[int] = []
            for value_index in range(len(parameter.values)):
                candidate = dict(partial)
                candidate[parameter_index] = value_index
                if self._normalize_partial(candidate) is not None:
                    feasible.append(value_index)

            if not feasible:
                return None, []

            if best_size is None or len(feasible) < best_size:
                best_parameter = parameter_index
                best_values = feasible
                best_size = len(feasible)

        return best_parameter, best_values

    def _ordered_values(self, parameter_index: int, values: Iterable[int], rng: random.Random | None) -> list[int]:
        parameter = self.model.parameters[parameter_index]
        values_list = list(values)
        if rng is None:
            return sorted(values_list, key=lambda value_index: (-parameter.normalized_weights[value_index], value_index))

        weighted = []
        for value_index in values_list:
            weight = parameter.normalized_weights[value_index]
            ticket = rng.random() / max(weight, 1e-9)
            weighted.append((ticket, value_index))
        weighted.sort(key=lambda item: item[0])
        return [value_index for _, value_index in weighted]

    def _can_complete_with_cp_sat(self, partial: PartialAssignment) -> bool:
        if cp_model is None:  # pragma: no cover - guarded by caller
            return False

        model = cp_model.CpModel()
        variables = [
            model.NewIntVar(0, len(parameter.values) - 1, parameter.name)
            for parameter in self.model.parameters
        ]

        for parameter_index, value_index in partial.items():
            model.Add(variables[parameter_index] == value_index)

        pair_constraints: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
        for left in self._all_assignment_refs():
            for right in self.invalid_pairs.get(left, set()):
                if left[0] >= right[0]:
                    continue
                pair_constraints[(left[0], right[0])].add((left[1], right[1]))

        for (left_index, right_index), forbidden_pairs in pair_constraints.items():
            model.AddForbiddenAssignments(
                [variables[left_index], variables[right_index]],
                sorted(forbidden_pairs),
            )

        literal_cache: dict[AssignmentRef, object] = {}

        def literal_for(assignment: AssignmentRef):
            cached = literal_cache.get(assignment)
            if cached is not None:
                return cached
            lit = model.NewBoolVar(f"p{assignment[0]}_is_{assignment[1]}")
            model.Add(variables[assignment[0]] == assignment[1]).OnlyEnforceIf(lit)
            model.Add(variables[assignment[0]] != assignment[1]).OnlyEnforceIf(lit.Not())
            literal_cache[assignment] = lit
            return lit

        for antecedents, forbidden in self.higher_order:
            model.Add(variables[forbidden[0]] != forbidden[1]).OnlyEnforceIf(
                [literal_for(assignment) for assignment in antecedents]
            )

        model.AddDecisionStrategy(variables, cp_model.CHOOSE_FIRST, cp_model.SELECT_MIN_VALUE)

        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        solver.parameters.max_time_in_seconds = 2.0
        status = solver.Solve(model)
        return status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

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
