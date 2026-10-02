"""Base classes and mixins for CellDesigner model and layout elements.

The public base classes here (``CellDesignerModelElement``, ``CellDesignerNode``,
``CellDesignerSingleHeadedArc``, ``CellDesignerDoubleHeadedArc``) are part of the
public API and may be subclassed.

The private ``_*Mixin`` classes are an internal composition protocol; their
public value (anchors, fields) is already reachable on the concrete ``*Layout``
and ``*Node`` classes, which is what you should subclass.
"""

import dataclasses
import typing

from momapy.builder import (
    issubclass_or_builder,
    super_or_builder,
)
from momapy.coloring import Color, black
from momapy.core.elements import ModelElement
from momapy.core.layout import DoubleHeadedArc, SingleHeadedArc
from momapy.drawing import Gradient
from momapy.drawing import DrawingElement, NoneValue, NoneValueType
from momapy.sbgn.elements import SBGNNode, _MultiMixin, _SBGNMixin, _SimpleMixin


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerModelElement(ModelElement):
    """Abstract base class for CellDesigner model elements."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerNode(SBGNNode):
    """Abstract base class for CellDesigner nodes."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerSingleHeadedArc(SingleHeadedArc):
    """Abstract base class for CellDesigner single-headed arcs."""

    arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    arrowhead_stroke_width: float | None = 1.0
    path_fill: NoneValueType | Color | Gradient | None = NoneValue
    path_stroke: NoneValueType | Color | Gradient | None = black
    path_stroke_width: float | None = 1.0

    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the arc's own drawing elements, including those of its mixins."""
        drawing_elements = super_or_builder(
            CellDesignerSingleHeadedArc, self
        ).own_drawing_elements()
        done_bases = []
        for base in type(self).__mro__:
            if (
                issubclass_or_builder(base, _SBGNMixin)
                and base is not type(self)
                and not any([issubclass(done_base, base) for done_base in done_bases])
            ):
                drawing_elements += getattr(base, "_mixin_drawing_elements")(self)
                done_bases.append(base)
        return drawing_elements


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerDoubleHeadedArc(DoubleHeadedArc):
    """Abstract base class for CellDesigner double-headed arcs."""

    path_fill: NoneValueType | Color | Gradient | None = NoneValue
    path_stroke: NoneValueType | Color | Gradient | None = black
    path_stroke_width: float | None = 1.0

    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the arc's own drawing elements, including those of its mixins."""
        drawing_elements = super_or_builder(
            CellDesignerDoubleHeadedArc, self
        ).own_drawing_elements()
        done_bases = []
        for base in type(self).__mro__:
            if (
                issubclass_or_builder(base, _SBGNMixin)
                and base is not type(self)
                and not any([issubclass(done_base, base) for done_base in done_bases])
            ):
                drawing_elements += getattr(base, "_mixin_drawing_elements")(self)
                done_bases.append(base)
        return drawing_elements


@dataclasses.dataclass(frozen=True, kw_only=True)
class _SimpleNodeMixin(_SimpleMixin):
    """Simple node mixin."""

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        return _SimpleMixin._mixin_drawing_elements(obj)


@dataclasses.dataclass(frozen=True, kw_only=True)
class _MultiNodeMixin(_MultiMixin):
    """Multi node mixin."""

    n: int = dataclasses.field(
        default=1,
        metadata={"description": "Number of stacked node copies to draw."},
    )

    @property
    def _n(self) -> int:
        return self.n

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        return _MultiMixin._mixin_drawing_elements(obj)
