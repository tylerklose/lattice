from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios.json"


def import_probe_dependencies() -> tuple[Any, Any]:
    try:
        import httpx
        import requests
    except ImportError as exc:
        raise SystemExit(
            "Install optional probe dependencies first: python3 -m pip install httpx requests"
        ) from exc
    return httpx, requests


def url_for(values: dict[str, str]) -> str:
    url = "https://example.com/"
    if values["path_shape"] == "nested_path":
        url = "https://example.com/api/items"

    if values["url_query"] == "single":
        return f"{url}?page=1"
    if values["url_query"] == "multi":
        return f"{url}?page=1&s=list"
    return url


def params_for(values: dict[str, str]) -> Any | None:
    params_arg = values["params_arg"]
    if params_arg == "absent":
        return None

    if params_arg == "single":
        items = [("pid", "0")]
    elif params_arg == "multi":
        items = [("pid", "0"), ("sort", "asc")]
    elif params_arg == "overlapping_key":
        items = [("page", "2"), ("pid", "0")]
    else:  # pragma: no cover - generated scenarios are schema-validated.
        raise ValueError(f"Unknown params_arg: {params_arg}")

    return dict(items) if values["params_shape"] == "dict" else items


def httpx_url(httpx: Any, values: dict[str, str]) -> str:
    url = url_for(values)
    params = params_for(values)
    method = values["method"]

    if values["entrypoint"] == "request_object":
        request = (
            httpx.Request(method, url, params=params)
            if params is not None
            else httpx.Request(method, url)
        )
        return str(request.url)

    with httpx.Client() as client:
        request = (
            client.build_request(method, url, params=params)
            if params is not None
            else client.build_request(method, url)
        )
    return str(request.url)


def requests_url(requests: Any, values: dict[str, str]) -> str:
    request = requests.Request(
        values["method"],
        url_for(values),
        params=params_for(values),
    )
    return request.prepare().url


def main() -> int:
    httpx, requests = import_probe_dependencies()
    payload = json.loads(SCENARIOS.read_text())
    mismatches: list[tuple[int, dict[str, str], str, str]] = []

    for scenario in payload["scenarios"]:
        values = scenario["values"]
        observed = httpx_url(httpx, values)
        expected = requests_url(requests, values)
        if observed != expected:
            mismatches.append((scenario["id"], values, observed, expected))

    print(f"Scenarios: {len(payload['scenarios'])}")
    print(f"Mismatches vs requests baseline: {len(mismatches)}")

    for scenario_id, values, observed, expected in mismatches:
        print()
        print(f"Scenario {scenario_id}: {values}")
        print(f"  httpx:    {observed}")
        print(f"  requests: {expected}")

    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
