"""The public demo: pick an instrument, answer it, see the scores plotted.

No storage anywhere in this module -- see the package docstring in
``demo/__init__.py``. A visitor's answers live in Gradio's per-session state and
are gone when the tab closes.
"""

from __future__ import annotations

import argparse

import gradio as gr

import personality_questionnaire as pq
from demo import form, plots

__all__ = ["build", "launch", "main"]

_INSTRUMENT_CHOICES = tuple((pq.get(key).abbreviation, key) for key in pq.keys())
"""(abbreviation, registry key) pairs, for the instrument dropdown."""


def build() -> gr.Blocks:
    """Construct the Gradio app.

    Returns:
        The assembled Blocks interface, not yet launched.
    """
    with gr.Blocks(title="Personality Questionnaire -- Demo") as demo:
        gr.Markdown(
            "# Personality Questionnaire -- Demo\n"
            "Pick an instrument, answer every item, then evaluate. "
            "**This is a demo: nothing you enter is stored anywhere.**"
        )

        instrument_dropdown = gr.Dropdown(
            choices=_INSTRUMENT_CHOICES, value=_INSTRUMENT_CHOICES[0][1], label="Instrument"
        )
        citation = gr.Markdown()

        radios: list[gr.Radio] = []
        sliders: list[gr.Slider] = []
        for _ in range(form.MAX_ITEMS):
            radios.append(gr.Radio(visible=False))
            sliders.append(gr.Slider(visible=False))

        evaluate_button = gr.Button("Evaluate", variant="primary")
        warning = gr.Markdown(visible=False)
        plot = gr.Plot(label="Results")

        def on_instrument_change(key: str):
            """Rebuild the visible fields for the chosen instrument."""
            questionnaire = pq.get(key)
            specs = form.field_specs(questionnaire)

            radio_updates = []
            slider_updates = []
            for index in range(form.MAX_ITEMS):
                if index < len(specs) and specs[index].kind == "radio":
                    spec = specs[index]
                    radio_updates.append(
                        gr.update(
                            choices=list(spec.choices),
                            value=None,
                            label=spec.item.prompt,
                            visible=True,
                        )
                    )
                    slider_updates.append(gr.update(visible=False))
                elif index < len(specs):
                    spec = specs[index]
                    radio_updates.append(gr.update(visible=False))
                    slider_updates.append(
                        gr.update(
                            minimum=spec.minimum,
                            maximum=spec.maximum,
                            value=(spec.minimum + spec.maximum) / 2,
                            step=1,
                            label=spec.item.prompt,
                            info=f"{spec.item.low_anchor} .. {spec.item.high_anchor}",
                            visible=True,
                        )
                    )
                else:
                    radio_updates.append(gr.update(visible=False))
                    slider_updates.append(gr.update(visible=False))

            note = f"*{questionnaire.citation}*"
            return [
                note,
                gr.update(visible=False),
                None,
                *radio_updates,
                *slider_updates,
            ]

        instrument_dropdown.change(
            on_instrument_change,
            inputs=[instrument_dropdown],
            outputs=[citation, warning, plot, *radios, *sliders],
        )

        def on_evaluate(key: str, *values):
            """Score whatever has been answered and plot the result, or warn."""
            questionnaire = pq.get(key)
            specs = form.field_specs(questionnaire)
            n = len(specs)
            radio_values = values[: form.MAX_ITEMS][:n]
            slider_values = values[form.MAX_ITEMS :][:n]

            responses: dict[int, int] = {}
            for spec, radio_value, slider_value in zip(
                specs, radio_values, slider_values, strict=True
            ):
                chosen = radio_value if spec.kind == "radio" else slider_value
                if chosen is not None:
                    responses[spec.item.number] = int(chosen)

            missing = form.missing_items(questionnaire, responses)
            if missing:
                message = (
                    f"**{len(missing)} item(s) still unanswered** "
                    f"(item {missing[0]}{', …' if len(missing) > 1 else ''})."
                )
                return gr.update(value=message, visible=True), None

            answers = [responses[n] for n in range(1, questionnaire.n_items + 1)]
            result = pq.score(questionnaire, [answers])
            figure = plots.plot_for(questionnaire, result)
            return gr.update(visible=False), figure

        evaluate_button.click(
            on_evaluate,
            inputs=[instrument_dropdown, *radios, *sliders],
            outputs=[warning, plot],
        )

        demo.load(
            on_instrument_change,
            inputs=[instrument_dropdown],
            outputs=[citation, warning, plot, *radios, *sliders],
        )

    return demo


def launch(*, host: str = "127.0.0.1", port: int = 7860) -> None:
    """Build and serve the demo.

    Defaults to loopback, matching a local trial run. The Docker image sets
    ``GRADIO_SERVER_NAME=0.0.0.0`` itself (see ``Dockerfile``), so a Space never
    relies on this default -- it only shapes what ``pq demo`` does on someone's
    own machine, where there is no reason to bind wider than loopback either.

    Args:
        host: Address to bind.
        port: Port to listen on.
    """
    build().launch(server_name=host, server_port=port)


def main() -> None:
    """Start the demo server from the command line."""
    parser = argparse.ArgumentParser(prog="pq-demo", description="Run the public Gradio demo.")
    parser.add_argument("--host", default="127.0.0.1", help="address to bind")
    parser.add_argument("--port", type=int, default=7860, help="port to listen on")
    args = parser.parse_args()

    launch(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
