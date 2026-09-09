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

## Reliability is computed per subscale, not from `ScoreResult.keyed`

Cronbach's alpha needs items pointing the same direction, so it looks like it should
reuse {attr}`~personality_questionnaire.scoring.ScoreResult.keyed` — which already
reflects every reverse-keyed item. It cannot: `keyed` applies one global mask, built
from every subscale's reverse set, and the same reasoning that rules it out for
scoring (see "Reverse-keying belongs to the subscale" above) applies here too. An
item that is forward-keyed in one subscale and reverse-keyed in another would be
flipped for both, corrupting whichever one didn't ask for it.

`personality_questionnaire.analysis.subscale_reliability` instead re-derives keying
per subscale, exactly as `scoring.score` does internally, before computing alpha and
item-total correlations on that subscale's own items alone. The cost is repeating a
few lines of masking logic rather than reusing a shared array; the alternative is a
diagnostic that is silently wrong for any instrument where one item serves two
scales with opposite polarity.

## The demo is a separate application, not a flag

`demo/` is its own top-level package rather than a `--demo` flag on the Lab
application. A flag means the record-writing code path *ships* to a public host
and is disabled by a boolean — one bad conditional away from persisting a
stranger's responses on a machine nobody administers. A separate package means
there is no `personality_questionnaire.db` import anywhere in `demo/` to
misconfigure: `tests/demo_app/test_isolation.py` walks every file in the package with
`ast` and fails if one ever imports the database layer, NiceGUI, or SQLAlchemy,
so the boundary is enforced by CI rather than by discipline.

The two applications share only `registry` and `scoring` — pure, stateless
modules with no notion of a database connection to accidentally reach for.

## A second, hand-ported demo exists because Gradio Lite is broken

`demo-react/` reimplements the same instrument-fill-evaluate-plot flow as
`demo/` in TypeScript, deployed to a free Hugging Face static Space. It exists
alongside `demo/`, not instead of it, because of a hosting constraint rather
than a technical one: Hugging Face's free personal-account tier does not
allow a Docker or native-Gradio Space at all (both require a paid PRO plan),
except for up to two Gradio Spaces running on ZeroGPU hardware -- a GPU-hosting
mechanism this app has no use for, since every instrument scores and plots on
CPU.

The natural fix looked like Gradio Lite (`@gradio/lite`): it runs the actual
`demo/app.py` client-side via Pyodide, so it would need no second
implementation at all, and it deploys as exactly the free static Space this
needed. Tried directly against the official example from Hugging Face's own
`gradio-lite` blog post (not just this app): it fails to load. `gradio`'s own
dependency chain pins `huggingface-hub<1.0,>=0.33.5`, and Pyodide's resolver
cannot satisfy that constraint against what is currently on PyPI. A Gradio
maintainer confirmed on the tracking issue
([gradio-app/gradio#12262](https://github.com/gradio-app/gradio/issues/12262))
that Lite is no longer maintained, and offered an unofficial patched build on
a personal S3 bucket as a one-off favor -- which gets past that crash but then
hits a second, unrelated one: `huggingface-hub`'s `filelock` dependency calls
`os.link(..., follow_symlinks=False)`, a call Pyodide's WASM filesystem shim
does not support. Two independent breakages in an explicitly unmaintained
library is not something to build a portfolio piece's public demo on.

`demo-react/src/scoring.ts` is therefore a deliberate, hand-written port of
`scoring.py`'s arithmetic, not a client-side Python runtime -- see
`personality_questionnaire/scoring.py`'s own module docstring for the
canonical algorithm. It is tested against the same fixtures `scoring.py`'s own
tests use (`tests/fixtures.py::PUBLISHED_OCEAN`, PANAS's sum-vs-mean
invariants, VAS-F's normalization bounds), not values invented for the port,
so a transcription mistake is caught the same way a mistake in the Python
would be. The instrument *data* (items, labels, subscale structure) does not
suffer the same duplication risk: `scripts/export_instruments.py` generates
`demo-react/src/instruments.json` from the live `registry.py`, and
`tests/demo_react/test_instruments_export.py` fails CI if the checked-in file
drifts from a fresh export.
