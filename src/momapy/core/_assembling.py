"""Internal helpers to assemble maps from map elements."""

import collections.abc
import dataclasses
import functools
import typing

from momapy.core.elements import LayoutElement
from momapy.core.elements import MapElement
from momapy.core.elements import ModelElement
from momapy.core.layout import Arc
from momapy.core.map import Map
from momapy.core.mapping import LayoutModelMapping
from momapy.core.mapping import LayoutModelMappingBuilder
from momapy.positioning import fit


MapElements = tuple[
    tuple[LayoutElement, ...],
    dict[LayoutElement, ModelElement],
    tuple[ModelElement, ...],
]


@dataclasses.dataclass(frozen=True, kw_only=True)
class ClusterRule:
    """How to compute the frozenset keys of the drawn copies of one kind of model element.

    A drawn copy is a layout element mapped to a model element of one of
    `model_element_classes`. Its key holds the layout element, the arcs of
    `arc_classes` whose source is the layout element, and the target of each
    of these arcs.
    """

    model_element_classes: tuple[type, ...] = dataclasses.field(
        metadata={"description": "The model element classes the rule applies to."}
    )
    arc_classes: tuple[tuple[type, tuple[type, ...]], ...] = dataclasses.field(
        default=(),
        metadata={
            "description": "Pairs of an arc class and the child model element classes its arcs may map to."
        },
    )
    reversible_arc_classes: tuple[tuple[type, tuple[type, ...]], ...] = (
        dataclasses.field(
            default=(),
            metadata={
                "description": "Pairs of an arc class and the other child model element classes its arcs may map to when the model element is reversible."
            },
        )
    )
    cluster_arc_targets: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether the target of an arc brings its whole cluster into the key."
        },
    )
    with_ends: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether the layout element is an arc whose source and target clusters belong to the key, and draw the source and target of the model element."
        },
    )
    single_key_without_arcs: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether a layout element with no arc gets a single key."
        },
    )
    not_implemented: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether mapping a model element of the rule is not supported."
        },
    )


def is_reference_field(cls: type, field_name: str) -> bool:
    """Return whether a field of a map element class refers to another element.

    A field refers to another element when a class of `cls.__mro__` that
    declares the field marks it with `"reference": True` in its metadata, so a
    subclass that declares the field again needs no mark.

    Args:
        cls: The map element class.
        field_name: The name of the field.

    Returns:
        `True` if the field is a reference field, `False` otherwise.
    """
    for base in cls.__mro__:
        field = base.__dict__.get("__dataclass_fields__", {}).get(field_name)
        if field is not None and field.metadata.get("reference", False):
            return True
    return False


@functools.cache
def get_field_names(cls: type) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the owning and the reference field names of a map element class.

    Args:
        cls: The map element class.

    Returns:
        The owning field names and the reference field names.
    """
    owning_field_names = []
    reference_field_names = []
    for field in dataclasses.fields(cls):
        if is_reference_field(cls, field.name):
            reference_field_names.append(field.name)
        else:
            owning_field_names.append(field.name)
    return tuple(owning_field_names), tuple(reference_field_names)


def get_field_elements(value: typing.Any) -> list[MapElement]:
    """Return the map elements held by a field value.

    Args:
        value: The field value.

    Returns:
        The value itself if it is a map element, the map elements it
        contains if it is a tuple or a frozenset, and an empty list otherwise.
    """
    if isinstance(value, MapElement):
        return [value]
    if isinstance(value, (tuple, frozenset)):
        return [item for item in value if isinstance(item, MapElement)]
    return []


def get_children(element: MapElement) -> list[MapElement]:
    """Return the map elements held by the owning fields of a map element.

    Args:
        element: The map element.

    Returns:
        The children of the element.
    """
    owning_field_names, _ = get_field_names(type(element))
    children = []
    for field_name in owning_field_names:
        children += get_field_elements(getattr(element, field_name))
    return children


def get_references(element: MapElement) -> list[MapElement]:
    """Return the map elements held by the reference fields of a map element.

    Args:
        element: The map element.

    Returns:
        The elements the element refers to.
    """
    _, reference_field_names = get_field_names(type(element))
    references = []
    for field_name in reference_field_names:
        references += get_field_elements(getattr(element, field_name))
    return references


def get_descendants(element: MapElement) -> list[MapElement]:
    """Return a map element and all the elements it owns, recursively.

    Args:
        element: The map element.

    Returns:
        The element followed by its descendants.
    """
    descendants = [element]
    for child in get_children(element):
        descendants += get_descendants(child)
    return descendants


def replace_field_value(
    value: typing.Any,
    get_new_element: collections.abc.Callable[[MapElement], MapElement],
) -> typing.Any:
    """Return a field value with each of its map elements replaced.

    Args:
        value: The field value.
        get_new_element: The function giving the replacement of a map element.

    Returns:
        The value itself if no map element is replaced, a new value otherwise.
    """
    if isinstance(value, MapElement):
        return get_new_element(value)
    if isinstance(value, (tuple, frozenset)):
        items = list(value)
        new_items = [
            get_new_element(item) if isinstance(item, MapElement) else item
            for item in items
        ]
        if all(new_item is item for new_item, item in zip(new_items, items)):
            return value
        return type(value)(new_items)
    return value


def rebuild_element(
    element: MapElement,
    get_new_child: collections.abc.Callable[[MapElement], MapElement],
    get_new_reference: collections.abc.Callable[[MapElement], MapElement],
) -> MapElement:
    """Return a map element with its children and references replaced.

    Args:
        element: The map element.
        get_new_child: The function giving the replacement of a child.
        get_new_reference: The function giving the replacement of a reference.

    Returns:
        The element itself if nothing is replaced, a new element otherwise.
    """
    owning_field_names, reference_field_names = get_field_names(type(element))
    changes = {}
    for field_names, get_new_element in [
        (owning_field_names, get_new_child),
        (reference_field_names, get_new_reference),
    ]:
        for field_name in field_names:
            value = getattr(element, field_name)
            new_value = replace_field_value(value, get_new_element)
            if new_value is not value:
                changes[field_name] = new_value
    if not changes:
        return element
    return dataclasses.replace(element, **changes)


def match_descendants(dropped: MapElement, kept: MapElement) -> dict[int, MapElement]:
    """Match a map element and its descendants to those of an equal element.

    Each child of `dropped` is matched to the equal child in the same field of
    the match of its owner (by position for a tuple).

    Args:
        dropped: The map element to match.
        kept: The map element equal to `dropped`.

    Returns:
        A dict mapping the `id()` of `dropped` and of each of its descendants
        to its match.
    """
    matches = {id(dropped): kept}
    owning_field_names, _ = get_field_names(type(dropped))
    for field_name in owning_field_names:
        dropped_value = getattr(dropped, field_name)
        kept_value = getattr(kept, field_name)
        if isinstance(dropped_value, MapElement):
            matches.update(match_descendants(dropped_value, kept_value))
        elif isinstance(dropped_value, tuple):
            for dropped_item, kept_item in zip(dropped_value, kept_value):
                if isinstance(dropped_item, MapElement):
                    matches.update(match_descendants(dropped_item, kept_item))
        elif isinstance(dropped_value, frozenset):
            kept_items = {item: item for item in kept_value}
            for dropped_item in dropped_value:
                if isinstance(dropped_item, MapElement):
                    matches.update(
                        match_descendants(dropped_item, kept_items[dropped_item])
                    )
    return matches


def describe(element: MapElement) -> str:
    """Return a short description of a map element for error messages.

    Args:
        element: The map element.

    Returns:
        The class name and the id of the element.
    """
    return f"{type(element).__name__} {element.id_!r}"


def get_survivors(elements: list[MapElement]) -> dict[MapElement, MapElement]:
    """Return the survivor of each group of equal map elements.

    Of several equal elements, the one with the smallest `id_` is kept, and
    the first one on equal ids.

    Args:
        elements: The map elements.

    Returns:
        A dict mapping each element to the survivor of its group (by equality).
    """
    survivors = {}
    for element in elements:
        survivor = survivors.get(element)
        if survivor is None or element.id_ < survivor.id_:
            survivors[element] = element
    return survivors


def get_collection_name(
    element: ModelElement, collection_table: dict[type, str]
) -> str | None:
    """Return the name of the model collection that holds a top-level model element.

    Args:
        element: The model element.
        collection_table: The table mapping model element classes to
            collection names.

    Returns:
        The collection name, or `None` if no class of the table matches.
    """
    for cls, collection_name in collection_table.items():
        if isinstance(element, cls):
            return collection_name
    return None


def deduplicate_model_elements(
    model_elements: collections.abc.Iterable[ModelElement],
    mapping_values: collections.abc.Iterable[ModelElement],
    collection_table: dict[type, str],
) -> tuple[dict[str, frozenset[ModelElement]], dict[int, ModelElement]]:
    """Merge equal top-level model elements and fill the model collections.

    Every element reached from `model_elements` and `mapping_values` through
    any field is walked. An element held in an owning field is owned, every
    other one is top-level. Equal top-level elements are merged into their
    survivor, and every element pointing to a dropped element is rebuilt to
    point to the kept one.

    Args:
        model_elements: The listed top-level model elements.
        mapping_values: The model elements of the layout-model mapping.
        collection_table: The table mapping model element classes to
            collection names.

    Returns:
        The filled collections, and a dict mapping the `id()` of each reached
        element to its kept element.

    Raises:
        ValueError: If an element is held by two owners, or if a top-level
            element has a class that no collection holds.
    """
    reached = []
    reached_ids = set()
    owners = {}
    elements_to_visit = list(model_elements) + list(mapping_values)
    elements_to_visit.reverse()
    while elements_to_visit:
        element = elements_to_visit.pop()
        if id(element) in reached_ids:
            continue
        reached_ids.add(id(element))
        reached.append(element)
        children = get_children(element)
        for child in children:
            owner = owners.get(id(child))
            if owner is None:
                owners[id(child)] = element
            elif owner is not element and owner != element:
                raise ValueError(
                    f"{describe(child)} is held by two owners: "
                    f"{describe(owner)} and {describe(element)}"
                )
        elements_to_visit += reversed(children + get_references(element))
    top_level_elements = [element for element in reached if id(element) not in owners]
    for element in top_level_elements:
        if get_collection_name(element, collection_table) is None:
            raise ValueError(
                f"{describe(element)} is not held by any element, and no model "
                "collection holds elements of its class"
            )
    survivors = get_survivors(top_level_elements)
    rebuilt_elements = {}
    kept_elements = {}

    def rebuild(element: ModelElement) -> ModelElement:
        rebuilt_element = rebuilt_elements.get(id(element))
        if rebuilt_element is None:
            rebuilt_element = rebuild_element(element, rebuild, get_kept_element)
            rebuilt_elements[id(element)] = rebuilt_element
        return rebuilt_element

    def get_kept_element(element: ModelElement) -> ModelElement:
        kept_element = kept_elements.get(id(element))
        if kept_element is None:
            root = element
            while id(root) in owners:
                root = owners[id(root)]
            kept_elements.update(match_descendants(root, rebuild(survivors[root])))
            kept_element = kept_elements[id(element)]
        return kept_element

    collection_elements = {
        collection_name: set() for collection_name in collection_table.values()
    }
    for element in top_level_elements:
        collection_name = get_collection_name(element, collection_table)
        collection_elements[collection_name].add(get_kept_element(element))
    return (
        {
            collection_name: frozenset(collection)
            for collection_name, collection in collection_elements.items()
        },
        kept_elements,
    )


def get_arcs_by_source(
    layout_elements: collections.abc.Iterable[LayoutElement],
) -> dict[int, list[Arc]]:
    """Group the arcs among layout elements and their descendants by source.

    Args:
        layout_elements: The top-level layout elements.

    Returns:
        A dict mapping the `id()` of each arc source to its arcs.
    """
    arcs_by_source = collections.defaultdict(list)
    for layout_element in layout_elements:
        for descendant in get_descendants(layout_element):
            if isinstance(descendant, Arc) and descendant.source is not None:
                arcs_by_source[id(descendant.source)].append(descendant)
    return arcs_by_source


def check_layout_element_identities(
    layout_elements: collections.abc.Iterable[LayoutElement],
    layout_element_to_model_element: dict[LayoutElement, ModelElement],
) -> None:
    """Check that mapping keys and arc ends are objects of the layout.

    Args:
        layout_elements: The top-level layout elements.
        layout_element_to_model_element: The layout-model mapping.

    Raises:
        ValueError: If a mapping key or an arc end is not an element of the
            layout (a top-level layout element or one of its descendants).
    """
    descendants = [
        descendant
        for layout_element in layout_elements
        for descendant in get_descendants(layout_element)
    ]
    descendant_ids = {id(descendant) for descendant in descendants}
    hint = (
        "; mapping keys and arc ends must be the objects of the layout itself, "
        "not equal copies (when a layout element is rebuilt, also rebuild the "
        "arcs that point to it)"
    )
    for layout_element in layout_element_to_model_element:
        if id(layout_element) not in descendant_ids:
            raise ValueError(
                f"mapping key {describe(layout_element)} is not an element of "
                f"the layout{hint}"
            )
    for descendant in descendants:
        if isinstance(descendant, Arc):
            for end in [descendant.source, descendant.target]:
                if end is not None and id(end) not in descendant_ids:
                    raise ValueError(
                        f"end {describe(end)} of arc {describe(descendant)} is "
                        f"not an element of the layout{hint}"
                    )


def check_arc_child(
    arc: Arc,
    child_classes: tuple[type, ...],
    model_element: ModelElement,
    layout_element_to_model_element: dict[LayoutElement, ModelElement],
) -> None:
    """Check the model element an arc of a cluster maps to.

    Args:
        arc: The arc, whose source is the layout element of the cluster.
        child_classes: The classes the model element of the arc may have.
        model_element: The model element of the cluster.
        layout_element_to_model_element: The layout-model mapping.

    Raises:
        ValueError: If the arc maps to a child that `model_element` does not
            hold, to a child of another class, or to a child whose referred
            element is not drawn by the target of the arc.
    """
    child = layout_element_to_model_element.get(arc)
    if child is None:
        return
    if not any(child is held_child for held_child in get_children(model_element)):
        raise ValueError(
            f"arc {describe(arc)} maps to {describe(child)}, which "
            f"{describe(model_element)} does not hold"
        )
    if not isinstance(child, child_classes):
        raise ValueError(
            f"arc {describe(arc)} maps to {describe(child)}, but may only map to "
            f"{', '.join(cls.__name__ for cls in child_classes)}"
        )
    if layout_element_to_model_element.get(arc.target) is not child.referred_element:
        raise ValueError(
            f"arc {describe(arc)} maps to {describe(child)}, which refers to "
            f"{describe(child.referred_element)}, but the target of the arc "
            "does not draw it"
        )


def make_layout_model_mapping(
    layout_elements: collections.abc.Iterable[LayoutElement],
    layout_element_to_model_element: dict[LayoutElement, ModelElement],
    cluster_rules: collections.abc.Iterable[ClusterRule],
) -> LayoutModelMapping:
    """Compute the layout-model mapping, frozenset keys included.

    Args:
        layout_elements: The top-level layout elements.
        layout_element_to_model_element: The layout-model mapping with single
            layout elements as keys only, whose values are the kept model
            elements.
        cluster_rules: The rules to compute the frozenset keys, in order.

    Returns:
        The layout-model mapping.

    Raises:
        ValueError: If an arc of a cluster maps to a wrong child, or if an arc
            end does not draw the source or target of its model element.
        NotImplementedError: If a model element of a rule that is not
            implemented is mapped.
    """
    cluster_rules = list(cluster_rules)
    cluster_classes = tuple(
        cls
        for cluster_rule in cluster_rules
        for cls in cluster_rule.model_element_classes
    )
    arcs_by_source = get_arcs_by_source(layout_elements)
    layout_model_mapping = LayoutModelMappingBuilder()

    def get_cluster(layout_element: LayoutElement) -> frozenset[LayoutElement]:
        key = layout_model_mapping.representative_to_key.get(layout_element)
        if key is not None:
            return key
        return frozenset([layout_element])

    for layout_element, model_element in layout_element_to_model_element.items():
        if not isinstance(model_element, cluster_classes):
            layout_model_mapping.add_mapping(layout_element, model_element)
    for cluster_rule in cluster_rules:
        for layout_element, model_element in layout_element_to_model_element.items():
            if not isinstance(model_element, cluster_rule.model_element_classes):
                continue
            if cluster_rule.not_implemented:
                raise NotImplementedError(
                    f"{describe(model_element)} cannot be mapped yet"
                )
            arc_classes = dict(cluster_rule.arc_classes)
            if getattr(model_element, "reversible", False):
                for arc_class, child_classes in cluster_rule.reversible_arc_classes:
                    arc_classes[arc_class] = arc_classes[arc_class] + child_classes
            arcs = [
                arc
                for arc in arcs_by_source.get(id(layout_element), [])
                if isinstance(arc, tuple(arc_classes))
            ]
            if not arcs and cluster_rule.single_key_without_arcs:
                layout_model_mapping.add_mapping(layout_element, model_element)
                continue
            key = {layout_element}
            for arc in arcs:
                child_classes = next(
                    child_classes
                    for arc_class, child_classes in arc_classes.items()
                    if isinstance(arc, arc_class)
                )
                check_arc_child(
                    arc, child_classes, model_element, layout_element_to_model_element
                )
                key.add(arc)
                if arc.target is not None:
                    if cluster_rule.cluster_arc_targets:
                        key |= get_cluster(arc.target)
                    else:
                        key.add(arc.target)
            if cluster_rule.with_ends:
                for end_name in ["source", "target"]:
                    end = getattr(layout_element, end_name)
                    if layout_element_to_model_element.get(end) is not getattr(
                        model_element, end_name
                    ):
                        raise ValueError(
                            f"the {end_name} of arc {describe(layout_element)} "
                            f"does not draw the {end_name} of "
                            f"{describe(model_element)}"
                        )
                    key |= get_cluster(end)
            layout_model_mapping.add_mapping(
                frozenset(key), model_element, representative=layout_element
            )
    return layout_model_mapping.build()


def make_map_from_map_elements(
    layout_elements: collections.abc.Iterable[LayoutElement],
    layout_element_to_model_element: dict[LayoutElement, ModelElement],
    model_elements: collections.abc.Iterable[ModelElement],
    map_class: type,
    model_class: type,
    layout_class: type,
    collection_table: dict[type, str],
    cluster_rules: collections.abc.Iterable[ClusterRule],
) -> Map:
    """Build a map from its layout elements, model elements and a simple mapping.

    Args:
        layout_elements: The top-level layout elements, in drawing order.
        layout_element_to_model_element: The layout-model mapping, with single
            layout elements as keys only.
        model_elements: Top-level model elements, needed only for those with
            no layout element.
        map_class: The class of the map.
        model_class: The class of the model.
        layout_class: The class of the layout.
        collection_table: The table mapping model element classes to
            collection names of `model_class`.
        cluster_rules: The rules to compute the frozenset keys, in order.

    Returns:
        The map. Its model is `None` if no model element is given, its layout
        is `None` if no layout element is given, and its mapping is `None` if
        either is `None`.

    Raises:
        ValueError: If the given elements are inconsistent.
        NotImplementedError: If a model element of a rule that is not
            implemented is mapped.
    """
    layout_elements = tuple(layout_elements)
    check_layout_element_identities(layout_elements, layout_element_to_model_element)
    collection_elements, kept_elements = deduplicate_model_elements(
        model_elements, layout_element_to_model_element.values(), collection_table
    )
    layout_element_to_model_element = {
        layout_element: kept_elements[id(model_element)]
        for layout_element, model_element in layout_element_to_model_element.items()
    }
    if kept_elements:
        model = model_class(**collection_elements)
    else:
        model = None
    if layout_elements:
        bbox = fit(layout_elements)
        layout = layout_class(
            layout_elements=layout_elements,
            position=bbox.position,
            width=bbox.width,
            height=bbox.height,
        )
    else:
        layout = None
    if model is not None and layout is not None:
        layout_model_mapping = make_layout_model_mapping(
            layout_elements, layout_element_to_model_element, cluster_rules
        )
    else:
        layout_model_mapping = None
    return map_class(
        model=model, layout=layout, layout_model_mapping=layout_model_mapping
    )


def get_map_elements_from_map(map_: Map) -> MapElements:
    """Take a map apart into its layout elements, model elements and a simple mapping.

    Args:
        map_: The map.

    Returns:
        The top-level layout elements, the layout-model mapping with single
        layout elements as keys only (each representative of a frozenset key
        maps to the model element of the key), and the top-level model
        elements.
    """
    if map_.layout is not None:
        layout_elements = tuple(map_.layout.layout_elements)
    else:
        layout_elements = ()
    layout_element_to_model_element = {}
    if map_.layout_model_mapping is not None:
        representative_to_key = map_.layout_model_mapping.representative_to_key
        for key, model_element in map_.layout_model_mapping.items():
            if isinstance(key, frozenset):
                for representative in representative_to_key.inverse.get(key, []):
                    layout_element_to_model_element[representative] = model_element
            else:
                layout_element_to_model_element[key] = model_element
    if map_.model is not None:
        model_elements = tuple(
            element
            for field in dataclasses.fields(map_.model)
            if isinstance(getattr(map_.model, field.name), frozenset)
            for element in getattr(map_.model, field.name)
            if isinstance(element, ModelElement)
        )
    else:
        model_elements = ()
    return layout_elements, layout_element_to_model_element, model_elements


def merge_map_elements(parts: collections.abc.Iterable[MapElements]) -> MapElements:
    """Combine several sets of map elements into one.

    Of equal top-level layout elements, the survivor is kept at the place of
    the first one, and every arc and mapping key is made to point to the kept
    elements. Model elements are concatenated.

    Args:
        parts: The sets of map elements, each as returned by
            `get_map_elements_from_map`.

    Returns:
        The combined layout elements, layout-model mapping and model elements.

    Raises:
        ValueError: If equal layout elements map to model elements that are
            not equal.
    """
    parts = list(parts)
    layout_elements = [layout_element for part in parts for layout_element in part[0]]
    survivors = get_survivors(layout_elements)
    replacements = {}
    for layout_element in layout_elements:
        survivor = survivors[layout_element]
        if layout_element is not survivor:
            replacements.update(match_descendants(layout_element, survivor))
    rebuilt_elements = {}

    def rebuild(layout_element: LayoutElement) -> LayoutElement:
        rebuilt_element = rebuilt_elements.get(id(layout_element))
        if rebuilt_element is None:
            rebuilt_element = rebuild_element(layout_element, rebuild, get_new_element)
            rebuilt_elements[id(layout_element)] = rebuilt_element
        return rebuilt_element

    def get_new_element(layout_element: LayoutElement) -> LayoutElement:
        return rebuild(replacements.get(id(layout_element), layout_element))

    new_layout_elements = []
    added_ids = set()
    for layout_element in layout_elements:
        survivor = survivors[layout_element]
        if id(survivor) not in added_ids:
            added_ids.add(id(survivor))
            new_layout_elements.append(rebuild(survivor))
    layout_element_to_model_element = {}
    for part in parts:
        for layout_element, model_element in part[1].items():
            new_layout_element = get_new_element(layout_element)
            existing_model_element = layout_element_to_model_element.get(
                new_layout_element
            )
            if existing_model_element is None:
                layout_element_to_model_element[new_layout_element] = model_element
            elif existing_model_element != model_element:
                raise ValueError(
                    f"equal layout elements {describe(new_layout_element)} map to "
                    "model elements that are not equal: "
                    f"{describe(existing_model_element)} and {describe(model_element)}"
                )
    model_elements = tuple(model_element for part in parts for model_element in part[2])
    return (
        tuple(new_layout_elements),
        layout_element_to_model_element,
        model_elements,
    )


def merge_maps(
    maps: collections.abc.Iterable[Map],
    map_class: type,
    model_class: type,
    layout_class: type,
    collection_table: dict[type, str],
    cluster_rules: collections.abc.Iterable[ClusterRule],
) -> Map:
    """Merge maps into one map.

    Maps are not moved: they overlap in their own coordinates.

    Args:
        maps: The maps to merge.
        map_class: The class of the merged map.
        model_class: The class of the merged model.
        layout_class: The class of the merged layout.
        collection_table: The table mapping model element classes to
            collection names of `model_class`.
        cluster_rules: The rules to compute the frozenset keys, in order.

    Returns:
        The merged map.
    """
    layout_elements, layout_element_to_model_element, model_elements = (
        merge_map_elements(get_map_elements_from_map(map_) for map_ in maps)
    )
    return make_map_from_map_elements(
        layout_elements,
        layout_element_to_model_element,
        model_elements,
        map_class,
        model_class,
        layout_class,
        collection_table,
        cluster_rules,
    )
