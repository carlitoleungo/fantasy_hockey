## Implementation complete — 008-cache-dir-env-var

**What I did:**
- Added `import os` to `data/cache.py`
- Changed `CACHE_DIR = ".cache"` to `CACHE_DIR = os.environ.get("CACHE_DIR", ".cache")`
- Added `import importlib` to `tests/test_cache.py`
- Added `test_cache_dir_env_var_overrides_default` test using `monkeypatch.setenv` + `importlib.reload`

**Files changed:**
- `data/cache.py` — added `import os`; made `CACHE_DIR` env-overridable (line 20, 24)
- `tests/test_cache.py` — added `import importlib` and one new test for env var behaviour

**How to verify:**
- Run `python3 -m pytest tests/test_cache.py -v` — all 26 tests should pass including `test_cache_dir_env_var_overrides_default`
- Manual check: `CACHE_DIR=/tmp/test_cache python3 -c "import data.cache; print(data.cache.CACHE_DIR)"` should print `/tmp/test_cache`
- Omitting the env var: `python3 -c "import data.cache; print(data.cache.CACHE_DIR)"` should print `.cache`

**Scope notes:**
- None — change is exactly as specified.

**Known limitations:**
- None. The `importlib.reload` pattern in the test is slightly fragile (as noted in the ticket) but the `finally` block ensures cleanup so other tests aren't contaminated.
