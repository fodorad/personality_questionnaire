---
title: Personality Questionnaire
emoji: 🧭
colorFrom: blue
colorTo: pink
sdk: static
app_build_command: npm run build
app_file: dist/index.html
pinned: false
license: mit
---

# Personality Questionnaire — demo (React)

Pick an instrument, answer it, and see your scores plotted. Nothing you enter
is stored anywhere — this is a stateless demo of the
[`personality_questionnaire`](https://github.com/fodorad/personality_questionnaire)
package's scoring, not the data-collection app it also ships (which runs on a
researcher's own machine, never on a public host).

This is a React/TypeScript reimplementation of the same demo, built for
Hugging Face's static-Space tier: Docker and Gradio Spaces require a paid
plan for a personal account, and the free ZeroGPU exception is capped at two
Spaces per account. A static Space with a build step has neither restriction,
so this exists alongside (not instead of) the Gradio version in `demo/`.

**Not currently deployed.** Hugging Face requires billing credits on the
account to run a Space's build step, even for the static SDK, so this Space
is not published. Local-first (`make react-demo`) is the supported way to run
it; see the root [README](../README.md#try-it-without-installing-anything).

The instrument/item/subscale data here is generated from the same Python
`registry.py` that defines the CLI, the Lab UI, and the Gradio demo
(`scripts/export_instruments.py` → `src/instruments.json`), so all four stay
in agreement on what each instrument actually asks. The scoring *arithmetic*
(`src/scoring.ts`) is a separate, hand-written TypeScript port of
`scoring.py` — an earlier attempt to run the actual Python client-side via
Gradio Lite (Pyodide) turned out to be broken and unmaintained upstream; see
`docs/design.md` in the main repository for that investigation.

Big Five instruments (BFI-2, BFI-2-XS, BFI-10) plot as a five-axis radar;
PANAS and VAS-F plot as a bar chart of their scales.

VAS-F's sliders start pre-set at the scale midpoint rather than genuinely
unanswered, matching `demo/app.py`'s own Gradio slider default. Unlike a
Likert item, a visual-analogue item (how tired, how energetic) has no
neutral "unanswered" state to render -- a slider always shows some position
-- so the midpoint is the least presumptive default, not a filled-in guess
at the participant's answer. A participant can leave any slider untouched
and still submit.

![React demo: BFI-10 scored as a Big Five radar chart](https://raw.githubusercontent.com/fodorad/personality_questionnaire/main/docs/assets/screenshot-demo-react.jpg)
