"""The localhost data-collection application.

Built for a machine in a lab: it binds to loopback, stores to a local database, and
makes no outbound request. Participant self-reports are consent-restricted, so the
default is a tool that cannot be reached from the network at all.

The interface is built **per browser connection** through ``@ui.page("/")`` rather
than the shared auto-index, so two tabs are two independent drafts and each one has a
live client while it builds.
"""

from __future__ import annotations

import logging

from nicegui import Client, app, context, ui

from personality_questionnaire import __version__
from personality_questionnaire.core import theme
from personality_questionnaire.core.config import settings
from personality_questionnaire.core.state import DraftRecord, state
from personality_questionnaire.pages import analyze as analyze_page
from personality_questionnaire.pages import export as export_page
from personality_questionnaire.pages import overview as overview_page
from personality_questionnaire.pages import questionnaire as questionnaire_page
from personality_questionnaire.pages import records as records_page
from personality_questionnaire.pages import setup as setup_page

__all__ = ["build", "main"]

log = logging.getLogger("personality_questionnaire")

_TABS: tuple[tuple[str, str, str, str], ...] = (
    ("overview", "insights", "Overview", "What this collects and where to start."),
    ("setup", "person_add", "Setup", "Name the record and choose an instrument."),
    (
        "questionnaire",
        "checklist",
        "Questionnaire",
        "Answer every item of the selected instrument.",
    ),
    ("export", "save", "Score", "Review the computed scores and save the record."),
    ("records", "table_view", "Records", "Browse and export everything collected."),
    (
        "analyze",
        "analytics",
        "Analyze",
        "Reliability and descriptive statistics over what has been collected so far.",
    ),
)
"""The tab bar in display order: ``(name, icon, label, tooltip)``."""

_drafts: dict[str, DraftRecord] = {}
"""One draft per browser connection, dropped when the connection closes."""


def draft_for(client: Client) -> DraftRecord:
    """Return the draft belonging to a connection, creating it on first use.

    Args:
        client: The browser connection.

    Returns:
        That connection's draft.
    """
    if client.id not in _drafts:
        _drafts[client.id] = DraftRecord()
        client.on_disconnect(lambda: _drafts.pop(client.id, None))
    return _drafts[client.id]


def build() -> None:
    """Build the tabbed interface for one connection."""
    ui.colors(primary=theme.PRIMARY, accent=theme.ACCENT)
    ui.add_css(
        f"body {{ background:{theme.PAPER}; color:{theme.INK}; }}"
        "html { overflow-y: scroll; scrollbar-gutter: stable; }"
    )

    draft = draft_for(context.client)
    holders: dict[str, ui.column] = {}
    tab_elements: dict[str, ui.tab] = {}

    with ui.header().classes("items-center q-px-md").style(f"background:{theme.PRIMARY}"):
        with ui.row().classes("flex-1 items-center gap-3"):
            # LOGO_MARK_SVG draws most of its dots in theme.PRIMARY -- correct on the
            # light backgrounds it appears on elsewhere (docs, favicon, README), but
            # invisible against a header set to that same PRIMARY. The translucent
            # chip below is what gives those dots contrast; the mark itself is
            # untouched, so every other use of LOGO_MARK_SVG is unaffected.
            with (
                ui.element("div")
                .classes("flex items-center justify-center")
                .style(
                    "width:2.75rem;height:2.75rem;border-radius:12px;"
                    "background:rgba(255,255,255,0.14);"
                    f"box-shadow:0 0 0 1px rgba(255,255,255,0.18), 0 0 10px 0 {theme.ACCENT}55;"
                    "padding:0.4rem"
                )
            ):
                ui.html(theme.LOGO_MARK_SVG).classes("w-full h-full")
            ui.label(settings.title).classes("text-lg font-medium")
        with ui.row().classes("flex-1 items-center justify-center"):
            with ui.tabs() as tabs:
                for name, icon, label, tooltip in _TABS:
                    tab = ui.tab(name, label=label, icon=icon)
                    with tab:
                        ui.tooltip(tooltip).props("delay=800")
                    tab_elements[name] = tab
        with ui.row().classes("flex-1 items-center justify-end gap-2"):
            ui.label(f"v{__version__}").classes("text-xs opacity-70")

    def navigate(name: str) -> None:
        """Switch to a tab by name.

        ``set_value`` raises the same change event a click does, so the panel is
        rebuilt by :func:`tab_changed` either way. Rebuilding here as well would run
        it twice and race Quasar's panel transition, leaving the previous tab's
        content on screen.
        """
        if tabs.value == name:
            rebuild(name)
        else:
            tabs.set_value(name)

    def sync_gating() -> None:
        """Enable or disable the tabs whose prerequisites depend on the draft."""
        for name, allowed in (
            ("questionnaire", draft.ready),
            ("export", draft.complete),
        ):
            element = tab_elements[name]
            if allowed:
                element.props(remove="disable")
            else:
                element.props(add="disable")

    def rebuild(name: str) -> None:
        """Rebuild one tab body from current state.

        The body is built into a container *inside* the panel rather than into the
        panel itself: clearing a ``tab_panel`` directly discards the layout Quasar
        attaches to it, and the rebuilt content then renders collapsed.

        """
        holder = holders[name]
        holder.clear()
        with holder:
            if name == "overview":
                overview_page.render(navigate)
            elif name == "setup":
                setup_page.render(draft, navigate, sync_gating)
            elif name == "questionnaire":
                questionnaire_page.render(draft, navigate, sync_gating)
            elif name == "export":
                export_page.render(draft, navigate, on_saved)
            elif name == "records":
                records_page.render(draft, navigate, sync_gating)
            elif name == "analyze":
                analyze_page.render()

    def on_saved() -> None:
        """React to a record being stored."""
        sync_gating()

    with ui.tab_panels(tabs, value="overview").classes("w-full").style(f"background:{theme.PAPER}"):
        for name, _, _, _ in _TABS:
            with ui.tab_panel(name):
                holders[name] = ui.column().classes("w-full")

    def tab_changed(event) -> None:  # noqa: ANN001 - NiceGUI event argument
        """Rebuild a tab as it is opened, so it reflects the current draft."""
        rebuild(event.value)

    tabs.on_value_change(tab_changed)
    rebuild("overview")
    sync_gating()


@ui.page("/")
def index() -> None:
    """Serve the application, fresh for each browser connection."""
    build()


def main() -> None:
    """Start the server."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    warning = settings.exposure_warning
    if warning:
        log.warning("%s", warning)

    log.info("records database: %s", state.repository.engine.url)
    app.on_shutdown(state.close)

    ui.run(
        host=settings.host,
        port=settings.port,
        title=settings.title,
        favicon=theme.LOGO_MARK_SVG,
        reload=False,
        show=settings.show,
        reconnect_timeout=30.0,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
