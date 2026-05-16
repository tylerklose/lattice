from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

from lattice.model import (
    Assignment,
    BidirectionalConstraint,
    ConditionalConstraint,
    ForcedConstraint,
    ForwardDependencyConstraint,
    HigherOrderConstraint,
    InvalidPairConstraint,
    Model,
    Parameter,
    normalize_scalar,
    NA_VALUE,
)


class ModelIOError(Exception):
    """Raised when reading or deserializing a model fails."""


class ValidationError(Exception):
    """Raised when a model is structurally invalid."""

    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


def load_model(path: str | None, strength_override: int | None = None) -> Model:
    text, source_name, extension = _read_model_input(path)
    data = _deserialize_model(text, source_name, extension)
    return parse_model_data(data, strength_override=strength_override)


def parse_model_data(data: Any, strength_override: int | None = None) -> Model:
    if not isinstance(data, dict):
        raise ValidationError(["Model root must be a JSON/YAML object."])

    errors: list[str] = []
    parameters = _parse_parameters(data.get("parameters"), errors)
    raw_constraints = data.get("constraints", [])
    if raw_constraints is None:
        raw_constraints = []
    if not isinstance(raw_constraints, list):
        errors.append("`constraints` must be a list.")
        raw_constraints = []

    _apply_conditional_parameters(parameters, raw_constraints, errors)
    constraints = _parse_constraints(raw_constraints, parameters, errors)
    strength = _parse_strength(strength_override if strength_override is not None else data.get("strength"), len(parameters), errors)
    model_name = normalize_scalar(data.get("model_name", "unnamed_model"))

    if errors:
        raise ValidationError(errors)

    return Model(
        model_name=model_name,
        parameters=tuple(parameters.values()),
        constraints=tuple(constraints),
        strength=strength,
    )


def _read_model_input(path: str | None) -> tuple[str, str, str | None]:
    if path in (None, "-"):
        text = sys.stdin.read()
        if not text.strip():
            raise ModelIOError("No model content found on stdin.")
        return text, "stdin", None

    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelIOError(f"Unable to read model file `{path}`: {exc}") from exc
    return text, str(file_path), file_path.suffix.lower()


def _deserialize_model(text: str, source_name: str, extension: str | None) -> Any:
    loaders = []
    if extension == ".json":
        loaders = [json.loads]
    elif extension in {".yaml", ".yml"}:
        loaders = [yaml.safe_load]
    else:
        loaders = [json.loads, yaml.safe_load]

    errors: list[str] = []
    for loader in loaders:
        try:
            return loader(text)
        except Exception as exc:  # pragma: no cover - exact parser error text varies
            errors.append(str(exc))

    joined = "; ".join(errors)
    raise ModelIOError(f"Unable to parse model from `{source_name}`: {joined}")


def _parse_parameters(raw_parameters: Any, errors: list[str]) -> "OrderedDict[str, Parameter]":
    parameters: "OrderedDict[str, Parameter]" = OrderedDict()
    if raw_parameters is None:
        errors.append("`parameters` is required.")
        return parameters

    if isinstance(raw_parameters, dict):
        items = raw_parameters.items()
        for name, spec in items:
            _add_parameter(parameters, name, spec, errors)
        return parameters

    if isinstance(raw_parameters, list):
        for index, raw_parameter in enumerate(raw_parameters):
            if not isinstance(raw_parameter, dict):
                errors.append(f"`parameters[{index}]` must be an object.")
                continue
            name = raw_parameter.get("name")
            if name is None:
                errors.append(f"`parameters[{index}]` is missing `name`.")
                continue
            _add_parameter(parameters, name, raw_parameter, errors)
        return parameters

    errors.append("`parameters` must be a mapping or list.")
    return parameters


def _add_parameter(parameters: "OrderedDict[str, Parameter]", name: Any, spec: Any, errors: list[str]) -> None:
    normalized_name = normalize_scalar(name)
    if normalized_name in parameters:
        errors.append(f"Duplicate parameter `{normalized_name}`.")
        return

    values: Any
    weights: Any = None
    if isinstance(spec, dict):
        values = spec.get("values")
        weights = spec.get("weights")
    else:
        values = spec

    parsed_values = _parse_values(values, f"parameter `{normalized_name}`", errors)
    parsed_weights = _parse_weights(weights, parsed_values, normalized_name, errors)
    if not parsed_values:
        return

    parameters[normalized_name] = Parameter(
        name=normalized_name,
        values=parsed_values,
        weights=parsed_weights,
    )


def _apply_conditional_parameters(parameters: "OrderedDict[str, Parameter]", raw_constraints: list[Any], errors: list[str]) -> None:
    for index, raw_constraint in enumerate(raw_constraints):
        if not isinstance(raw_constraint, dict):
            continue
        if raw_constraint.get("type") != "conditional":
            continue

        parameter_name = normalize_scalar(raw_constraint.get("parameter"))
        values = _parse_values(raw_constraint.get("values"), f"`constraints[{index}]` conditional values", errors)
        if not values:
            continue

        conditional_values = values
        if NA_VALUE not in conditional_values:
            conditional_values = conditional_values + (NA_VALUE,)

        existing = parameters.get(parameter_name)
        if existing is None:
            parameters[parameter_name] = Parameter(name=parameter_name, values=conditional_values)
            continue

        expected = set(conditional_values)
        actual = set(existing.values)
        if actual != expected:
            errors.append(
                f"Conditional parameter `{parameter_name}` conflicts with an existing parameter definition."
            )


def _parse_constraints(
    raw_constraints: list[Any],
    parameters: "OrderedDict[str, Parameter]",
    errors: list[str],
) -> list[Any]:
    parsed: list[Any] = []
    for index, raw_constraint in enumerate(raw_constraints):
        if not isinstance(raw_constraint, dict):
            errors.append(f"`constraints[{index}]` must be an object.")
            continue

        constraint_type = raw_constraint.get("type")
        if constraint_type == "invalid_pair":
            if_assignment = _parse_assignment(raw_constraint.get("if"), parameters, f"`constraints[{index}].if`", errors)
            then_not = _parse_assignment(raw_constraint.get("then_not"), parameters, f"`constraints[{index}].then_not`", errors)
            if if_assignment and then_not:
                parsed.append(InvalidPairConstraint(if_assignment=if_assignment, then_not=then_not))
            continue

        if constraint_type == "bidirectional":
            pair = raw_constraint.get("pair")
            if not isinstance(pair, list) or len(pair) != 2:
                errors.append(f"`constraints[{index}].pair` must contain exactly two assignments.")
                continue
            left = _parse_assignment(pair[0], parameters, f"`constraints[{index}].pair[0]`", errors)
            right = _parse_assignment(pair[1], parameters, f"`constraints[{index}].pair[1]`", errors)
            if left and right:
                parsed.append(BidirectionalConstraint(pair=(left, right)))
            continue

        if constraint_type == "forward_dep":
            source = _parse_assignment(raw_constraint.get("source"), parameters, f"`constraints[{index}].source`", errors)
            target = _parse_assignment(raw_constraint.get("target"), parameters, f"`constraints[{index}].target`", errors)
            if source and target:
                parsed.append(ForwardDependencyConstraint(source=source, target=target))
            continue

        if constraint_type == "conditional":
            parent = normalize_scalar(raw_constraint.get("parent"))
            parameter_name = normalize_scalar(raw_constraint.get("parameter"))
            values = _parse_values(raw_constraint.get("values"), f"`constraints[{index}].values`", errors)
            applies_when = _parse_values(raw_constraint.get("applies_when"), f"`constraints[{index}].applies_when`", errors)

            if parent not in parameters:
                errors.append(f"`constraints[{index}]` references unknown parent parameter `{parent}`.")
                continue
            if parameter_name not in parameters:
                errors.append(f"`constraints[{index}]` references unknown conditional parameter `{parameter_name}`.")
                continue

            parent_parameter = parameters[parent]
            missing = [value for value in applies_when if value not in parent_parameter.value_set]
            if missing:
                errors.append(
                    f"`constraints[{index}]` applies_when contains unknown values for `{parent}`: {', '.join(missing)}."
                )
                continue

            if not values:
                continue
            parsed.append(
                ConditionalConstraint(
                    parameter=parameter_name,
                    values=tuple(value for value in values if value != NA_VALUE),
                    parent=parent,
                    applies_when=applies_when,
                )
            )
            continue

        if constraint_type == "forced":
            assignments = raw_constraint.get("assignments")
            if not isinstance(assignments, list) or not assignments:
                errors.append(f"`constraints[{index}].assignments` must contain at least one assignment.")
                continue
            seen_parameters: set[str] = set()
            parsed_assignments: list[Assignment] = []
            for assignment_index, raw_assignment in enumerate(assignments):
                assignment = _parse_assignment(
                    raw_assignment,
                    parameters,
                    f"`constraints[{index}].assignments[{assignment_index}]`",
                    errors,
                )
                if assignment is None:
                    continue
                if assignment.parameter in seen_parameters:
                    errors.append(
                        f"`constraints[{index}]` repeats parameter `{assignment.parameter}` inside a forced interaction."
                    )
                    continue
                seen_parameters.add(assignment.parameter)
                parsed_assignments.append(assignment)
            if parsed_assignments:
                parsed.append(ForcedConstraint(assignments=tuple(parsed_assignments)))
            continue

        if constraint_type == "higher_order":
            if_all = raw_constraint.get("if_all")
            then_not = raw_constraint.get("then_not")
            if not isinstance(if_all, list) or len(if_all) < 2:
                errors.append(f"`constraints[{index}].if_all` must contain at least two assignments.")
                continue
            parsed_if_all: list[Assignment] = []
            for assignment_index, raw_assignment in enumerate(if_all):
                assignment = _parse_assignment(
                    raw_assignment,
                    parameters,
                    f"`constraints[{index}].if_all[{assignment_index}]`",
                    errors,
                )
                if assignment is not None:
                    parsed_if_all.append(assignment)
            parsed_then_not = _parse_assignment(then_not, parameters, f"`constraints[{index}].then_not`", errors)
            if parsed_if_all and parsed_then_not:
                parsed.append(HigherOrderConstraint(if_all=tuple(parsed_if_all), then_not=parsed_then_not))
            continue

        errors.append(f"`constraints[{index}]` has unknown type `{constraint_type}`.")

    return parsed


def _parse_assignment(
    raw_assignment: Any,
    parameters: "OrderedDict[str, Parameter]",
    field_name: str,
    errors: list[str],
) -> Assignment | None:
    if not isinstance(raw_assignment, dict):
        errors.append(f"{field_name} must be an object.")
        return None

    parameter_name = normalize_scalar(raw_assignment.get("parameter"))
    value = normalize_scalar(raw_assignment.get("value"))

    parameter = parameters.get(parameter_name)
    if parameter is None:
        errors.append(f"{field_name} references unknown parameter `{parameter_name}`.")
        return None

    if value not in parameter.value_set:
        errors.append(f"{field_name} references unknown value `{value}` for parameter `{parameter_name}`.")
        return None

    return Assignment(parameter=parameter_name, value=value)


def _parse_values(raw_values: Any, field_name: str, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(raw_values, list) or not raw_values:
        errors.append(f"{field_name} must be a non-empty list.")
        return ()

    values = tuple(normalize_scalar(value) for value in raw_values)
    if len(set(values)) != len(values):
        errors.append(f"{field_name} contains duplicate values.")
        return ()
    return values


def _parse_weights(
    raw_weights: Any,
    values: tuple[str, ...],
    parameter_name: str,
    errors: list[str],
) -> tuple[float, ...] | None:
    if raw_weights is None:
        return None
    if not isinstance(raw_weights, list):
        errors.append(f"`weights` for parameter `{parameter_name}` must be a list.")
        return None
    if len(raw_weights) != len(values):
        errors.append(
            f"`weights` for parameter `{parameter_name}` must have the same length as its values."
        )
        return None

    parsed: list[float] = []
    for weight in raw_weights:
        if not isinstance(weight, (int, float)):
            errors.append(f"`weights` for parameter `{parameter_name}` must be numeric.")
            return None
        if weight <= 0:
            errors.append(f"`weights` for parameter `{parameter_name}` must be greater than zero.")
            return None
        parsed.append(float(weight))
    return tuple(parsed)


def _parse_strength(raw_strength: Any, parameter_count: int, errors: list[str]) -> int:
    if raw_strength is None:
        strength = 2
    else:
        try:
            strength = int(raw_strength)
        except (TypeError, ValueError):
            errors.append("`strength` must be an integer.")
            return 2

    if strength < 1:
        errors.append("`strength` must be at least 1.")
    if parameter_count and strength > parameter_count:
        errors.append("`strength` cannot exceed the number of parameters.")
    return strength
