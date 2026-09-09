"""Command-line entry point.

Subcommands replace the pre-2.0 ``--questionnaire`` flag. The old form is still
accepted: it is rewritten to a subcommand with a deprecation warning, so existing
scripts keep working.

Two output channels are kept apart. Diagnostics go to :mod:`logging` on stderr, so
``pq export`` can be piped; participant-facing prompts and scores are the program's
actual output and go to stdout.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

from personality_questionnaire import __version__, io, registry, scoring
from personality_questionnaire.cli import render
from personality_questionnaire.cli.prompt import ask_items
from personality_questionnaire.provenance import capture

__all__ = ["build_parser", "main"]

log = logging.getLogger("personality_questionnaire")

EXIT_OK = 0
"""The command completed."""

EXIT_ABORTED = 1
"""The participant quit before finishing."""

EXIT_MISSING_INPUT = 3
"""A required input file was absent."""

EXIT_NOT_INTERACTIVE = 4
"""``run`` was invoked without a terminal to ask the questions on."""


def _emit(lines: list[str]) -> None:
    """Print rendered lines to stdout.

    Args:
        lines: Lines to print.
    """
    print("\n".join(lines))


def _cmd_list(args: argparse.Namespace) -> int:
    """List the registered instruments.

    Args:
        args: Parsed arguments.

    Returns:
        An exit code.
    """
    instruments = [registry.get(key) for key in registry.keys()]

    if args.json:
        payload = [
            {
                "key": q.key,
                "name": q.name,
                "items": q.n_items,
                "scale": q.scale.value,
                "minimum": q.minimum,
                "maximum": q.maximum,
                "paired": q.paired,
                "subscales": [s.name for s in q.subscales],
                "citation": q.citation,
            }
            for q in instruments
        ]
        print(json.dumps(payload, indent=2))
    else:
        _emit(render.format_registry(instruments))

    return EXIT_OK


def _cmd_info(args: argparse.Namespace) -> int:
    """Describe one instrument.

    Args:
        args: Parsed arguments.

    Returns:
        An exit code.
    """
    _emit(render.format_instrument(registry.get(args.questionnaire)))
    return EXIT_OK


def _write_side_cars(
    output_dir: Path,
    participant: str,
    questionnaire_key: str,
    tag: str,
    responses: list[int],
    result: scoring.ScoreResult,
) -> list[Path]:
    """Write the response and score CSVs for one administration.

    Args:
        output_dir: Directory to write into.
        participant: Participant identifier, used in every filename.
        questionnaire_key: Instrument key, used in every filename.
        tag: Optional administration tag, e.g. ``"pre"``.
        responses: The participant's responses.
        result: Their computed scores.

    Returns:
        The paths written.
    """
    suffix = f"-{tag}" if tag else ""
    stem = f"{participant}_{questionnaire_key}{suffix}"

    answers_path = output_dir / f"{stem}_answers_int.csv"
    scores_path = output_dir / f"{stem}_scores.csv"

    io.save_csv_int(answers_path, [responses])
    io.save_csv(scores_path, result.values)
    return [answers_path, scores_path]


def _cmd_run(args: argparse.Namespace) -> int:
    """Administer an instrument interactively.

    Args:
        args: Parsed arguments. ``args.read`` and ``args.write``, when present,
            replace :func:`input` and :func:`print` -- the seam the tests drive the
            whole administration path through.

    Returns:
        An exit code.
    """
    questionnaire = registry.get(args.questionnaire)
    read = getattr(args, "read", input)

    try:
        responses = ask_items(
            questionnaire,
            read=read,
            write=getattr(args, "write", print),
        )
    except EOFError as exc:
        # Reading a closed stdin used to block here forever, with no output.
        log.error(
            "%s. To score answers you already have, use: pq score %s --input <file>",
            exc,
            questionnaire.key,
        )
        return EXIT_NOT_INTERACTIVE
    if responses is None:
        print("Questionnaire abandoned; nothing was saved.")
        return EXIT_ABORTED

    result = scoring.score(questionnaire, [responses])
    print("")
    _emit(render.format_scores(result))

    if not args.no_save:
        saved = _save_record(args, questionnaire, responses)
        print("")
        print(f"Saved record {saved.session_id} for {saved.participant_code}.")

    provenance = capture()
    log.info(
        "scored %s for %s (version %s, git %s%s)",
        questionnaire.key,
        args.participant,
        provenance.package_version,
        (provenance.git_sha or "n/a")[:8],
        ", dirty" if provenance.git_dirty else "",
    )

    if args.output_dir is not None:
        written = _write_side_cars(
            Path(args.output_dir),
            args.participant,
            questionnaire.key,
            args.tag,
            responses,
            result,
        )
        print("")
        for path in written:
            print(f"Wrote {path}")

    return EXIT_OK


def _repository(args: argparse.Namespace):
    """Open the record store named by the arguments or the environment.

    Args:
        args: Parsed arguments, whose ``db`` may name a database URL.

    Returns:
        A repository bound to that database.
    """
    from personality_questionnaire.db import Repository, create_engine_from_env

    url = getattr(args, "db", None)
    engine = create_engine_from_env(url)
    log.debug("using database %s", engine.url)
    return Repository(engine)


def _save_record(
    args: argparse.Namespace,
    questionnaire: registry.Questionnaire,
    responses: list[int],
):
    """Persist one completed administration.

    Args:
        args: Parsed arguments.
        questionnaire: The instrument administered.
        responses: The participant's answers, in item order.

    Returns:
        The saved record, carrying its new session id.
    """
    from personality_questionnaire.db import Record

    record = Record(
        participant_code=args.participant,
        questionnaire=questionnaire.key,
        responses={n: v for n, v in enumerate(responses, start=1)},
        tag=args.tag,
        experiment=args.experiment or None,
        source="cli",
    )
    return _repository(args).save(record)


def _cmd_records(args: argparse.Namespace) -> int:
    """List stored records.

    Args:
        args: Parsed arguments.

    Returns:
        An exit code.
    """
    summaries = _repository(args).list(
        participant=args.participant,
        questionnaire=args.questionnaire,
        experiment=args.experiment,
    )
    _emit(render.format_records(summaries))
    return EXIT_OK


def _cmd_export(args: argparse.Namespace) -> int:
    """Export stored records to a file or stdout.

    Args:
        args: Parsed arguments.

    Returns:
        An exit code.
    """
    import json as _json

    from personality_questionnaire.db import export as export_module

    repository = _repository(args)
    summaries = repository.list(
        participant=args.participant,
        questionnaire=args.questionnaire,
        experiment=args.experiment,
    )
    session_ids = [s.session_id for s in summaries if s.complete]

    if not session_ids:
        log.error("no complete records match that selection")
        return EXIT_MISSING_INPUT

    if args.shape == "json":
        text = _json.dumps(export_module.to_json(repository, session_ids), indent=2) + "\n"
    else:
        text = export_module.to_csv(repository.engine, session_ids, shape=args.shape)

    if args.output is None:
        print(text, end="")
    else:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {len(session_ids)} record(s) to {args.output}")

    return EXIT_OK


def _load_responses(path: Path, questionnaire: registry.Questionnaire) -> np.ndarray:
    """Load responses from a CSV, NPY or JSON file.

    Args:
        path: File to read.
        questionnaire: Instrument the responses belong to, for width validation.

    Returns:
        Responses of shape ``(n_participants, n_items)``.

    Raises:
        ValueError: If the suffix is not recognised.
    """
    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.atleast_2d(np.load(path))
    if suffix == ".json":
        return np.atleast_2d(np.asarray(io.load_json(path), dtype=int))
    if suffix in {".csv", ".txt", ""}:
        return io.load_csv_int(path, questionnaire.n_items)

    raise ValueError(f"unsupported response format {suffix!r}; use .csv, .npy or .json")


def _cmd_score(args: argparse.Namespace) -> int:
    """Score responses held in a file.

    Args:
        args: Parsed arguments.

    Returns:
        An exit code.
    """
    questionnaire = registry.get(args.questionnaire)
    path = Path(args.input)

    if not path.exists():
        log.error("no such file: %s", path)
        return EXIT_MISSING_INPUT

    result = scoring.score(questionnaire, _load_responses(path, questionnaire))

    for row in range(result.n_participants):
        if result.n_participants > 1:
            print(f"\nParticipant {row + 1}:")
        _emit(render.format_scores(result, row))

    if args.output is not None:
        io.save_csv(Path(args.output), result.values)
        print(f"\nWrote {args.output}")

    return EXIT_OK


def _add_run_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``run`` subcommand.

    Args:
        subparsers: The subparser registry to add to.
    """
    parser = subparsers.add_parser("run", help="administer an instrument interactively")
    parser.add_argument("questionnaire", choices=registry.keys(), help="instrument to administer")
    parser.add_argument("--participant", required=True, help="participant identifier")
    parser.add_argument("--tag", default="", help="administration tag, e.g. pre or post")
    parser.add_argument("--experiment", default="", help="experiment name recorded with the run")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="write response and score CSVs into this directory",
    )
    parser.add_argument("--db", default=None, help="database URL (default: $PQ_DATABASE_URL)")
    parser.add_argument("--no-save", action="store_true", help="score without storing the record")
    parser.set_defaults(func=_cmd_run)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The configured parser.
    """
    parser = argparse.ArgumentParser(
        prog="pq",
        description="Administer, score and record personality and affect questionnaires.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="log diagnostics to stderr")
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress warnings")

    subparsers = parser.add_subparsers(dest="command", required=True)

    listing = subparsers.add_parser("list", help="list the available instruments")
    listing.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    listing.set_defaults(func=_cmd_list)

    info = subparsers.add_parser("info", help="describe one instrument")
    info.add_argument("questionnaire", choices=registry.keys(), help="instrument to describe")
    info.set_defaults(func=_cmd_info)

    _add_run_parser(subparsers)

    records = subparsers.add_parser("records", help="list stored records")
    records.add_argument("--participant", default=None, help="restrict to one participant")
    records.add_argument(
        "--questionnaire", default=None, choices=registry.keys(), help="restrict to one instrument"
    )
    records.add_argument("--experiment", default=None, help="restrict to one experiment")
    records.add_argument("--db", default=None, help="database URL")
    records.set_defaults(func=_cmd_records)

    export_parser = subparsers.add_parser("export", help="export stored records")
    export_parser.add_argument("--participant", default=None, help="restrict to one participant")
    export_parser.add_argument(
        "--questionnaire", default=None, choices=registry.keys(), help="restrict to one instrument"
    )
    export_parser.add_argument("--experiment", default=None, help="restrict to one experiment")
    export_parser.add_argument(
        "--shape", default="wide", choices=("wide", "long", "json"), help="output shape"
    )
    export_parser.add_argument("--output", default=None, help="write here instead of stdout")
    export_parser.add_argument("--db", default=None, help="database URL")
    export_parser.set_defaults(func=_cmd_export)

    score_parser = subparsers.add_parser("score", help="score responses from a file")
    score_parser.add_argument("questionnaire", choices=registry.keys(), help="instrument used")
    score_parser.add_argument("--input", required=True, help="responses (.csv, .npy or .json)")
    score_parser.add_argument("--output", default=None, help="write the scores to this CSV")
    score_parser.set_defaults(func=_cmd_score)

    return parser


def _configure_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    """Route diagnostics to the current stderr.

    The handler is rebuilt on every call rather than left to
    :func:`logging.basicConfig`, which binds ``sys.stderr`` once and then ignores
    later calls -- so a redirected stream, in a test or behind a shell redirect,
    would silently receive nothing.

    Args:
        verbose: Log at debug level.
        quiet: Log only errors.
    """
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.WARNING

    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False


def _translate_legacy(argv: list[str]) -> list[str] | None:
    """Rewrite the pre-2.0 flat command line into a subcommand invocation.

    The old form was ``--questionnaire bfi2 --participant_id P01``, with underscored
    flag names and no subcommand.

    Args:
        argv: Arguments after the program name.

    Returns:
        The rewritten arguments, or ``None`` if this is not the legacy form -- which
        includes any invocation that already names a subcommand.
    """
    if "--questionnaire" not in argv:
        return None

    # `records` and `export` take a --questionnaire filter of their own, so the flag
    # alone no longer identifies the legacy form. Only a command line that names no
    # subcommand at all can be the pre-2.0 one.
    subcommands = {"list", "info", "run", "score", "records", "export"}
    if any(token in subcommands for token in argv):
        return None

    values = {}
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--skip_questions":
            # A valueless flag in the old interface; consumed so the token after it
            # is not mistaken for its argument.
            index += 1
        elif token.startswith("--") and index + 1 < len(argv):
            values[token] = argv[index + 1]
            index += 2
        else:
            index += 1

    questionnaire = values.get("--questionnaire")
    if questionnaire is None:
        return None

    participant = values.get("--participant_id") or values.get("--participant") or "unknown"
    output_dir = values.get("--output_dir", "data")
    tag = values.get("--vasf_tag", "")

    rewritten = ["run", questionnaire, "--participant", participant, "--output-dir", output_dir]
    if tag and questionnaire == "vasf":
        rewritten += ["--tag", tag]

    return rewritten


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Arguments after the program name. Defaults to :data:`sys.argv`.

    Returns:
        An exit code.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)

    translated = _translate_legacy(arguments)
    if translated is not None:
        print(
            "warning: the --questionnaire flag is deprecated; "
            f"use `pq {' '.join(translated[:2])} ...` instead.",
            file=sys.stderr,
        )
        arguments = translated

    args = build_parser().parse_args(arguments)

    _configure_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        return int(args.func(args))
    except (KeyError, ValueError) as exc:
        log.error("%s", exc)
        return 2


def run() -> None:
    """Console-script wrapper that turns the exit code into process exit."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
