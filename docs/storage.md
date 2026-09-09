# Storing records

A **record** is one administration of one instrument to one participant: a session
row with its responses, its computed scores, and the provenance needed to reproduce
those scores later.

```python
from personality_questionnaire.db import Record, Repository, create_engine_from_env

repository = Repository(create_engine_from_env())
saved = repository.save(
    Record(
        participant_code="P01",
        questionnaire="bfi2",
        responses={1: 4, 2: 3, ...},
        tag="pre",
        experiment="fatigue-2026",
    )
)
```

From the command line, `pq run` saves by default:

```bash
pq run bfi2 --participant P01 --experiment fatigue-2026
pq run bfi2 --participant P01 --no-save          # score without storing
pq records                                        # what is stored
pq export --shape long --output records.csv
```

## Where the data lives

`PQ_DATABASE_URL` names the database. Unset, records go to
`~/.personality_questionnaire/records.db`, so a lab machine needs no server and no
configuration.

```bash
export PQ_DATABASE_URL="sqlite:////srv/study/records.db"       # a shared file
export PQ_DATABASE_URL="mysql+pymysql://user:pw@host/records"  # pip install '.[mysql]'
```

The schema is portable rather than merely claimed to be: `tests/db/test_dialects.py`
compiles every table against the MySQL dialect, which needs neither a server nor a
driver and catches the differences that actually bite — above all an indexed string
column with no declared length, which MySQL refuses outright.

## Schema

```
participant ──< session ──< response
                       └──< score
```

| Table | One row per |
| --- | --- |
| `participant` | person, identified by a study-local code |
| `session` | administration of one instrument |
| `response` | item answered |
| `score` | subscale computed |

## Design decisions

**Responses are rows, not a JSON blob.** One row per item costs nothing at this scale
and turns "what did everyone answer to item 5" into a query rather than a decode loop
over every record — which is exactly the shape a reliability coefficient needs.

**Scores are stored, not recomputed.** A stored score, beside the scoring version and
a hash of the instrument that produced it, is evidence of what a participant was
actually told. Recomputing on read would silently rewrite history whenever the scorer
changed. `scoring_version` is bumped whenever the arithmetic changes, so an old
record stays interpretable.

**The instrument is hashed, not just named.** `instrument_hash` covers the items,
subscales, reverse keys and response range as administered. A later typo fix in an
item's wording therefore cannot retroactively change what a stored record means.

**Participants are coded, not named.** This package stores human-subject data;
a study-local code keeps a record pseudonymous by default. Nothing here encrypts the
database — that is the operator's responsibility, and the reason the application
binds to localhost.

**No migrations.** The schema has one version. A research tool that owns its own
database is better served by an explicit export and re-import than by a migration
graph nobody exercises. This is a decision, not an omission.

**Timestamps are UTC and aware.** SQLite has no timezone type and returns naive
values, so the repository re-attaches UTC on read. Without that, a loaded record
could not be compared with a freshly built one at all.

## Export shapes

| Shape | Rows | Use |
| --- | --- | --- |
| `json` | one object per record | Archival. Self-describing, includes provenance |
| `wide` | one per session | A statistics package, single instrument |
| `long` | one per value | Tidy analysis, several instruments in one file |

The wide shape refuses a selection spanning instruments rather than emitting a union
of every item column, mostly empty. Filter by `--questionnaire`, or use `long`.

Export writes to stdout unless `--output` is given, and diagnostics go to stderr, so
`pq export --shape long | duckdb` works.
