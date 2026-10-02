"""Class for rendering with Cairo.

Note:
    SVG filter effects (e.g. drop shadow, Gaussian blur) are not supported
    by this backend. Cairo has no native filter primitives, so any
    `filter` attribute on drawing elements is ignored. Use the skia or
    svg-native backend if you need filter effects.
"""

import dataclasses
import typing
import typing_extensions
import math
import os

try:
    import cairo
    import gi

    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    import gi.repository.Pango
    import gi.repository.PangoCairo
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        f"The '{__name__}' module requires 'pycairo' and 'PyGObject'. "
        f"Install them with: pip install pycairo pygobject  "
        f"Or install momapy with cairo support: pip install momapy[cairo]"
    ) from e

from momapy.core.elements import LayoutElement
from momapy.drawing import ClosePath
from momapy.drawing import CurveTo
from momapy.drawing import DrawingElement
from momapy.drawing import Ellipse
from momapy.drawing import EllipticalArc as EllipticalArcDrawing
from momapy.drawing import FontStyle
from momapy.drawing import Gradient
from momapy.drawing import GradientUnits
from momapy.drawing import Group
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import LineTo
from momapy.drawing import LinearGradient
from momapy.drawing import MoveTo
from momapy.drawing import NoneValue
from momapy.drawing import Path
from momapy.drawing import QuadraticCurveTo
from momapy.drawing import Rectangle
from momapy.drawing import SpreadMethod
from momapy.drawing import Text
from momapy.geometry import Bbox
from momapy.geometry import EllipticalArc as EllipticalArcGeometry
from momapy.geometry import MatrixTransformation
from momapy.geometry import Point
from momapy.geometry import Rotation
from momapy.geometry import Scaling
from momapy.geometry import Transformation
from momapy.geometry import Translation
from momapy.rendering.core import make_gradient_matrix
from momapy.rendering.core import StatefulRenderer
from momapy.rendering.core import SupportsFileOutput
from momapy.utils import check_parent_dir_exists
from momapy.builder import Builder


@dataclasses.dataclass(kw_only=True)
class CairoRenderer(
    StatefulRenderer,
    SupportsFileOutput,
):
    """Renderer implementation using the Cairo graphics library.

    This renderer supports multiple output formats including PDF, SVG, PNG,
    and PostScript. It uses Pango for text rendering.

    SVG filter effects (drop shadow, Gaussian blur, etc.) are not supported:
    Cairo has no native filter primitives, so the `filter` attribute on
    drawing elements is ignored.

    Attributes:
        context: The Cairo context used for rendering

    Examples:
        ```python
        from momapy.meta.nodes import Rectangle
        from momapy.geometry import Point

        # Create a layout element to render
        node = Rectangle(
            position=Point(100.0, 100.0),
            width=200.0,
            height=100.0
        )

        # Create renderer and render the element
        renderer = CairoRenderer.from_file("output.pdf", 800, 600, "pdf")
        renderer.begin_session()
        renderer.render_layout_element(node)
        renderer.end_session()
        ```
    """

    supported_formats: typing.ClassVar[list[str]] = ["pdf", "svg", "png", "ps"]
    default_format: typing.ClassVar[str | None] = "pdf"
    _de_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        Group: "_render_group",
        Path: "_render_path",
        Text: "_render_text",
        Ellipse: "_render_ellipse",
        Rectangle: "_render_rectangle",
    }
    _pa_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        MoveTo: "_add_move_to",
        LineTo: "_add_line_to",
        CurveTo: "_add_curve_to",
        QuadraticCurveTo: "_add_quadratic_curve_to",
        ClosePath: "_add_close_path",
        EllipticalArcDrawing: "_add_elliptical_arc",
    }
    _tr_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        Translation: "_add_translation",
        Rotation: "_add_rotation",
        Scaling: "_add_scaling",
        MatrixTransformation: "_add_matrix_transformation",
    }
    _gr_spread_method_extend_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        SpreadMethod.PAD: cairo.EXTEND_PAD,
        SpreadMethod.REFLECT: cairo.EXTEND_REFLECT,
        SpreadMethod.REPEAT: cairo.EXTEND_REPEAT,
    }
    _de_stroke_linecap_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        LineCap.BUTT: cairo.LINE_CAP_BUTT,
        LineCap.ROUND: cairo.LINE_CAP_ROUND,
        LineCap.SQUARE: cairo.LINE_CAP_SQUARE,
    }
    _de_stroke_linejoin_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        LineJoin.MITER: cairo.LINE_JOIN_MITER,
        LineJoin.ROUND: cairo.LINE_JOIN_ROUND,
        LineJoin.BEVEL: cairo.LINE_JOIN_BEVEL,
    }
    _te_font_style_slant_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        FontStyle.NORMAL: gi.repository.Pango.Style.NORMAL,
        FontStyle.ITALIC: gi.repository.Pango.Style.ITALIC,
        FontStyle.OBLIQUE: gi.repository.Pango.Style.OBLIQUE,
    }
    context: cairo.Context = dataclasses.field(
        metadata={"description": "A cairo context"}
    )
    _config: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    _pango_font_descriptions: dict[tuple, typing.Any] = dataclasses.field(
        default_factory=dict
    )

    @classmethod
    def from_file(
        cls,
        file_path: str | os.PathLike,
        width: float,
        height: float,
        format_: str | None = None,
    ) -> typing_extensions.Self:
        """Create a CairoRenderer instance from a file path.

        Args:
            file_path: The output file path
            width: The width of the canvas
            height: The height of the canvas
            format_: The output format (pdf, svg, png, or ps). ``None`` selects
                the backend's :attr:`default_format` ("pdf").

        Returns:
            A new CairoRenderer instance

        Raises:
            ValueError: If the format is not supported

        Examples:
            ```python
            renderer = CairoRenderer.from_file("output.pdf", 800, 600, "pdf")
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
        if format_ == "pdf":
            surface = cairo.PDFSurface(file_path, width, height)
        elif format_ == "ps":
            surface = cairo.PSSurface(file_path, width, height)
        elif format_ == "svg":
            surface = cairo.SVGSurface(file_path, width, height)
        elif format_ == "png":
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        config["surface"] = surface
        config["file_path"] = file_path
        config["width"] = width
        config["height"] = height
        config["format"] = format_
        context = cairo.Context(surface)
        return cls(context=context, _config=config)

    def begin_session(self) -> None:
        """Begin a rendering session.

        This method initializes the rendering context. For CairoRenderer,
        no explicit initialization is needed beyond the context setup.
        """
        pass

    def end_session(self) -> None:
        """End the rendering session and save the output.

        This method finalizes the rendering and saves the output to the file.
        For PNG format, it writes the image data. For other formats, it
        finishes and flushes the surface.
        """
        surface = self.context.get_target()
        format_ = self._config.get("format")
        if format_ == "png":
            surface.write_to_png(self._config["file_path"])
        surface.finish()
        surface.flush()

    def new_page(self, width: float, height: float) -> None:
        """Create a new page in the output document.

        Args:
            width: The width of the new page
            height: The height of the new page

        Note:
            Only PDF and PostScript formats support multiple pages.
            Other formats will ignore this call.
        """
        format_ = self._config.get("format")
        if format_ == "pdf" or format_ == "ps":
            self.context.show_page()
            surface = self.context.get_target()
            surface.set_size(width, height)

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

        This method handles transformations and delegates to
        the appropriate rendering method based on the drawing element type.
        """
        self.save()
        self.set_current_state_from_drawing_element(drawing_element)
        self._add_transform_from_drawing_element(drawing_element)
        class_ = type(drawing_element)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        de_func = getattr(self, self._de_class_func_mapping[class_])
        de_func(drawing_element)
        self.restore()

    def self_save(self) -> None:
        """Save the Cairo context state.

        This method saves the current state of the Cairo context, including
        transformations, clipping regions, and drawing parameters.
        """
        self.context.save()

    def self_restore(self) -> None:
        """Restore the Cairo context state.

        This method restores the Cairo context to the state saved by the
        most recent call to self_save().
        """
        self.context.restore()
        self.context.new_path()

    def _make_stroke_paint(self, drawing_element: DrawingElement) -> bool:
        stroke = self.get_current_value("stroke")
        stroke_width = self.get_current_value("stroke_width")
        stroke_dasharray = self.get_current_value("stroke_dasharray")
        stroke_dashoffset = self.get_current_value("stroke_dashoffset")

        if stroke is not NoneValue:
            self.context.set_line_width(stroke_width)
            self.context.set_line_cap(
                self._de_stroke_linecap_mapping[
                    self.get_current_value("stroke_linecap")
                ]
            )
            self.context.set_line_join(
                self._de_stroke_linejoin_mapping[
                    self.get_current_value("stroke_linejoin")
                ]
            )
            self._set_context_source(stroke, drawing_element)
            if stroke_dasharray is not None and stroke_dasharray is not NoneValue:
                self.context.set_dash(stroke_dasharray, stroke_dashoffset or 0)
            else:
                self.context.set_dash([])
            return True
        return False

    def _make_fill_paint(self, drawing_element: DrawingElement) -> bool:
        fill = self.get_current_value("fill")
        if fill is not NoneValue:
            self._set_context_source(fill, drawing_element)
            return True
        return False

    def _set_context_source(
        self, paint: typing.Any, drawing_element: DrawingElement
    ) -> None:
        class_ = type(paint)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        if issubclass(class_, Gradient):
            bbox = drawing_element.bbox()
            if paint.gradient_units == GradientUnits.OBJECT_BOUNDING_BOX and (
                bbox.width == 0 or bbox.height == 0
            ):
                self.context.set_source_rgba(0.0, 0.0, 0.0, 0.0)
            else:
                self.context.set_source(self._make_gradient_source(paint, bbox))
        else:
            self.context.set_source_rgba(*paint.to_rgba(rgba_range=(0.0, 1.0)))

    def _make_gradient_source(self, gradient: Gradient, bbox: Bbox) -> typing.Any:
        class_ = type(gradient)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        if issubclass(class_, LinearGradient):
            source = cairo.LinearGradient(
                gradient.x1, gradient.y1, gradient.x2, gradient.y2
            )
        else:
            focal_x = gradient.fx if gradient.fx is not None else gradient.cx
            focal_y = gradient.fy if gradient.fy is not None else gradient.cy
            source = cairo.RadialGradient(
                focal_x, focal_y, gradient.fr, gradient.cx, gradient.cy, gradient.r
            )
        for stop in gradient.stops:
            source.add_color_stop_rgba(
                stop.offset, *stop.stop_color.to_rgba(rgba_range=(0.0, 1.0))
            )
        source.set_extend(self._gr_spread_method_extend_mapping[gradient.spread_method])
        matrix = make_gradient_matrix(gradient, bbox)
        cairo_matrix = cairo.Matrix(
            xx=matrix[0][0],
            yx=matrix[1][0],
            xy=matrix[0][1],
            yy=matrix[1][1],
            x0=matrix[0][2],
            y0=matrix[1][2],
        )
        cairo_matrix.invert()
        source.set_matrix(cairo_matrix)
        return source

    def _stroke_and_fill(self, drawing_element: DrawingElement) -> None:
        has_fill = self._make_fill_paint(drawing_element)
        has_stroke = self.get_current_value("stroke") is not NoneValue

        if has_fill:
            if has_stroke:
                self.context.fill_preserve()
            else:
                self.context.fill()

        if has_stroke:
            self._make_stroke_paint(drawing_element)
            self.context.stroke()

    def _add_transform_from_drawing_element(
        self, drawing_element: DrawingElement
    ) -> None:
        if (
            drawing_element.transform is not None
            and drawing_element.transform is not NoneValue
        ):
            for transformation in drawing_element.transform:
                self._add_transformation(transformation)

    def _add_transformation(self, transformation: Transformation) -> None:
        class_ = type(transformation)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        tr_func = getattr(self, self._tr_class_func_mapping[class_])
        return tr_func(transformation)

    def _render_group(self, group: Group) -> None:
        for drawing_element in group.elements:
            self.render_drawing_element(drawing_element)

    def _add_path_action_to_context(self, path_action: typing.Any) -> None:
        class_ = type(path_action)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        pa_func = getattr(self, self._pa_class_func_mapping[class_])
        pa_func(path_action)

    def _render_path(self, path: Path) -> None:
        for action in path.actions:
            self._add_path_action_to_context(action)
        self._stroke_and_fill(path)

    def _render_text(self, text: Text) -> None:
        pango_layout = gi.repository.PangoCairo.create_layout(self.context)

        font_family = self.get_current_value("font_family")
        font_size = self.get_current_value("font_size")
        font_weight = self.get_current_value("font_weight")
        font_style = self.get_current_value("font_style")

        pango_font_description = self._pango_font_descriptions.get(
            (font_family, font_size, font_weight, font_style)
        )

        if pango_font_description is None:
            pango_font_description = gi.repository.Pango.FontDescription()
            pango_font_description.set_family(font_family)
            pango_font_description.set_absolute_size(
                gi.repository.Pango.units_from_double(font_size)
            )
            pango_font_description.set_weight(int(font_weight))
            pango_style = self._te_font_style_slant_mapping.get(
                font_style, gi.repository.Pango.Style.NORMAL
            )
            pango_font_description.set_style(pango_style)
            self._pango_font_descriptions[
                (font_family, font_size, font_weight, font_style)
            ] = pango_font_description

        pango_layout.set_font_description(pango_font_description)
        pango_layout.set_text(text.text)
        pos = pango_layout.index_to_pos(0)
        x_offset = gi.repository.Pango.units_to_double(pos.x)
        pango_layout_iter = pango_layout.get_iter()
        baseline = pango_layout_iter.get_baseline()
        y_offset = gi.repository.Pango.units_to_double(baseline)
        if self._make_fill_paint(text):
            self.context.move_to(text.x - x_offset, text.y - y_offset)
            gi.repository.PangoCairo.show_layout(self.context, pango_layout)
        if self._make_stroke_paint(text):
            self.context.move_to(text.x - x_offset, text.y - y_offset)
            gi.repository.PangoCairo.layout_path(self.context, pango_layout)
            self.context.stroke()

    def _render_ellipse(self, ellipse: Ellipse) -> None:
        self.context.save()
        self.context.translate(ellipse.x, ellipse.y)
        self.context.scale(ellipse.rx, ellipse.ry)
        self.context.arc(0, 0, 1, 0, 2 * math.pi)
        self.context.close_path()
        self.context.restore()
        self._stroke_and_fill(ellipse)

    def _render_rectangle(self, rectangle: Rectangle) -> None:
        path = rectangle.to_path()
        self._render_path(path)

    def _add_move_to(self, move_to: MoveTo) -> None:
        self.context.move_to(move_to.x, move_to.y)

    def _add_line_to(self, line_to: LineTo) -> None:
        self.context.line_to(line_to.x, line_to.y)

    def _add_curve_to(self, curve_to: CurveTo) -> None:
        self.context.curve_to(
            curve_to.control_point1.x,
            curve_to.control_point1.y,
            curve_to.control_point2.x,
            curve_to.control_point2.y,
            curve_to.x,
            curve_to.y,
        )

    def _add_quadratic_curve_to(self, quadratic_curve_to: QuadraticCurveTo) -> None:
        cairo_current_point = self.context.get_current_point()
        current_point = Point(cairo_current_point[0], cairo_current_point[1])
        curve_to = quadratic_curve_to.to_curve_to(current_point)
        self._add_curve_to(curve_to)

    def _add_close_path(self, close_path: ClosePath) -> None:
        self.context.close_path()

    def _add_elliptical_arc(self, elliptical_arc: EllipticalArcDrawing) -> None:
        current_point = self.context.get_current_point()
        p1 = Point(current_point[0], current_point[1])

        obj = EllipticalArcGeometry(
            p1=p1,
            p2=elliptical_arc.point,
            rx=elliptical_arc.rx,
            ry=elliptical_arc.ry,
            x_axis_rotation=elliptical_arc.x_axis_rotation,
            arc_flag=elliptical_arc.arc_flag,
            sweep_flag=elliptical_arc.sweep_flag,
        )

        cx, cy, rx, ry, sigma, theta1, theta2, delta_theta = (
            obj.get_center_parameterization()
        )

        self.context.save()
        self.context.translate(cx, cy)
        self.context.rotate(sigma)
        self.context.scale(rx, ry)

        if delta_theta > 0:
            self.context.arc(0, 0, 1, theta1, theta2)
        else:
            self.context.arc_negative(0, 0, 1, theta1, theta2)

        self.context.restore()

    def _add_translation(self, translation: Translation) -> None:
        self.context.translate(translation.tx, translation.ty)

    def _add_rotation(self, rotation: Rotation) -> None:
        if rotation.point is not None:
            self.context.translate(rotation.point.x, rotation.point.y)
            self.context.rotate(rotation.angle)
            self.context.translate(-rotation.point.x, -rotation.point.y)
        else:
            self.context.rotate(rotation.angle)

    def _add_scaling(self, scaling: Scaling) -> None:
        self.context.scale(scaling.sx, scaling.sy)

    def _add_matrix_transformation(
        self, matrix_transformation: MatrixTransformation
    ) -> None:
        m = cairo.Matrix(
            xx=matrix_transformation.m[0][0],
            yx=matrix_transformation.m[1][0],
            xy=matrix_transformation.m[0][1],
            yy=matrix_transformation.m[1][1],
            x0=matrix_transformation.m[0][2],
            y0=matrix_transformation.m[1][2],
        )
        self.context.transform(m)
