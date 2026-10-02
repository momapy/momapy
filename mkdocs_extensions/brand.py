"""MkDocs hook: render every prose mention of momapy as the MomaPy brand.

Each standalone ``momapy`` word in the text of a built page (any case) is
replaced by ``<span class="momapy-brand">`` markup holding the ``Moma`` and
``Py`` halves, which ``docs/stylesheets/extra.css`` sets in
Montserrat with the brand colors. Code and cited titles are left untouched:
text inside ``<head>``, ``<code>``, ``<pre>``, ``<kbd>``, ``<samp>``, ``<svg>``,
``<cite>`` and raw-text elements is skipped, as are dotted, hyphenated or
bracketed names such as ``momapy.core``, ``momapy-repo`` or ``momapy[all]`` and
path segments such as ``adrienrougny/momapy``. Tag attributes are never rewritten.
"""

from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"<!--.*?-->|<![^>]*>|<[^>]+>", re.DOTALL)
TAG_NAME_PATTERN = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)")
BRAND_PATTERN = re.compile(r"(?<![\w./-])momapy(?![\w-]|\.\w|\[)", re.IGNORECASE)
BRAND_MARKUP = (
    '<span class="momapy-brand">'
    '<span class="momapy-brand-moma">Moma</span>'
    '<span class="momapy-brand-py">Py</span>'
    "</span>"
)
# elements whose content is not markup: copied verbatim up to their closing tag
RAW_TEXT_ELEMENTS = frozenset({"script", "style", "textarea"})
# elements whose text content must not be branded
SKIPPED_ELEMENTS = frozenset({"head", "code", "pre", "kbd", "samp", "svg", "cite"})


def brand_html(html: str) -> str:
    """Replace prose mentions of momapy in an HTML document with brand markup.

    Args:
        html: The HTML document.

    Returns:
        The HTML document with every prose mention branded.
    """
    parts = []
    skip_depth = 0
    position = 0
    while True:
        match = TOKEN_PATTERN.search(html, position)
        text_end = match.start() if match is not None else len(html)
        text = html[position:text_end]
        if skip_depth == 0:
            text = BRAND_PATTERN.sub(BRAND_MARKUP, text)
        parts.append(text)
        if match is None:
            break
        tag = match.group()
        position = match.end()
        parts.append(tag)
        tag_name_match = TAG_NAME_PATTERN.match(tag)
        if tag_name_match is None:
            continue
        is_closing = tag_name_match.group(1) == "/"
        tag_name = tag_name_match.group(2).lower()
        if not is_closing and tag_name in RAW_TEXT_ELEMENTS:
            closing_match = re.compile(rf"</\s*{tag_name}\s*>", re.IGNORECASE).search(
                html, position
            )
            raw_text_end = (
                closing_match.end() if closing_match is not None else len(html)
            )
            parts.append(html[position:raw_text_end])
            position = raw_text_end
        elif tag_name in SKIPPED_ELEMENTS and not tag.endswith("/>"):
            skip_depth = max(skip_depth - 1, 0) if is_closing else skip_depth + 1
    return "".join(parts)


def on_post_page(output: str, **kwargs: object) -> str:
    """Brand the fully rendered HTML of each page.

    Args:
        output: The rendered HTML of the page.
        **kwargs: The other MkDocs event arguments (unused).

    Returns:
        The branded HTML of the page.
    """
    return brand_html(output)


def on_post_template(output_content: str, template_name: str, **kwargs: object) -> str:
    """Brand the rendered HTML of the 404 page, which is not a regular page.

    Args:
        output_content: The rendered template.
        template_name: The name of the template.
        **kwargs: The other MkDocs event arguments (unused).

    Returns:
        The branded template for ``404.html``, the unchanged template otherwise.
    """
    if template_name == "404.html":
        return brand_html(output_content)
    return output_content
