from __future__ import annotations

import csv
import io
import json

from lattice.ipog import GenerationResult
from lattice.model import Model


def render_output(model: Model, result: GenerationResult, *, output_format: str, seed: int) -> str:
    if output_format == "table":
        return format_table(model, result)
    if output_format == "json":
        return format_json(model, result, seed=seed)
    if output_format == "csv":
        return format_csv(model, result)
    if output_format == "summary":
        return format_summary(model, result)
    raise ValueError(f"Unknown format `{output_format}`.")


def format_table(model: Model, result: GenerationResult) -> str:
    rows = _named_rows(model, result)
    headers = ["#"] + list(model.parameter_names)
    body = [[str(index + 1), *[row[name] for name in model.parameter_names]] for index, row in enumerate(rows)]
    widths = [
        max(len(headers[column]), *(len(record[column]) for record in body)) if body else len(headers[column])
        for column in range(len(headers))
    ]

    lines = [_headline(model, result), ""]
    lines.extend(_milestone_lines(result))
    lines.append("")
    lines.append(
        " | ".join(
            headers[column].rjust(widths[column]) if column == 0 else headers[column].ljust(widths[column])
            for column in range(len(headers))
        )
    )
    lines.append("-|-".join("-" * width for width in widths))

    for record in body:
        lines.append(
            " | ".join(
                record[column].rjust(widths[column]) if column == 0 else record[column].ljust(widths[column])
                for column in range(len(record))
            )
        )
    return "\n".join(lines)


def format_summary(model: Model, result: GenerationResult) -> str:
    lines = [_headline(model, result), ""]
    lines.extend(_milestone_lines(result))
    return "\n".join(lines)


def format_json(model: Model, result: GenerationResult, *, seed: int) -> str:
    payload = {
        "meta": {
            "model_name": model.model_name,
            "strength": model.strength,
            "test_count": len(result.rows),
            "exhaustive_count": model.exhaustive_count,
            "reduction": _reduction_label(model.exhaustive_count, len(result.rows)),
            "coverage": f"{result.coverage_curve[-1].cumulative_pct:.1f}%" if result.coverage_curve else "0.0%",
            "seed": seed,
        },
        "coverage_curve": [
            {
                "scenario": point.scenario,
                "cumulative_pct": point.cumulative_pct,
            }
            for point in result.coverage_curve
        ],
        "scenarios": [
            {
                "id": index + 1,
                "values": {name: row[name] for name in model.parameter_names},
            }
            for index, row in enumerate(_named_rows(model, result))
        ],
    }
    return json.dumps(payload, indent=2)


def format_csv(model: Model, result: GenerationResult) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(model.parameter_names)
    for row in _named_rows(model, result):
        writer.writerow([row[name] for name in model.parameter_names])
    return buffer.getvalue().strip()


def _headline(model: Model, result: GenerationResult) -> str:
    return f"Lattice — {len(result.rows)} scenarios (from {model.exhaustive_count:,} possible)"


def _milestone_lines(result: GenerationResult) -> list[str]:
    milestones: list[str] = []
    for threshold in (50.0, 75.0, 90.0, 100.0):
        scenario = next(
            (point.scenario for point in result.coverage_curve if point.cumulative_pct >= threshold),
            None,
        )
        if scenario is not None:
            milestones.append(f"  {int(threshold)}% coverage at scenario #{scenario}")
    return milestones


def _named_rows(model: Model, result: GenerationResult) -> list[dict[str, str]]:
    named_rows: list[dict[str, str]] = []
    for row in result.rows:
        named_rows.append(
            {
                parameter.name: parameter.values[row[index]]
                for index, parameter in enumerate(model.parameters)
            }
        )
    return named_rows


def _reduction_label(exhaustive_count: int, scenario_count: int) -> str:
    if scenario_count == 0:
        return "inf"
    reduction = exhaustive_count / scenario_count
    if abs(reduction - round(reduction)) < 1e-9:
        return f"{int(round(reduction))}x"
    return f"{reduction:.1f}x"
