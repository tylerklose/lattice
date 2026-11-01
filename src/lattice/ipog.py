"""Scenario generation, backed by the Rust engine (`lattice._engine`).

The engine builds a covering array greedily, choosing each row from several
candidates, then shrinks it with tabu search, and returns the rows ordered so
each adds the most new coverage. This module turns a parsed model into the
engine's input (constraints compiled to invalid pairs, requirements,
higher-order exclusions and forced interactions), then applies `max_rows` and
`stop_after_coverage` by cutting the ordered rows short. The Ruby gem calls the
same engine the same way, so both give identical rows.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from lattice import _engine
from lattice.constraints import ConstraintEngine
from lattice.model import Model

DEFAULT_CANDIDATES = 16
SHRINK_STEPS = 1_000_000
PATIENCE = 10_000


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
    pool_size: int = DEFAULT_CANDIDATES,
    progress: ProgressCallback | None = None,
    max_rows: int | None = None,
    stop_after_coverage: float | None = None,
) -> GenerationResult:
    """`pool_size` is the number of candidate rows built per greedy step."""
    actual_strength = strength if strength is not None else model.strength
    if pool_size < 1:
        raise ValueError("`pool_size` must be at least 1.")
    if max_rows is not None and max_rows < 1:
        raise ValueError("`max_rows` must be at least 1.")
    coverage_target = _coverage_target(stop_after_coverage)

    engine = ConstraintEngine(model)
    if not engine.can_complete({}):
        raise ValueError("Model has no valid full assignments.")

    rows, new_coverage, total = _engine.generate(
        [len(parameter.values) for parameter in model.parameters],
        [list(parameter.normalized_weights) for parameter in model.parameters],
        actual_strength,
        _pairs(engine.invalid_pairs),
        _pairs(engine.requires),
        [(list(antecedents), forbidden) for antecedents, forbidden in engine.higher_order],
        [list(forced) for forced in engine.forced_interactions],
        seed=seed % 2**64,
        candidates=pool_size,
        shrink_steps=SHRINK_STEPS,
        patience=PATIENCE,
    )

    _report(progress, "enumerated", 0, 0, total)
    kept: list[tuple[int, ...]] = []
    curve: list[CoveragePoint] = []
    covered = 0
    for row, gained in zip(rows, new_coverage):
        kept.append(tuple(row))
        covered += gained
        cumulative_pct = _coverage_pct(covered, total)
        curve.append(CoveragePoint(scenario=len(kept), cumulative_pct=cumulative_pct))
        _report(progress, "scenario", len(kept), covered, total)
        if _should_stop(len(kept), cumulative_pct, max_rows, coverage_target):
            if len(kept) < len(rows):
                _report(progress, "stopped", len(kept), covered, total)
            break

    return GenerationResult(rows=tuple(kept), coverage_curve=tuple(curve), total_valid_tuples=total)


def _pairs(table) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    return sorted((source, target) for source, targets in table.items() for target in targets)


def _report(progress: ProgressCallback | None, event: str, scenario: int, covered: int, total: int) -> None:
    if progress is None:
        return
    progress(
        GenerationProgress(
            event=event,
            scenario=scenario,
            covered=covered,
            total=total,
            cumulative_pct=_coverage_pct(covered, total),
            uncovered=total - covered,
        )
    )


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


def _coverage_pct(covered_count: int, total_count: int) -> float:
    if total_count == 0:
        return 100.0
    return round((covered_count / total_count) * 100, 1)
