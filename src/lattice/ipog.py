from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations, product

from lattice.constraints import ConstraintEngine
from lattice.model import Model


TupleKey = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class CoveragePoint:
    scenario: int
    cumulative_pct: float


@dataclass(frozen=True)
class GenerationResult:
    rows: tuple[tuple[int, ...], ...]
    coverage_curve: tuple[CoveragePoint, ...]
    total_valid_tuples: int


def generate_covering_array(
    model: Model,
    *,
    strength: int | None = None,
    seed: int = 42,
    pool_size: int = 50,
) -> GenerationResult:
    actual_strength = strength if strength is not None else model.strength
    if pool_size < 1:
        raise ValueError("`pool_size` must be at least 1.")

    engine = ConstraintEngine(model)
    if not engine.can_complete({}):
        raise ValueError("Model has no valid full assignments.")

    valid_tuples = enumerate_valid_tuples(model, engine, actual_strength)
    uncovered = set(valid_tuples)
    rows: list[tuple[int, ...]] = []
    coverage_points: list[CoveragePoint] = []
    rng = random.Random(seed)

    for forced in engine.forced_interactions:
        partial = {parameter_index: value_index for parameter_index, value_index in forced}
        row = _best_candidate_row(model, engine, partial, uncovered, actual_strength, pool_size, rng)
        if row is None or row in rows:
            continue
        newly_covered = _covered_tuples(row, actual_strength, uncovered)
        rows.append(row)
        uncovered.difference_update(newly_covered)
        coverage_points.append(
            CoveragePoint(
                scenario=len(rows),
                cumulative_pct=_coverage_pct(len(valid_tuples) - len(uncovered), len(valid_tuples)),
            )
        )

    while uncovered:
        seed_tuple = min(uncovered)
        partial = {parameter_index: value_index for parameter_index, value_index in seed_tuple}
        row = _best_candidate_row(model, engine, partial, uncovered, actual_strength, pool_size, rng)
        if row is None:
            raise RuntimeError(f"Unable to complete uncovered tuple: {seed_tuple!r}")

        newly_covered = _covered_tuples(row, actual_strength, uncovered)
        rows.append(row)
        uncovered.difference_update(newly_covered)
        coverage_points.append(
            CoveragePoint(
                scenario=len(rows),
                cumulative_pct=_coverage_pct(len(valid_tuples) - len(uncovered), len(valid_tuples)),
            )
        )

    return GenerationResult(
        rows=tuple(rows),
        coverage_curve=tuple(coverage_points),
        total_valid_tuples=len(valid_tuples),
    )


def enumerate_valid_tuples(model: Model, engine: ConstraintEngine, strength: int) -> tuple[TupleKey, ...]:
    tuples: list[TupleKey] = []
    for parameter_combo in combinations(range(len(model.parameters)), strength):
        domains = [range(len(model.parameters[parameter_index].values)) for parameter_index in parameter_combo]
        for value_combo in product(*domains):
            partial = {parameter_combo[offset]: value_combo[offset] for offset in range(strength)}
            if engine.can_complete(partial):
                tuples.append(tuple(zip(parameter_combo, value_combo)))
    return tuple(tuples)


def _best_candidate_row(
    model: Model,
    engine: ConstraintEngine,
    partial: dict[int, int],
    uncovered: set[TupleKey],
    strength: int,
    pool_size: int,
    rng: random.Random,
) -> tuple[int, ...] | None:
    candidates: dict[tuple[int, ...], tuple[int, float]] = {}
    deterministic = engine.complete_assignment(partial, rng=None)
    if deterministic is not None:
        candidates[deterministic] = _score_row(model, deterministic, uncovered, strength)

    for _ in range(pool_size - 1):
        attempt_rng = random.Random(rng.getrandbits(64))
        candidate = engine.complete_assignment(partial, rng=attempt_rng)
        if candidate is None:
            continue
        score = _score_row(model, candidate, uncovered, strength)
        previous = candidates.get(candidate)
        if previous is None or score > previous:
            candidates[candidate] = score

    if not candidates:
        return None

    return max(candidates.items(), key=lambda item: (item[1][0], item[1][1], _reverse_lex(item[0])))[0]


def _score_row(
    model: Model,
    row: tuple[int, ...],
    uncovered: set[TupleKey],
    strength: int,
) -> tuple[int, float]:
    newly_covered = len(_covered_tuples(row, strength, uncovered))
    weight_score = sum(
        model.parameters[parameter_index].normalized_weights[value_index]
        for parameter_index, value_index in enumerate(row)
    )
    return newly_covered, weight_score


def _covered_tuples(row: tuple[int, ...], strength: int, candidate_tuples: set[TupleKey]) -> set[TupleKey]:
    covered: set[TupleKey] = set()
    for parameter_combo in combinations(range(len(row)), strength):
        tuple_key = tuple((parameter_index, row[parameter_index]) for parameter_index in parameter_combo)
        if tuple_key in candidate_tuples:
            covered.add(tuple_key)
    return covered


def _coverage_pct(covered_count: int, total_count: int) -> float:
    if total_count == 0:
        return 100.0
    return round((covered_count / total_count) * 100, 1)


def _reverse_lex(row: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(-value for value in row)
