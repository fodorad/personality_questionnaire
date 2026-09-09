# Design decisions

## Instruments are data, not code

Before 2.0 each questionnaire carried its own scoring function. `bfi2()` held a
five-branch reverse-keying chain, a per-participant Python loop, and a hardcoded
`len(answer) == 60`; `vasf()` was a bare subtraction with no subscales at all. Adding
a third instrument meant writing a third scorer.

Now an instrument is a {class}`~personality_questionnaire.registry.Questionnaire`
value and all arithmetic lives in {mod}`personality_questionnaire.scoring`. The
before/after on the reverse-keying alone:

```python
# before -- one instrument, one scale, one participant at a time
def _R(value):
    if value == 1:
        return 5
    elif value == 2:
        return 4
    elif value == 4:
        return 2
    elif value == 5:
        return 1
    else:
        return value


# after -- any instrument, any range, whole cohort
def reverse(values, minimum, maximum):
    return (minimum + maximum) - values
```

## Reverse-keying belongs to the subscale

The obvious implementation builds a per-item boolean mask and reflects those columns
once. That is wrong, and the VAS-F proves it: items 6–10 are forward-keyed in
`Energy` and reverse-keyed in `Fatigue (composite)`. A per-item mask has to pick one,
and whichever it picks corrupts the other scale.

Instead the reflection is folded into the weight matrix. A forward item contributes
`value / k`; a reverse-keyed one contributes `(min + max - value) / k`, which splits
into a weight of `-1 / k` and a constant gathered into an offset vector. Scoring is
then `answers @ weights + offsets` — one matrix multiplication for every subscale of
every level, with per-column keying that a mask cannot express.

## Hierarchy is recorded, not computed

The BFI-2's domains could be composed from their facets. They are not: each domain
lists its own twelve item numbers, and `Subscale.parent` exists only to draw the tree
in documentation and the UI. Composition would add a code path and change no number.

## Polarity is data

Every subscale carries a `higher_is` string. This is a direct response to the bug
fixed in 2.0, where three facets were named for one construct and scored as its
opposite: with direction recorded next to the items, a reader never has to infer it
from a name, and a reviewer can see a contradiction without running anything.

## Scores are computed from raw responses

{attr}`~personality_questionnaire.scoring.ScoreResult.keyed` reports responses as a
reader of a single scale would see them, but scoring never consumes it — only the
per-subscale weights are authoritative. Keeping the presentation view and the
arithmetic separate is what makes the per-column keying above safe.

## Diagnostics and output are different streams

Participant prompts and scores are the program's output and go to stdout. Everything
else — which database is in use, what was written, deprecation notices — is a
diagnostic and goes to `logging` on stderr, so `pq export | jq` works.

The logging handler is rebuilt on each CLI invocation rather than left to
`logging.basicConfig`, which binds `sys.stderr` once and ignores later calls. Without
that, a redirected stream silently receives nothing — which is how the first version
of the CLI tests passed while asserting on empty strings.
