# 008 — CACHE_DIR env var

## Summary
`data/cache.py` currently hardcodes `CACHE_DIR = ".cache"`. On Fly.io, the persistent
volume is mounted at `/data`, so the cache must write to `/data/cache/` to survive
container restarts. This one-line change makes the path env-overridable and is a
deployment blocker — without it every restart clears the parquet cache and triggers
full re-fetches from the Yahoo API.

## Acceptance criteria
- [ ] When the `CACHE_DIR` environment variable is set, `data/cache.py` uses its value
  as the cache root (e.g. `CACHE_DIR=/data/cache` → cache files write under `/data/cache/`)
- [ ] When `CACHE_DIR` is not set, the module falls back to `".cache"` (existing behaviour
  unchanged, existing tests continue to pass unmodified)

## Files likely affected
- `data/cache.py`
- `tests/test_cache.py` (add one test for the env var path; do not modify existing tests)

## Dependencies
- None

## Notes for the engineer
- `data/cache.py` line 24: change `CACHE_DIR = ".cache"` to
  `CACHE_DIR = os.environ.get("CACHE_DIR", ".cache")` and add `import os` at the top of
  the file (check if it is already imported first).
- `CACHE_DIR` is used as a module-level constant. Reading `os.environ` at import time is
  correct here — the env var is set at process startup and does not change at runtime.
- The new test should: set `CACHE_DIR` in the environment via `monkeypatch.setenv`, then
  call `importlib.reload(data.cache)` to force re-evaluation of the module-level constant,
  and assert the path used for a `cache.write()` call includes the expected prefix. Clean up
  with `importlib.reload` after the test too so other tests are not affected.
- Do not change any other logic in `cache.py`.

## Notes for QA
- Run the full test suite to confirm the 0-diff baseline (existing cache tests still pass).
- Verify the new env-var test passes.
- Manually confirm: `CACHE_DIR=/tmp/test_cache python -c "import data.cache; print(data.cache.CACHE_DIR)"`
  prints `/tmp/test_cache`.
