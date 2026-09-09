---
title: Personality Questionnaire
emoji: 🧭
colorFrom: blue
colorTo: orange
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Personality Questionnaire — demo

Pick an instrument, answer it, and see your scores plotted. Nothing you enter is
stored anywhere — this is a stateless demo of the
[`personality_questionnaire`](https://github.com/fodorad/personality_questionnaire)
package's scoring, not the data-collection app it also ships (which runs on a
researcher's own machine, never on a public host).

Big Five instruments (BFI-2, BFI-2-XS, BFI-10) plot as a five-axis radar; PANAS and
VAS-F plot as a bar chart of their scales.

![Gradio demo: BFI-10 scored as a Big Five radar chart](https://raw.githubusercontent.com/fodorad/personality_questionnaire/main/docs/assets/screenshot-demo-gradio.jpg)
