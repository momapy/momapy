"""Implementation of the CSS-like styling system.

Public names are re-exported from :mod:`momapy.styling`. See the package
docstring for usage examples.
"""

import abc
import collections.abc
import dataclasses
import math
import os
import pathlib
import typing
import pyparsing
import copy


import momapy.coloring

from momapy.builder import Builder
from momapy.builder import builder_from_object
from momapy.builder import get_or_make_builder_cls
from momapy.builder import isinstance_or_builder
from momapy.builder import object_from_builder
from momapy.coloring import Color
from momapy.coloring import has_color
from momapy.core.elements import LayoutElement
from momapy.core.map import Map
from momapy.drawing import DropShadowEffect
from momapy.drawing import Filter
from momapy.drawing import GradientStop
from momapy.drawing import GradientUnits
from momapy.drawing import LineCap
from momapy.drawing import LineJoin
from momapy.drawing import LinearGradient
from momapy.drawing import NoneValue
from momapy.drawing import PRESENTATION_ATTRIBUTES
from momapy.drawing import RadialGradient
from momapy.drawing import SpreadMethod


class StyleCollection(dict):
    """A dictionary-based collection of style properties.

    StyleCollection maps attribute names to their values, similar to a CSS
    declaration block. It is used within StyleSheets to store styles for
    specific selectors.

    Examples:
        ```python
        styles = StyleCollection({"fill": "red", "stroke_width": 2})
        styles["fill"]
        ```
    """

    pass


class StyleSheet(dict):
    """A dictionary-based stylesheet mapping selectors to style collections.

    StyleSheet extends dict to map Selector objects to StyleCollection objects.
    Supports merging stylesheets using the | operator.

    Examples:
        ```python
        from momapy.styling import StyleSheet, TypeSelector
        ss = StyleSheet({TypeSelector("Rectangle"): StyleCollection({"fill": "blue"})})

        # Merge stylesheets
        combined = ss | another_stylesheet
        ```
    """

    def __or__(self, other: "StyleSheet") -> "StyleSheet":
        """Return a new stylesheet merging this one with another stylesheet."""
        merged = copy.deepcopy(self)
        merged |= other
        return merged

    def __ior__(self, other: "StyleSheet") -> "StyleSheet":
        """Merge another stylesheet into this one in place and return it."""
        for key, value in other.items():
            if key in self:
                self[key] |= value
            else:
                self[key] = value
        return self

    @classmethod
    def from_file(cls, file_path: str | os.PathLike) -> "StyleSheet":
        """Parse and return a StyleSheet from a CSS file.

        Relative ``@import`` paths inside the CSS file are resolved against
        the directory of ``file_path``, not against the process working
        directory.

        Args:
            file_path: Path to the CSS file to parse.

        Returns:
            A StyleSheet containing the parsed selectors and style collections.

        Raises:
            pyparsing.ParseException: If the CSS file is malformed.
        """
        path = pathlib.Path(file_path).resolve()
        doc_parser = _make_document_parser(path.parent)
        style_sheet = doc_parser.parse_file(str(path), parse_all=True)[0]
        return style_sheet

    @classmethod
    def from_string(cls, s: str) -> "StyleSheet":
        """Parse and return a StyleSheet from a CSS string.

        Relative ``@import`` paths inside the string are resolved against
        the current working directory (a string has no file location);
        absolute ``@import`` paths are resolved as-is.

        Args:
            s: CSS string to parse.

        Returns:
            A StyleSheet containing the parsed selectors and style collections.

        Raises:
            pyparsing.ParseException: If the CSS string is malformed.

        Examples:
            ```python
            css = "Rectangle { fill: red; }"
            ss = StyleSheet.from_string(css)
            ```
        """
        doc_parser = _make_document_parser(pathlib.Path.cwd())
        style_sheet = doc_parser.parse_string(s, parse_all=True)[0]
        return style_sheet

    @classmethod
    def from_files(cls, file_paths: collections.abc.Collection[str]) -> "StyleSheet":
        """Parse and combine multiple CSS files into a single StyleSheet.

        Args:
            file_paths: Collection of paths to CSS files.

        Returns:
            A merged StyleSheet containing all parsed styles; an empty
            StyleSheet when ``file_paths`` is empty.
        """
        style_sheet = cls()
        for file_path in file_paths:
            style_sheet |= StyleSheet.from_file(file_path)
        return style_sheet


def combine_style_sheets(
    style_sheets: collections.abc.Sequence[StyleSheet],
) -> StyleSheet | None:
    """Merge multiple StyleSheets into a single StyleSheet.

    Args:
        style_sheets: Collection of StyleSheets to merge.

    Returns:
        A combined StyleSheet, or None if the input is empty.
    """
    if not style_sheets:
        return None
    output_style_sheet = copy.deepcopy(style_sheets[0])
    for style_sheet in style_sheets[1:]:
        output_style_sheet |= style_sheet
    return output_style_sheet


def apply_style_collection(
    layout_element: (LayoutElement | Builder),
    style_collection: StyleCollection,
    strict: bool = True,
) -> LayoutElement | Builder:
    """Apply a StyleCollection to a layout element.

    Args:
        layout_element: The element or builder to apply styles to.
        style_collection: The styles to apply.
        strict: If True, raises AttributeError for invalid attributes.
            If False, silently ignores them.

    Returns:
        The modified layout element or builder.

    Raises:
        AttributeError: If strict=True and an attribute doesn't exist on the element.
    """
    if not isinstance(layout_element, Builder):
        layout_element = builder_from_object(layout_element)
        is_builder = False
    else:
        is_builder = True
    for attribute, value in style_collection.items():
        if hasattr(layout_element, attribute):
            setattr(layout_element, attribute, value)
        else:
            if strict:
                raise AttributeError(
                    f"{type(layout_element)} object has no attribute '{attribute}'"
                )
    if is_builder:
        return layout_element
    return object_from_builder(layout_element)


def apply_style_sheet(
    map_or_layout_element: (Map | LayoutElement | Builder),
    style_sheet: StyleSheet,
    strict: bool = True,
    ancestors: collections.abc.Collection[LayoutElement | Builder] | None = None,
) -> Map | LayoutElement | Builder:
    """Apply a StyleSheet to a layout element or map layout recursively.

    Args:
        map_or_layout_element: The map, element, or builder to style.
        style_sheet: The stylesheet to apply.
        strict: If True, raises errors for invalid attributes.
        ancestors: Internal list of ancestor elements for selector matching.

    Returns:
        The modified map, layout element, or builder.

    Raises:
        ValueError: If given a map without a layout (e.g. an SBML map).
    """
    if not isinstance(map_or_layout_element, Builder):
        map_or_layout_element = builder_from_object(map_or_layout_element)
        is_builder = False
    else:
        is_builder = True
    if isinstance_or_builder(map_or_layout_element, Map):
        layout_element = map_or_layout_element.layout
        if layout_element is None:
            raise ValueError("cannot apply a stylesheet to a map without a layout")
    else:
        layout_element = map_or_layout_element
    if style_sheet is not None:
        if ancestors is None:
            ancestors = []
        for selector, style_collection in style_sheet.items():
            if selector.select(layout_element, ancestors):
                apply_style_collection(
                    layout_element=layout_element,
                    style_collection=style_collection,
                    strict=strict,
                )
        ancestors = ancestors + [layout_element]
        for child in layout_element.children():
            apply_style_sheet(
                map_or_layout_element=child,
                style_sheet=style_sheet,
                strict=strict,
                ancestors=ancestors,
            )
    if is_builder:
        return map_or_layout_element
    return object_from_builder(map_or_layout_element)


@dataclasses.dataclass(frozen=True)
class Selector(abc.ABC):
    """Abstract base class for CSS-like selectors.

    Selectors determine whether a layout element matches specific criteria.
    All selector types inherit from this class and implement the select() method.
    """

    @abc.abstractmethod
    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the layout element matches this selector.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if the element matches, False otherwise.
        """
        pass


@dataclasses.dataclass(frozen=True)
class TypeSelector(Selector):
    """Selector that matches elements by their exact class name.

    Examples:
        ```python
        selector = TypeSelector("Rectangle")
        selector.select(some_rectangle, [])  # True if type is Rectangle
        ```
    """

    class_name: str = dataclasses.field(
        metadata={"description": "The name of the class"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the object's class name matches exactly.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements (unused for type matching).

        Returns:
            True if the object's class name or builder name matches.
        """
        obj_cls_name = type(obj).__name__
        return (
            obj_cls_name == self.class_name
            or obj_cls_name == f"{self.class_name}Builder"
        )


@dataclasses.dataclass(frozen=True)
class ClassSelector(Selector):
    """Selector that matches elements by class (including subclasses).

    Examples:
        ```python
        selector = ClassSelector("Shape")
        selector.select(some_rectangle, [])  # True if Rectangle is a Shape subclass
        ```
    """

    class_name: str = dataclasses.field(
        metadata={"description": "The name of the class"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the object is an instance of the specified class.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements (unused for class matching).

        Returns:
            True if the object is an instance of class_name or its subclasses.
        """
        for cls in type(obj).__mro__:
            cls_name = cls.__name__
            if cls_name == self.class_name or cls_name == f"{self.class_name}Builder":
                return True
        return False


@dataclasses.dataclass(frozen=True)
class IdSelector(Selector):
    """Selector that matches elements by their id attribute.

    Examples:
        ```python
        selector = IdSelector("main_node")
        selector.select(element, [])  # True if element.id_ == "main_node"
        ```
    """

    id_: str = dataclasses.field(metadata={"description": "The id"})

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the object has the specified id.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements (unused for id matching).

        Returns:
            True if the object has an id_ attribute matching the selector.
        """
        return hasattr(obj, "id_") and obj.id_ == self.id_


@dataclasses.dataclass(frozen=True)
class ChildSelector(Selector):
    """Selector that matches elements that are direct children of a parent.

    Examples:
        ```python
        selector = ChildSelector(TypeSelector("Group"), TypeSelector("Rectangle"))
        selector.select(rect, [group])  # True if rect is direct child of group
        ```
    """

    parent_selector: Selector = dataclasses.field(
        metadata={"description": "The parent selector"}
    )
    child_selector: Selector = dataclasses.field(
        metadata={"description": "The child selector"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the object is a direct child matching the criteria.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if the object matches child_selector and its immediate
            parent matches parent_selector.
        """
        if not ancestors:
            return False
        return self.child_selector.select(
            obj, ancestors
        ) and self.parent_selector.select(ancestors[-1], ancestors[:-1])


@dataclasses.dataclass(frozen=True)
class DescendantSelector(Selector):
    """Selector that matches elements that are descendants of an ancestor.

    Examples:
        ```python
        selector = DescendantSelector(TypeSelector("Group"), TypeSelector("Text"))
        selector.select(text, [subgroup, group])  # True if text is somewhere inside group
        ```
    """

    ancestor_selector: Selector = dataclasses.field(
        metadata={"description": "The ancestor selector"}
    )
    descendant_selector: Selector = dataclasses.field(
        metadata={"description": "The descendant selector"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if the object is a descendant matching the criteria.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if the object matches descendant_selector and any ancestor
            matches ancestor_selector.
        """
        if not ancestors:
            return False
        return self.descendant_selector.select(obj, ancestors) and any(
            [
                self.ancestor_selector.select(ancestor, ancestors[:i])
                for i, ancestor in enumerate(ancestors)
            ]
        )


@dataclasses.dataclass(frozen=True)
class OrSelector(Selector):
    """Selector that matches if any of its component selectors match (OR logic).

    Examples:
        ```python
        selector = OrSelector((TypeSelector("Rectangle"), TypeSelector("Circle")))
        selector.select(some_shape, [])  # True if shape is Rectangle OR Circle
        ```
    """

    selectors: tuple[Selector, ...] = dataclasses.field(
        metadata={"description": "The tuple of disjunct selectors"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if any selector in the tuple matches.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if any selector matches the object.
        """
        return any([selector.select(obj, ancestors) for selector in self.selectors])


@dataclasses.dataclass(frozen=True)
class CompoundSelector(Selector):
    """Selector that matches only if all of its component selectors match (AND logic).

    Examples:
        ```python
        selector = CompoundSelector((TypeSelector("Rectangle"), ClassSelector("Colored")))
        selector.select(element, [])  # True if element is Rectangle AND Colored
        ```
    """

    selectors: tuple[Selector, ...] = dataclasses.field(
        metadata={"description": "The tuple of conjunct selectors"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if all selectors in the tuple match.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if all selectors match the object.
        """
        return all([selector.select(obj, ancestors) for selector in self.selectors])


@dataclasses.dataclass(frozen=True)
class NotSelector(Selector):
    """Selector that matches if none of its component selectors match (NOT logic).

    Examples:
        ```python
        selector = NotSelector((TypeSelector("Hidden"),))
        selector.select(element, [])  # True if element is NOT of type Hidden
        ```
    """

    selectors: tuple[Selector, ...] = dataclasses.field(
        metadata={"description": "The tuple of negated conjunct selectors"}
    )

    def select(
        self,
        obj: LayoutElement | Builder,
        ancestors: collections.abc.Collection[LayoutElement | Builder],
    ) -> bool:
        """Check if none of the selectors in the tuple match.

        Args:
            obj: The layout element or builder to test.
            ancestors: List of ancestor elements.

        Returns:
            True if no selector matches the object.
        """
        return not any([selector.select(obj, ancestors) for selector in self.selectors])


_css_import_keyword = pyparsing.Literal("@import")
_css_unset_value = pyparsing.Literal("unset")
_css_none_value = pyparsing.Literal("none")
_css_float_value = pyparsing.Combine(
    pyparsing.Word(pyparsing.nums)
    + pyparsing.Literal(".")
    + pyparsing.Word(pyparsing.nums)
)
_css_string_value = pyparsing.quoted_string
_css_color_name_value = pyparsing.Word(pyparsing.alphas + "_")
_css_color_hex_value = pyparsing.Regex(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?")
_css_color_value = _css_color_hex_value | _css_color_name_value
_css_int_value = pyparsing.Word(pyparsing.nums)
_css_drop_shadow_filter_value = (
    pyparsing.Literal("drop-shadow(")
    + _css_float_value
    + pyparsing.Literal(",")
    + _css_float_value
    + pyparsing.Literal(",")
    + _css_float_value
    + pyparsing.Literal(",")
    + _css_float_value
    + pyparsing.Literal(",")
    + _css_color_value
    + pyparsing.Literal(")")
)
_css_filter_value = _css_drop_shadow_filter_value
_css_gradient_angle_value = pyparsing.Regex(r"-?[0-9]+(\.[0-9]+)?deg")
_css_gradient_percentage_value = pyparsing.Regex(r"-?[0-9]+(\.[0-9]+)?%")
_css_gradient_length_value = pyparsing.Regex(r"-?[0-9]+(\.[0-9]+)?")
_css_gradient_position_value = (
    _css_gradient_percentage_value | _css_gradient_length_value
)
_css_gradient_color_stop_value = pyparsing.Group(
    _css_color_value
    + pyparsing.Optional(_css_gradient_position_value)
    + pyparsing.Optional(_css_gradient_position_value)
)
_css_gradient_color_stops_value = pyparsing.Group(
    pyparsing.DelimitedList(_css_gradient_color_stop_value, ",", min=2)
)
_css_linear_gradient_value = (
    pyparsing.Literal("linear-gradient(")
    + pyparsing.Optional(_css_gradient_angle_value + pyparsing.Suppress(","))
    + _css_gradient_color_stops_value
    + pyparsing.Literal(")")
)
_css_repeating_linear_gradient_value = (
    pyparsing.Literal("repeating-linear-gradient(")
    + pyparsing.Optional(_css_gradient_angle_value + pyparsing.Suppress(","))
    + _css_gradient_color_stops_value
    + pyparsing.Literal(")")
)
_css_radial_gradient_value = (
    pyparsing.Literal("radial-gradient(")
    + _css_gradient_color_stops_value
    + pyparsing.Literal(")")
)
_css_keyword_value = pyparsing.one_of("miter round bevel butt square", as_keyword=True)
_css_simple_value = (
    _css_linear_gradient_value
    | _css_repeating_linear_gradient_value
    | _css_radial_gradient_value
    | _css_drop_shadow_filter_value
    | _css_keyword_value
    | _css_unset_value
    | _css_none_value
    | _css_float_value
    | _css_string_value
    | _css_color_value
    | _css_int_value
)
_css_list_value = pyparsing.Group(
    pyparsing.DelimitedList(_css_simple_value, ",", min=2)
)
_css_attribute_value = _css_list_value | _css_simple_value
_css_attribute_name = pyparsing.Word(
    pyparsing.alphas + "_", pyparsing.alphanums + "_" + "-"
)


_css_import_statement = _css_import_keyword + _css_string_value + pyparsing.Literal(";")
_css_style = (
    _css_attribute_name
    + pyparsing.Literal(":")
    + _css_attribute_value
    + pyparsing.Literal(";")
)
_css_style_collection = (
    pyparsing.Literal("{")
    + pyparsing.Group(_css_style[1, ...])
    + pyparsing.Literal("}")
)
_css_id = pyparsing.Word(pyparsing.printables, exclude_chars=",")
_css_id_selector = pyparsing.Literal("#") + _css_id
_css_class_name = pyparsing.Word(pyparsing.alphas + "_", pyparsing.alphanums + "_")
_css_type_selector = _css_class_name.copy()
_css_class_selector = pyparsing.Literal(".") + _css_class_name
_css_elementary_selector = _css_class_selector | _css_type_selector | _css_id_selector
_css_child_selector = (
    _css_elementary_selector + pyparsing.Literal(">") + _css_elementary_selector
)
_css_descendant_selector = (
    _css_elementary_selector
    + pyparsing.OneOrMore(pyparsing.White())
    + _css_elementary_selector
)
_css_or_selector = pyparsing.Group(
    pyparsing.DelimitedList(_css_elementary_selector, ",", min=2)
)
_css_selector = (
    _css_child_selector
    | _css_descendant_selector
    | _css_or_selector
    | _css_elementary_selector
)
_css_rule = _css_selector + _css_style_collection
_css_style_sheet = pyparsing.Group(_css_rule[1, ...])


@_css_unset_value.set_parse_action
def _resolve_css_unset_value(results: pyparsing.ParseResults) -> typing.Any:
    return results[0]


@_css_none_value.set_parse_action
def _resolve_css_none_value(results: pyparsing.ParseResults) -> typing.Any:
    return NoneValue


@_css_float_value.set_parse_action
def _resolve_css_float_value(results: pyparsing.ParseResults) -> float:
    return float(results[0])


@_css_string_value.set_parse_action
def _resolve_css_string_value(results: pyparsing.ParseResults) -> str:
    return str(results[0][1:-1])


@_css_int_value.set_parse_action
def _resolve_css_int_value(results: pyparsing.ParseResults) -> int:
    return int(results[0])


@_css_color_name_value.set_parse_action
def _resolve_css_color_name_value(results: pyparsing.ParseResults) -> typing.Any:
    if not has_color(results[0]):
        raise ValueError(f"{results[0]} is not a valid color name")
    return getattr(momapy.coloring, results[0])


@_css_color_hex_value.set_parse_action
def _resolve_css_color_hex_value(results: pyparsing.ParseResults) -> Color:
    if len(results[0]) == 7:
        return Color.from_hex(results[0])
    return Color.from_hexa(results[0])


@_css_gradient_angle_value.set_parse_action
def _resolve_css_gradient_angle_value(results: pyparsing.ParseResults) -> float:
    return float(results[0].removesuffix("deg"))


@_css_gradient_length_value.set_parse_action
def _resolve_css_gradient_length_value(results: pyparsing.ParseResults) -> float:
    return float(results[0])


def _make_css_gradient_stops(
    color_stops: pyparsing.ParseResults, allow_lengths: bool
) -> tuple[list[Color], list[float], bool]:
    colors = []
    positions = []
    for color_stop in color_stops:
        if len(color_stop) == 1:
            colors.append(color_stop[0])
            positions.append(None)
        for position in color_stop[1:]:
            colors.append(color_stop[0])
            positions.append(position)
    has_lengths = any(isinstance(position, float) for position in positions)
    if has_lengths:
        if not allow_lengths:
            raise ValueError(
                "gradient positions must be percentages, lengths are only "
                "supported in repeating-linear-gradient"
            )
        if not all(isinstance(position, float) for position in positions):
            raise ValueError(
                "all gradient positions must be given as lengths, or none of them"
            )
    else:
        positions = [
            None if position is None else float(position.removesuffix("%")) / 100
            for position in positions
        ]
        if positions[0] is None:
            positions[0] = 0.0
        if positions[-1] is None:
            positions[-1] = 1.0
        previous_index = 0
        for index in range(1, len(positions)):
            if positions[index] is not None:
                step = (positions[index] - positions[previous_index]) / (
                    index - previous_index
                )
                for missing_index in range(previous_index + 1, index):
                    positions[missing_index] = positions[previous_index] + step * (
                        missing_index - previous_index
                    )
                previous_index = index
    for index in range(1, len(positions)):
        positions[index] = max(positions[index], positions[index - 1])
    return colors, positions, has_lengths


def _make_css_linear_gradient(
    angle: float, color_stops: pyparsing.ParseResults, repeating: bool
) -> LinearGradient:
    colors, positions, has_lengths = _make_css_gradient_stops(
        color_stops, allow_lengths=repeating
    )
    direction_x = math.sin(math.radians(angle))
    direction_y = -math.cos(math.radians(angle))
    if has_lengths:
        gradient_units = GradientUnits.USER_SPACE_ON_USE
        start_x = 0.0
        start_y = 0.0
    else:
        gradient_units = GradientUnits.OBJECT_BOUNDING_BOX
        length = abs(direction_x) + abs(direction_y)
        direction_x *= length
        direction_y *= length
        start_x = 0.5 - direction_x / 2
        start_y = 0.5 - direction_y / 2
    if repeating:
        first = positions[0]
        last = positions[-1]
        if last == first:
            raise ValueError("repeating gradients must have a non-zero period")
        offsets = [(position - first) / (last - first) for position in positions]
        spread_method = SpreadMethod.REPEAT
    else:
        first = 0.0
        last = 1.0
        offsets = [min(max(position, 0.0), 1.0) for position in positions]
        spread_method = SpreadMethod.PAD
    return LinearGradient(
        gradient_units=gradient_units,
        spread_method=spread_method,
        x1=start_x + direction_x * first,
        y1=start_y + direction_y * first,
        x2=start_x + direction_x * last,
        y2=start_y + direction_y * last,
        stops=tuple(
            GradientStop(offset=offset, stop_color=color)
            for offset, color in zip(offsets, colors)
        ),
    )


@_css_linear_gradient_value.set_parse_action
def _resolve_css_linear_gradient_value(
    results: pyparsing.ParseResults,
) -> LinearGradient:
    angle = results[1] if len(results) == 4 else 180.0
    return _make_css_linear_gradient(angle, results[-2], repeating=False)


@_css_repeating_linear_gradient_value.set_parse_action
def _resolve_css_repeating_linear_gradient_value(
    results: pyparsing.ParseResults,
) -> LinearGradient:
    angle = results[1] if len(results) == 4 else 180.0
    return _make_css_linear_gradient(angle, results[-2], repeating=True)


@_css_radial_gradient_value.set_parse_action
def _resolve_css_radial_gradient_value(
    results: pyparsing.ParseResults,
) -> RadialGradient:
    colors, positions, _ = _make_css_gradient_stops(results[1], allow_lengths=False)
    return RadialGradient(
        r=math.sqrt(2) / 2,
        stops=tuple(
            GradientStop(offset=min(max(position, 0.0), 1.0), stop_color=color)
            for position, color in zip(positions, colors)
        ),
    )


@_css_drop_shadow_filter_value.set_parse_action
def _resolve_css_drop_shadow_filter_value(
    results: pyparsing.ParseResults,
) -> typing.Any:
    filter_effect = get_or_make_builder_cls(DropShadowEffect)(
        dx=results[1],
        dy=results[3],
        std_deviation=results[5],
        flood_opacity=results[7],
        flood_color=results[9],
    )
    filter = get_or_make_builder_cls(Filter)(effects=[filter_effect])
    return filter


# Issue: the function cannot return None (pyparsing bug?) otherwise it simply
# does not apply the function
@_css_simple_value.set_parse_action
def _resolve_css_simple_value(results: pyparsing.ParseResults) -> typing.Any:
    return results[0]


@_css_list_value.set_parse_action
def _resolve_css_list_value(results: pyparsing.ParseResults) -> typing.Any:
    return [list(results[0])]


@_css_attribute_value.set_parse_action
def _resolve_css_attribute_value(results: pyparsing.ParseResults) -> typing.Any:
    # see above
    if results[0] == "unset":
        results[0] = None
    return results


def _make_document_parser(base_dir: pathlib.Path) -> pyparsing.ParserElement:
    def _resolve_import(results: pyparsing.ParseResults) -> "StyleSheet":
        return StyleSheet.from_file(base_dir / results[1])

    import_stmt = _css_import_statement.copy()
    import_stmt.set_parse_action(_resolve_import)
    document = import_stmt[...] + _css_style_sheet[...]

    def _combine(results: pyparsing.ParseResults) -> "StyleSheet":
        style_sheets = [
            style_sheet for style_sheet in results if style_sheet is not None
        ]
        combined = combine_style_sheets(style_sheets)
        return combined if combined is not None else StyleSheet()

    document.set_parse_action(_combine)
    return document


@_css_attribute_name.set_parse_action
def _resolve_css_attribute_name(results: pyparsing.ParseResults) -> str:
    attribute_name = results[0].replace("-", "_")
    # A reserved-word presentation attribute is stored with a trailing
    # underscore (e.g. the CSS ``filter`` maps to the field ``filter_``).
    if (
        attribute_name not in PRESENTATION_ATTRIBUTES
        and f"{attribute_name}_" in PRESENTATION_ATTRIBUTES
    ):
        attribute_name = f"{attribute_name}_"
    return attribute_name


@_css_style.set_parse_action
def _resolve_css_style(results: pyparsing.ParseResults) -> typing.Any:
    attribute_name = results[0]
    attribute_value = results[2]
    for suffix, enum_class in [
        ("stroke_linecap", LineCap),
        ("stroke_linejoin", LineJoin),
    ]:
        if attribute_name.endswith(suffix) and isinstance(attribute_value, str):
            if attribute_value.upper() not in enum_class.__members__:
                raise ValueError(
                    f"{attribute_value} is not a valid value for {attribute_name}"
                )
            attribute_value = enum_class[attribute_value.upper()]
    return (
        attribute_name,
        attribute_value,
    )


@_css_style_collection.set_parse_action
def _resolve_css_style_collection(
    results: pyparsing.ParseResults,
) -> StyleCollection:
    return StyleCollection(dict(list(results[1])))


@_css_id.set_parse_action
def _resolve_css_id(results: pyparsing.ParseResults) -> typing.Any:
    return results[0]


@_css_id_selector.set_parse_action
def _resolve_id_selector(results: pyparsing.ParseResults) -> "IdSelector":
    return IdSelector(results[1])


@_css_class_name.set_parse_action
def _resolve_css_class_name(results: pyparsing.ParseResults) -> typing.Any:
    return results[0]


@_css_type_selector.set_parse_action
def _resolve_css_type_selector(results: pyparsing.ParseResults) -> "TypeSelector":
    return TypeSelector(results[0])


@_css_class_selector.set_parse_action
def _resolve_css_class_selector(results: pyparsing.ParseResults) -> "ClassSelector":
    return ClassSelector(results[1])


@_css_elementary_selector.set_parse_action
def _resolve_css_elementary_selector(
    results: pyparsing.ParseResults,
) -> typing.Any:
    return results[0]


@_css_child_selector.set_parse_action
def _resolve_css_child_selector(results: pyparsing.ParseResults) -> "ChildSelector":
    return ChildSelector(results[0], results[2])


@_css_descendant_selector.set_parse_action
def _resolve_css_descendant_selector(
    results: pyparsing.ParseResults,
) -> "DescendantSelector":
    return DescendantSelector(results[0], results[2])


@_css_or_selector.set_parse_action
def _resolve_css_or_selector(results: pyparsing.ParseResults) -> "OrSelector":
    return OrSelector(tuple(results[0]))


@_css_rule.set_parse_action
def _resolve_css_rule(results: pyparsing.ParseResults) -> typing.Any:
    return (
        results[0],
        results[1],
    )


@_css_style_sheet.set_parse_action
def _resolve_css_style_sheet(results: pyparsing.ParseResults) -> StyleSheet:
    return StyleSheet(dict(list(results[0])))


def _is_presentation_attribute(field_name: str) -> bool:
    """Check whether a field name corresponds to a presentation attribute.

    A field is considered a presentation attribute if its name — or its
    name after stripping an arbitrary prefix — matches an entry in
    ``PRESENTATION_ATTRIBUTES``.  This handles prefixed
    variants such as ``group_fill``, ``reaction_node_stroke``, or
    ``end_arrowhead_width`` without requiring an explicit prefix list.

    Args:
        field_name: The Python field name to check.

    Returns:
        True if the field is a presentation attribute.
    """
    for attribute_name in PRESENTATION_ATTRIBUTES:
        # A reserved-word attribute carries a trailing underscore (e.g.
        # ``filter_``); its prefixed variants do not (``group_filter``), so
        # match the suffix against the bare name.
        bare_name = attribute_name.rstrip("_")
        if field_name == attribute_name or field_name.endswith(f"_{bare_name}"):
            return True
    return False


def get_stylable_attributes(
    layout_element_or_class: LayoutElement | type,
    presentation_only: bool = False,
) -> list[str]:
    """Return the CSS-style names of stylable attributes of a layout element.

    Returns the names of all dataclass fields that can be set via a
    stylesheet (i.e., via ``apply_style_collection``), formatted as
    CSS property names (with hyphens instead of underscores).

    Args:
        layout_element_or_class: A layout element instance or class to
            inspect.
        presentation_only: If True, only return presentation attributes
            (fill, stroke, font, transform, etc.). Defaults to False.

    Returns:
        A sorted list of CSS-style attribute names.

    Raises:
        TypeError: If the argument is not a LayoutElement class or
            instance.
    """
    if isinstance(layout_element_or_class, type):
        layout_element_class = layout_element_or_class
    else:
        layout_element_class = type(layout_element_or_class)
    if not (
        dataclasses.is_dataclass(layout_element_class)
        and issubclass(layout_element_class, LayoutElement)
    ):
        raise TypeError(
            f"Expected a LayoutElement class or instance, got {layout_element_class}"
        )
    stylable_attributes = []
    for field in dataclasses.fields(layout_element_class):
        if field.name.startswith("_"):
            continue
        # id_ is the element's identity, not a stylable property: it is targeted
        # with the #id selector, and the CSS name "id" would not round-trip back
        # to id_ through the attribute-name parse action.
        if field.name == "id_":
            continue
        if presentation_only and not _is_presentation_attribute(field.name):
            continue
        css_name = field.name.rstrip("_").replace("_", "-")
        stylable_attributes.append(css_name)
    stylable_attributes.sort()
    return stylable_attributes
