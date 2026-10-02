"""Layout element hierarchy: all visual element classes."""

import abc
import collections
import dataclasses
import typing
import typing_extensions
import math
import copy

import uharfbuzz

from momapy.core.elements import HAlignment, LayoutElement, VAlignment
from momapy.core.fonts import find_font

from momapy.builder import isinstance_or_builder
from momapy.coloring import Color
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import Gradient
from momapy.drawing import ClosePath
from momapy.drawing import CurveTo
from momapy.drawing import drawing_elements_to_geometry
from momapy.drawing import DrawingElement
from momapy.drawing import EllipticalArc as DrawingEllipticalArc
from momapy.drawing import FillRule
from momapy.drawing import Filter
from momapy.drawing import FontStyle
from momapy.drawing import FontWeight
from momapy.drawing import get_drawing_elements_angle
from momapy.drawing import get_drawing_elements_bbox
from momapy.drawing import get_drawing_elements_border
from momapy.drawing import get_initial_value
from momapy.drawing import Group
from momapy.drawing import LineTo
from momapy.drawing import MoveTo
from momapy.drawing import NoneValue
from momapy.drawing import NoneValueType
from momapy.drawing import Path
from momapy.drawing import PathAction
from momapy.drawing import QuadraticCurveTo
from momapy.drawing import Text
from momapy.drawing import TextAnchor
from momapy.geometry import Bbox
from momapy.geometry import CubicBezierCurve
from momapy.geometry import EllipticalArc as GeometryEllipticalArc
from momapy.geometry import Line
from momapy.geometry import Point
from momapy.geometry import QuadraticBezierCurve
from momapy.geometry import Rotation
from momapy.geometry import Segment
from momapy.geometry import Transformation
from momapy.geometry import Translation


@dataclasses.dataclass(frozen=True, kw_only=True)
class TextLayout(LayoutElement):
    """Class for text layouts.

    A text layout draws a piece of text at a position with its own font and
    styling.
    """

    text: str = dataclasses.field(
        metadata={"description": "The text of the text layout"}
    )
    font_family: str = dataclasses.field(
        default=get_initial_value("font_family"),
        metadata={"description": "The font family of the text layout"},
    )
    font_size: float = dataclasses.field(
        default=get_initial_value("font_size"),
        metadata={"description": "The font size of the text layout"},
    )
    font_style: FontStyle = dataclasses.field(
        default=get_initial_value("font_style"),
        metadata={"description": "The font style of the text layout"},
    )
    font_weight: FontWeight | int = dataclasses.field(
        default=get_initial_value("font_weight"),
        metadata={"description": "The font weight of the text layout"},
    )
    position: Point = dataclasses.field(
        metadata={"description": "The position of the text layout"}
    )
    width: float | None = dataclasses.field(
        default=None, metadata={"description": "The width of the text layout"}
    )
    height: float | None = dataclasses.field(
        default=None, metadata={"description": "The height of the text layout"}
    )
    horizontal_alignment: HAlignment = dataclasses.field(
        default=HAlignment.LEFT,
        metadata={"description": "The horizontal alignment of the text layout"},
    )
    vertical_alignment: VAlignment = dataclasses.field(
        default=VAlignment.TOP,
        metadata={"description": "The vertical alignment of the text layout"},
    )
    justify: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether to justify the text or not"},
    )
    fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The text fill color of the text layout"},
    )
    filter_: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The filter of the text layout"},
    )  # should be a tuple of filters to follow SVG (to be implemented)
    stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke color of the text layout"},
    )
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke dasharray of the text layout"},
    )
    stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke dashoffset of the text layout"},
    )
    stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke line cap of the text layout"},
    )
    stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke line join of the text layout"},
    )
    stroke_width: float | None = dataclasses.field(
        default=None,
        metadata={"description": "The text stroke width of the text layout"},
    )
    text_anchor: TextAnchor | None = dataclasses.field(
        default=None,
        metadata={"description": "The text anchor of the text layout"},
    )
    transform: NoneValueType | tuple[Transformation, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "The transform of the text layout"},
    )

    @property
    def x(self) -> float:
        """Return the x coordinate of the text layout."""
        return self.position.x

    @property
    def y(self) -> float:
        """Return the y coordinate of the text layout."""
        return self.position.y

    @classmethod
    def _get_font_file_path(
        cls,
        font_family: str,
        font_weight: FontWeight | int,
        font_style: FontStyle,
    ) -> str | None:
        return find_font(
            family=font_family,
            weight=font_weight,
            style=font_style,
        )

    @classmethod
    def _make_font(cls, font_file_path: str, font_size: float) -> uharfbuzz.Font:
        with open(font_file_path, "rb") as f:
            fontdata = f.read()
        face = uharfbuzz.Face(fontdata)
        font = uharfbuzz.Font(face)
        font.scale = (font_size * 64, font_size * 64)
        return font

    @classmethod
    def _get_font_parameters(cls, font: uharfbuzz.Font) -> tuple[float, float, float]:
        font_extents = font.get_font_extents("ltr")
        ascent = font_extents.ascender / 64
        descent = abs(font_extents.descender / 64)
        line_gap = font_extents.line_gap / 64
        height = ascent + descent + line_gap
        return ascent, descent, height

    @classmethod
    def _get_text_width(cls, text: str, font: uharfbuzz.Font) -> float:
        if text:
            buffer = uharfbuzz.Buffer()
            buffer.add_str(text)
            buffer.guess_segment_properties()
            uharfbuzz.shape(font, buffer)
            width = sum(pos.x_advance for pos in buffer.glyph_positions) / 64
        else:
            width = 0.0
        return width

    def _get_line_positions(self) -> list[tuple[str, float, float, float]]:
        line_positions = []
        font_file_path = self._get_font_file_path(
            self.font_family, self.font_weight, self.font_style
        )
        font = self._make_font(font_file_path, self.font_size)
        font_ascent, font_descent, font_height = self._get_font_parameters(font)
        lines = self.text.split("\n")
        text_height = font_height * (len(lines) - 1) + font_ascent + font_descent
        for i, line in enumerate(lines):
            line_width = self._get_text_width(line, font)
            if self.width is not None and self.horizontal_alignment is HAlignment.LEFT:
                x = self.position.x - self.width / 2
            elif (
                self.width is not None and self.horizontal_alignment is HAlignment.RIGHT
            ):
                x = self.position.x + self.width / 2 - line_width
            else:
                x = self.position.x - line_width / 2
            if self.height is not None and self.vertical_alignment is VAlignment.TOP:
                y = self.position.y - self.height / 2 + font_ascent + i * font_height
            elif (
                self.height is not None and self.vertical_alignment is VAlignment.BOTTOM
            ):
                y = (
                    self.position.y
                    + self.height / 2
                    - text_height
                    + font_ascent
                    + i * font_height
                )
            else:
                y = self.position.y - text_height / 2 + font_ascent + i * font_height
            line_positions.append((line, x, y, line_width))
        return line_positions

    def drawing_elements(self) -> list[DrawingElement]:
        """Return the drawing elements of the text layout."""
        drawing_elements = []
        lines_positions = self._get_line_positions()
        for line, x, y, _ in lines_positions:
            text = Text(
                text=line,
                point=Point(x, y),
            )
            drawing_elements.append(text)
        group = Group(
            class_=f"{type(self).__name__}",
            elements=tuple(drawing_elements),
            id_=f"{self.id_}",
            fill=self.fill,
            filter_=self.filter_,
            font_family=self.font_family,
            font_size=self.font_size,
            font_style=self.font_style,
            font_weight=self.font_weight,
            stroke=self.stroke,
            stroke_dasharray=self.stroke_dasharray,
            stroke_dashoffset=self.stroke_dashoffset,
            stroke_linecap=self.stroke_linecap,
            stroke_linejoin=self.stroke_linejoin,
            stroke_width=self.stroke_width,
            text_anchor=self.text_anchor,
            transform=self.transform,
        )
        return [group]

    def bbox(self) -> Bbox:
        """Compute and return the bounding box of the layout element."""
        line_positions = self._get_line_positions()
        font_file_path = self._get_font_file_path(
            self.font_family, self.font_weight, self.font_style
        )
        font = self._make_font(font_file_path, self.font_size)
        font_ascent, font_descent, _ = self._get_font_parameters(font)
        line, x, y, line_width = line_positions[0]
        min_x = x
        max_x = min_x + line_width
        min_y = y - font_ascent
        max_y = y + font_descent
        for line, x, y, line_width in line_positions[1:]:
            start_x = x
            if start_x < min_x:
                min_x = start_x
            end_x = start_x + line_width
            if end_x > max_x:
                max_x = end_x
            max_y = y + font_descent
        return Bbox(
            Point(min_x / 2 + max_x / 2, min_y / 2 + max_y / 2),
            max_x - min_x,
            max_y - min_y,
        )

    def children(self) -> list[LayoutElement]:
        """Return the children of the text layout.

        The text layout has no children, so return an empty list.
        """
        return []

    def childless(self) -> typing_extensions.Self:
        """Return a copy of the text layout with no children.

        The text layout has no children, so return a copy of the text layout.
        """
        return copy.deepcopy(self)

    def north_west(self) -> Point:
        """Return the north west anchor of the text layout."""
        return self.bbox().north_west()

    def north_north_west(self) -> Point:
        """Return the north north west anchor of the text layout."""
        return self.bbox().north_north_west()

    def north(self) -> Point:
        """Return the north anchor of the text layout."""
        return self.bbox().north()

    def north_north_east(self) -> Point:
        """Return the north north east anchor of the text layout."""
        return self.bbox().north_north_east()

    def north_east(self) -> Point:
        """Return the north east anchor of the text layout."""
        return self.bbox().north_east()

    def east_north_east(self) -> Point:
        """Return the east north east anchor of the text layout."""
        return self.bbox().east_north_east()

    def east(self) -> Point:
        """Return the east anchor of the text layout."""
        return self.bbox().east()

    def east_south_east(self) -> Point:
        """Return the east south east anchor of the text layout."""
        return self.bbox().east_south_east()

    def south_east(self) -> Point:
        """Return the south east anchor of the text layout."""
        return self.bbox().south_east()

    def south_south_east(self) -> Point:
        """Return the south south east anchor of the text layout."""
        return self.bbox().south_south_east()

    def south(self) -> Point:
        """Return the south anchor of the text layout."""
        return self.bbox().south()

    def south_south_west(self) -> Point:
        """Return the south south west anchor of the text layout."""
        return self.bbox().south_south_west()

    def south_west(self) -> Point:
        """Return the south west anchor of the text layout."""
        return self.bbox().south_west()

    def west_south_west(self) -> Point:
        """Return the west south west anchor of the text layout."""
        return self.bbox().west_south_west()

    def west(self) -> Point:
        """Return the west anchor of the text layout."""
        return self.bbox().west()

    def west_north_west(self) -> Point:
        """Return the west north west anchor of the text layout."""
        return self.bbox().west_north_west()


@dataclasses.dataclass(frozen=True, kw_only=True)
class Shape(LayoutElement):
    """Class for basic shapes.

    A shape is the most simple layout element and has no children.
    """

    def childless(self) -> typing_extensions.Self:
        """Return a copy of the shape with no children.

        A shape has no children, so return a copy of the shape.
        """
        return copy.deepcopy(self)

    def children(self) -> list[LayoutElement]:
        """Return the children of the shape.

        A shape has no children, so return an empty list.
        """
        return []

    def bbox(self) -> Bbox:
        """Compute and return the bounding box of the shape."""
        primitives = self.to_geometry()
        if not primitives:
            return Bbox(Point(0.0, 0.0), 0, 0)
        bboxes = [p.bbox() for p in primitives]
        return Bbox.union(bboxes)


@dataclasses.dataclass(frozen=True, kw_only=True)
class GroupLayout(LayoutElement):
    """Base class for group layouts.

    A group layout is a layout element grouping other layout elements, with its
    own drawing elements and children combined into a single group drawing
    element.
    """

    layout_elements: tuple[LayoutElement, ...] = dataclasses.field(
        default_factory=tuple,
        metadata={
            "description": "The sub-layout elements of the group layout. These are part of the children of the group layout"
        },
    )
    group_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The fill color of the group layout"},
    )
    group_fill_rule: FillRule | None = dataclasses.field(
        default=None,
        metadata={"description": "The fill rule of the group layout"},
    )
    group_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The filter of the group layout"},
    )  # should be a tuple of filters to follow SVG (to be implemented)
    group_font_family: str | None = dataclasses.field(
        default=None,
        metadata={"description": "The font family of the group layout"},
    )
    group_font_size: float | None = dataclasses.field(
        default=None,
        metadata={"description": "The font size of the group layout"},
    )
    group_font_style: FontStyle | None = dataclasses.field(
        default=None,
        metadata={"description": "The font style of the group layout"},
    )
    group_font_weight: FontWeight | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The font weight of the group layout"},
    )
    group_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke color of the group layout"},
    )
    group_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The stroke dasharray of the group layout"},
        )
    )
    group_stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke dashoffset of the group layout"},
    )
    group_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line cap of the group layout"},
    )
    group_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line join of the group layout"},
    )
    group_stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke width of the group layout"},
    )
    group_text_anchor: TextAnchor | None = dataclasses.field(
        default=None,
        metadata={"description": "The text anchor of the group layout"},
    )
    group_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The transform of the group layout"},
        )
    )

    def own_to_geometry(
        self,
    ) -> list[
        Segment | QuadraticBezierCurve | CubicBezierCurve | GeometryEllipticalArc
    ]:
        """Return a list of geometry primitives from the self drawing elements."""
        return drawing_elements_to_geometry(self.own_drawing_elements())

    def own_bbox(self) -> Bbox:
        """Compute and return the bounding box of the self drawing element of the group layout."""
        primitives = self.own_to_geometry()
        if not primitives:
            return Bbox(Point(0.0, 0.0), 0, 0)
        bboxes = [p.bbox() for p in primitives]
        return Bbox.union(bboxes)

    def bbox(self) -> Bbox:
        """Compute and return the bounding box of the group layout element."""
        own_bbox = self.own_bbox()
        bboxes = [child.bbox() for child in self.children()]
        min_x = own_bbox.north_west().x
        min_y = own_bbox.north_west().y
        max_x = own_bbox.south_east().x
        max_y = own_bbox.south_east().y
        for bbox in bboxes:
            if bbox.north_west().x < min_x:
                min_x = bbox.north_west().x
            if bbox.north_west().y < min_y:
                min_y = bbox.north_west().y
            if bbox.south_east().x > max_x:
                max_x = bbox.south_east().x
            if bbox.south_east().y > max_y:
                max_y = bbox.south_east().y
        bbox = Bbox(
            Point(min_x / 2 + max_x / 2, min_y / 2 + max_y / 2),
            max_x - min_x,
            max_y - min_y,
        )
        return bbox

    @abc.abstractmethod
    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the self drawing elements of the group layout."""
        pass

    @abc.abstractmethod
    def own_children(self) -> list[LayoutElement]:
        """Return the self children of the group layout."""
        pass

    def drawing_elements(self) -> list[DrawingElement]:
        """Return the drawing elements of the group layout.

        The returned drawing elements are a group drawing element formed of the self drawing elements of the group layout and the drawing elements of its children.
        """
        drawing_elements = self.own_drawing_elements()
        for child in self.children():
            if child is not None:
                drawing_elements += child.drawing_elements()
        group = Group(
            class_=f"{type(self).__name__}",
            elements=tuple(drawing_elements),
            id_=f"{self.id_}",
            fill=self.group_fill,
            fill_rule=self.group_fill_rule,
            filter_=self.group_filter,
            font_family=self.group_font_family,
            font_size=self.group_font_size,
            font_style=self.group_font_style,
            font_weight=self.group_font_weight,
            stroke=self.group_stroke,
            stroke_dasharray=self.group_stroke_dasharray,
            stroke_dashoffset=self.group_stroke_dashoffset,
            stroke_linecap=self.group_stroke_linecap,
            stroke_linejoin=self.group_stroke_linejoin,
            stroke_width=self.group_stroke_width,
            text_anchor=self.group_text_anchor,
            transform=self.group_transform,
        )
        return [group]

    def children(self) -> list[LayoutElement]:
        """Return the children of the group layout.

        These are the self children of the group layout (returned by the `own_children` method) and the other children of the group layout (given by the `layout_elements` attribute).
        """
        return self.own_children() + list(self.layout_elements)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Node(GroupLayout):
    """Class for nodes.

    A node is a group layout drawn as a shape with a position, a size, an
    optional label and its own border styling.
    """

    fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The fill color of the node"},
    )
    filter_: NoneValueType | Filter | None = dataclasses.field(
        default=None, metadata={"description": "The filter of the node"}
    )
    height: float = dataclasses.field(
        metadata={"description": "The height of the node"}
    )
    label: TextLayout | None = dataclasses.field(
        default=None, metadata={"description": "The label of the node"}
    )
    position: Point = dataclasses.field(
        metadata={"description": "The position of the node"}
    )
    stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke color of the node"},
    )
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke dasharray of the node"},
    )
    stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke dashoffset of the node"},
    )
    stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line cap of the node"},
    )
    stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line join of the node"},
    )
    stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None, metadata={"description": "The stroke width of the node"}
    )
    transform: NoneValueType | tuple[Transformation, ...] | None = dataclasses.field(
        default=None, metadata={"description": "The transform of the node"}
    )
    width: float = dataclasses.field(metadata={"description": "The width of the node"})

    @property
    def x(self) -> float:
        """Return the x coordinate of the node."""
        return self.position.x

    @property
    def y(self) -> float:
        """Return the y coordinate of the node."""
        return self.position.y

    @abc.abstractmethod
    def _border_drawing_elements(self) -> list[DrawingElement]:
        pass

    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the node's own drawing elements."""
        drawing_elements = self._border_drawing_elements()
        group = Group(
            class_=f"{type(self).__name__}_own",
            elements=tuple(drawing_elements),
            fill=self.fill,
            filter_=self.filter_,
            id_=f"{self.id_}_own",
            stroke=self.stroke,
            stroke_dasharray=self.stroke_dasharray,
            stroke_dashoffset=self.stroke_dashoffset,
            stroke_linecap=self.stroke_linecap,
            stroke_linejoin=self.stroke_linejoin,
            stroke_width=self.stroke_width,
            transform=self.transform,
        )
        return [group]

    def own_children(self) -> list[LayoutElement]:
        """Return the self children of the node. A node has unique child that is its label."""
        if self.label is not None:
            return [self.label]
        return []

    def size(self) -> tuple[float, float]:
        """Return the size of the node."""
        return (self.width, self.height)

    def north_west(self) -> Point:
        """Return the north west anchor of the node."""
        line = Line(self.center(), self.center() - (self.width / 2, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def north_north_west(self) -> Point:
        """Return the north north west anchor of the node."""
        line = Line(self.center(), self.center() - (self.width / 4, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def north(self) -> Point:
        """Return the north anchor of the node."""
        return self.own_angle(90)

    def north_north_east(self) -> Point:
        """Return the north north east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 4, -self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def north_east(self) -> Point:
        """Return the north east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 2, -self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def east_north_east(self) -> Point:
        """Return the east north east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 2, -self.height / 4))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def east(self) -> Point:
        """Return the east anchor of the node."""
        return self.own_angle(0)

    def east_south_east(self) -> Point:
        """Return the east south east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 2, self.height / 4))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def south_east(self) -> Point:
        """Return the south east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 2, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def south_south_east(self) -> Point:
        """Return the south south east anchor of the node."""
        line = Line(self.center(), self.center() + (self.width / 4, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def south(self) -> Point:
        """Return the south anchor of the node."""
        return self.own_angle(270)

    def south_south_west(self) -> Point:
        """Return the south south west anchor of the node."""
        line = Line(self.center(), self.center() + (-self.width / 4, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def south_west(self) -> Point:
        """Return the south west anchor of the node."""
        line = Line(self.center(), self.center() + (-self.width / 2, self.height / 2))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def west_south_west(self) -> Point:
        """Return the west south west anchor of the node."""
        line = Line(self.center(), self.center() + (-self.width / 2, self.height / 4))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def west(self) -> Point:
        """Return the west anchor of the node."""
        return self.own_angle(180)

    def west_north_west(self) -> Point:
        """Return the west north west anchor of the node."""
        line = Line(self.center(), self.center() - (self.width / 2, self.height / 4))
        angle = -line.get_angle_to_horizontal()
        return self.own_angle(angle, unit="radians")

    def center(self) -> Point:
        """Return the center anchor of the node."""
        return self.position

    def label_center(self) -> Point:
        """Return the label center anchor of the node."""
        return self.position

    def own_border(self, point: Point) -> Point | None:
        """Return the point on the border of the node that intersects the self drawing elements of the node with the line formed of the center anchor point of the node and the given point.

        When there are multiple intersection points, the one closest to the given point is returned.
        """
        return get_drawing_elements_border(
            drawing_elements=self.own_drawing_elements(),
            point=point,
            center=self.center(),
        )

    def border(self, point: Point) -> Point | None:
        """Return the point on the border of the node that intersects the drawing elements of the node with the line formed of the center anchor point of the node and the given point.

        When there are multiple intersection points, the one closest to the given point is returned.
        """
        return get_drawing_elements_border(
            drawing_elements=self.drawing_elements(),
            point=point,
            center=self.center(),
        )

    def own_angle(
        self,
        angle: float,
        unit: typing.Literal["degrees", "radians"] = "degrees",
    ) -> Point | None:
        """Return the point on the border of the node that intersects the self drawing elements of the node with the line passing through the center anchor point of the node and at a given angle from the horizontal."""
        return get_drawing_elements_angle(
            drawing_elements=self.own_drawing_elements(),
            angle=angle,
            unit=unit,
            center=self.center(),
        )

    def angle(
        self,
        angle: float,
        unit: typing.Literal["degrees", "radians"] = "degrees",
    ) -> Point | None:
        """Return the point on the border of the node that intersects the drawing elements of the node with the line passing through the center anchor point of the node and at a given angle from the horizontal."""
        return get_drawing_elements_angle(
            drawing_elements=self.drawing_elements(),
            angle=angle,
            unit=unit,
            center=self.center(),
        )

    def childless(self) -> typing_extensions.Self:
        """Return a copy of the node with no children."""
        return dataclasses.replace(self, label=None, layout_elements=tuple([]))


@dataclasses.dataclass(frozen=True, kw_only=True)
class Arc(GroupLayout):
    """Base class for arcs.

    An arc is a group layout drawn as a path connecting a source to a target,
    with its own path styling.
    """

    end_shorten: float = dataclasses.field(
        default=0.0,
        metadata={"description": "The length the end of the arc will be shorten by"},
    )
    fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None, metadata={"description": "The fill color of the arc"}
    )
    filter_: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The filter of the arc"},
    )
    path_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The path fill color of the arc"},
    )
    path_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None, metadata={"description": "The path filter of the arc"}
    )
    path_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke color of the arc"},
    )
    path_stroke_dasharray: NoneValueType | tuple[float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke dasharray of the arc"},
    )
    path_stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke dashoffset of the arc"},
    )
    path_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke line cap of the arc"},
    )
    path_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke line join of the arc"},
    )
    path_stroke_width: float | None = dataclasses.field(
        default=None,
        metadata={"description": "The path stroke width of the arc"},
    )
    path_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None, metadata={"description": "The path transform of the arc"}
        )
    )
    stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke color of the arc"},
    )
    stroke_dasharray: NoneValueType | tuple[float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke dasharray of the arc"},
    )
    stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke dashoffset of the arc"},
    )
    stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line cap of the arc"},
    )
    stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The stroke line join of the arc"},
    )
    stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None, metadata={"description": "The stroke width of the arc"}
    )
    segments: tuple[
        Segment | QuadraticBezierCurve | CubicBezierCurve | GeometryEllipticalArc,
        ...,
    ] = dataclasses.field(
        default_factory=tuple,
        metadata={"description": "The path segments of the arc"},
    )
    source: LayoutElement | None = dataclasses.field(
        default=None, metadata={"description": "The source of the arc"}
    )
    start_shorten: float = dataclasses.field(
        default=0.0,
        metadata={"description": "The length the start of the arc will be shorten by"},
    )
    target: LayoutElement | None = dataclasses.field(
        default=None, metadata={"description": "The target of the arc"}
    )
    transform: NoneValueType | tuple[Transformation, ...] | None = dataclasses.field(
        default=None, metadata={"description": "The transform of the arc"}
    )

    def own_children(self) -> list[LayoutElement]:
        """Return the self children of the arc."""
        return []

    def points(self) -> list[Point]:
        """Return the points of the arc path.

        An arc with no segments has no points and returns an empty list.
        """
        if not self.segments:
            return []
        points = []
        for segment in self.segments:
            points.append(segment.p1)
        points.append(segment.p2)
        return points

    def length(self) -> float:
        """Return the total length of the arc path."""
        return sum([segment.length() for segment in self.segments])

    def start_point(self) -> Point:
        """Return the starting point of the arc.

        Raises:
            ValueError: If the arc has no segments.
        """
        if not self.segments:
            raise ValueError("arc has no segments")
        return self.points()[0]

    def end_point(self) -> Point:
        """Return the ending point of the arc.

        Raises:
            ValueError: If the arc has no segments.
        """
        if not self.segments:
            raise ValueError("arc has no segments")
        return self.points()[-1]

    def childless(self) -> typing_extensions.Self:
        """Return a copy of the arc with no children."""
        return dataclasses.replace(self, layout_elements=tuple([]))

    def fraction(self, fraction: float) -> tuple[Point, float]:
        """Return the position and angle on the arc at a given fraction (of the total arc length).

        Raises:
            ValueError: If the arc has no segments.
        """
        if not self.segments:
            raise ValueError("arc has no segments")
        current_length = 0
        length_to_reach = fraction * self.length()
        for segment in self.segments:
            current_length += segment.length()
            if current_length >= length_to_reach:
                break
        segment_start_length = current_length - segment.length()
        segment_fraction = (length_to_reach - segment_start_length) / segment.length()
        position, angle = segment.get_position_and_angle_at_fraction(segment_fraction)
        return position, angle

    @classmethod
    def _make_path_action_from_segment(
        cls,
        segment: Segment
        | CubicBezierCurve
        | QuadraticBezierCurve
        | GeometryEllipticalArc,
    ) -> PathAction:
        if isinstance_or_builder(segment, Segment):
            path_action = LineTo(segment.p2)
        elif isinstance_or_builder(segment, CubicBezierCurve):
            path_action = CurveTo(
                segment.p2,
                segment.control_point1,
                segment.control_point2,
            )
        elif isinstance_or_builder(segment, QuadraticBezierCurve):
            path_action = QuadraticCurveTo(segment.p2, segment.control_point)
        elif isinstance_or_builder(segment, GeometryEllipticalArc):
            path_action = DrawingEllipticalArc(
                segment.p2,
                segment.rx,
                segment.ry,
                segment.x_axis_rotation,
                segment.arc_flag,
                segment.sweep_flag,
            )
        return path_action


@dataclasses.dataclass(frozen=True, kw_only=True)
class SingleHeadedArc(Arc):
    """Base class for single-headed arcs.

    A single-headed arc is formed of a path and a unique arrowhead at its end.
    """

    arrowhead_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead fill color of the arc"},
    )
    arrowhead_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead filter of the arc"},
    )
    arrowhead_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead stroke color of the arc"},
    )
    arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The arrowhead stroke dasharray of the arc"},
        )
    )
    arrowhead_stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead stroke dashoffset of the arc"},
    )
    arrowhead_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead stroke line cap of the arc"},
    )
    arrowhead_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead stroke line join of the arc"},
    )
    arrowhead_stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The arrowhead stroke width of the arc"},
    )
    arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The arrowhead transform of the arc"},
        )
    )

    def arrowhead_length(self) -> float:
        """Return the length of the single-headed arc arrowhead."""
        bbox = get_drawing_elements_bbox(self._arrowhead_border_drawing_elements())
        if math.isnan(bbox.width):
            return 0.0
        return bbox.east().x

    def arrowhead_tip(self) -> Point:
        """Return the arrowhead tip anchor point of the single-headed arc."""
        segment = self.segments[-1]
        segment_length = segment.length()
        if segment_length == 0:
            return segment.p2
        fraction = 1 - self.end_shorten / segment_length
        return segment.get_position_at_fraction(fraction)

    def arrowhead_base(self) -> Point:
        """Return the arrowhead base anchor point of the single-headed arc."""
        arrowhead_length = self.arrowhead_length()
        segment = self.segments[-1]
        segment_length = segment.length()
        if segment_length == 0:
            return self.arrowhead_tip() - (arrowhead_length, 0)
        fraction = 1 - (arrowhead_length + self.end_shorten) / segment_length
        return segment.get_position_at_fraction(fraction)

    def arrowhead_bbox(self) -> Bbox:
        """Return the bounding box of the single-headed arc arrowhead."""
        return get_drawing_elements_bbox(self.arrowhead_drawing_elements())

    def arrowhead_border(self, point: Point) -> Point:
        """Return the point at the intersection of the drawing elements of the single-headed arc arrowhead and the line going through the center of these drawing elements and the given point.

        When there are multiple intersection points, the one closest to the given point is returned.
        """
        point = get_drawing_elements_border(self.arrowhead_drawing_elements(), point)
        if point is None:
            return self.arrowhead_tip()
        return point

    @abc.abstractmethod
    def _arrowhead_border_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        pass

    def _get_arrowhead_transformation(self) -> Transformation:
        arrowhead_length = self.arrowhead_length()
        arrowhead_base = self.arrowhead_base()
        last_segment = self.segments[-1]
        if arrowhead_length == 0:
            end_point = last_segment.p2
            end_angle = last_segment.get_angle_at_fraction(1.0)
            p1 = Point(
                end_point.x - math.cos(end_angle),
                end_point.y - math.sin(end_angle),
            )
            line = Line(p1, end_point)
        else:
            line = Line(arrowhead_base, last_segment.p2)
        angle = line.get_angle_to_horizontal()
        translation = Translation(arrowhead_base.x, arrowhead_base.y)
        rotation = Rotation(angle, arrowhead_base)
        return rotation * translation

    def arrowhead_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        """Return the drawing elements of the single-headed arc arrowhead."""
        drawing_elements = self._arrowhead_border_drawing_elements()
        group = Group(
            class_=f"{type(self).__name__}_arrowhead",
            elements=tuple(drawing_elements),
            fill=self.arrowhead_fill,
            filter_=self.arrowhead_filter,
            id_=f"{self.id_}_arrowhead",
            stroke=self.arrowhead_stroke,
            stroke_dasharray=self.arrowhead_stroke_dasharray,
            stroke_dashoffset=self.arrowhead_stroke_dashoffset,
            stroke_linecap=self.arrowhead_stroke_linecap,
            stroke_linejoin=self.arrowhead_stroke_linejoin,
            stroke_width=self.arrowhead_stroke_width,
            transform=self.arrowhead_transform,
        )
        transformation = self._get_arrowhead_transformation()
        group = group.transformed(transformation)
        return [group]

    def path_drawing_elements(self) -> list[Path]:
        """Return the drawing elements of the single-headed arc path."""
        arrowhead_length = self.arrowhead_length()
        if len(self.segments) == 1:
            segment = (
                self.segments[0]
                .shortened(self.start_shorten, "start")
                .shortened(self.end_shorten + arrowhead_length, "end")
            )
            actions = [
                MoveTo(segment.p1),
                self._make_path_action_from_segment(segment),
            ]
        else:
            first_segment = self.segments[0].shortened(self.start_shorten, "start")
            last_segment = self.segments[-1].shortened(
                self.end_shorten + arrowhead_length, "end"
            )
            actions = [
                MoveTo(first_segment.p1),
                self._make_path_action_from_segment(first_segment),
            ]
            for segment in self.segments[1:-1]:
                action = self._make_path_action_from_segment(segment)
                actions.append(action)
            actions.append(self._make_path_action_from_segment(last_segment))
        path = Path(
            actions=tuple(actions),
            class_=f"{type(self).__name__}_path",
            fill=self.path_fill,
            filter_=self.path_filter,
            id_=f"{self.id_}_path",
            stroke=self.path_stroke,
            stroke_dasharray=self.path_stroke_dasharray,
            stroke_dashoffset=self.path_stroke_dashoffset,
            stroke_linecap=self.path_stroke_linecap,
            stroke_linejoin=self.path_stroke_linejoin,
            stroke_width=self.path_stroke_width,
            transform=self.path_transform,
        )
        return [path]

    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the self drawing elements of the single-headed arc."""
        drawing_elements = (
            self.path_drawing_elements() + self.arrowhead_drawing_elements()
        )
        group = Group(
            class_=f"{type(self).__name__}_own",
            elements=tuple(drawing_elements),
            fill=self.fill,
            filter_=self.filter_,
            id_=f"{self.id_}_own",
            stroke=self.stroke,
            stroke_dasharray=self.stroke_dasharray,
            stroke_dashoffset=self.stroke_dashoffset,
            stroke_linecap=self.stroke_linecap,
            stroke_linejoin=self.stroke_linejoin,
            stroke_width=self.stroke_width,
            transform=self.transform,
        )
        return [group]


@dataclasses.dataclass(frozen=True, kw_only=True)
class DoubleHeadedArc(Arc):
    """Base class for double-headed arcs.

    A double-headed arc is formed of a path and two arrowheads, one at the start
    of the path and one at its end.
    """

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead fill color of the arc"},
    )
    end_arrowhead_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead filter of the arc"},
    )
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead stroke color of the arc"},
    )
    end_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The end arrowhead stroke dasharray of the arc"},
        )
    )
    end_arrowhead_stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead stroke dashoffset of the arc"},
    )
    end_arrowhead_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead stroke line cap of the arc"},
    )
    end_arrowhead_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead stroke line join of the arc"},
    )
    end_arrowhead_stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The end arrowhead stroke width of the arc"},
    )
    end_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The end arrowhead transform of the arc"},
        )
    )
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead fill color of the arc"},
    )
    start_arrowhead_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead filter of the arc"},
    )
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead stroke color of the arc"},
    )
    start_arrowhead_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The start arrowhead stroke dasharray of the arc"},
        )
    )
    start_arrowhead_stroke_dashoffset: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead stroke dashoffset of the arc"},
    )
    start_arrowhead_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead stroke line cap of the arc"},
    )
    start_arrowhead_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead stroke line join of the arc"},
    )
    start_arrowhead_stroke_width: NoneValueType | float | None = dataclasses.field(
        default=None,
        metadata={"description": "The start arrowhead stroke width of the arc"},
    )
    start_arrowhead_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "The start arrowhead transform of the arc"},
        )
    )

    def start_arrowhead_length(self) -> float:
        """Return the length of the double-headed arc start arrowhead."""
        bbox = get_drawing_elements_bbox(
            self._start_arrowhead_border_drawing_elements()
        )
        if math.isnan(bbox.width):
            return 0.0
        return abs(bbox.west().x)

    def start_arrowhead_tip(self) -> Point:
        """Return the tip anchor point of the double-headed arc start arrowhead."""
        segment = self.segments[0]
        segment = Segment(segment.p2, segment.p1)
        segment_length = segment.length()
        if segment_length == 0:
            return segment.p2
        fraction = 1 - self.start_shorten / segment_length
        return segment.get_position_at_fraction(fraction)

    def start_arrowhead_base(self) -> Point:
        """Return the base anchor point of the double-headed arc start arrowhead."""
        arrowhead_length = self.start_arrowhead_length()
        if arrowhead_length == 0:
            return self.start_point()
        segment = self.segments[0]
        segment = Segment(segment.p2, segment.p1)
        segment_length = segment.length()
        if segment_length == 0:
            return self.start_arrowhead_tip() + (arrowhead_length, 0)
        fraction = 1 - (arrowhead_length + self.start_shorten) / segment_length
        return segment.get_position_at_fraction(fraction)

    def start_arrowhead_bbox(self) -> Bbox:
        """Return the bounding box of the double-headed arc start arrowhead."""
        return get_drawing_elements_bbox(self.start_arrowhead_drawing_elements())

    def start_arrowhead_border(self, point: Point) -> Point:
        """Return the point at the intersection of the drawing elements of the double-headed arc start arrowhead and the line going through the center of these drawing elements and the given point.

        When there are multiple intersection points, the one closest to the given point is returned.
        """
        point = get_drawing_elements_border(
            self.start_arrowhead_drawing_elements(), point
        )
        if point is None:
            return self.start_arrowhead_tip()
        return point

    def end_arrowhead_length(self) -> float:
        """Return the length of the double-headed arc end arrowhead."""
        bbox = get_drawing_elements_bbox(self._end_arrowhead_border_drawing_elements())
        if math.isnan(bbox.width):
            return 0.0
        return bbox.east().x

    def end_arrowhead_tip(self) -> Point:
        """Return the tip anchor point of the double-headed arc end arrowhead."""
        segment = self.segments[-1]
        segment_length = segment.length()
        if segment_length == 0:
            return segment.p2
        fraction = 1 - self.end_shorten / segment_length
        return segment.get_position_at_fraction(fraction)

    def end_arrowhead_base(self) -> Point:
        """Return the base anchor point of the double-headed arc end arrowhead."""
        arrowhead_length = self.end_arrowhead_length()
        if arrowhead_length == 0:
            return self.end_point()
        segment = self.segments[-1]
        segment_length = segment.length()
        if segment_length == 0:
            return self.end_arrowhead_tip() - (arrowhead_length, 0)
        fraction = 1 - (arrowhead_length + self.end_shorten) / segment_length
        return segment.get_position_at_fraction(fraction)

    def end_arrowhead_bbox(self) -> Bbox:
        """Return the bounding box of the double-headed arc end arrowhead."""
        return get_drawing_elements_bbox(self.end_arrowhead_drawing_elements())

    def end_arrowhead_border(self, point: Point) -> Point:
        """Return the point at the intersection of the drawing elements of the double-headed arc end arrowhead and the line going through the center of these drawing elements and the given point.

        When there are multiple intersection points, the one closest to the given point is returned.
        """
        point = get_drawing_elements_border(
            self.end_arrowhead_drawing_elements(), point
        )
        if point is None:
            return self.end_arrowhead_tip()
        return point

    @abc.abstractmethod
    def _start_arrowhead_border_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        # base of the arrow if at (0, 0), and the direction to the left
        pass

    @abc.abstractmethod
    def _end_arrowhead_border_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        # base of the arrow if at (0, 0), and the direction to the right
        pass

    def _get_start_arrowhead_transformation(self) -> Transformation:
        arrowhead_length = self.start_arrowhead_length()
        arrowhead_base = self.start_arrowhead_base()
        segment = self.segments[0]
        if arrowhead_length == 0:
            start_point = segment.p1
            start_angle = segment.get_angle_at_fraction(0.0)
            p1 = Point(
                start_point.x + math.cos(start_angle),
                start_point.y + math.sin(start_angle),
            )
            line = Line(p1, start_point)
        else:
            line = Line(arrowhead_base, segment.p1)
        angle = line.get_angle_to_horizontal()
        angle += math.pi
        translation = Translation(arrowhead_base.x, arrowhead_base.y)
        rotation = Rotation(angle, arrowhead_base)
        return rotation * translation

    def start_arrowhead_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        """Return the drawing elements of the double-headed arc start arrowhead."""
        drawing_elements = self._start_arrowhead_border_drawing_elements()
        group = Group(
            class_=f"{type(self).__name__}_start_arrowhead",
            elements=tuple(drawing_elements),
            id_=f"{self.id_}_start_arrowhead",
            fill=self.start_arrowhead_fill,
            filter_=self.start_arrowhead_filter,
            stroke=self.start_arrowhead_stroke,
            stroke_dasharray=self.start_arrowhead_stroke_dasharray,
            stroke_dashoffset=self.start_arrowhead_stroke_dashoffset,
            stroke_linecap=self.start_arrowhead_stroke_linecap,
            stroke_linejoin=self.start_arrowhead_stroke_linejoin,
            stroke_width=self.start_arrowhead_stroke_width,
            transform=self.start_arrowhead_transform,
        )
        transformation = self._get_start_arrowhead_transformation()
        group = group.transformed(transformation)
        return [group]

    def _get_end_arrowhead_transformation(self) -> Transformation:
        arrowhead_length = self.end_arrowhead_length()
        arrowhead_base = self.end_arrowhead_base()
        segment = self.segments[-1]
        if arrowhead_length == 0:
            end_point = segment.p2
            end_angle = segment.get_angle_at_fraction(1.0)
            p1 = Point(
                end_point.x - math.cos(end_angle),
                end_point.y - math.sin(end_angle),
            )
            line = Line(p1, end_point)
        else:
            line = Line(arrowhead_base, segment.p2)
        angle = line.get_angle_to_horizontal()
        translation = Translation(arrowhead_base.x, arrowhead_base.y)
        rotation = Rotation(angle, arrowhead_base)
        return rotation * translation

    def end_arrowhead_drawing_elements(
        self,
    ) -> list[DrawingElement]:
        """Return the drawing elements of the double-headed arc end arrowhead."""
        drawing_elements = self._end_arrowhead_border_drawing_elements()
        group = Group(
            class_=f"{type(self).__name__}_end_arrowhead",
            elements=tuple(drawing_elements),
            fill=self.end_arrowhead_fill,
            filter_=self.end_arrowhead_filter,
            id_=f"{self.id_}_end_arrowhead",
            stroke=self.end_arrowhead_stroke,
            stroke_width=self.end_arrowhead_stroke_width,
            stroke_dasharray=self.end_arrowhead_stroke_dasharray,
            stroke_dashoffset=self.end_arrowhead_stroke_dashoffset,
            stroke_linecap=self.end_arrowhead_stroke_linecap,
            stroke_linejoin=self.end_arrowhead_stroke_linejoin,
            transform=self.end_arrowhead_transform,
        )
        transformation = self._get_end_arrowhead_transformation()
        group = group.transformed(transformation)
        return [group]

    def path_drawing_elements(self) -> list[Path]:
        """Return the drawing elements of the double-headed arc path."""
        start_arrowhead_length = self.start_arrowhead_length()
        end_arrowhead_length = self.end_arrowhead_length()
        if len(self.segments) == 1:
            segment = (
                self.segments[0]
                .shortened(self.start_shorten + start_arrowhead_length, "start")
                .shortened(self.end_shorten + end_arrowhead_length, "end")
            )
            actions = [
                MoveTo(segment.p1),
                self._make_path_action_from_segment(segment),
            ]
        else:
            first_segment = self.segments[0].shortened(
                self.start_shorten + start_arrowhead_length, "start"
            )
            last_segment = self.segments[-1].shortened(
                self.end_shorten + end_arrowhead_length, "end"
            )
            actions = [
                MoveTo(first_segment.p1),
                self._make_path_action_from_segment(first_segment),
            ]
            for segment in self.segments[1:-1]:
                action = self._make_path_action_from_segment(segment)
                actions.append(action)
            actions.append(self._make_path_action_from_segment(last_segment))
        path = Path(
            actions=tuple(actions),
            class_=f"{type(self).__name__}_path",
            fill=self.path_fill,
            filter_=self.path_filter,
            id_=f"{self.id_}_path",
            stroke=self.path_stroke,
            stroke_dasharray=self.path_stroke_dasharray,
            stroke_dashoffset=self.path_stroke_dashoffset,
            stroke_linecap=self.path_stroke_linecap,
            stroke_linejoin=self.path_stroke_linejoin,
            stroke_width=self.path_stroke_width,
            transform=self.path_transform,
        )
        return [path]

    def own_drawing_elements(self) -> list[DrawingElement]:
        """Return the self drawing elements of the double-headed arc. These include the drawing elements of the arc path, the start arrowhead, and the end arrowhead."""
        drawing_elements = (
            self.path_drawing_elements()
            + self.start_arrowhead_drawing_elements()
            + self.end_arrowhead_drawing_elements()
        )

        group = Group(
            class_=f"{type(self).__name__}_own",
            elements=tuple(drawing_elements),
            id_=f"{self.id_}_own",
            fill=self.fill,
            filter_=self.filter_,
            stroke=self.stroke,
            stroke_dasharray=self.stroke_dasharray,
            stroke_dashoffset=self.stroke_dashoffset,
            stroke_linecap=self.stroke_linecap,
            stroke_linejoin=self.stroke_linejoin,
            stroke_width=self.stroke_width,
            transform=self.transform,
        )
        return [group]


@dataclasses.dataclass(frozen=True, kw_only=True)
class Layout(Node):
    """Class for layouts.

    A layout is the root node holding all the visual elements of a map.
    """

    fill: NoneValueType | Color | Gradient | None = NoneValue

    def _border_drawing_elements(self) -> list[DrawingElement]:
        actions = [
            MoveTo(self.position - (self.width / 2, self.height / 2)),
            LineTo(self.position + (self.width / 2, -self.height / 2)),
            LineTo(self.position + (self.width / 2, self.height / 2)),
            LineTo(self.position + (-self.width / 2, self.height / 2)),
            ClosePath(),
        ]
        path = Path(actions=tuple(actions))
        return [path]

    def is_sublayout(
        self, other: "Layout", flattened: bool = False, unordered: bool = False
    ) -> bool:
        """Return `True` if the layout is a sublayout of another given layout, `False` otherwise."""

        def _is_sublist(
            list1: list[LayoutElement],
            list2: list[LayoutElement],
            unordered: bool = False,
        ) -> bool:
            if not unordered:
                i = 0
                for elem1 in list1:
                    elem2 = list2[i]
                    while elem2 != elem1 and i < len(list2) - 1:
                        i += 1
                        elem2 = list2[i]
                    if not elem2 == elem1:
                        return False
                    i += 1
            else:
                dlist1 = collections.defaultdict(int)
                dlist2 = collections.defaultdict(int)
                for elem1 in list1:
                    dlist1[elem1] += 1
                for elem2 in list2:
                    dlist2[elem2] += 1
                for elem in dlist1:
                    if dlist1[elem] > dlist2[elem]:
                        return False
            return True

        if self.childless() != other.childless():
            return False
        if flattened:
            return _is_sublist(
                self.flattened()[1:],
                other.flattened()[1:],
                unordered=unordered,
            )
        return _is_sublist(self.children(), other.children(), unordered=unordered)
