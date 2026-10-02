"""Arc classes with predefined arrowheads for connecting nodes.

This module provides arc classes that use specific arrowhead shapes from the
meta.shapes module. These arcs can be used directly in map layouts to
connect nodes with various arrowhead styles.

Available arc types:
    Single-headed (at most one arrowhead):
    - PolyLine: Straight lines without arrowheads
    - Triangle: Lines with triangular arrowheads
    - ReversedTriangle: Lines with reversed triangular arrowheads
    - Rectangle: Lines with rectangular arrowheads
    - Ellipse: Lines with elliptical arrowheads
    - Diamond: Lines with diamond-shaped arrowheads
    - Bar: Lines with bar-shaped arrowheads
    - ArcBarb: Lines with an arc-barb arrowhead
    - StraightBarb: Lines with a straight-barb arrowhead
    - To: Lines with an arrow-tip ("to") arrowhead

    Double-headed (two arrowheads):
    - DoubleTriangle: Lines with double triangular arrowheads

Examples:
    ```python
    from momapy.meta.arcs import Triangle, Diamond
    from momapy.meta.nodes import Rectangle
    from momapy.geometry import Point
    from momapy.geometry import Segment

    # Create nodes with Point positions
    source_node = Rectangle(
        position=Point(100.0, 100.0),
        width=50.0,
        height=30.0
    )
    target_node = Rectangle(
        position=Point(300.0, 100.0),
        width=50.0,
        height=30.0
    )

    # Create arc with segments defining the path
    segment = Segment(
        Point(125.0, 100.0),
        Point(275.0, 100.0)
    )
    arc1 = Triangle(segments=(segment,))
    arc2 = Diamond(segments=(segment,))
    ```
"""

import dataclasses

from momapy.coloring import Color
from momapy.core.elements import Direction
from momapy.core.layout import DoubleHeadedArc
from momapy.core.layout import SingleHeadedArc
from momapy.drawing import Gradient
from momapy.drawing import DrawingElement
from momapy.drawing import NoneValue
from momapy.drawing import NoneValueType
from momapy.geometry import Point
from momapy.meta.shapes import ArcBarb as ArcBarbShape
from momapy.meta.shapes import Bar as BarShape
from momapy.meta.shapes import Diamond as DiamondShape
from momapy.meta.shapes import Ellipse as EllipseShape
from momapy.meta.shapes import Rectangle as RectangleShape
from momapy.meta.shapes import StraightBarb as StraightBarbShape
from momapy.meta.shapes import To as ToShape
from momapy.meta.shapes import Triangle as TriangleShape


__all__ = [
    "PolyLine",
    "Triangle",
    "ReversedTriangle",
    "Rectangle",
    "Ellipse",
    "Diamond",
    "Bar",
    "ArcBarb",
    "StraightBarb",
    "To",
    "DoubleTriangle",
]


@dataclasses.dataclass(frozen=True, kw_only=True)
class PolyLine(SingleHeadedArc):
    """Single-headed arc with no arrowhead.

    A polyline arc drawn as bare line segments, without any arrowhead.
    """

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        return []


@dataclasses.dataclass(frozen=True, kw_only=True)
class Triangle(SingleHeadedArc):
    """Single-headed arc with a triangle arrowhead.

    An arc ending in a triangular arrowhead pointing along the arc.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = TriangleShape(
            position=Point(self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
            direction=Direction.RIGHT,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReversedTriangle(SingleHeadedArc):
    """Single-headed arc with a reversed triangle arrowhead.

    An arc ending in a triangular arrowhead pointing back towards the arc.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = TriangleShape(
            position=Point(self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
            direction=Direction.LEFT,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Rectangle(SingleHeadedArc):
    """Single-headed arc with a rectangle arrowhead.

    An arc ending in a rectangular arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = RectangleShape(
            position=Point(self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Ellipse(SingleHeadedArc):
    """Single-headed arc with an ellipse arrowhead.

    An arc ending in an elliptical arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = EllipseShape(
            position=Point(self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Diamond(SingleHeadedArc):
    """Single-headed arc with a diamond arrowhead.

    An arc ending in a diamond-shaped arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = DiamondShape(
            position=Point(self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Bar(SingleHeadedArc):
    """Single-headed arc with a bar arrowhead.

    An arc ending in a bar (perpendicular line) arrowhead.
    """

    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = BarShape(
            position=Point(0.0, 0.0),
            height=self.arrowhead_height,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class ArcBarb(SingleHeadedArc):
    """Single-headed arc with an arc-barb arrowhead.

    An arc ending in a curved (arc) barb arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )
    arrowhead_fill: NoneValueType | Color | Gradient | None = NoneValue

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = ArcBarbShape(
            position=Point(-self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
            direction=Direction.RIGHT,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class StraightBarb(SingleHeadedArc):
    """Single-headed arc with a straight-barb arrowhead.

    An arc ending in a straight barb arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )
    arrowhead_fill: NoneValueType | Color | Gradient | None = NoneValue

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = StraightBarbShape(
            position=Point(-self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
            direction=Direction.RIGHT,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class To(SingleHeadedArc):
    """Single-headed arc with a to arrowhead.

    An arc ending in an arrow-tip ("to") arrowhead.
    """

    arrowhead_width: float = dataclasses.field(
        default=5.0,
        metadata={"description": "The width of the arrowhead."},
    )
    arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the arrowhead."},
    )
    arrowhead_fill: NoneValueType | Color | Gradient | None = NoneValue

    def _arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = ToShape(
            position=Point(-self.arrowhead_width / 2, 0),
            width=self.arrowhead_width,
            height=self.arrowhead_height,
            direction=Direction.RIGHT,
        )
        return shape.drawing_elements()


@dataclasses.dataclass(frozen=True, kw_only=True)
class DoubleTriangle(DoubleHeadedArc):
    """Double-headed arc with triangle arrowheads.

    An arc with a triangular arrowhead at each end.
    """

    start_arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the start arrowhead."},
    )
    start_arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the start arrowhead."},
    )
    end_arrowhead_width: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The width of the end arrowhead."},
    )
    end_arrowhead_height: float = dataclasses.field(
        default=10.0,
        metadata={"description": "The height of the end arrowhead."},
    )

    def _start_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = TriangleShape(
            position=Point(-self.start_arrowhead_width / 2, 0),
            width=self.start_arrowhead_width,
            height=self.start_arrowhead_height,
            direction=Direction.LEFT,
        )
        return shape.drawing_elements()

    def _end_arrowhead_border_drawing_elements(self) -> list[DrawingElement]:
        shape = TriangleShape(
            position=Point(self.end_arrowhead_width / 2, 0),
            width=self.end_arrowhead_width,
            height=self.end_arrowhead_height,
            direction=Direction.RIGHT,
        )
        return shape.drawing_elements()
