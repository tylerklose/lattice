# Case Studies

Case studies are where Lattice should earn its keep. A good case study is not just a schema and generated rows. It should include a public behavior surface, a baseline or upstream reference, a reproducible probe, and a plain-language explanation of what the generated rows exposed.

The framing matters:

- Lattice does not claim ownership of upstream bugs.
- Lattice does not turn a compatibility baseline into a formal standard.
- Lattice supplies a compact, deterministic way to exercise valid feature interactions that are easy to miss by hand.

## HTTPX Query Parameter Merge

Reference example:

- [examples/httpx-query-param-merge/README.md](../examples/httpx-query-param-merge/README.md)
- [examples/httpx-query-param-merge/model.yaml](../examples/httpx-query-param-merge/model.yaml)
- [examples/httpx-query-param-merge/scenarios.json](../examples/httpx-query-param-merge/scenarios.json)
- [examples/httpx-query-param-merge/run_probe.py](../examples/httpx-query-param-merge/run_probe.py)

Upstream context:

- [encode/httpx#3621](https://github.com/encode/httpx/issues/3621)
- [encode/httpx#3761](https://github.com/encode/httpx/pull/3761)

The behavior surface is small and concrete:

- a URL may already contain query parameters
- a request may also pass `params=`
- HTTPX exposes both direct `Request` construction and `Client.build_request`
- `params=` may be represented as a dict or a list of tuples
- keys may be distinct or overlapping

Each feature is valid by itself. The interesting behavior appears when the features are combined. As of 2026-05-17, affected HTTPX versions dropped existing URL query parameters when a separate `params=` argument was present.

Lattice modeled that surface as six parameters:

```yaml
entrypoint: [request_object, client_build_request]
method: [GET, POST]
path_shape: [root_path, nested_path]
url_query: [absent, single, multi]
params_arg: [absent, single, multi, overlapping_key]
params_shape: [dict, list_tuples] # conditional on params_arg being present
```

That schema has 288 raw parameter combinations before constraints. Lattice generated 12 pairwise scenarios. The optional probe compared those rows against `requests` as a compatibility baseline and produced six mismatches for affected HTTPX versions.

The useful takeaway is not "Lattice found a new bug in HTTPX." The useful takeaway is that a known, production-impacting interaction issue can be described as a small constrained surface, generated deterministically, and reproduced without hand-picking only the one known failing call.

That is the shape to look for in future OSS audits: independently valid features, a public reference point, and a wrong output that appears only when the features meet.
