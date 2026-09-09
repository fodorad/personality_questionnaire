# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). From
2.0.0 onward, releases and version bumps are automated by
[release-please](https://github.com/googleapis/release-please) driven by Conventional
Commits.

---

## 2.0.0

### ⚠ BREAKING CHANGES

#### Negative Emotionality facets changed sign

The Anxiety, Depression and Emotional Volatility facets are now scored in the
direction their names describe. Previously they were flipped unconditionally while
the `neuroticism` domain was flipped only when `flip_neuroticism=True`, so with
default arguments the two levels of the returned dictionary contradicted each other:
`FACET[:, 9:12].mean(axis=1)` equalled `1 - OCEAN[:, 4]`.

Verified against the published scoring key — Soto & John (2017), *Big Five
Inventory-2*, APA PsycTESTS, [doi:10.1037/t64008-000](https://doi.org/10.1037/t64008-000)
— which defines reverse-keying as an item-level operation only and prescribes no
transformation after averaging. Confirmed independently against the
[LCBC-UiO `questionnaires`](https://github.com/LCBC-UiO/questionnaires) R package,
whose `bfi_sums()` reverse-codes items and then simply sums them.

Item membership was already correct: all twenty scales matched the published key
exactly, and `tests/test_bfi2.py::TestAgainstPublishedScoringKey` now pins them.

Domain scores are unchanged. To reproduce pre-2.0 numbers:

```python
bfi2(answers, legacy_facet_polarity=True)  # deprecated; removed in 3.0
```

#### Other breaking changes

- `DATA_DIR` and `PROJECT_DIR` emit a `DeprecationWarning` and no longer resolve from
  an installed wheel. They never did: `DATA_DIR` pointed at a directory beside
  `site-packages` that was never shipped, so the 1.x wheel was already broken for any
  consumer that touched it. Use `personality_questionnaire.asset()`.
- `DOMAIN_SCALES_AS_FACET_SCALES` is removed. It was never read by any code path.
- The minimum supported Python is now 3.12.

### Features

- Instruments are now data: `Item`, `Subscale` and `Questionnaire` dataclasses with a
  registry, and a single vectorised scorer shared by every instrument. Adding an
  instrument adds no arithmetic.
- The VAS-F gains its own Fatigue and Energy subscales, plus a clearly-named derived
  `Fatigue (composite)`. Previously it returned only an item-wise pre/post delta.
- New CLI subcommands: `pq list`, `pq info`, `pq run`, `pq score`. A short `pq` alias
  is installed alongside `personality-questionnaire`.
- Records carry provenance: package version, git SHA, dirty-tree flag and a hash of
  the administered instrument.
- The package ships `py.typed`.
- A theme module (`personality_questionnaire.core.theme`) holds every colour the
  project uses, shared by the repository mark, the documentation and the coming
  localhost application. Every foreground/background pairing meets WCAG AA, asserted
  in `tests/core/test_theme.py`.

### Bug Fixes

- Instrument data ships inside the wheel via `importlib.resources`.
- The VAS-F `pre` path no longer exits with status 1 on success.
- VAS-F prompts are composed in the instrument, fixing a `"while and 10 means"` typo
  and removing an index-range branch from the CLI.
- `--output-dir` now defaults to writing nothing; it previously defaulted to `data`,
  writing participant files into the repository's own tracked directory.
- CSV writers set an explicit encoding and `newline=""`, so rows are not
  double-spaced on Windows.
- CSV readers report the offending line number instead of raising an opaque numpy
  error, and no longer grow the result array quadratically.
- `pq run` no longer blocks forever when input is unavailable. Reading a closed stdin
  used to hang silently with no output; input ending mid-questionnaire now exits 4
  and names the item it stopped at, because a partial questionnaire cannot be scored.
  Piping answers in remains supported.

### Documentation

- New README, plus `docs/instruments.md`, `docs/design.md` and `docs/migration.md`,
  published to GitHub Pages via Sphinx.

### Continuous Integration

- Full pipeline added: uv, ruff, ty, coverage (90% gate), Makefile, GitHub Actions
  CI/CD, release-please, pre-commit, CodeQL, Dependabot and Codecov.

---

## 1.1.2 and earlier

Released before this changelog was kept. See the
[commit history](https://github.com/fodorad/personality_questionnaire/commits/main).
