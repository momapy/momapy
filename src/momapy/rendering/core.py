"""Base classes and functions for rendering maps or layout elements."""

import dataclasses
import copy
import abc
import typing
import typing_extensions
import collections.abc
import os
import pathlib

import numpy
import numpy.typing

from momapy.drawing import DEFAULT_FONT_FAMILY
from momapy.drawing import DrawingElement
from momapy.drawing import FontWeight
from momapy.drawing import Gradient
from momapy.drawing import GradientUnits
from momapy.drawing import INITIAL_VALUES
from momapy.drawing import PRESENTATION_ATTRIBUTES
from momapy.plugins.core import PluginRegistry
from momapy.styling import StyleSheet
from momapy.styling import apply_style_sheet
from momapy.styling import combine_style_sheets
from momapy.positioning import fit
from momapy.geometry import Bbox
from momapy.geometry import Translation
from momapy.builder import Builder
from momapy.builder import builder_from_object
from momapy.core.elements import LayoutElement
from momapy.core.map import Map


renderer_registry: "PluginRegistry[type[Renderer]]" = PluginRegistry(
    entry_point_group="momapy.renderers",
)


def get_renderer(name: str) -> type["Renderer"]:
    """Get a renderer class by name.

    Args:
        name: Renderer name (e.g., "skia", "cairo", "svg-native").

    Returns:
        Renderer class for the specified backend.

    Raises:
        ValueError: If no renderer with that name exists.
        ImportError: If the renderer is registered but its backend module
            cannot be imported (e.g. an optional dependency such as
            skia-python or pycairo is not installed).
    """
    renderer = renderer_registry.get(name)
    if renderer is None:
        available = renderer_registry.list_available()
        raise ValueError(
            f"No renderer named '{name}'. Available renderers: {', '.join(available)}"
        )
    return renderer


def list_renderers() -> list[str]:
    """List all available renderer names.

    Returns:
        Sorted list of available renderer names.
    """
    return renderer_registry.list_available()


def register_renderer(name: str, cls: type["Renderer"]) -> None:
    """Register a renderer class.

    Args:
        name: Name to register the renderer under.
        cls: Renderer class (must inherit from Renderer).
    """
    renderer_registry.register(name, cls)


def register_lazy_renderer(name: str, import_path: str) -> None:
    """Register a renderer for lazy loading.

    Args:
        name: Name to register the renderer under.
        import_path: Import path in format "module.path:ClassName".
    """
    renderer_registry.register_lazy(name, import_path)


def _detect_renderer(format_: str) -> str:
    for candidate in ["svg-native", "skia", "cairo"]:
        try:
            renderer_cls = get_renderer(candidate)
            if format_ in getattr(renderer_cls, "supported_formats", []):
                return candidate
        except (ValueError, ImportError, ModuleNotFoundError):
            continue
    raise ValueError(f"No renderer available for format '{format_}'")


def make_gradient_matrix(gradient: Gradient, bbox: Bbox) -> numpy.typing.NDArray:
    """Make the matrix from the gradient space to the user space.

    Args:
        gradient: The gradient.
        bbox: The bounding box of the painted element, used when the gradient
            units are `GradientUnits.OBJECT_BOUNDING_BOX`.

    Returns:
        A 3x3 matrix.
    """
    matrix = numpy.identity(3)
    if gradient.gradient_units == GradientUnits.OBJECT_BOUNDING_BOX:
        north_west = bbox.north_west()
        matrix = numpy.array(
            [
                [bbox.width, 0.0, north_west.x],
                [0.0, bbox.height, north_west.y],
                [0.0, 0.0, 1.0],
            ]
        )
    for transformation in gradient.gradient_transform:
        matrix = numpy.matmul(matrix, transformation.to_matrix())
    return matrix


def render_layout_element(
    layout_element: LayoutElement,
    file_path: str | os.PathLike,
    format_: str | None = None,
    renderer: str | None = None,
    style_sheet: StyleSheet | None = None,
    to_top_left: bool = False,
) -> None:
    """Render a layout element to a file in the given format with the given registered renderer.

    Args:
        layout_element: The layout element to render
        file_path: The output file path
        format_: The output format. If None, inferred from file extension.
        renderer: The registered renderer to use. If None, auto-detected based on format.
        style_sheet: An optional style sheet to apply before rendering
        to_top_left: Whether to move the layout element to the top left or not before rendering
    """
    render_layout_elements(
        layout_elements=[layout_element],
        file_path=file_path,
        format_=format_,
        renderer=renderer,
        style_sheet=style_sheet,
        to_top_left=to_top_left,
    )


def render_layout_elements(
    layout_elements: collections.abc.Sequence[LayoutElement],
    file_path: str | os.PathLike,
    format_: str | None = None,
    renderer: str | None = None,
    style_sheet: StyleSheet | None = None,
    to_top_left: bool = False,
    multi_pages: bool = False,
) -> None:
    """Render a collection of layout elements to a file in the given format with the given registered renderer.

    Args:
        layout_elements: The layout elements to render
        file_path: The output file path
        format_: The output format. If None, inferred from file extension.
        renderer: The registered renderer to use. If None, auto-detected based on format.
        style_sheet: An optional style sheet to apply before rendering
        to_top_left: Whether to move the layout elements to the top left before rendering
        multi_pages: Whether to render each layout element on a separate page.
            Defaults to `False` (all elements on a single page).
    """
    if format_ is None:
        file_path_obj = pathlib.Path(file_path)
        format_ = file_path_obj.suffix[1:]
        if not format_:
            raise ValueError(
                "Cannot determine format from file path. Please specify format_ parameter."
            )
    if renderer is None:
        renderer = _detect_renderer(format_)
    if not layout_elements:
        raise ValueError("no layout elements to render")

    def _prepare_layout_elements(
        layout_elements: list[LayoutElement],
        style_sheet: typing.Any = None,
        to_top_left: bool = False,
    ) -> tuple[list[LayoutElement], float, float]:
        bboxes = [layout_element.bbox() for layout_element in layout_elements]
        bbox = fit(bboxes)
        max_x = bbox.x + bbox.width / 2
        max_y = bbox.y + bbox.height / 2
        if style_sheet is not None or to_top_left:
            new_layout_elements = []
            for layout_element in layout_elements:
                if isinstance(layout_element, LayoutElement):
                    new_layout_elements.append(builder_from_object(layout_element))
                elif isinstance(layout_element, Builder):
                    new_layout_elements.append(copy.deepcopy(layout_element))
            layout_elements = new_layout_elements
        if style_sheet is not None:
            if (
                not isinstance(style_sheet, collections.abc.Collection)
                or isinstance(style_sheet, str)
                or isinstance(style_sheet, StyleSheet)
            ):
                style_sheets = [style_sheet]
            else:
                style_sheets = style_sheet
            style_sheets = [
                (
                    StyleSheet.from_file(style_sheet)
                    if not isinstance(style_sheet, StyleSheet)
                    else style_sheet
                )
                for style_sheet in style_sheets
            ]
            style_sheet = combine_style_sheets(style_sheets)
            for layout_element in layout_elements:
                apply_style_sheet(layout_element, style_sheet)
        if to_top_left:
            min_x = bbox.x - bbox.width / 2
            min_y = bbox.y - bbox.height / 2
            max_x -= min_x
            max_y -= min_y
            translation = Translation(-min_x, -min_y)
            for layout_element in layout_elements:
                for attr_name in ["group_transform", "transform"]:
                    if hasattr(layout_element, attr_name):
                        if getattr(layout_element, attr_name) is None:
                            setattr(layout_element, attr_name, [])
                        getattr(layout_element, attr_name).append(translation)
                        break
        return layout_elements, max_x, max_y

    renderer_cls = get_renderer(renderer)
    if not issubclass(renderer_cls, SupportsFileOutput):
        raise ValueError(
            f"Renderer '{renderer}' cannot render to a file: it does not "
            "support file output (no from_file capability)."
        )
    if not multi_pages:
        prepared_layout_elements, max_x, max_y = _prepare_layout_elements(
            layout_elements, style_sheet, to_top_left
        )
        renderer_instance = renderer_cls.from_file(file_path, max_x, max_y, format_)
        renderer_instance.begin_session()
        for prepared_layout_element in prepared_layout_elements:
            renderer_instance.render_layout_element(prepared_layout_element)
        renderer_instance.end_session()
    else:
        layout_element = layout_elements[0]
        prepared_layout_elements, max_x, max_y = _prepare_layout_elements(
            [layout_element], style_sheet, to_top_left
        )
        renderer_instance = renderer_cls.from_file(file_path, max_x, max_y, format_)
        renderer_instance.begin_session()
        renderer_instance.render_layout_element(prepared_layout_elements[0])
        for layout_element in layout_elements[1:]:
            prepared_layout_elements, max_x, max_y = _prepare_layout_elements(
                [layout_element], style_sheet, to_top_left
            )
            renderer_instance.new_page(max_x, max_y)
            renderer_instance.render_layout_element(prepared_layout_elements[0])
        renderer_instance.end_session()


def render_map(
    map_: Map,
    file_path: str | os.PathLike,
    format_: str | None = None,
    renderer: str | None = None,
    style_sheet: StyleSheet | None = None,
    to_top_left: bool = False,
) -> None:
    """Render a map to a file in the given format with the given registered renderer.

    Args:
        map_: The map to render
        file_path: The output file path
        format_: The output format. If None, inferred from file extension.
        renderer: The registered renderer to use. If None, auto-detected based on format.
        style_sheet: An optional style sheet to apply before rendering
        to_top_left: Whether to move the map to the top left before rendering

    Examples:
        ```python
        from momapy.io import read
        from momapy.rendering import render_map

        # Read a map from file
        result = read("path/to/map.sbgn")
        sbgn_map = result.obj

        # Render the map to SVG
        render_map(sbgn_map, "output.svg")
        ```
    """
    render_maps([map_], file_path, format_, renderer, style_sheet, to_top_left)


def render_maps(
    maps: collections.abc.Collection[Map],
    file_path: str | os.PathLike,
    format_: str | None = None,
    renderer: str | None = None,
    style_sheet: StyleSheet | None = None,
    to_top_left: bool = False,
    multi_pages: bool = False,
) -> None:
    """Render a collection of maps to a file in the given format with the given registered renderer.

    Args:
        maps: The maps to render
        file_path: The output file path
        format_: The output format. If None, inferred from file extension.
        renderer: The registered renderer to use. If None, auto-detected based on format.
        style_sheet: An optional style sheet to apply before rendering
        to_top_left: Whether to move the maps to the top left before rendering
        multi_pages: Whether to render each map on a separate page.
            Defaults to `False` (all maps on a single page).

    Examples:
        ```python
        from momapy.io import read
        from momapy.rendering import render_maps

        # Read multiple maps from files
        result1 = read("path/to/map1.sbgn")
        first_map = result1.obj
        result2 = read("path/to/map2.sbgn")
        second_map = result2.obj

        # Render both maps to a multi-page PDF
        render_maps([first_map, second_map], "output.pdf", multi_pages=True)
        ```
    """
    if not maps:
        raise ValueError("no maps to render")
    layout_elements = []
    for map_ in maps:
        if map_.layout is None:
            raise ValueError(
                "map has no layout to render (its layout is None); "
                "a layout-less map (e.g. an SBML map) cannot be rendered"
            )
        layout_elements.append(map_.layout)
    render_layout_elements(
        layout_elements=layout_elements,
        file_path=file_path,
        format_=format_,
        renderer=renderer,
        style_sheet=style_sheet,
        to_top_left=to_top_left,
        multi_pages=multi_pages,
    )


@dataclasses.dataclass
class Renderer(abc.ABC):
    """Base class for renderers.

    The abstract contract is the five render-session methods only
    (``begin_session``, ``end_session``, ``new_page``,
    ``render_layout_element``, ``render_drawing_element``). ``render_map`` is
    a concrete convenience method (it renders ``map_.layout`` via
    ``render_layout_element``), so backends need not implement it. File
    output is a
    separate capability provided by the :class:`SupportsFileOutput` mixin, not a
    base-class obligation: a renderer that does not target a file (in-memory
    surface, interactive canvas, null/test renderer) subclasses ``Renderer``
    directly and has neither ``from_file`` nor ``supported_formats``.
    """

    initial_values: typing.ClassVar[dict[str, typing.Any]] = {
        "font_family": DEFAULT_FONT_FAMILY,
        "font_weight": FontWeight.NORMAL,
    }
    font_weight_value_mapping: typing.ClassVar[dict[FontWeight, int]] = {
        FontWeight.NORMAL: 400,
        FontWeight.BOLD: 700,
    }

    @abc.abstractmethod
    def begin_session(self) -> None:
        """Begin a rendering session."""
        pass

    @abc.abstractmethod
    def end_session(self) -> None:
        """End the current rendering session."""
        pass

    @abc.abstractmethod
    def new_page(self, width: float, height: float) -> None:
        """Start a new page.

        Args:
            width: Width of the page.
            height: Height of the page.
        """
        pass

    def render_map(self, map_: Map) -> None:
        """Render a map.

        This is a convenience method, **not** part of the abstract
        contract: the default implementation renders the map's layout via
        :meth:`render_layout_element`, which is what every built-in backend
        needs. Subclasses may override it if a backend requires
        map-specific handling, but they are not obliged to. The file
        pipeline (:func:`render_map`/:func:`render_maps`) does not call this
        method; it renders each page through :meth:`render_layout_element`.

        Args:
            map_: The map to render.

        Raises:
            ValueError: If the map has no layout to render.
        """
        if map_.layout is None:
            raise ValueError(
                "map has no layout to render (its layout is None); "
                "a layout-less map (e.g. an SBML map) cannot be rendered"
            )
        self.render_layout_element(map_.layout)

    @abc.abstractmethod
    def render_layout_element(self, layout_element: LayoutElement) -> None:
        """Render a layout element.

        Args:
            layout_element: The layout element to render.
        """
        pass

    @abc.abstractmethod
    def render_drawing_element(self, drawing_element: DrawingElement) -> None:
        """Render a drawing element.

        Args:
            drawing_element: The drawing element to render.
        """
        pass

    @classmethod
    def get_lighter_font_weight(cls, font_weight: FontWeight | float) -> float:
        """Return the boldest font weight lighter than the given font weight."""
        if isinstance(font_weight, FontWeight):
            font_weight = cls.font_weight_value_mapping.get(font_weight)
            if font_weight is None:
                raise ValueError(
                    f"font weight must be a float, {FontWeight.NORMAL}, or {FontWeight.BOLD}"
                )
        if font_weight > 700:
            new_font_weight = 700.0
        elif font_weight > 500:
            new_font_weight = 400.0
        else:
            new_font_weight = 100.0
        return new_font_weight

    @classmethod
    def get_bolder_font_weight(cls, font_weight: FontWeight | float) -> float:
        """Return the lightest font weight bolder than the given font weight."""
        if isinstance(font_weight, FontWeight):
            font_weight = cls.font_weight_value_mapping.get(font_weight)
            if font_weight is None:
                raise ValueError(
                    f"font weight must be a float, {FontWeight.NORMAL}, or {FontWeight.BOLD}"
                )
        if font_weight < 400:
            new_font_weight = 400.0
        elif font_weight < 600:
            new_font_weight = 700.0
        else:
            new_font_weight = 900.0
        return new_font_weight


class SupportsFileOutput(abc.ABC):
    """Mixin declaring the file-output capability of a renderer.

    Mix into a :class:`Renderer` subclass to declare that it can build from and
    write to a file. This is the capability required by the file-output entry
    points (:func:`render_map`, :func:`render_maps`,
    :func:`render_layout_element`, :func:`render_layout_elements`); it is a
    *capability*, not an identity — a renderer mixing it in may still support
    other output targets (a live canvas, an in-memory surface) through its own
    constructors. Renderers with no file output simply do not mix it in.

    Implementers must declare :attr:`supported_formats` and implement
    :meth:`from_file`.
    """

    supported_formats: typing.ClassVar[list[str]] = []
    default_format: typing.ClassVar[str | None] = None
    """The format used when ``from_file`` is called with ``format_=None``.

    Subclasses set this to one of their :attr:`supported_formats`.
    """

    @classmethod
    @abc.abstractmethod
    def from_file(
        cls,
        file_path: str | os.PathLike,
        width: float,
        height: float,
        format_: str | None = None,
    ) -> typing_extensions.Self:
        """Build a renderer that writes its output to ``file_path``.

        Args:
            file_path: The output file path.
            width: The width of the canvas.
            height: The height of the canvas.
            format_: The output format. ``None`` selects the backend's
                :attr:`default_format`.

        Returns:
            A new renderer instance writing to ``file_path``.
        """
        ...


@dataclasses.dataclass
class StatefulRenderer(Renderer):
    """Base class for stateful renderers."""

    _current_state: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    _states: list[dict[str, typing.Any]] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize the renderer's current state after initialization."""
        self._initialize_current_state()

    @abc.abstractmethod
    def self_save(self) -> None:
        """Save the internal state of the renderer.

        This method must be implemented by subclasses to save any internal
        state that is not part of the current state dictionary.
        """
        pass

    @abc.abstractmethod
    def self_restore(self) -> None:
        """Restore the internal state of the renderer.

        This method must be implemented by subclasses to restore any internal
        state that is not part of the current state dictionary.
        """
        pass

    @classmethod
    def _make_initial_current_state(cls) -> dict[str, typing.Any]:
        state = {}
        for (
            attr_name,
            attr_d,
        ) in PRESENTATION_ATTRIBUTES.items():
            if attr_name in cls.initial_values:
                attr_value = cls.initial_values[attr_name]
            else:
                attr_value = attr_d["initial"]
            state[attr_name] = attr_value
        return state

    def _initialize_current_state(self) -> None:
        state = self._make_initial_current_state()
        self.set_current_state(state)

    def save(self) -> None:
        """Save the current state."""
        self._states.append(copy.deepcopy(self.get_current_state()))
        self.self_save()

    def restore(self) -> None:
        """Set the current state to the last saved state."""
        if len(self._states) > 0:
            state = self._states.pop()
            self.set_current_state(state)
            self.self_restore()
        else:
            raise RuntimeError(
                "restore() called with an empty state stack: no matching "
                "save() to restore from"
            )

    def get_initial_value(self, attr_name: str) -> typing.Any:
        """Return the initial value for an attribute."""
        attr_value = self.initial_values.get(attr_name)
        if attr_value is None:
            attr_d = PRESENTATION_ATTRIBUTES[attr_name]
            attr_value = attr_d["initial"]
            if attr_value is None:
                attr_value = INITIAL_VALUES[attr_name]
        return attr_value

    def get_current_value(self, attr_name: str) -> typing.Any:
        """Return the current value for an attribute."""
        return self.get_current_state()[attr_name]

    def get_current_state(self) -> dict[str, typing.Any]:
        """Return the current state."""
        return self._current_state

    def set_current_value(self, attr_name: str, attr_value: typing.Any) -> None:
        """Set the current value for an attribute."""
        if attr_value is None:
            attr_d = PRESENTATION_ATTRIBUTES[attr_name]
            if not attr_d["inherited"]:
                attr_value = self.initial_values.get(attr_name)
                if attr_value is None:
                    attr_value = attr_d["initial"]
                if attr_value is None:
                    attr_value = INITIAL_VALUES[attr_name]
        if attr_name == "font_weight":
            if isinstance(attr_value, FontWeight):
                if attr_value == FontWeight.NORMAL or attr_value == FontWeight.BOLD:
                    attr_value = self.font_weight_value_mapping[attr_value]
                elif attr_value == FontWeight.BOLDER:
                    attr_value = self.get_bolder_font_weight(
                        self.get_current_value("font_weight")
                    )
                elif attr_value == FontWeight.LIGHTER:
                    attr_value = self.get_lighter_font_weight(
                        self.get_current_value("font_weight")
                    )
        if attr_value is not None:
            self._current_state[attr_name] = attr_value

    def set_current_state(self, state: dict[str, typing.Any]) -> None:
        """Set the current state to the given state."""
        for attr_name, attr_value in state.items():
            self.set_current_value(attr_name, attr_value)

    def _get_state_from_drawing_element(
        self, drawing_element: DrawingElement
    ) -> dict[str, typing.Any]:
        """Return the presentation state from a drawing element.

        Args:
            drawing_element: The drawing element to extract state from

        Returns:
            A dictionary mapping attribute names to their values
        """
        state = {}
        for attr_name in PRESENTATION_ATTRIBUTES:
            state[attr_name] = getattr(drawing_element, attr_name)
        return state

    def set_current_state_from_drawing_element(
        self, drawing_element: DrawingElement
    ) -> None:
        """Set the current state to a state given by a drawing element."""
        state = self._get_state_from_drawing_element(drawing_element)
        self.set_current_state(state)
