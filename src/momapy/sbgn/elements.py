"""Abstract base classes and mixins for SBGN model and layout elements.

The public base classes here (``SBGNModelElement``, ``SBGNAuxiliaryUnit``,
``SBGNRole``, ``SBGNNode``, ``SBGNSingleHeadedArc``, ``SBGNDoubleHeadedArc``)
are part of the public API and may be subclassed.

The private ``_*Mixin`` classes are an internal composition protocol; their
public value (anchors, fields) is already reachable on the concrete ``*Layout``
and ``*Node`` classes, which is what you should subclass.
"""

import abc
import dataclasses
import typing

from momapy.builder import issubclass_or_builder
from momapy.coloring import Color
from momapy.coloring import black
from momapy.coloring import white
from momapy.core.elements import Orientation
from momapy.core.elements import ModelElement
from momapy.core.layout import DoubleHeadedArc
from momapy.core.layout import Node
from momapy.core.layout import Shape
from momapy.core.layout import SingleHeadedArc
from momapy.core.layout import TextLayout
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import Gradient
from momapy.drawing import DEFAULT_FONT_FAMILY
from momapy.drawing import DrawingElement
from momapy.drawing import Filter
from momapy.drawing import FontStyle
from momapy.drawing import FontWeight
from momapy.drawing import Group
from momapy.drawing import LineTo
from momapy.drawing import MoveTo
from momapy.drawing import NoneValue
from momapy.drawing import NoneValueType
from momapy.drawing import Path
from momapy.geometry import Point
from momapy.geometry import Transformation


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNModelElement(ModelElement):
    """Abstract base class for SBGN model elements."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNAuxiliaryUnit(SBGNModelElement):
    """Abstract base class for SBGN auxiliary units."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNRole(SBGNModelElement):
    """Abstract base class for SBGN roles."""

    referred_element: SBGNModelElement = dataclasses.field(
        metadata={"description": "The SBGN model element this role refers to."}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNNode(Node):
    """Abstract base class for SBGN nodes."""

    fill: NoneValueType | Color | Gradient | None = white
    stroke: NoneValueType | Color | Gradient | None = black
    stroke_width: float | None = 1.25

    def _border_drawing_elements(self) -> list[DrawingElement]:
        """Generate drawing elements for the node border.

        Returns:
            List of drawing elements composing the border.
        """
        drawing_elements = []
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
class SBGNSingleHeadedArc(SingleHeadedArc):
    """Abstract base class for SBGN single-headed arcs."""

    arrowhead_fill: NoneValueType | Color | Gradient | None = white
    arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    arrowhead_stroke_width: float | None = 1.25
    path_fill: NoneValueType | Color | Gradient | None = NoneValue
    path_stroke: NoneValueType | Color | Gradient | None = black
    path_stroke_width: float | None = 1.25


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNDoubleHeadedArc(DoubleHeadedArc):
    """Abstract base class for SBGN double-headed arcs."""

    end_arrowhead_fill: NoneValueType | Color | Gradient | None = white
    end_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    end_arrowhead_stroke_width: float | None = 1.25
    path_fill: NoneValueType | Color | Gradient | None = NoneValue
    path_stroke: NoneValueType | Color | Gradient | None = black
    path_stroke_width: float | None = 1.25
    start_arrowhead_fill: NoneValueType | Color | Gradient | None = white
    start_arrowhead_stroke: NoneValueType | Color | Gradient | None = black
    start_arrowhead_stroke_width: float | None = 1.25


@dataclasses.dataclass(frozen=True)
class _SBGNMixin(object):
    """SBGN mixin."""

    @classmethod
    @abc.abstractmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        """Generate drawing elements for this mixin.

        Args:
            obj: The object instance to generate elements for.

        Returns:
            List of drawing elements.
        """
        pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class _ConnectorsMixin(_SBGNMixin):
    """Connectors mixin."""

    orientation: Orientation = dataclasses.field(
        default=Orientation.HORIZONTAL,
        metadata={"description": "Orientation of connectors (HORIZONTAL or VERTICAL)."},
    )
    left_to_right: bool = dataclasses.field(
        default=True,
        metadata={"description": "Whether connectors flow left to right."},
    )
    left_connector_length: float = dataclasses.field(
        default=10.0,
        metadata={"description": "Length of the left connector."},
    )
    right_connector_length: float = dataclasses.field(
        default=10.0,
        metadata={"description": "Length of the right connector."},
    )
    left_connector_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "Stroke color for the left connector line."},
    )
    left_connector_stroke_width: float | None = dataclasses.field(
        default=None,
        metadata={"description": "Stroke width for the left connector line."},
    )
    left_connector_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Dash pattern for the left connector line."},
        )
    )
    left_connector_stroke_dashoffset: float | None = dataclasses.field(
        default=None,
        metadata={"description": "Dash offset for the left connector line."},
    )
    left_connector_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "Line cap for the left connector line."},
    )
    left_connector_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "Line join for the left connector line."},
    )
    left_connector_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "Fill color for the left connector."},
    )
    left_connector_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Transformations applied to the left connector."},
        )
    )
    left_connector_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "Filter applied to the left connector."},
    )
    right_connector_stroke: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "Stroke color for the right connector line."},
    )
    right_connector_stroke_width: float | None = dataclasses.field(
        default=None,
        metadata={"description": "Stroke width for the right connector line."},
    )
    right_connector_stroke_dasharray: NoneValueType | tuple[float, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Dash pattern for the right connector line."},
        )
    )
    right_connector_stroke_dashoffset: float | None = dataclasses.field(
        default=None,
        metadata={"description": "Dash offset for the right connector line."},
    )
    right_connector_stroke_linecap: LineCap | None = dataclasses.field(
        default=None,
        metadata={"description": "Line cap for the right connector line."},
    )
    right_connector_stroke_linejoin: LineJoin | None = dataclasses.field(
        default=None,
        metadata={"description": "Line join for the right connector line."},
    )
    right_connector_fill: NoneValueType | Color | Gradient | None = dataclasses.field(
        default=None,
        metadata={"description": "Fill color for the right connector."},
    )
    right_connector_transform: NoneValueType | tuple[Transformation, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Transformations applied to the right connector."},
        )
    )
    right_connector_filter: NoneValueType | Filter | None = dataclasses.field(
        default=None,
        metadata={"description": "Filter applied to the right connector."},
    )

    def left_connector_base(self) -> Point:
        """Get the base point of the left connector.

        Returns:
            Point where the left connector attaches to the shape.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y - self.height / 2)
        else:
            return Point(self.x - self.width / 2, self.y)

    def right_connector_base(self) -> Point:
        """Get the base point of the right connector.

        Returns:
            Point where the right connector attaches to the shape.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y + self.height / 2)
        else:
            return Point(self.x + self.width / 2, self.y)

    def left_connector_tip(self) -> Point:
        """Get the tip point of the left connector.

        Returns:
            Point at the end of the left connector line.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y - self.height / 2 - self.left_connector_length)
        else:
            return Point(self.x - self.width / 2 - self.left_connector_length, self.y)

    def right_connector_tip(self) -> Point:
        """Get the tip point of the right connector.

        Returns:
            Point at the end of the right connector line.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y + self.height / 2 + self.right_connector_length)
        else:
            return Point(self.x + self.width / 2 + self.right_connector_length, self.y)

    def west(self) -> Point:
        """Get the west (left) anchor point.

        Returns:
            Point on the west side of the element.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x - self.width / 2, self.y)
        else:
            return Point(self.x - self.width / 2 - self.left_connector_length, self.y)

    def south(self) -> Point:
        """Get the south (bottom) anchor point.

        Returns:
            Point on the south side of the element.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y + self.height / 2 + self.right_connector_length)
        else:
            return Point(self.x, self.y + self.height / 2)

    def east(self) -> Point:
        """Get the east (right) anchor point.

        Returns:
            Point on the east side of the element.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x + self.width / 2, self.y)
        else:
            return Point(self.x + self.width / 2 + self.right_connector_length, self.y)

    def north(self) -> Point:
        """Get the north (top) anchor point.

        Returns:
            Point on the north side of the element.
        """
        if self.orientation == Orientation.VERTICAL:
            return Point(self.x, self.y - self.height / 2 - self.left_connector_length)
        else:
            return Point(self.x, self.y - self.height / 2)

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        """Generate drawing elements for connectors.

        Args:
            obj: The object instance to generate elements for.

        Returns:
            List of drawing elements for the connector lines.
        """
        if obj.orientation == Orientation.VERTICAL:
            left_actions = [
                MoveTo(obj.left_connector_base()),
                LineTo(obj.left_connector_base() - (0, obj.left_connector_length)),
            ]
            right_actions = [
                MoveTo(obj.right_connector_base()),
                LineTo(obj.right_connector_base() + (0, obj.right_connector_length)),
            ]
        else:
            left_actions = [
                MoveTo(obj.left_connector_base()),
                LineTo(obj.left_connector_base() - (obj.left_connector_length, 0)),
            ]
            right_actions = [
                MoveTo(obj.right_connector_base()),
                LineTo(obj.right_connector_base() + (obj.right_connector_length, 0)),
            ]
        path_left = Path(
            stroke=obj.left_connector_stroke,
            stroke_width=obj.left_connector_stroke_width,
            stroke_dasharray=obj.left_connector_stroke_dasharray,
            stroke_dashoffset=obj.left_connector_stroke_dashoffset,
            stroke_linecap=obj.left_connector_stroke_linecap,
            stroke_linejoin=obj.left_connector_stroke_linejoin,
            fill=obj.left_connector_fill,
            transform=obj.left_connector_transform,
            filter_=obj.left_connector_filter,
            actions=left_actions,
        )
        path_right = Path(
            stroke=obj.right_connector_stroke,
            stroke_width=obj.right_connector_stroke_width,
            stroke_dasharray=obj.right_connector_stroke_dasharray,
            stroke_dashoffset=obj.right_connector_stroke_dashoffset,
            stroke_linecap=obj.right_connector_stroke_linecap,
            stroke_linejoin=obj.right_connector_stroke_linejoin,
            fill=obj.right_connector_fill,
            transform=obj.right_connector_transform,
            filter_=obj.right_connector_filter,
            actions=right_actions,
        )
        return [path_left, path_right]


@dataclasses.dataclass(frozen=True)
class _SimpleMixin(_SBGNMixin):
    """Simple mixin."""

    @abc.abstractmethod
    def _make_shape(self) -> Shape:
        """Create the shape for this node.

        Returns:
            Shape object representing the node's geometry.
        """
        pass

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        """Generate drawing elements for the shape.

        Args:
            obj: The object instance to generate elements for.

        Returns:
            List of drawing elements.
        """
        shape = obj._make_shape()
        drawing_elements = shape.drawing_elements()
        return drawing_elements


@dataclasses.dataclass(frozen=True, kw_only=True)
class _MultiMixin(_SBGNMixin):
    """Multi mixin."""

    _n: typing.ClassVar[int] = 2
    offset: float = dataclasses.field(
        default=3.0,
        metadata={"description": "Offset distance between stacked units."},
    )
    subunits_stroke: tuple[NoneValueType | Color | Gradient, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Tuple of stroke colors for each subunit."},
        )
    )
    subunits_stroke_width: tuple[NoneValueType | float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of stroke widths for each subunit."},
    )
    subunits_stroke_dasharray: tuple[NoneValueType | tuple[float, ...], ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Tuple of dash patterns for each subunit."},
        )
    )
    subunits_stroke_dashoffset: tuple[float, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of dash offsets for each subunit."},
    )
    subunits_stroke_linecap: tuple[LineCap, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of line caps for each subunit."},
    )
    subunits_stroke_linejoin: tuple[LineJoin, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of line joins for each subunit."},
    )
    subunits_fill: tuple[NoneValueType | Color | Gradient, ...] | None = (
        dataclasses.field(
            default=None,
            metadata={"description": "Tuple of fill colors for each subunit."},
        )
    )
    subunits_transform: (
        tuple[NoneValueType | tuple[Transformation, ...], ...] | None
    ) = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of transformations for each subunit."},
    )
    subunits_filter: tuple[NoneValueType | Filter, ...] | None = dataclasses.field(
        default=None,
        metadata={"description": "Tuple of filters for each subunit."},
    )

    @abc.abstractmethod
    def _make_subunit_shape(
        self,
        position: Point,
        width: float,
        height: float,
    ) -> Shape:
        """Create a single subunit shape.

        Args:
            position: Center position for the subunit.
            width: Width of the subunit.
            height: Height of the subunit.

        Returns:
            Shape object for the subunit.
        """
        pass

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        """Generate drawing elements for all subunits.

        Args:
            obj: The object instance to generate elements for.

        Returns:
            List of drawing elements for all stacked subunits.
        """
        drawing_elements = []
        width = obj.width - obj.offset * (obj._n - 1)
        height = obj.height - obj.offset * (obj._n - 1)
        for i in range(obj._n):
            position = obj.position + (
                obj.width / 2 - width / 2 - i * obj.offset,
                obj.height / 2 - height / 2 - i * obj.offset,
            )
            kwargs = {}
            for attr_name in [
                "stroke",
                "stroke_width",
                "stroke_dasharray",
                "stroke_dashoffset",
                "stroke_linecap",
                "stroke_linejoin",
                "fill",
                "transform",
                "filter",
            ]:
                attr_value = getattr(obj, f"subunits_{attr_name}")
                if attr_value is not None and len(attr_value) > i:
                    kwarg_name = "filter_" if attr_name == "filter" else attr_name
                    kwargs[kwarg_name] = attr_value[i]
            subunit_shape = obj._make_subunit_shape(position, width, height)
            kwargs["elements"] = subunit_shape.drawing_elements()
            group = Group(**kwargs)
            drawing_elements.append(group)
        return drawing_elements

    def label_center(self) -> Point:
        """Get the center position for the node label.

        Returns:
            Point where the label should be centered.
        """
        width = self.width - self.offset * (self._n - 1)
        height = self.height - self.offset * (self._n - 1)
        position = self.position + (
            self.width / 2 - width / 2 - (self._n - 1) * self.offset,
            self.height / 2 - height / 2 - (self._n - 1) * self.offset,
        )
        return self._make_subunit_shape(
            position=position, width=width, height=height
        ).position


@dataclasses.dataclass(frozen=True, kw_only=True)
class _TextMixin(_SBGNMixin):
    """Text mixin."""

    _font_size_func: typing.ClassVar[typing.Callable]
    text: str = dataclasses.field(
        default="",
        metadata={"description": "Text content to display."},
    )
    font_family: str = dataclasses.field(
        default=DEFAULT_FONT_FAMILY,
        metadata={"description": "Font family for the text."},
    )
    font_fill: Color | Gradient | NoneValueType = dataclasses.field(
        default=black,
        metadata={"description": "Fill color for the text."},
    )
    font_stroke: Color | Gradient | NoneValueType = dataclasses.field(
        default=NoneValue,
        metadata={"description": "Stroke color for the text outline."},
    )
    font_style: FontStyle = dataclasses.field(
        default=FontStyle.NORMAL,
        metadata={"description": "Font style (normal, italic, etc.)."},
    )
    font_weight: FontWeight | float = dataclasses.field(
        default=FontWeight.NORMAL,
        metadata={"description": "Font weight (normal, bold, etc.)."},
    )

    def _make_text_layout(self) -> TextLayout:
        """Create a text layout for the label.

        Returns:
            TextLayout object configured for this node's label.
        """
        text_layout = TextLayout(
            text=self.text,
            position=self.label_center(),
            font_family=self.font_family,
            font_size=self._font_size_func(),
            font_style=self.font_style,
            font_weight=self.font_weight,
            fill=self.font_fill,
            stroke=self.font_stroke,
        )
        return text_layout

    @classmethod
    def _mixin_drawing_elements(cls, obj: typing.Any) -> list[DrawingElement]:
        """Generate drawing elements for the text label.

        Args:
            obj: The object instance to generate elements for.

        Returns:
            List of drawing elements for the text.
        """
        return obj._make_text_layout().drawing_elements()
