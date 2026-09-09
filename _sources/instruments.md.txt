# Instruments

Every shipped instrument is a {class}`~personality_questionnaire.registry.Questionnaire`
value. This page records what each one measures, how it is scored, and where it comes
from.

## Big Five Inventory-2 (`bfi2`)

Sixty items on a 1–5 agreement scale, completing the stem *"I am someone who…"*.

The BFI-2 is hierarchical: five domains, each resolved by three facets of four items.
Both levels are declared as sibling subscales over the same item pool, so a single
pass scores all twenty scales.

| Domain | Facets |
| --- | --- |
| Openness | Intellectual Curiosity, Aesthetic Sensitivity, Creative Imagination |
| Conscientiousness | Organization, Productiveness, Responsibility |
| Extraversion | Sociability, Assertiveness, Energy Level |
| Agreeableness | Compassion, Respectfulness, Trust |
| Neuroticism | Anxiety, Depression, Emotional Volatility |

Domains are emitted in OCEAN order, matching what the package has returned since
1.0.0 and what [PersonalityLinMulT](https://github.com/fodorad/PersonalityLinMulT)
expects.

:::{note}
The three Negative Emotionality facets score in the direction their names describe.
Before 2.0 they were flipped unconditionally while the domain was not; see
[migration](migration.md).
:::

> Soto, C. J., & John, O. P. (2017). The next Big Five Inventory (BFI-2): Developing
> and assessing a hierarchical model with 15 facets to enhance bandwidth, fidelity,
> and predictive power. *Journal of Personality and Social Psychology, 113*, 117–143.

Free for research purposes; see the authors' terms.

## BFI-2 Extra-Short Form (`bfi2-xs`)

Fifteen items on the same 1–5 agreement scale as the BFI-2, three per domain, one
drawn from each of that domain's facets. Retains roughly 80% of the full form's
domain-level reliability.

**Domains only.** With one item per facet the form cannot support facet scores, and
the authors say so explicitly.

Every item is borrowed from the BFI-2 **by reference** rather than retyped, so a
wording correction in the parent propagates automatically. Only the item-number
mapping is local, and the reverse keys are derived from the parent rather than
transcribed — polarity is a property of an item's wording, so a borrowed item keeps
the keying its source earned. A test checks the derived result against the published
key regardless.

Note that the numbering is the short form's own: item 1 of the BFI-2-XS is item 16 of
the BFI-2.

:::{note}
Short-form scores are **not** interchangeable with full-form scores item for item.
The BFI-2 reverses exactly half of each twelve-item domain, so a constant response
collapses to the midpoint; a three-item domain reverses one or two of three and
cannot balance. Both forms agree at the scale midpoint, and diverge away from it.
:::

> Soto, C. J., & John, O. P. (2017). Short and extra-short forms of the Big Five
> Inventory-2: The BFI-2-S and BFI-2-XS. *Journal of Research in Personality, 68*,
> 69–81.

## Big Five Inventory-10 (`bfi10`)

Ten items, two per domain, for settings under severe time pressure.

Unlike the BFI-2-XS, the BFI-10 is **not** a subset of the BFI-2. It descends from
the older BFI-44, so its wording differs, its stem differs ("I see myself as someone
who…" rather than "I am someone who…"), and its midpoint label differs ("Neither
agree nor disagree" rather than "Neutral; no opinion"). Its items are therefore
native and carry no `source_number`. Published labels are reproduced per form rather
than harmonised across them.

Each domain deliberately pairs one positively and one negatively keyed item, so
exactly five of the ten items are reversed and any uniform response cancels to the
midpoint.

| Domain | Items |
| --- | --- |
| Extraversion | 1R, 6 |
| Agreeableness | 2, 7R |
| Conscientiousness | 3R, 8 |
| Neuroticism | 4R, 9 |
| Openness | 5R, 10 |

> Rammstedt, B., & John, O. P. (2007). Measuring personality in one minute or less: A
> 10-item short version of the Big Five Inventory in English and German. *Journal of
> Research in Personality, 41*, 203–212.

## Visual Analogue Scale to Evaluate Fatigue Severity (`vasf`)

Eighteen items, each a line from 0 to 10 between two named anchors.

The VAS-F is administered twice — before and after some intervention — and its
primary result is the change. It is therefore marked `paired`; use
{func}`~personality_questionnaire.scoring.delta`.

| Subscale | Items | Direction |
| --- | --- | --- |
| Fatigue | 1–5, 11–18 | higher is more fatigued |
| Energy | 6–10 | higher is more energetic |
| Fatigue (composite) | all 18, energy items reversed | higher is more fatigued |

`Fatigue` and `Energy` are the instrument's own two scales, each scored in its own
direction. `Fatigue (composite)` reverse-keys the energy items to give a single
number across all eighteen; it is a modelling convenience rather than part of Lee et
al.'s scoring, which is why it is named explicitly and tagged at its own level.

Anchor word order differs between item types — *"not at all tired"* but *"keeping my
eyes open is no effort at all"* — so each item carries its finished `prompt`. Before
2.0 the caller reassembled these from two dictionaries behind an index-range branch.

> Lee, K. A., Hicks, G., & Nino-Murcia, G. (1991). Validity and reliability of a
> scale to assess fatigue. *Psychiatry Research, 36*(3), 291–298.

## Choosing a Big Five form

All three report the same five domains, in the same order, on the same `[0, 1]`
scale, so they are interchangeable to downstream code.

| | Items | Facets | Use when |
| --- | --- | --- | --- |
| `bfi2` | 60 | yes | Personality is a primary variable |
| `bfi2-xs` | 15 | no | Domain scores suffice and BFI-2 comparability matters |
| `bfi10` | 10 | no | Time is severely constrained |

## Adding an instrument

Adding one is adding data. Declare the items and subscales, call
{func}`~personality_questionnaire.registry.register`, and import the module from
`instruments/__init__.py`. Registration validates the definition, so a subscale that
references a missing item or reverse-keys an item it does not contain fails at import
— and therefore in CI — rather than producing a plausible wrong score.
