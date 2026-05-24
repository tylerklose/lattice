from __future__ import annotations

import random
from collections.abc import Callable
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


@dataclass(frozen=True)
class GenerationProgress:
    event: str
    scenario: int
    covered: int
    total: int
    cumulative_pct: float
    uncovered: int


ProgressCallback = Callable[[GenerationProgress], None]


def generate_covering_array(
    model: Model,
    *,
    strength: int | None = None,
    seed: int = 42,
    pool_size: int = 50,
    progress: ProgressCallback | None = None,
    max_rows: int | None = None,
    stop_after_coverage: float | None = None,
) -> GenerationResult:
    actual_strength = strength if strength is not None else model.strength
    if pool_size < 1:
        raise ValueError("`pool_size` must be at least 1.")
    if max_rows is not None and max_rows < 1:
        raise ValueError("`max_rows` must be at least 1.")
    coverage_target = _coverage_target(stop_after_coverage)

    engine = ConstraintEngine(model)
    if not engine.can_complete({}):
        raise ValueError("Model has no valid full assignments.")

    valid_tuples = enumerate_valid_tuples(model, engine, actual_strength, progress=progress)
    uncovered = set(valid_tuples)
    rows: list[tuple[int, ...]] = []
    coverage_points: list[CoveragePoint] = []
    rng = random.Random(seed)
    limit_reached = False
    if progress is not None:
        progress(
            GenerationProgress(
                event="enumerated",
                scenario=0,
                covered=0,
                total=len(valid_tuples),
                cumulative_pct=_coverage_pct(0, len(valid_tuples)),
                uncovered=len(uncovered),
            )
        )

    for forced in engine.forced_interactions:
        partial = {parameter_index: value_index for parameter_index, value_index in forced}
        row = _best_candidate_row(model, engine, partial, uncovered, actual_strength, pool_size, rng)
        if row is None or row in rows:
            continue
        newly_covered = _covered_tuples(row, actual_strength, uncovered)
        rows.append(row)
        uncovered.difference_update(newly_covered)
        covered = len(valid_tuples) - len(uncovered)
        cumulative_pct = _coverage_pct(covered, len(valid_tuples))
        coverage_points.append(
            CoveragePoint(
                scenario=len(rows),
                cumulative_pct=cumulative_pct,
            )
        )
        if progress is not None:
            progress(
                GenerationProgress(
                    event="scenario",
                    scenario=len(rows),
                    covered=covered,
                    total=len(valid_tuples),
                    cumulative_pct=cumulative_pct,
                    uncovered=len(uncovered),
                )
            )
        if _should_stop(len(rows), cumulative_pct, max_rows, coverage_target):
            limit_reached = True
            if progress is not None:
                progress(
                    GenerationProgress(
                        event="stopped",
                        scenario=len(rows),
                        covered=covered,
                        total=len(valid_tuples),
                        cumulative_pct=cumulative_pct,
                        uncovered=len(uncovered),
                    )
                )
            break

    while uncovered and not limit_reached:
        seed_tuple = min(uncovered)
        partial = {parameter_index: value_index for parameter_index, value_index in seed_tuple}
        row = _best_candidate_row(model, engine, partial, uncovered, actual_strength, pool_size, rng)
        if row is None:
            raise RuntimeError(f"Unable to complete uncovered tuple: {seed_tuple!r}")

        newly_covered = _covered_tuples(row, actual_strength, uncovered)
        rows.append(row)
        uncovered.difference_update(newly_covered)
        covered = len(valid_tuples) - len(uncovered)
        cumulative_pct = _coverage_pct(covered, len(valid_tuples))
        coverage_points.append(
            CoveragePoint(
                scenario=len(rows),
                cumulative_pct=cumulative_pct,
            )
        )
        if progress is not None:
            progress(
                GenerationProgress(
                    event="scenario",
                    scenario=len(rows),
                    covered=covered,
                    total=len(valid_tuples),
                    cumulative_pct=cumulative_pct,
                    uncovered=len(uncovered),
                )
            )
        if _should_stop(len(rows), cumulative_pct, max_rows, coverage_target):
            limit_reached = True
            if progress is not None:
                progress(
                    GenerationProgress(
                        event="stopped",
                        scenario=len(rows),
                        covered=covered,
                        total=len(valid_tuples),
                        cumulative_pct=cumulative_pct,
                        uncovered=len(uncovered),
                    )
                )
            break

    return GenerationResult(
        rows=tuple(rows),
        coverage_curve=tuple(coverage_points),
        total_valid_tuples=len(valid_tuples),
    )


def enumerate_valid_tuples(
    model: Model,
    engine: ConstraintEngine,
    strength: int,
    *,
    progress: ProgressCallback | None = None,
) -> tuple[TupleKey, ...]:
    tuples: list[TupleKey] = []
    total_candidates = _candidate_tuple_count(model, strength)
    checked = 0
    for parameter_combo in combinations(range(len(model.parameters)), strength):
        domains = [range(len(model.parameters[parameter_index].values)) for parameter_index in parameter_combo]
        for value_combo in product(*domains):
            checked += 1
            partial = {parameter_combo[offset]: value_combo[offset] for offset in range(strength)}
            if engine.can_complete(partial):
                tuples.append(tuple(zip(parameter_combo, value_combo)))
            if progress is not None and checked % 1000 == 0:
                progress(
                    GenerationProgress(
                        event="enumerating",
                        scenario=0,
                        covered=checked,
                        total=total_candidates,
                        cumulative_pct=_coverage_pct(checked, total_candidates),
                        uncovered=max(0, total_candidates - checked),
                    )
                )
    if progress is not None:
        progress(
            GenerationProgress(
                event="enumerating",
                scenario=0,
                covered=checked,
                total=total_candidates,
                cumulative_pct=_coverage_pct(checked, total_candidates),
                uncovered=max(0, total_candidates - checked),
            )
        )
    return tuple(tuples)


def _candidate_tuple_count(model: Model, strength: int) -> int:
    total = 0
    for parameter_combo in combinations(range(len(model.parameters)), strength):
        count = 1
        for parameter_index in parameter_combo:
            count *= len(model.parameters[parameter_index].values)
        total += count
    return total


def _coverage_target(stop_after_coverage: float | None) -> float | None:
    if stop_after_coverage is None:
        return None
    if not 0 < stop_after_coverage <= 100:
        raise ValueError("`stop_after_coverage` must be in the range (0, 100].")
    if stop_after_coverage >= 100:
        return None
    return stop_after_coverage


def _should_stop(
    row_count: int,
    cumulative_pct: float,
    max_rows: int | None,
    coverage_target: float | None,
) -> bool:
    if max_rows is not None and row_count >= max_rows:
        return True
    if coverage_target is not None and cumulative_pct >= coverage_target:
        return True
    return False


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
