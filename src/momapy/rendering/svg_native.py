"""Classes for rendering in the SVG format."""

import dataclasses
import os
import typing
import collections.abc
import math
import xml.sax.saxutils

import typing_extensions

from momapy.core.elements import LayoutElement
from momapy.drawing import ClosePath
from momapy.drawing import CompositeEffect
from momapy.drawing import CompositionOperator
from momapy.drawing import CurveTo
from momapy.drawing import DrawingElement
from momapy.drawing import DropShadowEffect
from momapy.drawing import EdgeMode
from momapy.drawing import Ellipse
from momapy.drawing import EllipticalArc
from momapy.drawing import FillRule
from momapy.drawing import Filter
from momapy.drawing import FilterEffect
from momapy.drawing import FilterEffectInput
from momapy.drawing import FilterUnits
from momapy.drawing import FloodEffect
from momapy.drawing import FontStyle
from momapy.drawing import FontWeight
from momapy.drawing import GaussianBlurEffect
from momapy.drawing import Gradient
from momapy.drawing import GradientStop
from momapy.drawing import GradientUnits
from momapy.drawing import Group
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import LineTo
from momapy.drawing import LinearGradient
from momapy.drawing import MoveTo
from momapy.drawing import NoneValue
from momapy.drawing import OffsetEffect
from momapy.drawing import Path
from momapy.drawing import PRESENTATION_ATTRIBUTES
from momapy.drawing import QuadraticCurveTo
from momapy.drawing import RadialGradient
from momapy.drawing import Rectangle
from momapy.drawing import SpreadMethod
from momapy.drawing import Text
from momapy.drawing import TextAnchor
from momapy.coloring import Color
from momapy.geometry import MatrixTransformation
from momapy.geometry import Rotation
from momapy.geometry import Scaling
from momapy.geometry import Transformation
from momapy.geometry import Translation
from momapy.rendering.core import Renderer
from momapy.rendering.core import SupportsFileOutput
from momapy.utils import check_parent_dir_exists
from momapy.builder import Builder


@dataclasses.dataclass
class SVGElement(object):
    """Class for SVG elements.

    This class represents an SVG element with a name, optional text value,
    attributes, and child elements.

    Examples:
        ```python
        element = SVGElement(
            name="rect",
            attributes={"x": "0", "y": "0", "width": "100", "height": "100"}
        )
        print(element)
        ```
    """

    name: str = dataclasses.field(
        metadata={
            "description": "The tag name of the SVG element (e.g. 'svg', 'rect', 'path')"
        }
    )
    value: str | None = dataclasses.field(
        default=None,
        metadata={"description": "The optional text content of the element"},
    )
    attributes: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    elements: list["SVGElement"] = dataclasses.field(default_factory=list)

    def to_string(self, indent: int = 0) -> str:
        """Return the SVG string representing the element.

        Args:
            indent: The indentation level (number of tabs)

        Returns:
            The SVG markup as a string
        """
        s_indent = "\t" * indent
        s_value = f"{s_indent}{self.value}\n" if self.value is not None else ""
        if self.attributes:
            l_s_attributes = []
            for attr_name, attr_value in self.attributes.items():
                s_attr_name = attr_name
                s_attr_value = f'"{attr_value}"'
                s_attribute = f"{s_attr_name}={s_attr_value}"
                l_s_attributes.append(s_attribute)
            s_attributes = f" {' '.join(l_s_attributes)}"
        else:
            s_attributes = ""
        if self.elements:
            s_elements = "\n".join(
                [child.to_string(indent + 1) for child in self.elements]
            )
            s_elements += "\n"
        else:
            s_elements = ""
        return f"{s_indent}<{self.name}{s_attributes}>\n{s_value}{s_elements}{s_indent}</{self.name}>"

    def __str__(self) -> str:
        """Return the SVG string representation of the element."""
        return self.to_string()

    def add_element(self, element: "SVGElement") -> None:
        """Add a sub-element to the SVG element.

        Args:
            element: The child SVGElement to add
        """
        self.elements.append(element)


@dataclasses.dataclass
class SVGNativeRenderer(Renderer, SupportsFileOutput):
    """Renderer implementation for generating native SVG output.

    This renderer creates SVG markup directly without external dependencies.
    It supports all standard SVG features including filters, transformations,
    and presentation attributes.

    Examples:
        ```python
        from momapy.meta.nodes import Rectangle
        import momapy.geometry

        # Create a layout element to render
        node = Rectangle(
            position=momapy.geometry.Point(100.0, 100.0),
            width=200.0,
            height=100.0
        )

        # Create renderer and render the element
        renderer = SVGNativeRenderer.from_file("output.svg", 800, 600, "svg")
        renderer.begin_session()
        renderer.render_layout_element(node)
        renderer.end_session()
        ```
    """

    supported_formats: typing.ClassVar[list[str]] = ["svg"]
    default_format: typing.ClassVar[str | None] = "svg"
    _de_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        Group: "_make_group_element",
        Path: "_make_path_element",
        Text: "_make_text_element",
        Ellipse: "_make_ellipse_element",
        Rectangle: "_make_rectangle_element",
    }
    _pa_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        MoveTo: "_make_move_to_value",
        LineTo: "_make_line_to_value",
        CurveTo: "_make_curve_to_value",
        QuadraticCurveTo: "_make_quadratic_curve_to_value",
        ClosePath: "_make_close_value",
        EllipticalArc: "_make_elliptical_arc_value",
    }
    _tr_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        Translation: "_make_translation_value",
        Rotation: "_make_rotation_value",
        Scaling: "_make_scaling_value",
        MatrixTransformation: "_make_matrix_transformation_value",
    }
    _fe_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        DropShadowEffect: "_make_drop_shadow_effect_element",
        CompositeEffect: "_make_composite_effect_element",
        GaussianBlurEffect: "_make_gaussian_blur_effect_element",
        OffsetEffect: "_make_offset_effect_element",
        FloodEffect: "_make_flood_effect_element",
    }
    _fe_composite_comp_op_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        CompositionOperator.OVER: "over",
        CompositionOperator.IN: "in",
        CompositionOperator.OUT: "out",
        CompositionOperator.ATOP: "atop",
        CompositionOperator.XOR: "xor",
        CompositionOperator.LIGHTER: "lighter",
        CompositionOperator.ARITHMETIC: "arithmetic",
    }
    _fe_gaussian_blur_edgemode_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        EdgeMode.WRAP: "wrap",
        EdgeMode.DUPLICATE: "duplicate",
        NoneValue: "none",
    }
    _fe_filter_unit_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        FilterUnits.USER_SPACE_ON_USE: "UserSpaceOnUse",
        FilterUnits.OBJECT_BOUNDING_BOX: "objectBoundingBox",
    }
    _gr_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        LinearGradient: "_make_linear_gradient_element",
        RadialGradient: "_make_radial_gradient_element",
    }
    _gr_gradient_units_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        GradientUnits.USER_SPACE_ON_USE: "userSpaceOnUse",
        GradientUnits.OBJECT_BOUNDING_BOX: "objectBoundingBox",
    }
    _gr_spread_method_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        SpreadMethod.PAD: "pad",
        SpreadMethod.REFLECT: "reflect",
        SpreadMethod.REPEAT: "repeat",
    }
    _fe_input_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        FilterEffectInput.SOURCE_GRAPHIC: "SourceGraphic",
        FilterEffectInput.SOURCE_ALPHA: "SourceAlpha",
        FilterEffectInput.BACKGROUND_IMAGE: "BackgroundImage",
        FilterEffectInput.BACKGROUND_ALPHA: "BackgroundAlpha",
        FilterEffectInput.FILL_PAINT: "FillPaint",
        FilterEffectInput.STROKE_PAINT: "StrokePaint",
    }
    _te_font_style_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        FontStyle.NORMAL: "normal",
        FontStyle.ITALIC: "italic",
        FontStyle.OBLIQUE: "oblique",
    }
    _te_font_weight_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        FontWeight.NORMAL: "normal",
        FontWeight.BOLD: "bold",
        FontWeight.BOLDER: "bolder",
        FontWeight.LIGHTER: "lighter",
    }
    _te_text_anchor_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        TextAnchor.START: "start",
        TextAnchor.MIDDLE: "middle",
        TextAnchor.END: "end",
    }
    _de_fill_rule_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        FillRule.NONZERO: "nonzero",
        FillRule.EVENODD: "evenodd",
    }
    _de_stroke_linecap_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        LineCap.BUTT: "butt",
        LineCap.ROUND: "round",
        LineCap.SQUARE: "square",
    }
    _de_stroke_linejoin_value_mapping: typing.ClassVar[dict[typing.Any, str]] = {
        LineJoin.MITER: "miter",
        LineJoin.ROUND: "round",
        LineJoin.BEVEL: "bevel",
    }

    svg: SVGElement = dataclasses.field(
        metadata={
            "description": "The root SVG element that will contain all rendered content"
        }
    )
    _config: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    _filter_elements: list[SVGElement] = dataclasses.field(default_factory=list)
    _gradient_elements: list[SVGElement] = dataclasses.field(default_factory=list)

    @classmethod
    def from_file(
        cls,
        file_path: str | os.PathLike,
        width: float,
        height: float,
        format_: str | None = None,
    ) -> typing_extensions.Self:
        """Create an SVGNativeRenderer instance from a file path.

        Args:
            file_path: The output file path
            width: The width of the SVG canvas
            height: The height of the SVG canvas
            format_: The output format. ``None`` selects the backend's
                :attr:`default_format` ("svg").

        Returns:
            A new SVGNativeRenderer instance

        Raises:
            ValueError: If the format is not supported

        Examples:
            ```python
            renderer = SVGNativeRenderer.from_file("output.svg", 800, 600, "svg")
            ```
        """
        if format_ is None:
            format_ = cls.default_format
        if format_ not in cls.supported_formats:
            raise ValueError(
                f"unsupported format {format_!r}: expected one of "
                f"{', '.join(cls.supported_formats)}"
            )
        check_parent_dir_exists(file_path)
        config = {}
        config["output_file"] = file_path
        config["width"] = width
        config["height"] = height
        config["format"] = format_
        svg = SVGElement(
            name="svg",
            attributes={
                "xmlns": "http://www.w3.org/2000/svg",
                "viewBox": f"0 0 {width} {height}",
            },
        )
        return cls(svg=svg, _config=config)

    def begin_session(self) -> None:
        """Begin a rendering session.

        This method initializes the rendering context. For SVGNativeRenderer,
        no explicit initialization is needed as the SVG element is created
        during instantiation.
        """
        pass

    def end_session(self) -> None:
        """End the rendering session and save the output.

        This method finalizes the SVG document, adds any filter and gradient
        definitions to the defs section, and writes the output to the file.
        """
        defs_elements = self._filter_elements + self._gradient_elements
        if defs_elements:
            defs = SVGElement(name="defs", elements=defs_elements)
            self.svg.add_element(defs)
        if self._config.get("output_file") is not None:
            with open(self._config["output_file"], "w", encoding="utf-8") as f:
                f.write(str(self.svg))

    def new_page(self, width: float, height: float) -> None:
        """Create a new page in the output document.

        Args:
            width: The width of the new page
            height: The height of the new page

        Note:
            SVG format does not support multiple pages. This method is a no-op.
        """
        pass

    def render_layout_element(self, layout_element: LayoutElement) -> None:
        """Render a layout element to the output.

        Args:
            layout_element: The layout element to render
        """
        drawing_elements = layout_element.drawing_elements()
        for drawing_element in drawing_elements:
            self.render_drawing_element(drawing_element)

    def render_drawing_element(self, drawing_element: DrawingElement) -> None:
        """Render a drawing element to the output.

        Args:
            drawing_element: The drawing element to render

        This method converts the drawing element to an SVG element
        and adds it to the SVG document.
        """
        element = self._make_drawing_element_element(drawing_element)
        self.svg.add_element(element)

    def _make_color_value(self, color: Color) -> str:
        return f"rgb({color.red}, {color.green}, {color.blue})"

    def _make_opacity_value(self, color: Color) -> str:
        return str(color.alpha)

    def _make_transform_value(
        self, transform: collections.abc.Iterable[Transformation]
    ) -> str:
        value = " ".join(
            [
                self._make_transformation_value(transformation)
                for transformation in transform
            ]
        )
        return value

    def _make_transformation_value(self, transformation: Transformation) -> str:
        class_ = type(transformation)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        tr_func = getattr(self, self._tr_class_func_mapping[class_])
        return tr_func(transformation)

    def _make_drawing_element_element_id_class_atrributes(
        self, drawing_element: DrawingElement
    ) -> dict[str, typing.Any]:
        attributes = {}
        id_ = getattr(drawing_element, "id_", None)
        if id_ is not None:
            attributes["id"] = id_
        class_ = getattr(drawing_element, "class_", None)
        if class_ is not None:
            attributes["class"] = class_
        return attributes

    def _make_drawing_element_presentation_attributes(
        self, drawing_element: DrawingElement
    ) -> dict[str, typing.Any]:
        attributes = {}
        for attr_name in PRESENTATION_ATTRIBUTES:
            attr_value = getattr(drawing_element, attr_name)
            if attr_value is not None:
                if attr_value is NoneValue:
                    attr_value = "none"
                else:
                    if attr_name == "stroke" or attr_name == "fill":
                        class_ = type(attr_value)
                        if issubclass(class_, Builder):
                            class_ = class_._cls_to_build
                        if issubclass(class_, Gradient):
                            gradient_element = self._make_gradient_element(attr_value)
                            if gradient_element not in self._gradient_elements:
                                self._gradient_elements.append(gradient_element)
                            attr_value = f"url(#{attr_value.id_})"
                        else:
                            opacity_value = self._make_opacity_value(attr_value)
                            attributes[f"{attr_name}-opacity"] = opacity_value
                            attr_value = self._make_color_value(attr_value)
                    elif attr_name == "transform":
                        attr_value = self._make_transform_value(attr_value)
                    elif attr_name == "filter_":
                        filter_element = self._make_filter_element(attr_value)
                        if filter_element not in self._filter_elements:
                            self._filter_elements.append(filter_element)
                        attr_value = f"url(#{attr_value.id_})"
                    elif attr_name == "font_style":
                        attr_value = self._te_font_style_value_mapping[attr_value]
                    elif attr_name == "font_weight":
                        if isinstance(attr_value, FontWeight):
                            attr_value = self._te_font_weight_value_mapping[attr_value]
                    elif attr_name == "text_anchor":
                        attr_value = self._te_text_anchor_value_mapping[attr_value]
                    elif attr_name == "fill_rule":
                        attr_value = self._de_fill_rule_value_mapping[attr_value]
                    elif attr_name == "stroke_linecap":
                        attr_value = self._de_stroke_linecap_value_mapping[attr_value]
                    elif attr_name == "stroke_linejoin":
                        attr_value = self._de_stroke_linejoin_value_mapping[attr_value]
                    elif attr_name == "stroke_dasharray":
                        attr_value = " ".join(
                            [
                                str(attr_value_element)
                                for attr_value_element in attr_value
                            ]
                        )
                attr_name = attr_name.rstrip("_").replace("_", "-")
                attributes[attr_name] = attr_value
        return attributes

    def _make_filter_element(self, filter_: Filter) -> SVGElement:
        name = "filter"
        attributes = {}
        attributes["id"] = filter_.id_
        attributes["filterUnits"] = self._fe_filter_unit_value_mapping[
            filter_.filter_units
        ]
        attributes["x"] = filter_.x
        attributes["y"] = filter_.y
        attributes["width"] = filter_.width
        attributes["height"] = filter_.height
        subelements = []
        for filter_effect in filter_.effects:
            subelement = self._make_filter_effect_element(filter_effect)
            subelements.append(subelement)
        element = SVGElement(name=name, attributes=attributes, elements=subelements)
        return element

    def _make_gradient_element(self, gradient: Gradient) -> SVGElement:
        class_ = type(gradient)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        gr_func = getattr(self, self._gr_class_func_mapping[class_])
        element = gr_func(gradient)
        return element

    def _make_gradient_attributes(self, gradient: Gradient) -> dict[str, typing.Any]:
        attributes = {}
        attributes["id"] = gradient.id_
        attributes["gradientUnits"] = self._gr_gradient_units_value_mapping[
            gradient.gradient_units
        ]
        attributes["spreadMethod"] = self._gr_spread_method_value_mapping[
            gradient.spread_method
        ]
        if gradient.gradient_transform:
            attributes["gradientTransform"] = self._make_transform_value(
                gradient.gradient_transform
            )
        return attributes

    def _make_gradient_stop_element(self, stop: GradientStop) -> SVGElement:
        attributes = {}
        attributes["offset"] = stop.offset
        attributes["stop-color"] = self._make_color_value(stop.stop_color)
        attributes["stop-opacity"] = self._make_opacity_value(stop.stop_color)
        element = SVGElement(name="stop", attributes=attributes)
        return element

    def _make_linear_gradient_element(self, gradient: LinearGradient) -> SVGElement:
        attributes = self._make_gradient_attributes(gradient)
        attributes["x1"] = gradient.x1
        attributes["y1"] = gradient.y1
        attributes["x2"] = gradient.x2
        attributes["y2"] = gradient.y2
        subelements = [
            self._make_gradient_stop_element(stop) for stop in gradient.stops
        ]
        element = SVGElement(
            name="linearGradient", attributes=attributes, elements=subelements
        )
        return element

    def _make_radial_gradient_element(self, gradient: RadialGradient) -> SVGElement:
        attributes = self._make_gradient_attributes(gradient)
        attributes["cx"] = gradient.cx
        attributes["cy"] = gradient.cy
        attributes["r"] = gradient.r
        if gradient.fx is not None:
            attributes["fx"] = gradient.fx
        if gradient.fy is not None:
            attributes["fy"] = gradient.fy
        attributes["fr"] = gradient.fr
        subelements = [
            self._make_gradient_stop_element(stop) for stop in gradient.stops
        ]
        element = SVGElement(
            name="radialGradient", attributes=attributes, elements=subelements
        )
        return element

    def _make_filter_effect_element(self, filter_effect: FilterEffect) -> SVGElement:
        class_ = type(filter_effect)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        fe_func = getattr(self, self._fe_class_func_mapping[class_])
        element = fe_func(filter_effect)
        return element

    def _make_drop_shadow_effect_element(
        self, filter_effect: DropShadowEffect
    ) -> SVGElement:
        name = "feDropShadow"
        attributes = {}
        attributes["dx"] = filter_effect.dx
        attributes["dy"] = filter_effect.dy
        attributes["stdDeviation"] = filter_effect.std_deviation
        attributes["flood-opacity"] = filter_effect.flood_opacity
        attributes["flood-color"] = self._make_color_value(filter_effect.flood_color)
        if filter_effect.result is not None:
            attributes["result"] = filter_effect.result
        element = SVGElement(
            name=name,
            attributes=attributes,
        )
        return element

    def _make_composite_effect_element(
        self, filter_effect: CompositeEffect
    ) -> SVGElement:
        name = "feComposite"
        attributes = {}
        if isinstance(filter_effect.in_, FilterEffectInput):
            attributes["in"] = self._fe_input_value_mapping[filter_effect.in_]
        else:
            attributes["in"] = filter_effect.in_
        if isinstance(filter_effect.in2, FilterEffectInput):
            attributes["in2"] = self._fe_input_value_mapping[filter_effect.in2]
        else:
            attributes["in2"] = filter_effect.in2
        attributes["operator"] = self._fe_composite_comp_op_value_mapping[
            filter_effect.operator
        ]
        if filter_effect.operator == CompositionOperator.ARITHMETIC:
            attributes["k1"] = str(filter_effect.k1)
            attributes["k2"] = str(filter_effect.k2)
            attributes["k3"] = str(filter_effect.k3)
            attributes["k4"] = str(filter_effect.k4)
        if filter_effect.result is not None:
            attributes["result"] = filter_effect.result
        element = SVGElement(
            name=name,
            attributes=attributes,
        )
        return element

    def _make_flood_effect_element(self, filter_effect: FloodEffect) -> SVGElement:
        name = "feFlood"
        attributes = {}
        attributes["flood-opacity"] = filter_effect.flood_opacity
        attributes["flood-color"] = self._make_color_value(filter_effect.flood_color)
        if filter_effect.result is not None:
            attributes["result"] = filter_effect.result
        element = SVGElement(
            name=name,
            attributes=attributes,
        )
        return element

    def _make_gaussian_blur_effect_element(
        self, filter_effect: GaussianBlurEffect
    ) -> SVGElement:
        name = "feGaussianBlur"
        attributes = {}
        if isinstance(filter_effect.in_, FilterEffectInput):
            attributes["in"] = self._fe_input_value_mapping[filter_effect.in_]
        else:
            attributes["in"] = filter_effect.in_
        attributes["stdDeviation"] = filter_effect.std_deviation
        if filter_effect.edge_mode is not None:
            attributes["edgeMode"] = self._fe_gaussian_blur_edgemode_value_mapping[
                filter_effect.edge_mode
            ]
        if filter_effect.result is not None:
            attributes["result"] = filter_effect.result
        element = SVGElement(
            name=name,
            attributes=attributes,
        )
        return element

    def _make_offset_effect_element(self, filter_effect: OffsetEffect) -> SVGElement:
        name = "feOffset"
        attributes = {}
        attributes["dx"] = filter_effect.dx
        attributes["dy"] = filter_effect.dy
        if filter_effect.result is not None:
            attributes["result"] = filter_effect.result
        element = SVGElement(
            name=name,
            attributes=attributes,
        )
        return element

    def _make_drawing_element_element(
        self, drawing_element: DrawingElement
    ) -> SVGElement:
        class_ = type(drawing_element)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        de_func = getattr(self, self._de_class_func_mapping[class_])
        element = de_func(drawing_element)
        return element

    def _make_group_element(self, group: Group) -> SVGElement:
        name = "g"
        presentation_attributes = self._make_drawing_element_presentation_attributes(
            group
        )
        id_class_attributes = self._make_drawing_element_element_id_class_atrributes(
            group
        )
        attributes = presentation_attributes | id_class_attributes
        subelements = []
        for drawing_element in group.elements:
            subelement = self._make_drawing_element_element(drawing_element)
            subelements.append(subelement)
        element = SVGElement(name=name, attributes=attributes, elements=subelements)
        return element

    def _make_path_action_value(self, path_action: typing.Any) -> str:
        class_ = type(path_action)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        pa_func = getattr(self, self._pa_class_func_mapping[class_])
        value = pa_func(path_action)
        return value

    def _make_move_to_value(self, move_to: MoveTo) -> str:
        return f"M {move_to.x} {move_to.y}"

    def _make_line_to_value(self, line_to: LineTo) -> str:
        return f"L {line_to.x} {line_to.y}"

    def _make_close_value(self, close: ClosePath) -> str:
        return "Z"

    def _make_elliptical_arc_value(self, elliptical_arc: EllipticalArc) -> str:
        return (
            f"A {elliptical_arc.rx} "
            f"{elliptical_arc.ry} "
            f"{elliptical_arc.x_axis_rotation} "
            f"{elliptical_arc.arc_flag} "
            f"{elliptical_arc.sweep_flag} "
            f"{elliptical_arc.x} "
            f"{elliptical_arc.y}"
        )

    def _make_quadratic_curve_to_value(
        self, quadratic_curve_to: QuadraticCurveTo
    ) -> str:
        return (
            f"Q {quadratic_curve_to.control_point.x} "
            f"{quadratic_curve_to.control_point.y} "
            f"{quadratic_curve_to.x} "
            f"{quadratic_curve_to.y}"
        )

    def _make_curve_to_value(self, curve_to: CurveTo) -> str:
        return (
            f"C {curve_to.control_point1.x} "
            f"{curve_to.control_point1.y} "
            f"{curve_to.control_point2.x} "
            f"{curve_to.control_point2.y} "
            f"{curve_to.x} "
            f"{curve_to.y}"
        )

    def _make_path_element(self, path: Path) -> SVGElement:
        name = "path"
        presentation_attributes = self._make_drawing_element_presentation_attributes(
            path
        )
        id_class_attributes = self._make_drawing_element_element_id_class_atrributes(
            path
        )
        attributes = presentation_attributes | id_class_attributes
        d_value = " ".join(
            [self._make_path_action_value(path_action) for path_action in path.actions]
        )
        attributes["d"] = d_value
        element = SVGElement(name=name, attributes=attributes)
        return element

    def _make_text_element(self, text: Text) -> SVGElement:
        name = "text"
        presentation_attributes = self._make_drawing_element_presentation_attributes(
            text
        )
        id_class_attributes = self._make_drawing_element_element_id_class_atrributes(
            text
        )
        attributes = presentation_attributes | id_class_attributes
        attributes["x"] = text.x
        attributes["y"] = text.y
        value = xml.sax.saxutils.escape(text.text)
        element = SVGElement(name=name, attributes=attributes, value=value)
        return element

    def _make_ellipse_element(self, ellipse: Ellipse) -> SVGElement:
        name = "ellipse"
        presentation_attributes = self._make_drawing_element_presentation_attributes(
            ellipse
        )
        id_class_attributes = self._make_drawing_element_element_id_class_atrributes(
            ellipse
        )
        attributes = presentation_attributes | id_class_attributes
        attributes["cx"] = ellipse.x
        attributes["cy"] = ellipse.y
        attributes["rx"] = ellipse.rx
        attributes["ry"] = ellipse.ry
        element = SVGElement(name=name, attributes=attributes)
        return element

    def _make_rectangle_element(self, rectangle: Rectangle) -> SVGElement:
        name = "rect"
        presentation_attributes = self._make_drawing_element_presentation_attributes(
            rectangle
        )
        id_class_attributes = self._make_drawing_element_element_id_class_atrributes(
            rectangle
        )
        attributes = presentation_attributes | id_class_attributes
        attributes["x"] = rectangle.x
        attributes["y"] = rectangle.y
        attributes["width"] = rectangle.width
        attributes["height"] = rectangle.height
        attributes["rx"] = rectangle.rx
        attributes["ry"] = rectangle.ry
        element = SVGElement(name=name, attributes=attributes)
        return element

    def _make_translation_value(self, translation: Translation) -> str:
        return f"translate({translation.tx} {translation.ty})"

    def _make_rotation_value(self, rotation: Rotation) -> str:
        angle = math.degrees(rotation.angle)
        s_point = (
            f" {rotation.point.x} {rotation.point.y}"
            if rotation.point is not None
            else ""
        )
        value = f"rotate({angle}{s_point})"
        return value

    def _make_scaling_value(self, scaling: Scaling) -> str:
        return f"scale({scaling.sx} {scaling.sy})"

    def _make_matrix_transformation_value(
        self, matrix_transformation: MatrixTransformation
    ) -> str:
        m = matrix_transformation.m
        a, b = m[0][0], m[1][0]
        c, d = m[0][1], m[1][1]
        e, f = m[0][2], m[1][2]
        return f"matrix({a} {b} {c} {d} {e} {f})"


@dataclasses.dataclass
class SVGNativeCompatRenderer(SVGNativeRenderer):
    """Renderer for SVG with compatibility mode filters.

    This renderer extends SVGNativeRenderer to provide compatibility with
    older SVG viewers by converting filters to a compatible format.

    Examples:
        ```python
        renderer = SVGNativeCompatRenderer.from_file("output.svg", 800, 600, "svg")
        renderer.begin_session()
        renderer.render_layout_element(layout_element)
        renderer.end_session()
        ```
    """

    def _make_filter_element(self, filter_: Filter) -> SVGElement:
        """Create an SVG filter element with compatibility conversion.

        Args:
            filter_: The filter to convert to an SVG element

        Returns:
            An SVGElement representing the filter

        This method converts the filter to a compatible format before
        creating the SVG element.
        """
        filter_ = filter_.to_compat()
        element = super()._make_filter_element(filter_)
        return element
