"""Map class and functions to build and merge maps."""

import collections.abc
import dataclasses
import typing

from momapy.core._assembling import get_new_top_level_map_elements
from momapy.core._assembling import make_layout_model_mapping
from momapy.core._assembling import make_model_from_merged_model_elements
from momapy.core._assembling import merge_equal_map_elements
from momapy.core.elements import LayoutElement
from momapy.core.elements import MapElement
from momapy.core.elements import ModelElement
from momapy.core.layout import Layout
from momapy.core.mapping import LayoutModelMapping
from momapy.core.model import Model


@dataclasses.dataclass(frozen=True, kw_only=True)
class Map(MapElement):
    """Class for maps."""

    model: Model | None = dataclasses.field(
        default=None, metadata={"description": "The model of the map"}
    )
    layout: Layout | None = dataclasses.field(
        default=None, metadata={"description": "The layout of the map"}
    )
    layout_model_mapping: LayoutModelMapping | None = dataclasses.field(
        default=None,
        metadata={"description": "The layout model mapping of the map"},
    )

    def is_submap(self, other: "Map") -> bool:
        """Return `True` if the `Map` is a submap of another given map, `False` otherwise.

        A complete map is never a submap of an incomplete one: if either `self`
        or `other` has a `None` model, layout, or layout-model mapping, this
        returns `False`.
        """
        if (
            self.model is None
            or self.layout is None
            or self.layout_model_mapping is None
            or other.model is None
            or other.layout is None
            or other.layout_model_mapping is None
        ):
            return False
        return (
            self.model.is_submodel(other.model)
            and self.layout.is_sublayout(other.layout)
            and self.layout_model_mapping.is_submapping(other.layout_model_mapping)
        )

    def get_mapping(
        self,
        map_element: "MapElement",
    ) -> "ModelElement | list[LayoutElement | frozenset[LayoutElement]] | None":
        """Return the model element or layout elements mapped to `map_element`.

        The lookup is bidirectional: a layout key (a singleton or frozenset)
        resolves to its model element, and a model element resolves to the
        list of layout keys mapped to it. Forwards to
        `layout_model_mapping.get_mapping`.

        Returns `None` when the map has no `layout_model_mapping` (for
        example a layout-less map such as one read from SBML).
        """
        if self.layout_model_mapping is None:
            return None
        return self.layout_model_mapping.get_mapping(map_element)


def make_map(
    map_class: type[Map],
    model_elements: collections.abc.Iterable[ModelElement] = (),
    layout_elements: collections.abc.Iterable[LayoutElement] = (),
    layout_model_pairs: collections.abc.Iterable[
        tuple[LayoutElement, ModelElement]
    ] = (),
) -> Map:
    """Build a map from its top-level model elements, layout elements and pairs.

    Equal elements of `model_elements` become one, the one with the smallest
    `id_` (the first one on equal ids), and the same for `layout_elements`.
    Every reference, arc end and layout element or model element of a pair
    is replaced by the element that stands for it in the map. The keys of
    the layout-model mapping are computed from the pairs.

    Args:
        map_class: The class of the map.
        model_elements: All the top-level model elements, drawn or not.
        layout_elements: All the top-level layout elements, in drawing order.
        layout_model_pairs: The `(layout_element, model_element)` pairs, where
            `layout_element` draws `model_element`. Each element of a pair
            must be an element of `model_elements` or `layout_elements`, or
            one of their descendants, as the same object.

    Returns:
        The map. Its model is `None` if no model element is given, its layout
        `None` if no layout element is given, and its mapping `None` if
        either is `None`.

    Raises:
        ValueError: If an element of a pair is not under the given elements,
            if an element referred to is neither under the given elements nor
            equal to one of them, if merging would lose a reference, if two
            pairs have equal layout elements that are not the same object, or
            if no model collection accepts a top-level model element.
    """
    from momapy.positioning import fit

    model_elements = list(model_elements)
    layout_elements = list(layout_elements)
    layout_model_pairs = list(layout_model_pairs)
    model_class = _get_map_field_class(map_class, "model")
    layout_class = _get_map_field_class(map_class, "layout")
    if layout_elements and layout_class is None:
        raise ValueError(f"{map_class.__name__} has no layout")
    for map_elements, element_index in [
        (model_elements, 1),
        (layout_elements, 0),
    ]:
        under_map_element_ids = {
            id(map_element)
            for top_level_map_element in map_elements
            for map_element in [top_level_map_element]
            + top_level_map_element.descendants()
        }
        for layout_model_pair in layout_model_pairs:
            map_element = layout_model_pair[element_index]
            if id(map_element) not in under_map_element_ids:
                raise ValueError(
                    f"{type(map_element).__name__} {map_element.id_!r} of the pair "
                    f"{layout_model_pair[0].id_!r} -> {layout_model_pair[1].id_!r} "
                    "is not one of the given elements or one of their descendants"
                )
    model_element_id_to_new_model_element = merge_equal_map_elements(model_elements)
    layout_element_id_to_new_layout_element = merge_equal_map_elements(layout_elements)
    new_model_elements = get_new_top_level_map_elements(
        model_elements, model_element_id_to_new_model_element
    )
    new_layout_elements = get_new_top_level_map_elements(
        layout_elements, layout_element_id_to_new_layout_element
    )
    new_layout_model_pairs = [
        (
            layout_element_id_to_new_layout_element[id(layout_element)],
            model_element_id_to_new_model_element[id(model_element)],
        )
        for layout_element, model_element in layout_model_pairs
    ]
    if new_model_elements:
        model = make_model_from_merged_model_elements(model_class, new_model_elements)
    else:
        model = None
    if new_layout_elements:
        bbox = fit(new_layout_elements)
        layout = layout_class(
            layout_elements=tuple(new_layout_elements),
            position=bbox.position,
            width=bbox.width,
            height=bbox.height,
        )
    else:
        layout = None
    if model is not None and layout is not None:
        layout_model_mapping = make_layout_model_mapping(
            new_layout_elements, new_layout_model_pairs
        )
    else:
        layout_model_mapping = None
    return map_class(
        model=model, layout=layout, layout_model_mapping=layout_model_mapping
    )


def merge_maps(maps: collections.abc.Iterable[Map]) -> Map:
    """Merge maps into one map.

    Calls `make_map` with the top-level model elements, the top-level layout
    elements and the pairs of all the maps, so equal top-level elements
    become one. Maps are not moved: they overlap in their own coordinates.
    The fields of the map, the model and the layout other than their
    collections take the defaults of their classes.

    Args:
        maps: The maps to merge, all of the same class.

    Returns:
        The merged map.

    Raises:
        ValueError: If there is no map, if the maps are of different classes,
            or as `make_map`.
    """
    maps = list(maps)
    if not maps:
        raise ValueError("no map to merge")
    map_class = type(maps[0])
    for map_ in maps:
        if type(map_) is not map_class:
            raise ValueError(
                f"cannot merge a {type(map_).__name__} with a {map_class.__name__}"
            )
    model_elements = []
    layout_elements = []
    layout_model_pairs = []
    for map_ in maps:
        if map_.model is not None:
            model_elements += map_.model.children()
        if map_.layout is not None:
            layout_elements += map_.layout.children()
        if map_.layout_model_mapping is not None:
            layout_model_pairs += map_.layout_model_mapping.get_layout_model_pairs()
    return make_map(map_class, model_elements, layout_elements, layout_model_pairs)


def _get_map_field_class(map_class: type[Map], field_name: str) -> type | None:
    """Return the class of the model or the layout of a map class.

    Args:
        map_class: The map class.
        field_name: `"model"` or `"layout"`.

    Returns:
        The member of the union type of the field that is not `None`, or
        `None` if the field is typed `None`.
    """
    field_type = typing.get_type_hints(map_class)[field_name]
    classes = [
        cls
        for cls in typing.get_args(field_type) or (field_type,)
        if cls is not type(None)
    ]
    if not classes:
        return None
    return classes[0]
