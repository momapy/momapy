"""Build, take apart and merge maps from their map elements."""

import collections
import collections.abc
import dataclasses
import typing

from momapy.core.elements import LayoutElement
from momapy.core.elements import MapElement
from momapy.core.elements import ModelElement
from momapy.core.elements import is_reference_field
from momapy.core.layout import Arc
from momapy.core.map import Map
from momapy.core.mapping import LayoutModelMapping
from momapy.core.mapping import LayoutModelMappingBuilder
from momapy.core.model import Model


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
    model_class = get_map_field_class(map_class, "model")
    layout_class = get_map_field_class(map_class, "layout")
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
            layout_model_pairs += get_layout_model_pairs(map_.layout_model_mapping)
    return make_map(map_class, model_elements, layout_elements, layout_model_pairs)


def get_layout_model_pairs(
    layout_model_mapping: LayoutModelMapping,
) -> list[tuple[LayoutElement, ModelElement]]:
    """Return the pairs a layout-model mapping is made from.

    Args:
        layout_model_mapping: The layout-model mapping.

    Returns:
        A `(key, model_element)` pair for each single key, and a
        `(representative, model_element)` pair for each representative of
        each frozenset key.
    """
    layout_model_pairs = []
    for key, model_element in layout_model_mapping.items():
        if isinstance(key, frozenset):
            for (
                representative
            ) in layout_model_mapping.representative_to_key.inverse.get(key, []):
                layout_model_pairs.append((representative, model_element))
        else:
            layout_model_pairs.append((key, model_element))
    return layout_model_pairs


def make_layout_model_mapping(
    layout_elements: collections.abc.Iterable[LayoutElement],
    layout_model_pairs: collections.abc.Iterable[tuple[LayoutElement, ModelElement]],
) -> LayoutModelMapping:
    """Compute the layout-model mapping of pairs.

    Each pair gets one entry. The key of a layout element that draws a model
    element holds the layout element and the keys of the layout elements
    connected to it (by an arc end or a container) that draw an element
    related to the model element (a descendant of it, or an element referred
    to by it or by one of its descendants), or that draw nothing and are
    connected by an arc end. The key of a layout element that draws nothing
    holds the layout element and the layout elements it refers to that draw
    nothing. A key with one layout element is a single key; otherwise it is a
    frozenset key whose representative is the layout element of the pair.

    Args:
        layout_elements: The top-level layout elements.
        layout_model_pairs: The `(layout_element, model_element)` pairs. Their
            layout elements must be elements of `layout_elements` or
            descendants of them, as the same objects.

    Returns:
        The layout-model mapping.

    Raises:
        ValueError: If two pairs have equal layout elements that are not the
            same object.
    """
    layout_model_pairs = list(layout_model_pairs)
    paired_layout_elements = {}
    for layout_element, _ in layout_model_pairs:
        paired_layout_element = paired_layout_elements.setdefault(
            layout_element, layout_element
        )
        if paired_layout_element is not layout_element:
            raise ValueError(
                f"layout elements {paired_layout_element.id_!r} and "
                f"{layout_element.id_!r} are equal but are two objects; "
                "two equal layout elements cannot be told apart"
            )
    layout_element_id_to_model_element = {
        id(layout_element): model_element
        for layout_element, model_element in layout_model_pairs
    }
    layout_element_id_to_referring_layout_elements = collections.defaultdict(list)
    for top_level_layout_element in layout_elements:
        for layout_element in [
            top_level_layout_element
        ] + top_level_layout_element.descendants():
            for reference in layout_element.references():
                layout_element_id_to_referring_layout_elements[id(reference)].append(
                    layout_element
                )
    layout_element_id_to_key_elements = {}

    def is_connected_by_arc_end(
        layout_element: LayoutElement, connected_layout_element: LayoutElement
    ) -> bool:
        for arc, end in [
            (layout_element, connected_layout_element),
            (connected_layout_element, layout_element),
        ]:
            if isinstance(arc, Arc) and (arc.source is end or arc.target is end):
                return True
        return False

    def get_key_elements(layout_element: LayoutElement) -> list[LayoutElement]:
        key_elements = layout_element_id_to_key_elements.get(id(layout_element))
        if key_elements is not None:
            return key_elements
        key_elements = [layout_element]
        model_element = layout_element_id_to_model_element.get(id(layout_element))
        if model_element is None:
            for reference in layout_element.references():
                if id(reference) not in layout_element_id_to_model_element:
                    key_elements.append(reference)
        else:
            related_element_ids = {
                id(descendant) for descendant in model_element.descendants()
            } | {
                id(reference)
                for element in [model_element] + model_element.descendants()
                for reference in element.references()
            }
            for connected_layout_element in (
                layout_element.references()
                + layout_element_id_to_referring_layout_elements[id(layout_element)]
            ):
                connected_model_element = layout_element_id_to_model_element.get(
                    id(connected_layout_element)
                )
                if (
                    connected_model_element is None
                    and is_connected_by_arc_end(
                        layout_element, connected_layout_element
                    )
                ) or (
                    connected_model_element is not None
                    and id(connected_model_element) in related_element_ids
                ):
                    key_elements += get_key_elements(connected_layout_element)
        layout_element_id_to_key_elements[id(layout_element)] = key_elements
        return key_elements

    layout_model_mapping = LayoutModelMappingBuilder()
    for layout_element, model_element in layout_model_pairs:
        key = frozenset(get_key_elements(layout_element))
        if len(key) == 1:
            layout_model_mapping.add_mapping(layout_element, model_element)
        else:
            layout_model_mapping.add_mapping(
                key, model_element, representative=layout_element
            )
    return layout_model_mapping.build()


def check_equal_layout_elements(
    layout_elements: collections.abc.Iterable[LayoutElement],
) -> None:
    """Check that no two top-level layout elements are equal.

    Args:
        layout_elements: The top-level layout elements.

    Raises:
        ValueError: If two elements of `layout_elements` are equal and are
            not the same object.
    """
    first_layout_elements = {}
    for layout_element in layout_elements:
        first_layout_element = first_layout_elements.setdefault(
            layout_element, layout_element
        )
        if first_layout_element is not layout_element:
            raise ValueError(
                f"layout elements {first_layout_element.id_!r} and "
                f"{layout_element.id_!r} are equal; two equal layout elements "
                "cannot be told apart"
            )


def make_model_from_merged_model_elements(
    model_class: type[Model],
    merged_top_level_model_elements: collections.abc.Iterable[ModelElement],
) -> Model:
    """Make a model holding top-level model elements in their collections.

    Each element goes in the field of `model_class` typed `frozenset[T]` such
    that the element is an instance of `T`.

    Args:
        model_class: The class of the model.
        merged_top_level_model_elements: The top-level model elements, already
            merged: no two of them are equal.

    Returns:
        The model.

    Raises:
        ValueError: If no collection of `model_class` accepts an element.
    """
    collection_name_to_classes = {}
    for field_name, field_type in typing.get_type_hints(model_class).items():
        if typing.get_origin(field_type) is frozenset:
            element_type = typing.get_args(field_type)[0]
            collection_name_to_classes[field_name] = typing.get_args(element_type) or (
                element_type,
            )
    collection_name_to_model_elements = {
        collection_name: [] for collection_name in collection_name_to_classes
    }
    for model_element in merged_top_level_model_elements:
        collection_name = next(
            (
                collection_name
                for collection_name, classes in collection_name_to_classes.items()
                if isinstance(model_element, classes)
            ),
            None,
        )
        if collection_name is None:
            raise ValueError(
                f"no collection of {model_class.__name__} accepts "
                f"{type(model_element).__name__} {model_element.id_!r}"
            )
        collection_name_to_model_elements[collection_name].append(model_element)
    return model_class(
        **{
            collection_name: frozenset(model_elements)
            for collection_name, model_elements in (
                collection_name_to_model_elements.items()
            )
        }
    )


def merge_equal_map_elements(
    top_level_map_elements: collections.abc.Iterable[MapElement],
) -> dict[int, MapElement]:
    """Merge equal top-level map elements.

    In each group of equal elements of `top_level_map_elements`, the kept
    element is the one with the smallest `id_`, or the first one on equal
    ids. The new element of each element of a group is the kept element,
    rebuilt so that its references and those of its descendants are new
    elements. The new element of a descendant is its matching descendant in
    the new element of its top-level element. An element referred to that is
    not under `top_level_map_elements` but is equal to one of them gets the
    new element of that one, and its descendants their matching descendants.

    Args:
        top_level_map_elements: The top-level map elements, all model
            elements or all layout elements.

    Returns:
        A dict mapping the `id()` of each element reachable from
        `top_level_map_elements` (through children and references) to its
        new element.

    Raises:
        ValueError: If an element reachable from `top_level_map_elements` is
            neither under them, nor equal to one of them, nor a descendant of
            a reachable element, or if merging would lose a reference.
    """
    top_level_map_elements = list(top_level_map_elements)
    kept_map_elements = {}
    for map_element in top_level_map_elements:
        kept_map_element = kept_map_elements.get(map_element)
        if kept_map_element is None or map_element.id_ < kept_map_element.id_:
            kept_map_elements[map_element] = map_element
    reachable_map_elements = {}
    map_element_id_to_owner = {}
    map_elements_to_visit = list(reversed(top_level_map_elements))
    while map_elements_to_visit:
        map_element = map_elements_to_visit.pop()
        if id(map_element) in reachable_map_elements:
            continue
        reachable_map_elements[id(map_element)] = map_element
        children = map_element.children()
        for child in children:
            map_element_id_to_owner[id(child)] = map_element
        map_elements_to_visit += reversed(children + map_element.references())
    top_level_map_element_ids = {
        id(map_element) for map_element in top_level_map_elements
    }
    for map_element in reachable_map_elements.values():
        if (
            id(map_element) not in top_level_map_element_ids
            and id(map_element) not in map_element_id_to_owner
            and map_element not in kept_map_elements
        ):
            raise ValueError(
                f"{type(map_element).__name__} {map_element.id_!r} is referred "
                "to but is neither one of the given elements, nor equal to one, "
                "nor a descendant of one"
            )
    map_element_id_to_new_map_element = {}
    kept_map_element_id_to_new_map_element = {}

    def get_root(map_element: MapElement) -> MapElement:
        while (
            id(map_element) in map_element_id_to_owner
            and id(map_element) not in top_level_map_element_ids
        ):
            map_element = map_element_id_to_owner[id(map_element)]
        return map_element

    def get_new_map_element(map_element: MapElement) -> MapElement:
        new_map_element = map_element_id_to_new_map_element.get(id(map_element))
        if new_map_element is not None:
            return new_map_element
        root = get_root(map_element)
        kept_map_element = kept_map_elements[root]
        new_kept_map_element = kept_map_element_id_to_new_map_element.get(
            id(kept_map_element)
        )
        if new_kept_map_element is None:
            for descendant in [kept_map_element] + kept_map_element.descendants():
                for reference in descendant.references():
                    get_new_map_element(reference)
            new_kept_map_element = replace_map_element_references(
                kept_map_element, map_element_id_to_new_map_element
            )
            kept_map_element_id_to_new_map_element[id(kept_map_element)] = (
                new_kept_map_element
            )
        if root is not kept_map_element:
            check_lost_references(root, kept_map_element, get_new_map_element)
        map_element_id_to_new_map_element.update(
            get_matching_descendant_map_elements(root, new_kept_map_element)
        )
        return map_element_id_to_new_map_element[id(map_element)]

    for map_element in reachable_map_elements.values():
        get_new_map_element(map_element)
    return map_element_id_to_new_map_element


def check_lost_references(
    dropped_map_element: MapElement,
    kept_map_element: MapElement,
    get_new_map_element: collections.abc.Callable[[MapElement], MapElement],
) -> None:
    """Check that merging a map element into an equal one loses no reference.

    For each reference field of `dropped_map_element`, and of each of its
    descendants compared with its matching descendant in `kept_map_element`,
    the elements referred to on both sides must have the same new elements.

    Args:
        dropped_map_element: The map element merged into `kept_map_element`.
        kept_map_element: The map element equal to `dropped_map_element`.
        get_new_map_element: The function giving the new element of a map
            element.

    Raises:
        ValueError: If a reference would be lost.
    """
    descendant_id_to_matching_descendant = get_matching_descendant_map_elements(
        dropped_map_element, kept_map_element
    )
    for descendant in [dropped_map_element] + dropped_map_element.descendants():
        matching_descendant = descendant_id_to_matching_descendant[id(descendant)]
        for field in dataclasses.fields(descendant):
            if not is_reference_field(type(descendant), field.name):
                continue
            field_value = getattr(descendant, field.name)
            matching_field_value = getattr(matching_descendant, field.name)
            if isinstance(field_value, tuple):
                new_elements = [
                    get_new_map_element(item) if isinstance(item, MapElement) else item
                    for item in field_value
                ]
                matching_new_elements = [
                    get_new_map_element(item) if isinstance(item, MapElement) else item
                    for item in matching_field_value
                ]
                is_lost = len(new_elements) != len(matching_new_elements) or any(
                    new_element is not matching_new_element
                    for new_element, matching_new_element in zip(
                        new_elements, matching_new_elements
                    )
                )
            elif isinstance(field_value, frozenset):
                is_lost = {
                    id(get_new_map_element(item))
                    for item in field_value
                    if isinstance(item, MapElement)
                } != {
                    id(get_new_map_element(item))
                    for item in matching_field_value
                    if isinstance(item, MapElement)
                }
            elif isinstance(field_value, MapElement):
                is_lost = get_new_map_element(field_value) is not get_new_map_element(
                    matching_field_value
                )
            else:
                is_lost = False
            if is_lost:
                raise ValueError(
                    f"{type(dropped_map_element).__name__} "
                    f"{dropped_map_element.id_!r} is equal to "
                    f"{type(kept_map_element).__name__} {kept_map_element.id_!r}, "
                    f"but the field {field.name!r} of {descendant.id_!r} and of "
                    f"{matching_descendant.id_!r} refers to elements that stay "
                    f"distinct ({field_value!r} and {matching_field_value!r}); "
                    "merging them would lose a reference"
                )


def get_matching_descendant_map_elements(
    map_element: MapElement, equal_map_element: MapElement
) -> dict[int, MapElement]:
    """Match a map element and its descendants to those of an equal element.

    The matching descendant of a descendant is the descendant of
    `equal_map_element` reached through the same fields, taking at each step
    the equal child (in a tuple, the child at the same position).

    Args:
        map_element: The map element.
        equal_map_element: A map element equal to `map_element`.

    Returns:
        A dict mapping the `id()` of `map_element` to `equal_map_element`, and
        the `id()` of each descendant of `map_element` to its matching
        descendant.
    """
    descendant_id_to_matching_descendant = {id(map_element): equal_map_element}
    for field in dataclasses.fields(map_element):
        if is_reference_field(type(map_element), field.name):
            continue
        field_value = getattr(map_element, field.name)
        equal_field_value = getattr(equal_map_element, field.name)
        if isinstance(field_value, MapElement):
            child_pairs = [(field_value, equal_field_value)]
        elif isinstance(field_value, tuple):
            child_pairs = list(zip(field_value, equal_field_value))
        elif isinstance(field_value, frozenset):
            equal_children = {child: child for child in equal_field_value}
            child_pairs = [(child, equal_children[child]) for child in field_value]
        else:
            child_pairs = []
        for child, equal_child in child_pairs:
            if isinstance(child, MapElement):
                descendant_id_to_matching_descendant.update(
                    get_matching_descendant_map_elements(child, equal_child)
                )
    return descendant_id_to_matching_descendant


def replace_map_element_references(
    map_element: MapElement,
    map_element_id_to_new_map_element: dict[int, MapElement],
) -> MapElement:
    """Replace the references of a map element and of its descendants.

    Args:
        map_element: The map element.
        map_element_id_to_new_map_element: A dict mapping the `id()` of a map
            element to its new map element. A map element that is not in it
            is kept.

    Returns:
        The map element itself if no reference changes, otherwise a copy of
        it whose references, and those of its descendants, are replaced.
    """
    field_name_to_new_field_value = {}
    for field in dataclasses.fields(map_element):
        field_value = getattr(map_element, field.name)
        is_reference = is_reference_field(type(map_element), field.name)
        if isinstance(field_value, (tuple, frozenset)):
            new_items = [
                replace_field_item(
                    item, is_reference, map_element_id_to_new_map_element
                )
                for item in field_value
            ]
            if all(new_item is item for new_item, item in zip(new_items, field_value)):
                new_field_value = field_value
            else:
                new_field_value = type(field_value)(new_items)
        else:
            new_field_value = replace_field_item(
                field_value, is_reference, map_element_id_to_new_map_element
            )
        if new_field_value is not field_value:
            field_name_to_new_field_value[field.name] = new_field_value
    if not field_name_to_new_field_value:
        return map_element
    return dataclasses.replace(map_element, **field_name_to_new_field_value)


def replace_field_item(
    item: typing.Any,
    is_reference: bool,
    map_element_id_to_new_map_element: dict[int, MapElement],
) -> typing.Any:
    """Return the replacement of a field value, or of an item of it.

    Args:
        item: The field value, or an item of a tuple or frozenset field value.
        is_reference: Whether the field is a reference field.
        map_element_id_to_new_map_element: As in
            `replace_map_element_references`.

    Returns:
        The new map element of `item` if the field is a reference field,
        `item` with its references replaced if it is a child, and `item`
        otherwise.
    """
    if not isinstance(item, MapElement):
        return item
    if is_reference:
        return map_element_id_to_new_map_element.get(id(item), item)
    return replace_map_element_references(item, map_element_id_to_new_map_element)


def get_new_top_level_map_elements(
    top_level_map_elements: list[MapElement],
    map_element_id_to_new_map_element: dict[int, MapElement],
) -> list[MapElement]:
    """Return the new elements of top-level map elements, without duplicates.

    Args:
        top_level_map_elements: The top-level map elements.
        map_element_id_to_new_map_element: The dict returned by
            `merge_equal_map_elements`.

    Returns:
        The new elements, each at the position of the first element of its
        group.
    """
    new_map_element_id_to_new_map_element = {}
    for map_element in top_level_map_elements:
        new_map_element = map_element_id_to_new_map_element[id(map_element)]
        new_map_element_id_to_new_map_element[id(new_map_element)] = new_map_element
    return list(new_map_element_id_to_new_map_element.values())


def get_map_field_class(map_class: type[Map], field_name: str) -> type | None:
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
