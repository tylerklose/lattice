# HTTPX Query Parameter Merge

This example is an OSS audit case study. It documents a real HTTPX behavior that was already reported upstream, then shows how Lattice models the interaction surface around it.

The issue is not that either feature fails alone:

- a URL can contain query parameters
- a request can pass additional `params=`

The failure appears when those valid features are combined. As of 2026-05-17, building a request with both an existing URL query string and a separate `params=` argument dropped the original URL query parameters in HTTPX `main`.

```python
import httpx

request = httpx.Request(
    "GET",
    "https://example.com/path?page=1&s=list",
    params={"pid": 0},
)

print(request.url)
```

Observed:

```text
https://example.com/path?pid=0
```

The comparable `requests` behavior preserves and appends the parameters:

```text
https://example.com/path?page=1&s=list&pid=0
```

This example uses `requests` as a compatibility baseline, not as a formal URL standard. The upstream HTTPX PR also frames the proposed fix as aligning with `requests` behavior and user expectations.

## Upstream Context

This is not presented as a newly discovered HTTPX bug. It is intentionally cross-referenced to the upstream discussion:

- Issue: [encode/httpx#3621](https://github.com/encode/httpx/issues/3621)
- PR at the time this example was written: [encode/httpx#3761](https://github.com/encode/httpx/pull/3761)

At the time this example was written, the PR thread was useful context because it described the same behavior, included a fix, and had a user comment saying the issue affected a production upgrade.

HTTPX's API reference describes `params` as query parameters to include in the URL, and `Client.build_request()` as the place where request-level values are merged with client-level configuration:

- [HTTPX request API](https://www.python-httpx.org/api/#request)
- [HTTPX client API](https://www.python-httpx.org/api/#client)

## Lattice Model

The Lattice model covers the small interaction surface around the behavior:

- entrypoint: direct `Request` construction or `Client.build_request`
- method: `GET` or `POST`
- path shape: root or nested path
- URL query: absent, single parameter, or multiple parameters
- `params=` argument: absent, single parameter, multiple parameters, or an overlapping key
- `params=` shape: dict or list of tuples when `params=` is present

The schema product has 288 raw parameter combinations before constraints. Lattice generates 12 pairwise scenarios.

The important part is not the reduction alone. The generated rows exercise the valid feature interactions where a request still builds successfully but the resulting URL is wrong.

When this example was added on 2026-05-17, the probe produced six mismatches against the `requests` compatibility baseline. Each mismatch had the same shape: existing URL query parameters were dropped when a separate `params=` argument was present.

## Reproduce

Generate the scenarios:

```bash
PYTHONPATH=src python3 -m lattice generate examples/httpx-query-param-merge/model.yaml > examples/httpx-query-param-merge/scenarios.json
```

Run the optional probe against installed `httpx` and `requests`:

```bash
python3 -m pip install "httpx==0.28.1" requests
python3 examples/httpx-query-param-merge/run_probe.py
```

The pinned command reproduces the affected behavior captured here. The probe itself compares whichever installed HTTPX version is available against `requests` as a compatibility baseline. It exits non-zero when mismatches are present, which is expected for affected HTTPX versions. It is not part of Lattice's core test suite because Lattice does not depend on HTTPX or requests.
