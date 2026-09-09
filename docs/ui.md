# The data-collection application

A localhost application for administering questionnaires to participants and keeping
the results.

```bash
pip install "personality_questionnaire[ui]"
pq ui                      # http://127.0.0.1:8080
pq ui --port 9000 --show   # different port, open a browser
```

## It stays on the machine it runs on

The application **binds to `127.0.0.1`** and makes no outbound request. Participant
self-reports are consent-restricted, and consent to answer a questionnaire in a lab
rarely extends to that data crossing a network. A tool that cannot be reached from
another machine is the honest default for this kind of collection.

Binding elsewhere is possible and deliberate:

```bash
PQ_HOST=0.0.0.0 pq ui      # logs a warning naming the address
```

Nothing here encrypts the database. Securing the machine is the operator's
responsibility; see [storage](storage.md).

## The five tabs

| Tab | Does |
| --- | --- |
| **Overview** | What the tool collects, the shipped instruments and their citations |
| **Setup** | Participant code, optional label, experiment and tag, and the instrument |
| **Questionnaire** | Every item with its published response labels, and a progress bar |
| **Score** | The computed scores, the provenance to be recorded, and the save button |
| **Records** | Everything collected, with filters, deletion and export |

Questionnaire and Score stay disabled until their prerequisites are met — a
participant code and an instrument for the first, a complete set of answers for the
second — so the tabs themselves say what remains to be done.

## Two browser tabs are two participants

State is per connection. Opening the application twice gives two independent drafts,
which is what allows one machine to run two stations side by side. A closed tab drops
its draft.

## Items are shown as their authors wrote them

A Likert instrument renders radio buttons carrying the published response labels —
*Disagree strongly* … *Agree strongly* for the BFI-2, *Very slightly or not at all* …
*Extremely* for the PANAS — rather than a row of bare numbers. A visual-analogue
instrument renders a slider between that item's own two anchors. The widget follows
the instrument's declared scale type, so adding an instrument needs no interface
change.

## Exporting

The Records tab offers the same three shapes as `pq export` — wide CSV, long CSV and
archival JSON — filtered to one instrument or across all of them. The wide shape is
available only when the selection is a single instrument; see
[storage](storage.md#export-shapes).

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `PQ_HOST` | `127.0.0.1` | Address to bind |
| `PQ_PORT` | `8080` | Port to listen on |
| `PQ_DATABASE_URL` | `~/.personality_questionnaire/records.db` | Where records go |

## How it is built

`app.py` builds the tab shell per browser connection and owns navigation and gating.
`pages/` holds one module per tab, and those modules build elements and nothing else:
readiness, progress, what remains unanswered and how a record is assembled all live
in `core/state.py`, which is tested directly and sits at 100% coverage. That split is
why `pages/` is excluded from the coverage gate — the logic was extracted, not
skipped.

Colours come from `core/theme.py`. Every pairing in it meets WCAG AA, asserted in
`tests/core/test_theme.py`, because a participant reads sixty items off this palette.
