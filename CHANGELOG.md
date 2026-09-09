# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). From
2.0.0 onward, releases and version bumps are automated by
[release-please](https://github.com/googleapis/release-please) driven by Conventional
Commits.

---

## [2.4.0](https://github.com/fodorad/personality_questionnaire/compare/v2.3.0...v2.4.0) (2026-09-09)


### Features

* **ui:** add a five-tab NiceGUI application ([#21](https://github.com/fodorad/personality_questionnaire/issues/21)) ([6b675f2](https://github.com/fodorad/personality_questionnaire/commit/6b675f28da2568ea64d31a51f3ddb403f431628a))

## [2.3.0](https://github.com/fodorad/personality_questionnaire/compare/v2.2.0...v2.3.0) (2026-09-09)


### Features

* **cli:** add records and export commands, and persist completed runs ([341974b](https://github.com/fodorad/personality_questionnaire/commit/341974b509eb556cae94efe798f9b1c4bcf9b7fa))
* **db:** persist records with reproducibility metadata ([#17](https://github.com/fodorad/personality_questionnaire/issues/17)) ([341974b](https://github.com/fodorad/personality_questionnaire/commit/341974b509eb556cae94efe798f9b1c4bcf9b7fa))


### Bug Fixes

* **cli:** stop treating --questionnaire on a subcommand as the legacy form ([341974b](https://github.com/fodorad/personality_questionnaire/commit/341974b509eb556cae94efe798f9b1c4bcf9b7fa))


### Documentation

* document the record schema, its design decisions and the export shapes ([341974b](https://github.com/fodorad/personality_questionnaire/commit/341974b509eb556cae94efe798f9b1c4bcf9b7fa))

## [2.2.0](https://github.com/fodorad/personality_questionnaire/compare/v2.1.0...v2.2.0) (2026-09-09)


### Features

* **instruments:** add the PANAS affect schedule ([#15](https://github.com/fodorad/personality_questionnaire/issues/15)) ([b395cda](https://github.com/fodorad/personality_questionnaire/commit/b395cda6d7c52704cf0dcb2db912f488da1ce553))
* **scoring:** let a subscale declare how it aggregates its items ([b395cda](https://github.com/fodorad/personality_questionnaire/commit/b395cda6d7c52704cf0dcb2db912f488da1ce553))


### Bug Fixes

* **scoring:** report a clean zero at the floor of a normalised scale ([b395cda](https://github.com/fodorad/personality_questionnaire/commit/b395cda6d7c52704cf0dcb2db912f488da1ce553))


### Documentation

* document the PANAS, its two reported forms and its time frame ([b395cda](https://github.com/fodorad/personality_questionnaire/commit/b395cda6d7c52704cf0dcb2db912f488da1ce553))

## [2.1.0](https://github.com/fodorad/personality_questionnaire/compare/v2.0.0...v2.1.0) (2026-09-09)


### Features

* **instruments:** add the BFI-2-XS and BFI-10 short forms ([#13](https://github.com/fodorad/personality_questionnaire/issues/13)) ([eb995e0](https://github.com/fodorad/personality_questionnaire/commit/eb995e0f4b0fadf3f118ca32ab7fb06bff117435))


### Documentation

* document the short forms and when to choose each Big Five form ([eb995e0](https://github.com/fodorad/personality_questionnaire/commit/eb995e0f4b0fadf3f118ca32ab7fb06bff117435))

## [2.0.0](https://github.com/fodorad/personality_questionnaire/compare/v1.1.2...v2.0.0) (2026-09-09)


### ⚠ BREAKING CHANGES

* restructure onto a questionnaire registry and correct BFI-2 scoring ([#1](https://github.com/fodorad/personality_questionnaire/issues/1))
* the three Negative Emotionality facets change sign. Pass legacy_facet_polarity=True to bfi2() to restore pre-2.0 values; domain scores are unaffected. DATA_DIR and PROJECT_DIR now warn and do not resolve from an installed wheel -- DATA_DIR pointed at a directory beside site-packages that was never shipped, so the 1.x wheel was already broken for any consumer that touched it; use personality_questionnaire.asset() instead. DOMAIN_SCALES_AS_FACET_SCALES is removed, having never been read by any code path. The minimum supported Python is now 3.12. Every other published name -- bfi2(), bfi2_trait(), flip_trait_dimension(), vasf(), DOMAIN_SCALES, FACET_SCALES, ANSWER, BFI2_QUESTIONNAIRE, VASF_QUESTIONNAIRE and ANSWER_DIMS -- keeps its exact signature and return value.

### Features

* **cli:** replace the --questionnaire flag with list, info, run and score subcommands ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **core:** add a theme module with a WCAG AA verified palette and repository mark ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **instruments:** give the VAS-F its own Fatigue and Energy subscales ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* record package version, git SHA and instrument hash with every scoring run ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* restructure onto a questionnaire registry and correct BFI-2 scoring ([#1](https://github.com/fodorad/personality_questionnaire/issues/1)) ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* ship py.typed so downstream type checkers see the annotations ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))


### Bug Fixes

* **cli:** default --output-dir to writing nothing instead of the tracked data directory ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **cli:** exit rather than block forever when input ends mid-questionnaire ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **cli:** stop returning a failure exit code from the VAS-F pre path ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **instruments:** compose VAS-F prompts in the instrument, correcting an anchor typo ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **io:** report the offending line number instead of raising an opaque numpy error ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* **io:** set an explicit encoding and newline so CSV rows are not double-spaced ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* ship instrument data inside the wheel via importlib.resources ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))


### Documentation

* add a README, instrument reference, design notes and migration guide ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* add the coverage badge and correct the Python badge to 3.12-3.14 ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))
* publish the Sphinx site to GitHub Pages ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))


### Build System

* raise the minimum supported Python to 3.12 ([2179b13](https://github.com/fodorad/personality_questionnaire/commit/2179b138047505d0ede5bd9b6d0cddff614b5223))

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
