"""MkDocs hook: set fenced code blocks in titled frames, like notebook cells.

Each fenced code block of a page (``<div class="language-X highlight">``, as
rendered by ``pymdownx.highlight``) is wrapped in a ``code-frame``: a header
holding the language name and a copy button, above the block, which becomes the
code panel. A block followed by an ``Output:`` paragraph and a second block (a
command and what it prints) makes a single frame, the second block becoming its
output panel and the paragraph being dropped. ``docs/stylesheets/extra.css``
styles the frames and ``docs/javascripts/code_frames.js`` drives the copy
buttons.

In the API reference, the docstring examples are framed like any fenced block,
and the code of each collapsible "Source code in ..." block of mkdocstrings is
framed inside it, below its summary. Signatures are left as bare code panels
(styled by ``extra.css``): their ``<div>`` carries the extra ``doc-signature``
class, and a source code table's ``<div>`` does not directly hold a ``<pre>``,
so neither matches the block pattern.
"""

from __future__ import annotations

import re

BLOCK_PATTERN = (
    r'<div class="language-(?P<{name}>[\w+-]+) highlight"><pre>.*?</pre></div>'
)
FRAME_PATTERN = re.compile(
    "(?P<code>"
    + BLOCK_PATTERN.format(name="language")
    + r")(?:\s*<p>Output:</p>\s*(?P<output>"
    + BLOCK_PATTERN.format(name="output_language")
    + "))?",
    re.DOTALL,
)
SOURCE_PATTERN = re.compile(
    r'(?P<summary><details class="mkdocstrings-source">\s*<summary>.*?</summary>)'
    r'\s*(?P<code><div class="language-(?P<language>[\w+-]+) highlight">.*?)'
    r"\s*(?=</details>)",
    re.DOTALL,
)
LANGUAGE_TITLES = {
    "bash": "Bash",
    "css": "CSS",
    "json": "JSON",
    "python": "Python",
    "text": "",
}
# the copy icon of the notebook cells (GitHub's octicon)
COPY_ICON = (
    '<svg aria-hidden="true" class="code-frame-copy-icon" viewBox="0 0 16 16">'
    '<path fill="currentColor" fill-rule="evenodd" d="M0 6.75C0 5.784.784 5 '
    "1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25"
    ".25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 "
    '16h-7.5A1.75 1.75 0 010 14.25v-7.5z"></path>'
    '<path fill="currentColor" fill-rule="evenodd" d="M5 1.75C5 .784 5.784 0 '
    "6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 "
    "1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25"
    'h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25h-7.5z"></path>'
    "</svg>"
)
FRAME_TEMPLATE = (
    '<div class="code-frame">'
    '<div class="code-frame-header">'
    '<span class="code-frame-title">{title}</span>'
    '<button type="button" class="code-frame-copy" aria-label="Copy to clipboard">'
    '<span class="code-frame-copied" hidden>Copied!</span>'
    f"{COPY_ICON}"
    "</button>"
    "</div>"
    '<div class="code-frame-panel">{code}</div>'
    "{output}"
    "</div>"
)
OUTPUT_TEMPLATE = '<div class="code-frame-output">{output}</div>'


def make_title(language: str) -> str:
    """Give the frame title of a code block language.

    Args:
        language: The language of the code block.

    Returns:
        The frame title.
    """
    return LANGUAGE_TITLES.get(language, language.capitalize())


def make_frame(match: re.Match[str]) -> str:
    """Build the frame of a matched code block, with its output block if any.

    Args:
        match: The match of ``FRAME_PATTERN``.

    Returns:
        The frame markup.
    """
    output = match.group("output")
    return FRAME_TEMPLATE.format(
        title=make_title(match.group("language")),
        code=match.group("code"),
        output=OUTPUT_TEMPLATE.format(output=output) if output is not None else "",
    )


def make_source_frame(match: re.Match[str]) -> str:
    """Frame the code of a matched mkdocstrings source block, below its summary.

    Args:
        match: The match of ``SOURCE_PATTERN``.

    Returns:
        The summary followed by the frame markup.
    """
    return match.group("summary") + FRAME_TEMPLATE.format(
        title=make_title(match.group("language")),
        code=match.group("code"),
        output="",
    )


def frame_code_blocks(html: str) -> str:
    """Wrap every code block of an HTML fragment in a code frame.

    Args:
        html: The HTML fragment.

    Returns:
        The HTML fragment with its fenced and source code blocks framed.
    """
    html = FRAME_PATTERN.sub(make_frame, html)
    return SOURCE_PATTERN.sub(make_source_frame, html)


def on_page_content(html: str, page: object, **kwargs: object) -> str:
    """Frame the code blocks of each page.

    Args:
        html: The HTML content of the page.
        page: The page (unused).
        **kwargs: The other MkDocs event arguments (unused).

    Returns:
        The HTML content with its code blocks framed.
    """
    return frame_code_blocks(html)
