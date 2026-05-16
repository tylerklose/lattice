from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any, TypeAlias


NormalizedValue: TypeAlias = str
NA_VALUE = "N/A"


def normalize_scalar(value: Any) -> NormalizedValue:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    return str(value)


@dataclass(frozen=True, order=True)
class Assignment:
    parameter: str
    value: NormalizedValue


@dataclass(frozen=True)
class Parameter:
    name: str
    values: tuple[NormalizedValue, ...]
    weights: tuple[float, ...] | None = None

    @cached_property
    def value_set(self) -> frozenset[NormalizedValue]:
        return frozenset(self.values)

    @cached_property
    def normalized_weights(self) -> tuple[float, ...]:
        if self.weights is None:
            uniform = 1.0 / len(self.values)
            return tuple(uniform for _ in self.values)

        total = sum(self.weights)
        if total <= 0:
            uniform = 1.0 / len(self.values)
            return tuple(uniform for _ in self.values)

        return tuple(weight / total for weight in self.weights)


@dataclass(frozen=True)
class InvalidPairConstraint:
    if_assignment: Assignment
    then_not: Assignment


@dataclass(frozen=True)
class BidirectionalConstraint:
    pair: tuple[Assignment, Assignment]


@dataclass(frozen=True)
class ForwardDependencyConstraint:
    source: Assignment
    target: Assignment


@dataclass(frozen=True)
class ConditionalConstraint:
    parameter: str
    values: tuple[NormalizedValue, ...]
    parent: str
    applies_when: tuple[NormalizedValue, ...]


@dataclass(frozen=True)
class ForcedConstraint:
    assignments: tuple[Assignment, ...]


@dataclass(frozen=True)
class HigherOrderConstraint:
    if_all: tuple[Assignment, ...]
    then_not: Assignment


Constraint = (
    InvalidPairConstraint
    | BidirectionalConstraint
    | ForwardDependencyConstraint
    | ConditionalConstraint
    | ForcedConstraint
    | HigherOrderConstraint
)


@dataclass(frozen=True)
class Model:
    model_name: str
    parameters: tuple[Parameter, ...]
    constraints: tuple[Constraint, ...]
    strength: int = 2

    @cached_property
    def parameter_names(self) -> tuple[str, ...]:
        return tuple(parameter.name for parameter in self.parameters)

    @cached_property
    def parameter_lookup(self) -> dict[str, Parameter]:
        return {parameter.name: parameter for parameter in self.parameters}

    @cached_property
    def exhaustive_count(self) -> int:
        total = 1
        for parameter in self.parameters:
            total *= len(parameter.values)
        return total
