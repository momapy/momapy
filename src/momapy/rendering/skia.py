"""Class for rendering with Skia."""

import dataclasses
import typing
import typing_extensions
import math
import os

try:
    import skia
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        f"The '{__name__}' module requires the 'skia-python' package. "
        f"Install it with: pip install skia-python  "
        f"Or install momapy with skia support: pip install momapy[skia]"
    ) from e

from momapy.drawing import ClosePath
from momapy.drawing import CompositeEffect
from momapy.drawing import CompositionOperator
from momapy.drawing import CurveTo
from momapy.drawing import DrawingElement
from momapy.drawing import DropShadowEffect
from momapy.drawing import EdgeMode
from momapy.drawing import Ellipse
from momapy.drawing import EllipticalArc
from momapy.drawing import Filter
from momapy.drawing import FilterEffectInput
from momapy.drawing import FloodEffect
from momapy.drawing import FontStyle
from momapy.drawing import GaussianBlurEffect
from momapy.drawing import Gradient
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
from momapy.drawing import QuadraticCurveTo
from momapy.drawing import Rectangle
from momapy.drawing import SpreadMethod
from momapy.drawing import Text
from momapy.geometry import Bbox
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
from momapy.core.elements import LayoutElement


@dataclasses.dataclass(kw_only=True)
class SkiaRenderer(
    StatefulRenderer,
    SupportsFileOutput,
):
    """Renderer implementation using the Skia graphics library.

    This renderer supports multiple output formats including PDF, SVG, PNG,
    JPEG, and WebP. It provides hardware-accelerated rendering capabilities
    and advanced features like filters and effects.

    Attributes:
        canvas: The Skia canvas used for rendering

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
        renderer = SkiaRenderer.from_file("output.pdf", 800, 600, "pdf")
        renderer.begin_session()
        renderer.render_layout_element(node)
        renderer.end_session()
        ```
    """

    supported_formats: typing.ClassVar[list[str]] = [
        "pdf",
        "svg",
        "png",
        "jpeg",
        "webp",
    ]
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
        EllipticalArc: "_add_elliptical_arc",
    }
    _tr_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        Translation: "_add_translation",
        Rotation: "_add_rotation",
        Scaling: "_add_scaling",
        MatrixTransformation: "_add_matrix_transformation",
    }
    _fe_class_func_mapping: typing.ClassVar[dict[type, str]] = {
        DropShadowEffect: "_make_drop_shadow_effect",
        CompositeEffect: "_make_composite_effect",
        GaussianBlurEffect: "_make_gaussian_blur_effect",
        OffsetEffect: "_make_offset_effect",
        FloodEffect: "_make_flood_effect",
    }
    _fe_composite_comp_op_blendmode_mapping: typing.ClassVar[
        dict[typing.Any, typing.Any]
    ] = {
        CompositionOperator.OVER: skia.BlendMode.kSrcOver,
        CompositionOperator.IN: skia.BlendMode.kSrcIn,
        CompositionOperator.OUT: skia.BlendMode.kSrcOut,
        CompositionOperator.ATOP: skia.BlendMode.kSrcATop,
        CompositionOperator.XOR: skia.BlendMode.kXor,
        CompositionOperator.LIGHTER: skia.BlendMode.kLighten,
    }
    _fe_gaussian_blur_edgemode_tilemode_mapping: typing.ClassVar[
        dict[typing.Any, typing.Any]
    ] = {
        EdgeMode.WRAP: skia.TileMode.kMirror,
        EdgeMode.DUPLICATE: skia.TileMode.kClamp,
        NoneValue: skia.TileMode.kDecal,
    }
    _gr_spread_method_tilemode_mapping: typing.ClassVar[
        dict[typing.Any, typing.Any]
    ] = {
        SpreadMethod.PAD: skia.TileMode.kClamp,
        SpreadMethod.REFLECT: skia.TileMode.kMirror,
        SpreadMethod.REPEAT: skia.TileMode.kRepeat,
    }
    _de_stroke_linecap_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        LineCap.BUTT: skia.Paint.kButt_Cap,
        LineCap.ROUND: skia.Paint.kRound_Cap,
        LineCap.SQUARE: skia.Paint.kSquare_Cap,
    }
    _de_stroke_linejoin_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        LineJoin.MITER: skia.Paint.kMiter_Join,
        LineJoin.ROUND: skia.Paint.kRound_Join,
        LineJoin.BEVEL: skia.Paint.kBevel_Join,
    }
    _te_font_style_slant_mapping: typing.ClassVar[dict[typing.Any, typing.Any]] = {
        FontStyle.NORMAL: skia.FontStyle.Slant.kUpright_Slant,
        FontStyle.ITALIC: skia.FontStyle.Slant.kItalic_Slant,
        FontStyle.OBLIQUE: skia.FontStyle.Slant.kOblique_Slant,
    }
    canvas: skia.Canvas = dataclasses.field(metadata={"description": "A skia canvas"})
    _config: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    _skia_typefaces: dict[tuple, typing.Any] = dataclasses.field(default_factory=dict)
    _skia_fonts: dict[tuple, typing.Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_file(
        cls,
        file_path: str | os.PathLike,
        width: float,
        height: float,
        format_: str | None = None,
    ) -> typing_extensions.Self:
        """Create a SkiaRenderer instance from a file path.

        Args:
            file_path: The output file path
            width: The width of the canvas
            height: The height of the canvas
            format_: The output format (pdf, svg, png, jpeg, or webp). ``None``
                selects the backend's :attr:`default_format` ("pdf").

        Returns:
            A new SkiaRenderer instance

        Raises:
            ValueError: If the format is not supported

        Examples:
            ```python
            renderer = SkiaRenderer.from_file("output.pdf", 800, 600, "pdf")
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
        canvas = None
        if format_ == "pdf":
            stream = skia.FILEWStream(file_path)
            document = skia.PDF.MakeDocument(stream)
            canvas = document.beginPage(width, height)
            config["stream"] = stream
            config["document"] = document
        elif format_ in ["png", "jpeg", "webp"]:
            surface = skia.Surface(width=int(width), height=int(height))
            canvas = surface.getCanvas()
            config["surface"] = surface
            config["file_path"] = file_path
        elif format_ == "svg":
            stream = skia.FILEWStream(file_path)
            canvas = skia.SVGCanvas.Make((width, height), stream)
            config["stream"] = stream
        config["file_path"] = file_path
        config["width"] = width
        config["height"] = height
        config["format"] = format_
        return cls(canvas=canvas, _config=config)

    def begin_session(self) -> None:
        """Begin a rendering session.

        This method initializes the rendering context. For SkiaRenderer,
        no explicit initialization is needed beyond the canvas setup.
        """
        pass

    def end_session(self) -> None:
        """End the rendering session and save the output.

        This method finalizes the rendering, flushes the canvas, and saves
        the output to the file. The specific actions depend on the output format:
        - PDF: Ends the page and closes the document
        - PNG/JPEG/WebP: Takes a snapshot and saves the image
        - SVG: Flushes the stream
        """
        self.canvas.flush()
        format_ = self._config.get("format")
        if format_ == "pdf":
            self._config["document"].endPage()
            self._config["document"].close()
        elif format_ == "png":
            image = self._config["surface"].makeImageSnapshot()
            image.save(self._config["file_path"], skia.kPNG)
        elif format_ == "jpeg":
            image = self._config["surface"].makeImageSnapshot()
            image.save(self._config["file_path"], skia.kJPEG)
        elif format_ == "webp":
            image = self._config["surface"].makeImageSnapshot()
            image.save(self._config["file_path"], skia.kWEBP)
        elif format_ == "svg":
            del self.canvas
            self._config["stream"].flush()

    def new_page(self, width: float, height: float) -> None:
        """Create a new page in the output document.

        Args:
            width: The width of the new page
            height: The height of the new page

        Note:
            Only PDF format supports multiple pages. Other formats will ignore this call.
        """
        format_ = self._config.get("format")
        if format_ == "pdf":
            self._config["document"].endPage()
            canvas = self._config["document"].beginPage(width, height)
            self.canvas = canvas

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

        This method handles filters, transformations, and delegates to
        the appropriate rendering method based on the drawing element type.
        """
        self.save()
        self.set_current_state_from_drawing_element(drawing_element)
        self._add_transform_from_drawing_element(drawing_element)
        class_ = type(drawing_element)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        de_func = getattr(self, self._de_class_func_mapping[class_])
        filter_ = self.get_current_value("filter_")
        if filter_ is not NoneValue:
            bbox = drawing_element.bbox()
            saved_canvas = self.canvas
            recorder = skia.PictureRecorder()
            canvas = recorder.beginRecording(
                skia.Rect.MakeXYWH(
                    bbox.north_west().x,
                    bbox.north_west().y,
                    bbox.width,
                    bbox.height,
                )
            )
            self.canvas = canvas
            de_func(drawing_element)
            picture = recorder.finishRecordingAsPicture()
            skia_paint = self._make_filter_paint(
                filter_, drawing_element.get_filter_region()
            )
            self.canvas = saved_canvas
            self.canvas.drawPicture(picture, paint=skia_paint)
        else:
            de_func(drawing_element)
        self.restore()

    def self_save(self) -> None:
        """Save the Skia canvas state.

        This method saves the current state of the Skia canvas, including
        transformations and clipping regions.
        """
        self.canvas.save()

    def self_restore(self) -> None:
        """Restore the Skia canvas state.

        This method restores the Skia canvas to the state saved by the
        most recent call to self_save().
        """
        self.canvas.restore()

    def _make_stroke_paint(self, drawing_element: DrawingElement) -> typing.Any:
        if self.get_current_value("stroke_dasharray") is not NoneValue:
            skia_path_effect = skia.DashPathEffect.Make(
                list(self.get_current_value("stroke_dasharray")),
                self.get_current_value("stroke_dashoffset"),
            )
        else:
            skia_path_effect = None
        skia_paint = skia.Paint(
            AntiAlias=True,
            StrokeWidth=self.get_current_value("stroke_width"),
            StrokeCap=self._de_stroke_linecap_mapping[
                self.get_current_value("stroke_linecap")
            ],
            StrokeJoin=self._de_stroke_linejoin_mapping[
                self.get_current_value("stroke_linejoin")
            ],
            PathEffect=skia_path_effect,
            Style=skia.Paint.kStroke_Style,
        )
        self._set_skia_paint_source(
            skia_paint, self.get_current_value("stroke"), drawing_element
        )
        return skia_paint

    def _make_fill_paint(self, drawing_element: DrawingElement) -> typing.Any:
        skia_paint = skia.Paint(
            AntiAlias=True,
            Style=skia.Paint.kFill_Style,
        )
        self._set_skia_paint_source(
            skia_paint, self.get_current_value("fill"), drawing_element
        )
        return skia_paint

    def _set_skia_paint_source(
        self,
        skia_paint: typing.Any,
        paint: typing.Any,
        drawing_element: DrawingElement,
    ) -> None:
        class_ = type(paint)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        if issubclass(class_, Gradient):
            bbox = drawing_element.bbox()
            if paint.gradient_units == GradientUnits.OBJECT_BOUNDING_BOX and (
                bbox.width == 0 or bbox.height == 0
            ):
                skia_paint.setColor4f(skia.Color4f(0.0, 0.0, 0.0, 0.0))
            else:
                skia_paint.setShader(self._make_gradient_shader(paint, bbox))
        else:
            skia_paint.setColor4f(skia.Color4f(paint.to_rgba(rgba_range=(0.0, 1.0))))

    def _make_gradient_shader(self, gradient: Gradient, bbox: Bbox) -> typing.Any:
        matrix = make_gradient_matrix(gradient, bbox)
        skia_matrix = skia.Matrix.MakeAll(
            matrix[0][0],
            matrix[0][1],
            matrix[0][2],
            matrix[1][0],
            matrix[1][1],
            matrix[1][2],
            0.0,
            0.0,
            1.0,
        )
        colors = [
            skia.Color4f(stop.stop_color.to_rgba(rgba_range=(0.0, 1.0))).toColor()
            for stop in gradient.stops
        ]
        positions = [stop.offset for stop in gradient.stops]
        tile_mode = self._gr_spread_method_tilemode_mapping[gradient.spread_method]
        class_ = type(gradient)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        if issubclass(class_, LinearGradient):
            return skia.GradientShader.MakeLinear(
                points=[
                    skia.Point(gradient.x1, gradient.y1),
                    skia.Point(gradient.x2, gradient.y2),
                ],
                colors=colors,
                positions=positions,
                mode=tile_mode,
                localMatrix=skia_matrix,
            )
        focal_x = gradient.fx if gradient.fx is not None else gradient.cx
        focal_y = gradient.fy if gradient.fy is not None else gradient.cy
        return skia.GradientShader.MakeTwoPointConical(
            start=skia.Point(focal_x, focal_y),
            startRadius=gradient.fr,
            end=skia.Point(gradient.cx, gradient.cy),
            endRadius=gradient.r,
            colors=colors,
            positions=positions,
            mode=tile_mode,
            localMatrix=skia_matrix,
        )

    def _make_filter_paint(self, filter_: Filter, filter_region: Bbox) -> typing.Any:
        dskia_filters = {}
        for filter_effect in filter_.effects:
            class_ = type(filter_effect)
            if issubclass(class_, Builder):
                class_ = class_._cls_to_build
            fe_func = getattr(self, self._fe_class_func_mapping[class_])
            skia_filter = fe_func(filter_effect, filter_region, dskia_filters)
            if filter_effect.result is not None:
                dskia_filters[filter_effect.result] = skia_filter
        skia_paint = skia.Paint(AntiAlias=True, ImageFilter=skia_filter)
        return skia_paint

    def _make_crop_rect_from_filter_region(self, filter_region: Bbox) -> typing.Any:
        crop_rect = skia.IRect.MakeXYWH(
            round(filter_region.north_west().x),
            round(filter_region.north_west().y),
            round(filter_region.width),
            round(filter_region.height),
        )
        return crop_rect

    def _make_input_filter_from_reference(
        self, dskia_filters: dict[str, typing.Any], filter_reference: typing.Any
    ) -> typing.Any:
        if isinstance(filter_reference, FilterEffectInput):
            return None  # all SVG options default to source bitmap in skia
        in_skia_filter = dskia_filters.get(filter_reference)
        if in_skia_filter is None:  # if no reference or bad reference
            if dskia_filters:  # we take the last filter effect primitive if it exists, otherwise remains None (source Bitmap)
                in_skia_filter = dskia_filters[list(dskia_filters.keys())[-1]]
        return in_skia_filter

    def _make_drop_shadow_effect(
        self,
        filter_effect: DropShadowEffect,
        filter_region: Bbox,
        dskia_filters: dict[str, typing.Any],
    ) -> typing.Any:
        crop_rect = self._make_crop_rect_from_filter_region(filter_region)
        skia_filter = skia.ImageFilters.DropShadow(
            dx=filter_effect.dx,
            dy=filter_effect.dy,
            sigmaX=filter_effect.std_deviation,
            sigmaY=filter_effect.std_deviation,
            color=skia.Color4f(
                *filter_effect.flood_color.to_rgb(rgb_range=(0.0, 1.0)),
                filter_effect.flood_opacity,
            ),
            cropRect=crop_rect,
        )
        return skia_filter

    def _make_composite_effect(
        self,
        filter_effect: CompositeEffect,
        filter_region: Bbox,
        dskia_filters: dict[str, typing.Any],
    ) -> typing.Any:
        crop_rect = self._make_crop_rect_from_filter_region(filter_region)
        in_skia_filter = self._make_input_filter_from_reference(
            dskia_filters, filter_effect.in_
        )
        in2_skia_filter = self._make_input_filter_from_reference(
            dskia_filters, filter_effect.in2
        )
        if filter_effect.operator == CompositionOperator.ARITHMETIC:
            return skia.ImageFilters.Arithmetic(
                k1=filter_effect.k1,
                k2=filter_effect.k2,
                k3=filter_effect.k3,
                k4=filter_effect.k4,
                enforcePMColor=True,
                background=in2_skia_filter,
                foreground=in_skia_filter,
                cropRect=crop_rect,
            )
        blend_mode = self._fe_composite_comp_op_blendmode_mapping[
            filter_effect.operator
        ]
        return skia.ImageFilters.Xfermode(
            mode=blend_mode,
            background=in2_skia_filter,
            foreground=in_skia_filter,
            cropRect=crop_rect,
        )

    def _make_flood_effect(
        self,
        filter_effect: FloodEffect,
        filter_region: Bbox,
        dskia_filters: dict[str, typing.Any],
    ) -> typing.Any:
        crop_rect = self._make_crop_rect_from_filter_region(filter_region)
        skia_paint = skia.Paint(
            AntiAlias=True,
            Color4f=skia.Color4f(
                *filter_effect.flood_color.to_rgb(rgb_range=(0.0, 1.0)),
                filter_effect.flood_opacity,
            ),
            Style=skia.Paint.kFill_Style,
        )
        skia_filter = skia.ImageFilters.Paint(
            paint=skia_paint,
            cropRect=crop_rect,
        )
        return skia_filter

    def _make_gaussian_blur_effect(
        self,
        filter_effect: GaussianBlurEffect,
        filter_region: Bbox,
        dskia_filters: dict[str, typing.Any],
    ) -> typing.Any:
        crop_rect = self._make_crop_rect_from_filter_region(filter_region)
        in_skia_filter = self._make_input_filter_from_reference(
            dskia_filters, filter_effect.in_
        )
        tile_mode = self._fe_gaussian_blur_edgemode_tilemode_mapping[
            filter_effect.edge_mode
        ]
        skia_filter = skia.ImageFilters.Blur(
            sigmaX=filter_effect.std_deviation,
            sigmaY=filter_effect.std_deviation,
            tileMode=tile_mode,
            input=in_skia_filter,
            cropRect=crop_rect,
        )
        return skia_filter

    def _make_offset_effect(
        self,
        filter_effect: OffsetEffect,
        filter_region: Bbox,
        dskia_filters: dict[str, typing.Any],
    ) -> typing.Any:
        crop_rect = self._make_crop_rect_from_filter_region(filter_region)
        in_skia_filter = self._make_input_filter_from_reference(
            dskia_filters, filter_effect.in_
        )
        skia_filter = skia.ImageFilters.Offset(
            dx=filter_effect.dx,
            dy=filter_effect.dy,
            input=in_skia_filter,
            cropRect=crop_rect,
        )
        return skia_filter

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

    def _add_path_action_to_skia_path(
        self, skia_path: typing.Any, path_action: typing.Any
    ) -> None:
        class_ = type(path_action)
        if issubclass(class_, Builder):
            class_ = class_._cls_to_build
        pa_func = getattr(self, self._pa_class_func_mapping[class_])
        pa_func(skia_path, path_action)

    def _make_skia_path(self, path: Path) -> typing.Any:
        skia_path = skia.Path()
        for action in path.actions:
            self._add_path_action_to_skia_path(skia_path, action)
        return skia_path

    def _render_path(self, path: Path) -> None:
        skia_path = self._make_skia_path(path)
        if self.get_current_value("fill") is not NoneValue:
            skia_paint = self._make_fill_paint(path)
            self.canvas.drawPath(path=skia_path, paint=skia_paint)
        if self.get_current_value("stroke") is not NoneValue:
            skia_paint = self._make_stroke_paint(path)
            self.canvas.drawPath(path=skia_path, paint=skia_paint)

    def _render_text(self, text: Text) -> None:
        font_family = self.get_current_value("font_family")
        font_weight = self.get_current_value("font_weight")
        font_style = self.get_current_value("font_style")
        skia_typeface = self._skia_typefaces.get((font_family, font_weight, font_style))
        if skia_typeface is None:
            skia_font_slant = self._te_font_style_slant_mapping[font_style]
            skia_font_style = skia.FontStyle(
                weight=int(font_weight),
                slant=skia_font_slant,
                width=skia.FontStyle.kNormal_Width,
            )
            skia_typeface = skia.Typeface(
                familyName=font_family,
                fontStyle=skia_font_style,
            )
            self._skia_typefaces[(font_family, font_weight, font_style)] = skia_typeface
        font_size = self.get_current_value("font_size")
        skia_font = self._skia_fonts.get(
            (
                font_family,
                font_weight,
                font_style,
                font_size,
            )
        )
        if skia_font is None:
            skia_font = skia.Font(
                typeface=skia_typeface,
                size=font_size,
            )
            self._skia_fonts[
                (
                    font_family,
                    font_weight,
                    font_style,
                    font_size,
                )
            ] = skia_font
        if self.get_current_value("fill") is not NoneValue:
            skia_paint = self._make_fill_paint(text)
            self.canvas.drawString(
                text=text.text,
                x=text.x,
                y=text.y,
                font=skia_font,
                paint=skia_paint,
            )
        if self.get_current_value("stroke") is not NoneValue:
            skia_paint = self._make_stroke_paint(text)
            self.canvas.drawString(
                text=text.text,
                x=text.x,
                y=text.y,
                font=skia_font,
                paint=skia_paint,
            )

    def _render_ellipse(self, ellipse: Ellipse) -> None:
        skia_rect = skia.Rect(
            ellipse.x - ellipse.rx,
            ellipse.y - ellipse.ry,
            ellipse.x + ellipse.rx,
            ellipse.y + ellipse.ry,
        )
        if self.get_current_value("fill") is not NoneValue:
            skia_paint = self._make_fill_paint(ellipse)
            self.canvas.drawOval(oval=skia_rect, paint=skia_paint)
        if self.get_current_value("stroke") is not NoneValue:
            skia_paint = self._make_stroke_paint(ellipse)
            self.canvas.drawOval(oval=skia_rect, paint=skia_paint)

    def _render_rectangle(self, rectangle: Rectangle) -> None:
        skia_rect = skia.Rect(
            rectangle.x,
            rectangle.y,
            rectangle.x + rectangle.width,
            rectangle.y + rectangle.height,
        )
        if self.get_current_value("fill") is not NoneValue:
            skia_paint = self._make_fill_paint(rectangle)
            self.canvas.drawRoundRect(
                rect=skia_rect,
                rx=rectangle.rx,
                ry=rectangle.ry,
                paint=skia_paint,
            )
        if self.get_current_value("stroke") is not NoneValue:
            skia_paint = self._make_stroke_paint(rectangle)
            self.canvas.drawRoundRect(
                rect=skia_rect,
                rx=rectangle.rx,
                ry=rectangle.ry,
                paint=skia_paint,
            )

    def _add_move_to(self, skia_path: typing.Any, move_to: MoveTo) -> None:
        skia_path.moveTo(move_to.x, move_to.y)

    def _add_line_to(self, skia_path: typing.Any, line_to: LineTo) -> None:
        skia_path.lineTo(line_to.x, line_to.y)

    def _add_curve_to(self, skia_path: typing.Any, curve_to: CurveTo) -> None:
        skia_path.cubicTo(
            curve_to.control_point1.x,
            curve_to.control_point1.y,
            curve_to.control_point2.x,
            curve_to.control_point2.y,
            curve_to.x,
            curve_to.y,
        )

    def _add_quadratic_curve_to(
        self, skia_path: typing.Any, quadratic_curve_to: QuadraticCurveTo
    ) -> None:
        skia_current_point = skia_path.getPoint(skia_path.countPoints() - 1)
        current_point = Point(skia_current_point.fX, skia_current_point.fY)
        curve_to = quadratic_curve_to.to_curve_to(current_point)
        self._add_curve_to(skia_path, curve_to)

    def _add_close_path(self, skia_path: typing.Any, close_path: ClosePath) -> None:
        skia_path.close()

    def _add_elliptical_arc(
        self, skia_path: typing.Any, elliptical_arc: EllipticalArc
    ) -> None:
        if elliptical_arc.arc_flag == 0:
            skia_arc_flag = skia.Path.ArcSize.kSmall_ArcSize
        else:
            skia_arc_flag = skia.Path.ArcSize.kLarge_ArcSize
        if elliptical_arc.sweep_flag == 1:
            skia_sweep_flag = skia.PathDirection.kCW
        else:
            skia_sweep_flag = skia.PathDirection.kCCW
        skia_path.arcTo(
            rx=elliptical_arc.rx,
            ry=elliptical_arc.ry,
            xAxisRotate=elliptical_arc.x_axis_rotation,
            largeArc=skia_arc_flag,
            sweep=skia_sweep_flag,
            x=elliptical_arc.x,
            y=elliptical_arc.y,
        )

    def _add_translation(self, translation: Translation) -> None:
        self.canvas.translate(dx=translation.tx, dy=translation.ty)

    def _add_rotation(self, rotation: Rotation) -> None:
        angle = math.degrees(rotation.angle)
        if rotation.point is not None:
            self.canvas.rotate(degrees=angle, px=rotation.point.x, py=rotation.point.y)
        else:
            self.canvas.rotate(degrees=angle)

    def _add_scaling(self, scaling: Scaling) -> None:
        self.canvas.scale(sx=scaling.sx, sy=scaling.sy)

    def _add_matrix_transformation(
        self, matrix_transformation: MatrixTransformation
    ) -> None:
        m = skia.Matrix.MakeAll(
            scaleX=matrix_transformation.m[0][0],
            skewX=matrix_transformation.m[0][1],
            transX=matrix_transformation.m[0][2],
            skewY=matrix_transformation.m[1][0],
            scaleY=matrix_transformation.m[1][1],
            transY=matrix_transformation.m[1][2],
            pers0=matrix_transformation.m[2][0],
            pers1=matrix_transformation.m[2][1],
            pers2=matrix_transformation.m[2][2],
        )
        self.canvas.concat(m)
