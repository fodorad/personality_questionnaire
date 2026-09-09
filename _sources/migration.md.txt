# Migrating to 2.0

## Neuroticism facet polarity

**What changed.** The three Negative Emotionality facets — Anxiety, Depression and
Emotional Volatility — now score in the direction their names describe.

**What was wrong.** `bfi2()` flipped the `neuroticism` *domain* only when
`flip_neuroticism=True`, but flipped its three *facets* unconditionally. With the
default arguments the two levels of the returned dictionary pointed in opposite
directions:

```python
result = bfi2(answers)
result["FACET"][:, 9:12].mean(axis=1) == 1 - result["OCEAN"][:, 4]  # pre-2.0
```

On the repository's own fixture, participant 1 had `neuroticism = 0.250` alongside
Anxiety 0.688, Depression 0.750 and Emotional Volatility 0.813 — facets reported as
emotional *stability* under neurotic names.

**Why it matters.** This package produces ground truth for Big Five prediction.
Anyone who trained on `FACET` trusting the facet names had three inverted label
columns.

**How this was verified.** The change was checked against the published scoring key
before being made, not inferred from the code:

- **Soto & John (2017), Big Five Inventory-2**, APA PsycTESTS
  ([doi:10.1037/t64008-000](https://doi.org/10.1037/t64008-000)). The key gives item
  membership per scale, marking false-keyed items with "R" — for example *Anxiety:
  4R, 19, 34, 49R*. All twenty of this package's scales match it exactly, and
  `tests/test_bfi2.py::TestAgainstPublishedScoringKey` pins them so they cannot
  drift. Crucially, the key prescribes **no transformation after averaging**: it
  contains no instruction to flip, invert or subtract any scale, Negative
  Emotionality included.
- **An independent implementation**, the
  [LCBC-UiO `questionnaires`](https://github.com/LCBC-UiO/questionnaires) R package,
  agrees. Its `bfi_sums()` reverse-codes the R-marked items and then does exactly
  `rowSums(tmp)` — no post-aggregation flip for the Negative Emotionality domain or
  for the Anxiety, Depression and Emotional Volatility facets.

So reverse-keying in the BFI-2 is an **item-level** operation only. The pre-2.0 code
applied a second, scale-level flip to three facets that the instrument does not
define, which is what made them contradict their own domain.

**What to do.**

| You want | Call |
| --- | --- |
| Correct, consistent scores | `bfi2(answers)` |
| Neuroticism as Emotional Stability, both levels | `bfi2(answers, flip_neuroticism=True)` |
| Exact pre-2.0 numbers | `bfi2(answers, legacy_facet_polarity=True)` |

`legacy_facet_polarity` warns on use and is scheduled for removal in 3.0. Domain
scores are **unchanged** in every case; only the three facet columns move.

## `DATA_DIR` and `PROJECT_DIR`

Both now emit a `DeprecationWarning`, and neither resolves usefully from an installed
wheel — `DATA_DIR` pointed at a `data` directory beside `site-packages` that was
never shipped, so any installed-package use was already broken.

```python
import personality_questionnaire as pq

pq.asset("bfi-2_questionnaire.tsv").read_text()
```

## `DOMAIN_SCALES_AS_FACET_SCALES`

Removed. It was never read by any code path, including the tests.

## The command line

The flat form still works and prints a deprecation notice:

```bash
personality-questionnaire --questionnaire bfi2 --participant_id P01   # still works
pq run bfi2 --participant P01                                         # preferred
```

Two changes worth noting: `--output-dir` now defaults to writing **nothing** (the
old default wrote participant files into the repository's tracked `data/`), and the
VAS-F `pre` path no longer exits with status 1 on success.

## Unchanged

`bfi2()`, `bfi2_trait()`, `flip_trait_dimension()`, `vasf()`, `DOMAIN_SCALES`,
`FACET_SCALES`, `ANSWER`, `BFI2_QUESTIONNAIRE`, `VASF_QUESTIONNAIRE` and
`ANSWER_DIMS` all keep their exact signatures and return values. `DOMAIN_SCALES` and
`FACET_SCALES` still use the `"5R"` item-key notation, now generated from the
registry rather than duplicated.
