# Contributing

## Quick start

```bash
uv sync --all-extras
uv run pre-commit install   # optional: runs ruff before every commit
```

## Development workflow

1. **Branch from `main`** — `feat/*`, `fix/*`, `ci/*` or `docs/*`.
2. **Make focused changes.**
3. **Write or update tests** in `tests/`, mirroring the package layout.
4. **Run the checks** before pushing:
   ```bash
   make fix      # format and autofix
   make check    # lint, type-check, tests, docs -- mirrors CI
   make check-ci # the same in a throwaway venv built exactly like CI's
   ```
5. **Open a pull request** against `main`.

## Adding an instrument

An instrument is data. Add a module under `personality_questionnaire/instruments/`
declaring its items and subscales, call `register()`, and import it from
`instruments/__init__.py`. Do **not** add a scoring function: if an instrument needs
arithmetic that `scoring.py` cannot express, that is a gap in the scorer, and fixing
it there keeps every other instrument working the same way.

`register()` validates the definition, so a subscale referencing a missing item fails
at import — and therefore in CI.

## Commit messages

Conventional Commits; release-please derives the version from them.

| Prefix | Meaning | Bump |
| --- | --- | --- |
| `fix:` | Bug fix | Patch |
| `feat:` | New feature or instrument | Minor |
| `feat!:` / `BREAKING CHANGE:` | Incompatible change | Major |
| `docs:` / `test:` / `refactor:` / `chore:` / `ci:` | Everything else | None |

## Release process

1. Merge Conventional-Commit PRs into `main`.
2. release-please opens or updates a release PR, updating `CHANGELOG.md` and the
   version in `pyproject.toml`.
3. Merging that PR creates the tag and the GitHub Release.
4. The tag triggers CD, which builds the wheel and publishes to PyPI.

Never publish manually and never hand-pick a version.

## Code style

- **Formatter and linter**: ruff — `make fix`
- **Type checker**: ty — `make type-check`
- **Line length**: 100
- **Docstrings**: Google style, on every public module, class and function

## Tests

`unittest` under `coverage`, not pytest. The gate is 80%; the suite currently sits
well above it.

Coverage omits nothing that holds logic. Where a layer is hard to test directly —
the UI shell, for instance — the logic is *extracted* into a tested module rather
than the file being excluded. "Omitted because extracted, not because hard" is the
standard here.

Slow checks are opt-in locally and always on in CI:

```bash
RUN_PACKAGING_TESTS=1 make test-full   # builds a real wheel and installs it
```
