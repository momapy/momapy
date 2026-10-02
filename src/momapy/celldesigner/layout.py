"""Layout classes for CellDesigner maps.

This module provides classes for representing the visual layout of a
CellDesigner pathway, including node layouts (species, compartments,
logic gates), arc layouts (reactions, modulations), and reaction node
decorations.

Most layout classes are named after the model class they draw, with a
``Layout`` suffix appended (e.g. model ``GenericProtein`` gives layout
``GenericProteinLayout``). The active-state variants keep the model name and
insert ``Active`` before the suffix (e.g. ``GenericProteinActiveLayout``).

The private ``_*Mixin`` classes are an internal composition protocol; their
public value (anchors, fields) is already reachable on the concrete ``*Layout``
classes, which is what you should subclass.
"""

import dataclasses
import enum
import math
import typing

from momapy.core.elements import Direction
from momapy.core.layout import Layout, Shape, TextLayout
from momapy.geometry import Point, Rotation, Transformation, get_normalized_angle
from momapy.coloring import Color, black, white
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import Gradient
from momapy.drawing import (
    ClosePath,
    DEFAULT_FONT_FAMILY,
    DrawingElement,
    Ellipse as DrawingEllipse,
    EllipticalArc,
    Filter,
    FontStyle,
    FontWeight,
    LineTo,
    MoveTo,
    NoneValue,
    NoneValueType,
    Path,
    QuadraticCurveTo,
    Rectangle as DrawingRectangle,
)
from momapy.meta.shapes import (
    Ellipse as MetaShapesEllipse,
    Hexagon,
    Parallelogram,
    Rectangle as MetaShapesRectangle,
    Triangle as MetaShapesTriangle,
    TurnedHexagon,
)
from momapy.meta.nodes import Rectangle as MetaNodesRectangle
from momapy.meta.arcs import (
    Bar,
    Diamond,
    DoubleTriangle,
    Ellipse as MetaArcsEllipse,
    PolyLine,
    StraightBarb,
    Triangle as MetaArcsTriangle,
)
from momapy.sbgn.pd import MacromoleculeMultimerLayout

from momapy.celldesigner.elements import (
    CellDesignerNode,
    CellDesignerSingleHeadedArc,
    CellDesignerDoubleHeadedArc,
    _SimpleNodeMixin,
    _MultiNodeMixin,
)
from momapy.sbgn.elements import _SBGNMixin, _TextMixin


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerLayout(Layout):
    """CellDesigner layout."""

    fill: NoneValueType | Color | Gradient | None = white


# Default label font sizes the CellDesigner reader injects when building layouts.
# Exposed so that code building CellDesigner maps programmatically (rather than
# reading a file) can reproduce momapy's default appearance.
DEFAULT_FONT_SIZE = 12.0  # species / node labels
DEFAULT_MODIFICATION_FONT_SIZE = 9.0  # modifications / structural states
# Padding added around an active-state border relative to its base node.
DEFAULT_ACTIVE_XSEP = 4.0
DEFAULT_ACTIVE_YSEP = 4.0


@dataclasses.dataclass(frozen=True, kw_only=True)
class GenericProteinLayout(_MultiNodeMixin, CellDesignerNode):
    """Generic protein layout."""

    width: float = 80.0
    height: float = 40.0
    rounded_corners: float = dataclasses.field(
        default=5.0, metadata={"description": "The radius of the rounded corners."}
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCFFCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MacromoleculeMultimerLayout._make_subunit_shape(
            self, position, width, height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class GenericProteinActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Generic protein active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 40.0 + DEFAULT_ACTIVE_YSEP * 2
    rounded_corners: float = dataclasses.field(
        default=5.0, metadata={"description": "The radius of the rounded corners."}
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MacromoleculeMultimerLayout._make_subunit_shape(
            self, position, width, height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _IonChannelShape(Shape):
    """Ion channel shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    right_rectangle_width: float = dataclasses.field(
        metadata={"description": "The width of the right-hand gate rectangle."}
    )
    rounded_corners: float = dataclasses.field(
        metadata={"description": "The radius of the rounded corners."}
    )

    def joint1(self) -> Point:
        return self.position + (
            self.rounded_corners - self.width / 2,
            -self.height / 2,
        )

    def joint2(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width - self.rounded_corners,
            -self.height / 2,
        )

    def joint3(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width,
            self.rounded_corners - self.height / 2,
        )

    def joint4(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width,
            self.height / 2 - self.rounded_corners,
        )

    def joint5(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width - self.rounded_corners,
            self.height / 2,
        )

    def joint6(self) -> Point:
        return self.position + (
            self.rounded_corners - self.width / 2,
            self.height / 2,
        )

    def joint7(self) -> Point:
        return self.position + (
            -self.width / 2,
            self.height / 2 - self.rounded_corners,
        )

    def joint8(self) -> Point:
        return self.position + (
            -self.width / 2,
            self.rounded_corners - self.height / 2,
        )

    def joint9(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width + self.rounded_corners,
            self.height / 2,
        )

    def joint10(self) -> Point:
        return self.position + (
            self.width / 2 - self.rounded_corners,
            -self.height / 2,
        )

    def joint11(self) -> Point:
        return self.position + (
            self.width / 2,
            self.rounded_corners - self.height / 2,
        )

    def joint12(self) -> Point:
        return self.position + (
            self.width / 2,
            self.height / 2 - self.rounded_corners,
        )

    def joint13(self) -> Point:
        return self.position + (
            self.width / 2 - self.rounded_corners,
            self.height / 2,
        )

    def joint14(self) -> Point:
        return self.position + (
            self.rounded_corners + self.width / 2 - self.right_rectangle_width,
            self.height / 2,
        )

    def joint15(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width,
            self.height / 2 - self.rounded_corners,
        )

    def joint16(self) -> Point:
        return self.position + (
            self.width / 2 - self.right_rectangle_width,
            self.rounded_corners - self.height / 2,
        )

    def drawing_elements(self) -> list[DrawingElement]:
        left_rectangle = DrawingRectangle(
            point=self.position - (self.width / 2, self.height / 2),
            height=self.height,
            width=self.width - self.right_rectangle_width,
            rx=self.rounded_corners,
            ry=self.rounded_corners,
        )
        right_rectangle = DrawingRectangle(
            point=self.position
            + (self.width / 2 - self.right_rectangle_width, -self.height / 2),
            height=self.height,
            width=self.right_rectangle_width,
            rx=self.rounded_corners,
            ry=self.rounded_corners,
        )
        return [left_rectangle, right_rectangle]


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonChannelLayout(_MultiNodeMixin, CellDesignerNode):
    """Ion channel layout."""

    width: float = 80.0
    height: float = 40.0
    rounded_corners: float = dataclasses.field(
        default=5.0, metadata={"description": "The radius of the rounded corners."}
    )
    right_rectangle_width: float = dataclasses.field(
        default=20.0,
        metadata={"description": "The width of the right-hand gate rectangle."},
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCFFCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _IonChannelShape(
            position=position,
            width=width,
            height=height,
            rounded_corners=self.rounded_corners,
            right_rectangle_width=self.right_rectangle_width,
        )

    def label_center(self) -> Point:
        """Return the center point for the node's label."""
        return Point(self.position.x - self.right_rectangle_width / 2, self.position.y)


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonChannelActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Ion channel active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 40.0 + DEFAULT_ACTIVE_YSEP * 2
    rounded_corners: float = dataclasses.field(
        default=5.0, metadata={"description": "The radius of the rounded corners."}
    )
    right_rectangle_width: float = dataclasses.field(
        default=20.0,
        metadata={"description": "The width of the right-hand gate rectangle."},
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _IonChannelShape(
            position=position,
            width=width,
            height=height,
            rounded_corners=self.rounded_corners,
            right_rectangle_width=self.right_rectangle_width,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexLayout(_MultiNodeMixin, CellDesignerNode):
    """Complex layout."""

    width: float = 100.0
    height: float = 120.0
    cut_corners: float = dataclasses.field(
        default=6.0, metadata={"description": "The size of the cut corners."}
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#F7F7F7")
    stroke_width: float | None = 2.0
    # label -12 from south

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesRectangle(
            position=position,
            width=width,
            height=height,
            top_left_rx=self.cut_corners,
            top_left_ry=self.cut_corners,
            top_left_rounded_or_cut="cut",
            top_right_rx=self.cut_corners,
            top_right_ry=self.cut_corners,
            top_right_rounded_or_cut="cut",
            bottom_left_rx=self.cut_corners,
            bottom_left_ry=self.cut_corners,
            bottom_left_rounded_or_cut="cut",
            bottom_right_rx=self.cut_corners,
            bottom_right_ry=self.cut_corners,
            bottom_right_rounded_or_cut="cut",
        )

    def label_center(self) -> Point:
        """Return the center point for the node's label."""
        return self.south() - (0, 12)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Complex active layout."""

    width: float = 100.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 120.0 + DEFAULT_ACTIVE_YSEP * 2
    cut_corners: float = dataclasses.field(
        default=6.0, metadata={"description": "The size of the cut corners."}
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesRectangle(
            position=position,
            width=width,
            height=height,
            top_left_rx=self.cut_corners,
            top_left_ry=self.cut_corners,
            top_left_rounded_or_cut="cut",
            top_right_rx=self.cut_corners,
            top_right_ry=self.cut_corners,
            top_right_rounded_or_cut="cut",
            bottom_left_rx=self.cut_corners,
            bottom_left_ry=self.cut_corners,
            bottom_left_rounded_or_cut="cut",
            bottom_right_rx=self.cut_corners,
            bottom_right_ry=self.cut_corners,
            bottom_right_rounded_or_cut="cut",
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleMoleculeLayout(_MultiNodeMixin, CellDesignerNode):
    """Simple molecule layout."""

    width: float = 70.0
    height: float = 25.0
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCFF66")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleMoleculeActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Simple molecule active layout."""

    width: float = 70.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 25.0 + DEFAULT_ACTIVE_YSEP * 2
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonLayout(_MultiNodeMixin, CellDesignerNode):
    """Ion layout."""

    width: float = 35.0
    height: float = 35.0
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#9999FF")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Ion active layout."""

    width: float = 35.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 35.0 + DEFAULT_ACTIVE_YSEP * 2
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownLayout(_MultiNodeMixin, CellDesignerNode):
    """Unknown layout."""

    width: float = 60.0
    height: float = 30.0
    stroke: NoneValueType | Color | Gradient | None = NoneValue
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCCCCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Unknown active layout."""

    width: float = 60.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 30.0 + DEFAULT_ACTIVE_YSEP * 2
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesEllipse(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class _DegradedShape(Shape):
    """Degraded shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )

    def drawing_elements(self) -> list[DrawingElement]:
        circle = DrawingEllipse(
            point=self.position, rx=self.width / 2, ry=self.height / 2
        )
        actions = [
            MoveTo(self.position - (self.width / 2, -self.height / 2)),
            LineTo(self.position + (self.width / 2, -self.height / 2)),
        ]
        bar = Path(actions=actions)
        return [circle, bar]


@dataclasses.dataclass(frozen=True, kw_only=True)
class DegradedLayout(_MultiNodeMixin, CellDesignerNode):
    """Degraded layout."""

    width: float = 30.0
    height: float = 30.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _DegradedShape(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class DegradedActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Degraded active layout."""

    width: float = 30.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 30.0 + DEFAULT_ACTIVE_YSEP * 2
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _DegradedShape(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GeneLayout(_MultiNodeMixin, CellDesignerNode):
    """Gene layout."""

    width: float = 80.0
    height: float = 25.0
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#FFFFCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesRectangle(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GeneActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Gene active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 25.0 + DEFAULT_ACTIVE_YSEP * 2
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return MetaShapesRectangle(position=position, width=width, height=height)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhenotypeLayout(_MultiNodeMixin, CellDesignerNode):
    """Phenotype layout."""

    width: float = 80.0
    height: float = 30.0
    angle: float = dataclasses.field(
        default=60.0,
        metadata={
            "description": "The angle of the left and right points of the hexagon."
        },
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CC99FF")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Hexagon(
            position=position,
            width=width,
            height=height,
            left_angle=self.angle,
            right_angle=self.angle,
        )

    def north_west(self) -> Point:
        """Return the north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1()

    def north_north_west(self) -> Point:
        """Return the north-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.75 + shape.joint2() * 0.25

    def north(self) -> Point:
        """Return the north anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() / 2 + shape.joint2() / 2

    def north_north_east(self) -> Point:
        """Return the north-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.25 + shape.joint2() * 0.75

    def north_east(self) -> Point:
        """Return the north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint2()

    def east_north_east(self) -> Point:
        """Return the east-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() / 2 + shape.joint2() / 2

    def east(self) -> Point:
        """Return the east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3()

    def east_south_east(self) -> Point:
        """Return the east-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint3() / 2

    def south_east(self) -> Point:
        """Return the south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4()

    def south_south_east(self) -> Point:
        """Return the south-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5() * 0.25 + shape.joint4() * 0.75

    def south(self) -> Point:
        """Return the south anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5() / 2 + shape.joint4() / 2

    def south_south_west(self) -> Point:
        """Return the south-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5() * 0.75 + shape.joint4() * 0.25

    def south_west(self) -> Point:
        """Return the south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5()

    def west_south_west(self) -> Point:
        """Return the west-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() / 2 + shape.joint5() / 2

    def west(self) -> Point:
        """Return the west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6()

    def west_north_west(self) -> Point:
        """Return the west-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() / 2 + shape.joint1() / 2


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhenotypeActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Phenotype active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 30.0 + DEFAULT_ACTIVE_YSEP * 2
    angle: float = dataclasses.field(
        default=60.0,
        metadata={
            "description": "The angle of the left and right points of the hexagon."
        },
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Hexagon(
            position=position,
            width=width,
            height=height,
            left_angle=self.angle,
            right_angle=self.angle,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class RNALayout(_MultiNodeMixin, CellDesignerNode):
    """RNA layout."""

    width: float = 90.0
    height: float = 25.0
    angle: float = dataclasses.field(
        default=45.0, metadata={"description": "The slant angle of the parallelogram."}
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#66FF66")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Parallelogram(
            position=position, width=width, height=height, angle=self.angle
        )

    def north_west(self) -> Point:
        """Return the north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1()

    def north_north_west(self) -> Point:
        """Return the north-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.75 + shape.joint2() * 0.25

    def north(self) -> Point:
        """Return the north anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() / 2 + shape.joint2() / 2

    def north_north_east(self) -> Point:
        """Return the north-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.25 + shape.joint2() * 0.75

    def north_east(self) -> Point:
        """Return the north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint2()

    def east_north_east(self) -> Point:
        """Return the east-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() * 0.25 + shape.joint2() * 0.75

    def east(self) -> Point:
        """Return the east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() / 2 + shape.joint2() / 2

    def east_south_east(self) -> Point:
        """Return the east-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() * 0.75 + shape.joint2() * 0.25

    def south_east(self) -> Point:
        """Return the south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3()

    def south_south_east(self) -> Point:
        """Return the south-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.25 + shape.joint3() * 0.75

    def south(self) -> Point:
        """Return the south anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint3() / 2

    def south_south_west(self) -> Point:
        """Return the south-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.75 + shape.joint3() * 0.25

    def south_west(self) -> Point:
        """Return the south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4()

    def west_south_west(self) -> Point:
        """Return the west-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.75 + shape.joint1() * 0.25

    def west(self) -> Point:
        """Return the west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint1() / 2

    def west_north_west(self) -> Point:
        """Return the west-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.25 + shape.joint1() * 0.75


@dataclasses.dataclass(frozen=True, kw_only=True)
class RNAActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """RNA active layout."""

    width: float = 90.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 25.0 + DEFAULT_ACTIVE_YSEP * 2
    angle: float = dataclasses.field(
        default=45.0, metadata={"description": "The slant angle of the parallelogram."}
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Parallelogram(
            position=position, width=width, height=height, angle=self.angle
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AntisenseRNALayout(_MultiNodeMixin, CellDesignerNode):
    """Antisense RNA layout."""

    width: float = 90.0
    height: float = 25.0
    angle: float = dataclasses.field(
        default=45.0, metadata={"description": "The slant angle of the parallelogram."}
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#FFCCCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Parallelogram(
            position=position,
            width=width,
            height=height,
            angle=180 - self.angle,
        )

    def north_west(self) -> Point:
        """Return the north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1()

    def north_north_west(self) -> Point:
        """Return the north-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.75 + shape.joint2() * 0.25

    def north(self) -> Point:
        """Return the north anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() / 2 + shape.joint2() / 2

    def north_north_east(self) -> Point:
        """Return the north-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() * 0.25 + shape.joint2() * 0.75

    def north_east(self) -> Point:
        """Return the north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint2()

    def east_north_east(self) -> Point:
        """Return the east-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() * 0.25 + shape.joint2() * 0.75

    def east(self) -> Point:
        """Return the east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() / 2 + shape.joint2() / 2

    def east_south_east(self) -> Point:
        """Return the east-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3() * 0.75 + shape.joint2() * 0.25

    def south_east(self) -> Point:
        """Return the south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3()

    def south_south_east(self) -> Point:
        """Return the south-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.25 + shape.joint3() * 0.75

    def south(self) -> Point:
        """Return the south anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint3() / 2

    def south_south_west(self) -> Point:
        """Return the south-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.75 + shape.joint3() * 0.25

    def south_west(self) -> Point:
        """Return the south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4()

    def west_south_west(self) -> Point:
        """Return the west-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.75 + shape.joint1() * 0.25

    def west(self) -> Point:
        """Return the west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint1() / 2

    def west_north_west(self) -> Point:
        """Return the west-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.25 + shape.joint1() * 0.75


@dataclasses.dataclass(frozen=True, kw_only=True)
class AntisenseRNAActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Antisense RNA active layout."""

    width: float = 90.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 25.0 + DEFAULT_ACTIVE_YSEP * 2
    angle: float = dataclasses.field(
        default=45.0, metadata={"description": "The slant angle of the parallelogram."}
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return Parallelogram(
            position=position,
            width=width,
            height=height,
            angle=180 - self.angle,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _TruncatedProteinShape(Shape):
    """Truncated protein shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    rounded_corners: float = dataclasses.field(
        metadata={"description": "The radius of the rounded corners."}
    )
    vertical_truncation: float = dataclasses.field(
        metadata={
            "description": "The proportion of the height removed by the truncation."
        }
    )
    horizontal_truncation: float = dataclasses.field(
        metadata={
            "description": "The proportion of the width removed by the truncation."
        }
    )

    def joint1(self) -> Point:
        return self.position + (
            self.rounded_corners - self.width / 2,
            -self.height / 2,
        )

    def joint2(self) -> Point:
        return self.position + (
            self.width / 2,
            -self.height / 2,
        )

    def joint3(self) -> Point:
        return self.position + (
            self.width / 2,
            self.height / 2 - self.vertical_truncation * self.height,
        )

    def joint4(self) -> Point:
        return self.position + (
            self.width / 2 - self.horizontal_truncation * self.width,
            self.vertical_truncation * self.height - self.height / 2,
        )

    def joint5(self) -> Point:
        return self.position + (
            self.width / 2 - self.horizontal_truncation * self.width,
            self.height / 2,
        )

    def joint6(self) -> Point:
        return self.position + (
            self.rounded_corners - self.width / 2,
            self.height / 2,
        )

    def joint7(self) -> Point:
        return self.position + (
            -self.width / 2,
            self.height / 2 - self.rounded_corners,
        )

    def joint8(self) -> Point:
        return self.position + (
            -self.width / 2,
            self.rounded_corners - self.height / 2,
        )

    def drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(self.joint1()),
            LineTo(self.joint2()),
            LineTo(self.joint3()),
            LineTo(self.joint4()),
            LineTo(self.joint5()),
            LineTo(self.joint6()),
            EllipticalArc(
                self.joint7(),
                self.rounded_corners,
                self.rounded_corners,
                0,
                0,
                1,
            ),
            LineTo(self.joint8()),
            EllipticalArc(
                self.joint1(),
                self.rounded_corners,
                self.rounded_corners,
                0,
                0,
                1,
            ),
            ClosePath(),
        ]
        border = Path(actions=actions)
        return [border]


@dataclasses.dataclass(frozen=True, kw_only=True)
class TruncatedProteinLayout(_MultiNodeMixin, CellDesignerNode):
    """Truncated protein layout."""

    width: float = 80.0
    height: float = 50.0
    rounded_corners: float = dataclasses.field(
        default=15.0, metadata={"description": "The radius of the rounded corners."}
    )
    vertical_truncation: float = dataclasses.field(
        default=0.40,
        metadata={
            "description": "The proportion of the height removed by the truncation."
        },
    )
    horizontal_truncation: float = dataclasses.field(
        default=0.20,
        metadata={
            "description": "The proportion of the width removed by the truncation."
        },
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCFFCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _TruncatedProteinShape(
            position=position,
            width=width,
            height=height,
            rounded_corners=self.rounded_corners,
            vertical_truncation=self.vertical_truncation,
            horizontal_truncation=self.horizontal_truncation,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class TruncatedProteinActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Truncated protein active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 50.0 + DEFAULT_ACTIVE_YSEP * 2
    rounded_corners: float = dataclasses.field(
        default=15.0, metadata={"description": "The radius of the rounded corners."}
    )
    vertical_truncation: float = dataclasses.field(
        default=0.40,
        metadata={
            "description": "The proportion of the height removed by the truncation."
        },
    )
    horizontal_truncation: float = dataclasses.field(
        default=0.20,
        metadata={
            "description": "The proportion of the width removed by the truncation."
        },
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _TruncatedProteinShape(
            position=position,
            width=width,
            height=height,
            rounded_corners=self.rounded_corners,
            vertical_truncation=self.vertical_truncation,
            horizontal_truncation=self.horizontal_truncation,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReceptorLayout(_MultiNodeMixin, CellDesignerNode):
    """Receptor layout."""

    width: float = 80.0
    height: float = 40.0
    vertical_truncation: float = dataclasses.field(
        default=0.10,
        metadata={"description": "The proportion of the height taken by the notch."},
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#CCFFCC")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        angle = math.atan2(width / 2, self.vertical_truncation * height)
        angle = get_normalized_angle(angle)
        angle = math.degrees(angle)
        return TurnedHexagon(
            position=position,
            width=width,
            height=height,
            top_angle=180 - angle,
            bottom_angle=angle,
        )

    def north_west(self) -> Point:
        """Return the north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1()

    def north_north_west(self) -> Point:
        """Return the north-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint1() / 2 + shape.joint2() / 2

    def north(self) -> Point:
        """Return the north anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint2()

    def north_north_east(self) -> Point:
        """Return the north-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint2() * 0.25 + shape.joint3() * 0.75

    def north_east(self) -> Point:
        """Return the north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint3()

    def east_north_east(self) -> Point:
        """Return the east-north-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.25 + shape.joint3() * 0.75

    def east(self) -> Point:
        """Return the east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() / 2 + shape.joint3() / 2

    def east_south_east(self) -> Point:
        """Return the east-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4() * 0.75 + shape.joint3() * 0.25

    def south_east(self) -> Point:
        """Return the south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint4()

    def south_south_east(self) -> Point:
        """Return the south-south-east anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5() / 2 + shape.joint4() / 2

    def south(self) -> Point:
        """Return the south anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint5()

    def south_south_west(self) -> Point:
        """Return the south-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() / 2 + shape.joint5() / 2

    def south_west(self) -> Point:
        """Return the south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6()

    def west_south_west(self) -> Point:
        """Return the west-south-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() * 0.75 + shape.joint1() * 0.25

    def west(self) -> Point:
        """Return the west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() / 2 + shape.joint1() / 2

    def west_north_west(self) -> Point:
        """Return the west-north-west anchor point of the top subunit shape."""
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2,
            self.height / 2 - height / 2,
        )
        shape = self._make_subunit_shape(position, width, height)
        return shape.joint6() * 0.25 + shape.joint1() * 0.75


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReceptorActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Receptor active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 40.0 + DEFAULT_ACTIVE_YSEP * 2
    vertical_truncation: float = dataclasses.field(
        default=0.10,
        metadata={"description": "The proportion of the height taken by the notch."},
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        angle = math.atan2(width / 2, self.vertical_truncation * height)
        angle = get_normalized_angle(angle)
        angle = math.degrees(angle)
        return TurnedHexagon(
            position=position,
            width=width,
            height=height,
            top_angle=180 - angle,
            bottom_angle=angle,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _DrugShape(Shape):
    """Drug shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    horizontal_proportion: float = dataclasses.field(
        metadata={
            "description": "The proportion of the width taken by each rounded end."
        }
    )
    sep: float = dataclasses.field(
        metadata={"description": "The separation between the outer and inner outlines."}
    )

    def joint1(self) -> Point:
        return self.position + (
            -self.width / 2 + self.horizontal_proportion * self.width,
            -self.height / 2,
        )

    def joint2(self) -> Point:
        return self.position + (
            self.width / 2 - self.horizontal_proportion * self.width,
            -self.height / 2,
        )

    def joint3(self) -> Point:
        return self.position + (
            self.width / 2 - self.horizontal_proportion * self.width,
            self.height / 2,
        )

    def joint4(self) -> Point:
        return self.position + (
            -self.width / 2 + self.horizontal_proportion * self.width,
            self.height / 2,
        )

    def drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(self.joint1()),
            LineTo(self.joint2()),
            EllipticalArc(
                self.joint3(),
                self.horizontal_proportion * self.width,
                self.height / 2,
                0,
                0,
                1,
            ),
            LineTo(self.joint4()),
            EllipticalArc(
                self.joint1(),
                self.horizontal_proportion * self.width,
                self.height / 2,
                0,
                0,
                1,
            ),
            ClosePath(),
        ]
        outer_stadium = Path(actions=actions)
        inner_joint1 = self.joint1() + (0, self.sep)
        inner_joint2 = self.joint2() + (0, self.sep)
        inner_joint3 = self.joint3() + (0, -self.sep)
        inner_joint4 = self.joint4() + (0, -self.sep)
        inner_rx = self.horizontal_proportion * self.width - self.sep
        inner_ry = self.height / 2 - self.sep
        actions = [
            MoveTo(inner_joint1),
            LineTo(inner_joint2),
            EllipticalArc(
                inner_joint3,
                inner_rx,
                inner_ry,
                0,
                0,
                1,
            ),
            LineTo(inner_joint4),
            EllipticalArc(
                inner_joint1,
                inner_rx,
                inner_ry,
                0,
                0,
                1,
            ),
            ClosePath(),
        ]
        inner_stadium = Path(actions=actions)
        return [outer_stadium, inner_stadium]


@dataclasses.dataclass(frozen=True, kw_only=True)
class DrugLayout(_MultiNodeMixin, CellDesignerNode):
    """Drug layout."""

    width: float = 80.0
    height: float = 30.0
    horizontal_proportion: float = dataclasses.field(
        default=0.20,
        metadata={
            "description": "The proportion of the width taken by each rounded end."
        },
    )
    sep: float = dataclasses.field(
        default=4.0,
        metadata={
            "description": "The separation between the outer and inner outlines."
        },
    )
    fill: NoneValueType | Color | Gradient | None = Color.from_hex("#FF00FF")
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _DrugShape(
            position=position,
            width=width,
            height=height,
            horizontal_proportion=self.horizontal_proportion,
            sep=self.sep,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class DrugActiveLayout(_MultiNodeMixin, CellDesignerNode):
    """Drug active layout."""

    width: float = 80.0 + DEFAULT_ACTIVE_XSEP * 2
    height: float = 30.0 + DEFAULT_ACTIVE_YSEP * 2
    horizontal_proportion: float = dataclasses.field(
        default=0.20,
        metadata={
            "description": "The proportion of the width taken by each rounded end."
        },
    )
    sep: float = dataclasses.field(
        default=4.0,
        metadata={
            "description": "The separation between the outer and inner outlines."
        },
    )
    fill: NoneValueType | Color | Gradient | None = NoneValue
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        4,
        2,
    )
    stroke_width: float | None = 1.0

    def _make_subunit_shape(
        self, position: Point, width: float, height: float
    ) -> Shape:
        return _DrugShape(
            position=position,
            width=width,
            height=height,
            horizontal_proportion=self.horizontal_proportion,
            sep=self.sep,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class StructuralStateLayout(_SimpleNodeMixin, CellDesignerNode):
    """Structural state layout."""

    width: float = 50.0
    height: float = 16.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModificationLayout(_SimpleNodeMixin, CellDesignerNode):
    """Modification layout."""

    width: float = 16.0
    height: float = 16.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _OvalCompartmentShape(Shape):
    """Oval compartment shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    inner_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The fill color of the inner ellipse."}
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The stroke color of the inner ellipse."}
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=None, metadata={"description": "The stroke width of the inner ellipse."}
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={
            "description": "The separation between the outer and inner ellipses."
        },
    )

    def drawing_elements(self) -> list[DrawingElement]:
        outer_oval = DrawingEllipse(
            point=self.position,
            rx=self.width / 2,
            ry=self.height / 2,
        )
        inner_oval = DrawingEllipse(
            fill=self.inner_fill,
            stroke=self.inner_stroke,
            stroke_width=self.inner_stroke_width,
            point=self.position,
            rx=self.width / 2 - self.sep,
            ry=self.height / 2 - self.sep,
        )
        return [outer_oval, inner_oval]


@dataclasses.dataclass(frozen=True, kw_only=True)
class OvalCompartmentLayout(_SimpleNodeMixin, CellDesignerNode):
    """Oval compartment layout."""

    height: float = 16.0
    inner_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=white, metadata={"description": "The fill color of the inner ellipse."}
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=black,
        metadata={"description": "The stroke color of the inner ellipse."},
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=1.0, metadata={"description": "The stroke width of the inner ellipse."}
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={
            "description": "The separation between the outer and inner ellipses."
        },
    )
    width: float = 16.0

    def _make_shape(self) -> Shape:
        return _OvalCompartmentShape(
            height=self.height,
            inner_fill=self.inner_fill,
            inner_stroke=self.inner_stroke,
            inner_stroke_width=self.inner_stroke_width,
            position=self.position,
            width=self.width,
            sep=self.sep,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _RectangleCompartmentShape(Shape):
    """Rectangle compartment shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    inner_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The fill color of the inner rectangle."}
    )
    inner_rounded_corners: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The corner radius of the inner rectangle."},
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke color of the inner rectangle."},
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke width of the inner rectangle."},
    )
    rounded_corners: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The corner radius of the outer rectangle."},
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={
            "description": "The separation between the outer and inner rectangles."
        },
    )

    def drawing_elements(self) -> list[DrawingElement]:
        outer_rectangle = DrawingRectangle(
            point=self.position - (self.width / 2, self.height / 2),
            height=self.height,
            rx=self.rounded_corners,
            ry=self.rounded_corners,
            width=self.width,
        )
        inner_rectangle = DrawingRectangle(
            fill=self.inner_fill,
            height=self.height - 2 * self.sep,
            point=self.position
            - (self.width / 2 - self.sep, self.height / 2 - self.sep),
            rx=self.inner_rounded_corners,
            ry=self.inner_rounded_corners,
            stroke=self.inner_stroke,
            stroke_width=self.inner_stroke_width,
            width=self.width - 2 * self.sep,
        )
        return [outer_rectangle, inner_rectangle]


@dataclasses.dataclass(frozen=True, kw_only=True)
class RectangleCompartmentLayout(_SimpleNodeMixin, CellDesignerNode):
    """Rectangle compartment layout."""

    width: float = 16.0
    height: float = 16.0
    inner_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=white,
        metadata={"description": "The fill color of the inner rectangle."},
    )
    inner_rounded_corners: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The corner radius of the inner rectangle."},
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=black,
        metadata={"description": "The stroke color of the inner rectangle."},
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=1.0,
        metadata={"description": "The stroke width of the inner rectangle."},
    )
    rounded_corners: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The corner radius of the outer rectangle."},
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={
            "description": "The separation between the outer and inner rectangles."
        },
    )

    def _make_shape(self) -> Shape:
        return _RectangleCompartmentShape(
            height=self.height,
            inner_fill=self.inner_fill,
            inner_rounded_corners=self.inner_rounded_corners,
            inner_stroke=self.inner_stroke,
            inner_stroke_width=self.inner_stroke_width,
            position=self.position,
            rounded_corners=self.rounded_corners,
            sep=self.sep,
            width=self.width,
        )


class CompartmentCorner(enum.Enum):
    """Compartment corner."""

    NORTHWEST = "NORTHWEST"
    NORTHEAST = "NORTHEAST"
    SOUTHWEST = "SOUTHWEST"
    SOUTHEAST = "SOUTHEAST"


class CompartmentSide(enum.Enum):
    """Compartment side."""

    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"


@dataclasses.dataclass(frozen=True, kw_only=True)
class _CornerCompartmentShape(Shape):
    """Corner compartment shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    corner: CompartmentCorner = dataclasses.field(
        metadata={"description": "The corner where the rounded border sits."}
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The stroke color of the inner border."}
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=None, metadata={"description": "The stroke width of the inner border."}
    )
    rounded_corners: float = dataclasses.field(
        default=40.0,
        metadata={"description": "The corner radius of the rounded border."},
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={"description": "The separation between the outer and inner borders."},
    )

    def drawing_elements(self) -> list[DrawingElement]:
        left = self.position.x - self.width / 2
        right = self.position.x + self.width / 2
        top = self.position.y - self.height / 2
        bottom = self.position.y + self.height / 2
        sep = self.sep
        r_outer = self.rounded_corners
        r_inner = max(r_outer - sep, 0.0)
        P = Point
        if self.corner is CompartmentCorner.NORTHWEST:
            outer_start = P(right, top)
            outer_tan_a = P(left + r_outer, top)
            outer_corner = P(left, top)
            outer_tan_b = P(left, top + r_outer)
            outer_end = P(left, bottom)
            inner_start = P(right, top + sep)
            inner_tan_a = P(left + r_outer, top + sep)
            inner_corner = P(left + sep, top + sep)
            inner_tan_b = P(left + sep, top + r_outer)
            inner_end = P(left + sep, bottom)
        elif self.corner is CompartmentCorner.NORTHEAST:
            outer_start = P(left, top)
            outer_tan_a = P(right - r_outer, top)
            outer_corner = P(right, top)
            outer_tan_b = P(right, top + r_outer)
            outer_end = P(right, bottom)
            inner_start = P(left, top + sep)
            inner_tan_a = P(right - r_outer, top + sep)
            inner_corner = P(right - sep, top + sep)
            inner_tan_b = P(right - sep, top + r_outer)
            inner_end = P(right - sep, bottom)
        elif self.corner is CompartmentCorner.SOUTHWEST:
            outer_start = P(right, bottom)
            outer_tan_a = P(left + r_outer, bottom)
            outer_corner = P(left, bottom)
            outer_tan_b = P(left, bottom - r_outer)
            outer_end = P(left, top)
            inner_start = P(right, bottom - sep)
            inner_tan_a = P(left + r_outer, bottom - sep)
            inner_corner = P(left + sep, bottom - sep)
            inner_tan_b = P(left + sep, bottom - r_outer)
            inner_end = P(left + sep, top)
        else:  # SOUTHEAST
            outer_start = P(left, bottom)
            outer_tan_a = P(right - r_outer, bottom)
            outer_corner = P(right, bottom)
            outer_tan_b = P(right, bottom - r_outer)
            outer_end = P(right, top)
            inner_start = P(left, bottom - sep)
            inner_tan_a = P(right - r_outer, bottom - sep)
            inner_corner = P(right - sep, bottom - sep)
            inner_tan_b = P(right - sep, bottom - r_outer)
            inner_end = P(right - sep, top)
        if r_inner <= 0:
            inner_tan_a = inner_corner
            inner_tan_b = inner_corner
        fill_path = Path(
            stroke=NoneValue,
            actions=(
                MoveTo(outer_start),
                LineTo(outer_tan_a),
                QuadraticCurveTo(point=outer_tan_b, control_point=outer_corner),
                LineTo(outer_end),
                LineTo(inner_end),
                LineTo(inner_tan_b),
                QuadraticCurveTo(point=inner_tan_a, control_point=inner_corner),
                LineTo(inner_start),
                ClosePath(),
            ),
        )
        outer_path = Path(
            fill=NoneValue,
            actions=(
                MoveTo(outer_start),
                LineTo(outer_tan_a),
                QuadraticCurveTo(point=outer_tan_b, control_point=outer_corner),
                LineTo(outer_end),
            ),
        )
        inner_path = Path(
            fill=NoneValue,
            stroke=self.inner_stroke,
            stroke_width=self.inner_stroke_width,
            actions=(
                MoveTo(inner_start),
                LineTo(inner_tan_a),
                QuadraticCurveTo(point=inner_tan_b, control_point=inner_corner),
                LineTo(inner_end),
            ),
        )
        return [fill_path, outer_path, inner_path]


@dataclasses.dataclass(frozen=True, kw_only=True)
class CornerCompartmentLayout(_SimpleNodeMixin, CellDesignerNode):
    """Corner compartment layout."""

    width: float = 16.0
    height: float = 16.0
    corner: CompartmentCorner = dataclasses.field(
        default=CompartmentCorner.NORTHWEST,
        metadata={"description": "The corner where the rounded border sits."},
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=black,
        metadata={"description": "The stroke color of the inner border."},
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=1.0,
        metadata={"description": "The stroke width of the inner border."},
    )
    rounded_corners: float = dataclasses.field(
        default=40.0,
        metadata={"description": "The corner radius of the rounded border."},
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={"description": "The separation between the outer and inner borders."},
    )

    def _make_shape(self) -> Shape:
        return _CornerCompartmentShape(
            position=self.position,
            width=self.width,
            height=self.height,
            corner=self.corner,
            inner_stroke=self.inner_stroke,
            inner_stroke_width=self.inner_stroke_width,
            rounded_corners=self.rounded_corners,
            sep=self.sep,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _LineCompartmentShape(Shape):
    """Line compartment shape."""

    position: Point = dataclasses.field(
        metadata={"description": "The center position of the shape."}
    )
    width: float = dataclasses.field(
        metadata={"description": "The width of the shape."}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the shape."}
    )
    side: CompartmentSide = dataclasses.field(
        metadata={"description": "The side bounded by the double line."}
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The stroke color of the inner line."}
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=None, metadata={"description": "The stroke width of the inner line."}
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={"description": "The separation between the outer and inner lines."},
    )

    def drawing_elements(self) -> list[DrawingElement]:
        left = self.position.x - self.width / 2
        right = self.position.x + self.width / 2
        top = self.position.y - self.height / 2
        bottom = self.position.y + self.height / 2
        sep = self.sep
        P = Point
        if self.side is CompartmentSide.NORTH:
            outer_a, outer_b = P(left, top), P(right, top)
            inner_a, inner_b = P(left, top + sep), P(right, top + sep)
        elif self.side is CompartmentSide.SOUTH:
            outer_a, outer_b = P(left, bottom), P(right, bottom)
            inner_a, inner_b = P(left, bottom - sep), P(right, bottom - sep)
        elif self.side is CompartmentSide.EAST:
            outer_a, outer_b = P(right, top), P(right, bottom)
            inner_a, inner_b = P(right - sep, top), P(right - sep, bottom)
        else:  # WEST
            outer_a, outer_b = P(left, top), P(left, bottom)
            inner_a, inner_b = P(left + sep, top), P(left + sep, bottom)
        fill_path = Path(
            stroke=NoneValue,
            actions=(
                MoveTo(outer_a),
                LineTo(outer_b),
                LineTo(inner_b),
                LineTo(inner_a),
                ClosePath(),
            ),
        )
        outer_path = Path(
            fill=NoneValue,
            actions=(
                MoveTo(outer_a),
                LineTo(outer_b),
            ),
        )
        inner_path = Path(
            fill=NoneValue,
            stroke=self.inner_stroke,
            stroke_width=self.inner_stroke_width,
            actions=(
                MoveTo(inner_a),
                LineTo(inner_b),
            ),
        )
        return [fill_path, outer_path, inner_path]


@dataclasses.dataclass(frozen=True, kw_only=True)
class LineCompartmentLayout(_SimpleNodeMixin, CellDesignerNode):
    """Line compartment layout."""

    width: float = 16.0
    height: float = 16.0
    side: CompartmentSide = dataclasses.field(
        default=CompartmentSide.NORTH,
        metadata={"description": "The side bounded by the double line."},
    )
    inner_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=black, metadata={"description": "The stroke color of the inner line."}
    )
    inner_stroke_width: float | None = dataclasses.field(
        default=1.0, metadata={"description": "The stroke width of the inner line."}
    )
    sep: float = dataclasses.field(
        default=12.0,
        metadata={"description": "The separation between the outer and inner lines."},
    )

    def _make_shape(self) -> Shape:
        return _LineCompartmentShape(
            position=self.position,
            width=self.width,
            height=self.height,
            side=self.side,
            inner_stroke=self.inner_stroke,
            inner_stroke_width=self.inner_stroke_width,
            sep=self.sep,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ConsumptionLayout(CellDesignerSingleHeadedArc):
    """Consumption layout."""

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return PolyLine._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProductionLayout(CellDesignerSingleHeadedArc):
    """Production layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = black
    arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the arrowhead."}
    )
    end_shorten: float = 2.0

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return MetaArcsTriangle._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class CatalysisLayout(CellDesignerSingleHeadedArc):
    """Catalysis layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=7.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=7.0, metadata={"description": "The width of the arrowhead."}
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return MetaArcsEllipse._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownCatalysisLayout(CellDesignerSingleHeadedArc):
    """Unknown catalysis layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=7.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=7.0, metadata={"description": "The width of the arrowhead."}
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return MetaArcsEllipse._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class InhibitionLayout(CellDesignerSingleHeadedArc):
    """Inhibition layout."""

    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead bar."}
    )
    end_shorten: float = 3.0

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return Bar._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownInhibitionLayout(CellDesignerSingleHeadedArc):
    """Unknown inhibition layout."""

    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead bar."}
    )
    end_shorten: float = 3.0
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return Bar._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhysicalStimulationLayout(CellDesignerSingleHeadedArc):
    """Physical stimulation layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the arrowhead."}
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return MetaArcsTriangle._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownPhysicalStimulationLayout(CellDesignerSingleHeadedArc):
    """Unknown physical stimulation layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the arrowhead."}
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return MetaArcsTriangle._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModulationLayout(CellDesignerSingleHeadedArc):
    """Modulation layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the arrowhead."}
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return Diamond._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownModulationLayout(CellDesignerSingleHeadedArc):
    """Unknown modulation layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the arrowhead."}
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return Diamond._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class PositiveInfluenceLayout(CellDesignerSingleHeadedArc):
    """Positive influence layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = NoneValue
    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_stroke_width: float | None = 2.0
    arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the arrowhead."}
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return StraightBarb._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownPositiveInfluenceLayout(CellDesignerSingleHeadedArc):
    """Unknown positive influence layout."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = NoneValue
    arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead."}
    )
    arrowhead_stroke_width: float | None = 2.0
    arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the arrowhead."}
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return StraightBarb._arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class TriggeringLayout(CellDesignerSingleHeadedArc):
    """Triggering layout."""

    arrowhead_bar_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the arrowhead bar."}
    )
    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_sep: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The separation between the bar and the triangle."},
    )
    arrowhead_triangle_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead triangle."}
    )
    arrowhead_triangle_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the arrowhead triangle."}
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(Point(0, -self.arrowhead_bar_height / 2)),
            LineTo(Point(0, self.arrowhead_bar_height / 2)),
        ]
        bar = Path(actions=actions)
        actions = [
            MoveTo(Point(0.0, 0.0)),
            LineTo(Point(self.arrowhead_sep, 0)),
        ]
        sep = Path(actions=actions)
        triangle = MetaShapesTriangle(
            position=Point(
                self.arrowhead_sep + self.arrowhead_triangle_width / 2,
                0,
            ),
            width=self.arrowhead_triangle_width,
            height=self.arrowhead_triangle_height,
            direction=Direction.RIGHT,
        )
        return [bar, sep] + triangle.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownTriggeringLayout(CellDesignerSingleHeadedArc):
    """Unknown triggering layout."""

    arrowhead_bar_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the arrowhead bar."}
    )
    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_sep: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The separation between the bar and the triangle."},
    )
    arrowhead_triangle_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the arrowhead triangle."}
    )
    arrowhead_triangle_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the arrowhead triangle."}
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (12, 4)

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(Point(0, -self.arrowhead_bar_height / 2)),
            LineTo(Point(0, self.arrowhead_bar_height / 2)),
        ]
        bar = Path(actions=actions)
        actions = [
            MoveTo(Point(0.0, 0.0)),
            LineTo(Point(self.arrowhead_sep, 0)),
        ]
        sep = Path(actions=actions)
        triangle = MetaShapesTriangle(
            position=Point(
                self.arrowhead_sep + self.arrowhead_triangle_width / 2,
                0,
            ),
            width=self.arrowhead_triangle_width,
            height=self.arrowhead_triangle_height,
            direction=Direction.RIGHT,
        )
        return [bar, sep] + triangle.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReactionLayout(CellDesignerDoubleHeadedArc):
    """Reaction layout."""

    reversible: bool = dataclasses.field(
        default=False, metadata={"description": "Whether the reaction is reversible."}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class _ReactionNodeMixin(_SBGNMixin):
    """Reaction node mixin."""

    _font_size_func: typing.ClassVar[typing.Callable] = (
        lambda obj: obj.reaction_node_width / 1.1
    )
    left_connector_fraction: float = dataclasses.field(
        default=0.375,
        metadata={
            "description": "The fraction along the segment where the left connector attaches."
        },
    )
    right_connector_fraction: float = dataclasses.field(
        default=0.625,
        metadata={
            "description": "The fraction along the segment where the right connector attaches."
        },
    )
    reaction_node_font_family: str = dataclasses.field(
        default=DEFAULT_FONT_FAMILY,
        metadata={"description": "The font family of the reaction node label."},
    )
    reaction_node_font_fill: Color | Gradient | NoneValueType = dataclasses.field(
        default=black,
        metadata={"description": "The fill color of the reaction node label."},
    )
    reaction_node_font_stroke: Color | Gradient | NoneValueType = dataclasses.field(
        default=NoneValue,
        metadata={"description": "The stroke color of the reaction node label."},
    )
    reaction_node_font_style: FontStyle = dataclasses.field(
        default=FontStyle.NORMAL,
        metadata={"description": "The font style of the reaction node label."},
    )
    reaction_node_font_weight: FontWeight | float = dataclasses.field(
        default=FontWeight.NORMAL,
        metadata={"description": "The font weight of the reaction node label."},
    )
    reaction_node_text: str | None = dataclasses.field(
        default=None, metadata={"description": "The text of the reaction node label."}
    )
    reaction_node_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the reaction node."}
    )
    reaction_node_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the reaction node."}
    )
    reaction_node_segment: int = dataclasses.field(
        default=1,
        metadata={
            "description": "The index of the arc segment carrying the reaction node."
        },
    )
    reaction_node_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=black,
        metadata={"description": "The stroke color of the reaction node."},
    )
    reaction_node_stroke_width: float | None = dataclasses.field(
        default=1.0, metadata={"description": "The stroke width of the reaction node."}
    )
    reaction_node_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The dash pattern of the reaction node's border."},
        )
    )
    reaction_node_stroke_dashoffset: float | None = dataclasses.field(
        default=None,
        metadata={"description": "The dash offset of the reaction node's border."},
    )
    reaction_node_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The line cap of the reaction node's border."},
    )
    reaction_node_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The line join of the reaction node's border."},
    )
    reaction_node_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=white, metadata={"description": "The fill color of the reaction node."}
    )
    reaction_node_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The transform applied to the reaction node."},
        )
    )
    reaction_node_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The filter applied to the reaction node."},
    )

    def left_connector_tip(self) -> Point:
        segment = self.segments[self.reaction_node_segment]
        position = segment.get_position_at_fraction(self.left_connector_fraction)
        return position

    def right_connector_tip(self) -> Point:
        segment = self.segments[self.reaction_node_segment]
        position = segment.get_position_at_fraction(self.right_connector_fraction)
        return position

    def reaction_node_border(self, point: Point) -> Point:
        reaction_node = self._make_reaction_node()
        rotation = self._make_reaction_node_rotation()
        rotated_point = point.transformed(rotation)
        border_point = reaction_node.own_border(rotated_point)
        if border_point is None:
            border_point = reaction_node.center()
        border_point = border_point.transformed(rotation.inverted())
        return border_point

    def reaction_node_angle(self, angle: float) -> Point:
        reaction_node = self._make_reaction_node()
        border_point = reaction_node.own_angle(
            angle, self._get_reaction_node_position()
        )
        if border_point is None:
            border_point = reaction_node.center()
        rotation = self._make_reaction_node_rotation()
        border_point = border_point.transformed(
            rotation, self._get_reaction_node_position()
        )
        return border_point

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        return [obj._make_rotated_reaction_node_drawing_element()]

    def _get_reaction_node_position(self) -> Point:
        segment = self.segments[self.reaction_node_segment]
        position = segment.get_position_at_fraction(0.5)
        return position

    def _get_reaction_node_rotation_angle(self) -> float:
        segment = self.segments[self.reaction_node_segment]
        angle = segment.get_angle_to_horizontal()
        return angle

    def _make_reaction_node_rotation(self) -> Rotation:
        angle = self._get_reaction_node_rotation_angle()
        position = self._get_reaction_node_position()
        rotation = Rotation(angle, position)
        return rotation

    def _make_reaction_node(self) -> MetaNodesRectangle:
        position = self._get_reaction_node_position()
        if self.reaction_node_text is not None:
            label = TextLayout(
                text=self.reaction_node_text,
                position=position,
                font_family=self.reaction_node_font_family,
                font_size=self._font_size_func(),
                font_style=self.reaction_node_font_style,
                font_weight=self.reaction_node_font_weight,
                fill=self.reaction_node_font_fill,
                stroke=self.reaction_node_font_stroke,
                transform=(self._make_reaction_node_rotation(),),
            )
        else:
            label = None
        reaction_node = MetaNodesRectangle(
            height=self.reaction_node_height,
            position=position,
            width=self.reaction_node_width,
            stroke=self.reaction_node_stroke,
            stroke_width=self.reaction_node_stroke_width,
            stroke_dasharray=self.reaction_node_stroke_dasharray,
            stroke_dashoffset=self.reaction_node_stroke_dashoffset,
            stroke_linecap=self.reaction_node_stroke_linecap,
            stroke_linejoin=self.reaction_node_stroke_linejoin,
            fill=self.reaction_node_fill,
            transform=self.reaction_node_transform,
            filter_=self.reaction_node_filter,
            label=label,
        )
        return reaction_node

    def _make_rotated_reaction_node_drawing_element(self) -> DrawingElement:
        reaction_node = self._make_reaction_node()
        drawing_element = reaction_node.drawing_elements()[0]
        rotation = self._make_reaction_node_rotation()
        drawing_element = drawing_element.transformed(rotation)
        return drawing_element


@dataclasses.dataclass(frozen=True, kw_only=True)
class StateTransitionLayout(ReactionLayout, _ReactionNodeMixin):
    """State transition layout."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class KnownTransitionOmittedLayout(ReactionLayout, _ReactionNodeMixin):
    """Known transition omitted layout."""

    reaction_node_font_weight: FontWeight | float = dataclasses.field(
        default=FontWeight.BOLD,
        metadata={"description": "The font weight of the reaction node label."},
    )
    reaction_node_text: str | None = dataclasses.field(
        default="//", metadata={"description": "The text of the reaction node label."}
    )
    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownTransitionLayout(ReactionLayout, _ReactionNodeMixin):
    """Unknown transition layout."""

    reaction_node_font_weight: FontWeight | float = dataclasses.field(
        default=FontWeight.BOLD,
        metadata={"description": "The font weight of the reaction node label."},
    )
    reaction_node_text: str | None = dataclasses.field(
        default="?", metadata={"description": "The text of the reaction node label."}
    )
    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class TranscriptionLayout(ReactionLayout, _ReactionNodeMixin):
    """Transcription layout."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        12,
        4,
        2,
        4,
        2,
        4,
    )
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class TranslationLayout(ReactionLayout, _ReactionNodeMixin):
    """Translation layout."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        12,
        4,
        2,
        4,
    )
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)


@dataclasses.dataclass(frozen=True, kw_only=True)
class TransportLayout(ReactionLayout, _ReactionNodeMixin):
    """Transport layout."""

    end_arrowhead_bar_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead bar."}
    )
    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_sep: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The separation between the end bar and triangle."},
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_triangle_height: float = dataclasses.field(
        default=8.0,
        metadata={"description": "The height of the end arrowhead triangle."},
    )
    end_arrowhead_triangle_width: float = dataclasses.field(
        default=15.0,
        metadata={"description": "The width of the end arrowhead triangle."},
    )
    end_shorten: float = 2.0
    start_arrowhead_bar_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead bar."}
    )
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_sep: float = dataclasses.field(
        default=4.0,
        metadata={"description": "The separation between the start bar and triangle."},
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_triangle_height: float = dataclasses.field(
        default=8.0,
        metadata={"description": "The height of the start arrowhead triangle."},
    )
    start_arrowhead_triangle_width: float = dataclasses.field(
        default=15.0,
        metadata={"description": "The width of the start arrowhead triangle."},
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            actions = [
                MoveTo(Point(0, -self.start_arrowhead_bar_height / 2)),
                LineTo(Point(0, self.start_arrowhead_bar_height / 2)),
            ]
            bar = Path(actions=actions)
            actions = [
                MoveTo(Point(0.0, 0.0)),
                LineTo(Point(-self.start_arrowhead_sep, 0)),
            ]
            sep = Path(actions=actions)
            triangle = MetaShapesTriangle(
                position=Point(
                    -self.start_arrowhead_sep - self.start_arrowhead_triangle_width / 2,
                    0,
                ),
                width=self.start_arrowhead_triangle_width,
                height=self.start_arrowhead_triangle_height,
                direction=Direction.LEFT,
            )
            return [bar, sep] + triangle.drawing_elements()
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(Point(0, -self.end_arrowhead_bar_height / 2)),
            LineTo(Point(0, self.end_arrowhead_bar_height / 2)),
        ]
        bar = Path(actions=actions)
        actions = [
            MoveTo(Point(0.0, 0.0)),
            LineTo(Point(self.end_arrowhead_sep, 0)),
        ]
        sep = Path(actions=actions)
        triangle = MetaShapesTriangle(
            position=Point(
                self.end_arrowhead_sep + self.end_arrowhead_triangle_width / 2,
                0,
            ),
            width=self.end_arrowhead_triangle_width,
            height=self.end_arrowhead_triangle_height,
            direction=Direction.RIGHT,
        )
        return [bar, sep] + triangle.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class HeterodimerAssociationLayout(ReactionLayout, _ReactionNodeMixin):
    """Heterodimer association layout."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=6.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=6.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return DoubleTriangle._end_arrowhead_border_drawing_elements(self)

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = MetaShapesEllipse(
            position=Point(0.0, 0.0),
            width=self.start_arrowhead_width,
            height=self.start_arrowhead_height,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class DissociationLayout(ReactionLayout, _ReactionNodeMixin):
    """Dissociation layout."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = white
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_sep: float = dataclasses.field(
        default=2.0,
        metadata={
            "description": "The separation between the outer and inner end circles."
        },
    )
    end_arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        if self.reversible:
            return DoubleTriangle._start_arrowhead_border_drawing_elements(self)
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        outer_circle = MetaShapesEllipse(
            position=Point(0.0, 0.0),
            width=self.end_arrowhead_width,
            height=self.end_arrowhead_height,
        )
        inner_circle = MetaShapesEllipse(
            position=Point(0.0, 0.0),
            width=self.end_arrowhead_width - 2 * self.end_arrowhead_sep,
            height=self.end_arrowhead_height - 2 * self.end_arrowhead_sep,
        )
        return outer_circle.drawing_elements() + inner_circle.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class TruncationLayout(ReactionLayout, _ReactionNodeMixin):
    """Truncation layout."""

    reaction_node_font_weight: FontWeight | float = dataclasses.field(
        default=FontWeight.BOLD,
        metadata={"description": "The font weight of the reaction node label."},
    )
    reaction_node_text: str | None = dataclasses.field(
        default="N", metadata={"description": "The text of the reaction node label."}
    )
    end_arrowhead_fill: NoneValueType | Color | Gradient | None = white
    end_arrowhead_filter: NoneValueType | Filter | None = None
    end_arrowhead_height: float = dataclasses.field(
        default=10.0, metadata={"description": "The height of the end arrowhead."}
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    end_arrowhead_stroke_dashoffset: float | None = None
    end_arrowhead_stroke_width: float | None = 1.0
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    end_arrowhead_sep: float = dataclasses.field(
        default=2.0,
        metadata={
            "description": "The separation between the outer and inner end circles."
        },
    )
    end_arrowhead_width: float = dataclasses.field(
        default=10.0, metadata={"description": "The width of the end arrowhead."}
    )
    end_shorten: float = 2.0
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = black
    start_arrowhead_filter: NoneValueType | Filter | None = None
    start_arrowhead_height: float = dataclasses.field(
        default=8.0, metadata={"description": "The height of the start arrowhead."}
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = None
    start_arrowhead_stroke_dashoffset: float | None = None
    start_arrowhead_stroke_width: float | None = 1.0
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = None
    start_arrowhead_width: float = dataclasses.field(
        default=15.0, metadata={"description": "The width of the start arrowhead."}
    )
    start_shorten: float = 2.0

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return []

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return []


@dataclasses.dataclass(frozen=True, kw_only=True)
class AndGateLayout(
    _SimpleNodeMixin,
    _TextMixin,
    CellDesignerNode,
):
    """AND gate layout."""

    _font_size_func: typing.ClassVar[typing.Callable] = lambda obj: obj.width
    text: str = dataclasses.field(
        default="&", metadata={"description": "The label drawn inside the gate."}
    )
    width: float = 15.0
    height: float = 15.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class OrGateLayout(
    _SimpleNodeMixin,
    _TextMixin,
    CellDesignerNode,
):
    """OR gate layout."""

    _font_size_func: typing.ClassVar[typing.Callable] = lambda obj: obj.width / 3
    text: str = dataclasses.field(
        default="|", metadata={"description": "The label drawn inside the gate."}
    )
    width: float = 15.0
    height: float = 15.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class NotGateLayout(
    _SimpleNodeMixin,
    _TextMixin,
    CellDesignerNode,
):
    """NOT gate layout."""

    _font_size_func: typing.ClassVar[typing.Callable] = lambda obj: obj.width / 3
    text: str = dataclasses.field(
        default="!", metadata={"description": "The label drawn inside the gate."}
    )
    width: float = 15.0
    height: float = 15.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownGateLayout(
    _SimpleNodeMixin,
    _TextMixin,
    CellDesignerNode,
):
    """Unknown gate layout."""

    _font_size_func: typing.ClassVar[typing.Callable] = lambda obj: obj.width / 3
    text: str = dataclasses.field(
        default="?", metadata={"description": "The label drawn inside the gate."}
    )
    width: float = 15.0
    height: float = 15.0

    def _make_shape(self) -> Shape:
        return MetaShapesEllipse(
            position=self.position, width=self.width, height=self.height
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogicArcLayout(CellDesignerSingleHeadedArc):
    """Logic arc layout."""

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return PolyLine._arrowhead_border_drawing_elements(self)
