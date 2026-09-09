"""Sphinx configuration.

The front page is generated from README.md at build time so the two cannot drift:
GitHub and the docs site show the same text, with in-repo links rewritten to point
at their rendered pages.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "personality_questionnaire"
copyright = "2026, Adam Fodor"
author = "Adam Fodor"

from personality_questionnaire import __version__  # noqa: E402

release = __version__

extensions = [
    "autoapi.extension",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

autoapi_dirs = ["../personality_questionnaire"]
autoapi_options = [
    "members",
    "undoc-members",  # required -- without it autoapi skips submodule pages
    "show-inheritance",
    "show-module-summary",
]
autoapi_add_toctree_entry = False
autoapi_member_order = "source"
autoapi_python_class_content = "both"


def skip_undocumented_attributes(app, what, name, obj, skip, options):
    """Hide undocumented attributes from the API pages."""
    if what == "attribute" and not obj.docstring:
        return True
    return skip


napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = True

myst_enable_extensions = ["colon_fence", "deflist"]
# GitHub renders ```mermaid fences natively. Sphinx has no such lexer, so the
# fence is rendered as an unhighlighted block rather than failing the -W build.
myst_fence_as_directive: list[str] = []
lexers_to_ignore = ["mermaid"]
suppress_warnings = ["misc.highlighting_failure"]
myst_heading_anchors = 3

html_theme = "furo"
html_title = "personality_questionnaire"
html_logo = "assets/logo.svg"
html_static_path = ["assets"]
html_baseurl = "https://fodorad.github.io/personality_questionnaire/"
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#12294B",
        "color-brand-content": "#12294B",
    },
    "dark_css_variables": {
        "color-brand-primary": "#E8925C",
        "color-brand-content": "#E8925C",
    },
    "source_repository": "https://github.com/fodorad/personality_questionnaire/",
    "source_branch": "main",
    "source_directory": "docs/",
}

GENERATED_README = "_readme.md"
REPO_BLOB = "https://github.com/fodorad/personality_questionnaire/blob/main/"
README_PAGE_LINKS = {
    "docs/instruments.md": "/instruments",
    "docs/design.md": "/design",
    "docs/migration.md": "/migration",
    "CHANGELOG.md": "/changelog",
}

exclude_patterns = [GENERATED_README]


def _with_one_title(text: str) -> str:
    """Demote the README's section headings and give the page a single title.

    The README uses ``#`` for each top-level section, which reads well on GitHub
    but would leave the page with many H1s and no title.

    Args:
        text: The README source.

    Returns:
        The rewritten source.
    """
    lines, fenced, out = text.split("\n"), False, []
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("#"):
            line = "#" + line
        out.append(line)
    return "# personality_questionnaire\n\n" + "\n".join(out)


def _rewrite_links(text: str) -> str:
    """Repoint in-repo markdown links at their rendered pages.

    Args:
        text: The README source.

    Returns:
        The rewritten source.
    """
    # `[^\]]*` would stop at the inner `]` of a badge, so nested brackets are
    # matched explicitly and badge links are rewritten too.
    pattern = r"\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)\)"

    def replace(match: re.Match) -> str:
        label, target = match.group(1), match.group(2)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            return match.group(0)
        page = README_PAGE_LINKS.get(target.lstrip("./"))
        if page:
            return f"[{label}]({page})"
        return f"[{label}]({REPO_BLOB}{target.lstrip('./')})"

    return re.sub(pattern, replace, text)


def _generate_readme_page(app):
    """Write docs/_readme.md from the repository README."""
    source = Path(app.srcdir).parent / "README.md"
    if not source.exists():
        return
    text = _rewrite_links(source.read_text(encoding="utf-8"))
    (Path(app.srcdir) / GENERATED_README).write_text(_with_one_title(text), encoding="utf-8")


def _drop_sourceless_viewcode_modules(app, env) -> None:
    """Remove modules viewcode found no source for, before it builds its index.

    Without this the build emits a dead ``builtins.html`` link, which ``-W`` turns
    into a failure.
    """
    modules = getattr(env, "_viewcode_modules", None)
    if not modules:
        return
    for name in [name for name, entry in modules.items() if not entry]:
        del modules[name]


def setup(app):
    """Register the build hooks."""
    app.connect("autoapi-skip-member", skip_undocumented_attributes)
    app.connect("builder-inited", _generate_readme_page)
    app.connect("env-updated", _drop_sourceless_viewcode_modules)
