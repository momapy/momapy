"""Abstract base class for SBGN layouts."""

import dataclasses

from momapy.coloring import Color
from momapy.coloring import white
from momapy.core.layout import Layout
from momapy.drawing import Gradient
from momapy.drawing import NoneValueType


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNLayout(Layout):
    """Base class for SBGN layouts.

    SBGN layouts define the visual representation of SBGN models,
    including the positions and styles of glyphs.
    """

    fill: NoneValueType | Color | Gradient | None = white


# Default label font sizes the SBGN-ML reader injects when building layouts.
# Exposed so that code building SBGN maps programmatically (rather than reading a
# file) can reproduce momapy's default appearance.
DEFAULT_FONT_SIZE = 11.0  # SBGN glyph / entity-pool labels
DEFAULT_AUXILIARY_UNIT_FONT_SIZE = 8.0  # state variable & unit-of-information labels
