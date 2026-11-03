"""Internal utilities for map readers.

These functions record the elements read, merge equal elements at the end
of reading, and build the id mappings.  They are not part of the public API.
"""

import collections
import dataclasses
import math
import os
import typing

import frozendict
import lxml.etree

from momapy.core._assembling import check_lost_references
from momapy.core._assembling import get_matching_descendant_map_elements
from momapy.core._assembling import get_new_top_level_map_elements
from momapy.core._assembling import make_model_from_merged_model_elements
from momapy.core._assembling import merge_equal_map_elements
from momapy.core.elements import LayoutElement
from momapy.core.elements import MapElement
from momapy.core.elements import ModelElement
from momapy.core.layout import Layout
from momapy.core.map import Map
from momapy.core.model import Model
from momapy.geometry import Point
from momapy.utils import FrozenIdentityMultiDict
from momapy.utils import FrozenSurjectionDict
from momapy.utils import IdentityMultiDict
from momapy.utils import get_element_from_collection


# Everything here (context dataclasses, reading helpers) is internal and
# may change without a deprecation cycle; nothing is part of the public API.
__all__ = []


@dataclasses.dataclass
class WritingContext:
    """Base writing context shared by all format-specific writers.

    Holds the map being written and the ancillary state (annotations,
    notes, source-id lookups, feature flags) needed during XML
    construction.  Format-specific writers subclass this and add
    their own fields.
    """

    map_: typing.Any = dataclasses.field(
        metadata={"description": "The map being written."}
    )
    element_to_annotations: dict = dataclasses.field(
        metadata={"description": "Mapping from map elements to their annotations."}
    )
    element_to_notes: dict = dataclasses.field(
        metadata={"description": "Mapping from map elements to their notes."}
    )
    source_id_to_model_element: FrozenIdentityMultiDict | None
    """N-to-m source id -> model element mapping; one source id may name
    several model elements (e.g. CellDesigner active/inactive species).
    A ``Mapping[str, frozenset[ModelElement]]``: use
    ``source_id_to_model_element.get(id_, frozenset())`` for the values and
    ``.inverse`` to recover the source ids of a model element."""
    source_id_to_layout_element: FrozenSurjectionDict | None
    """1-to-1 source id -> layout element mapping.  Layout elements are
    not subject to the same n-to-m driver as model elements (every
    layout element has at most one source id)."""
    source_id_to_annotations: dict | None
    """Per-source-id annotations carried over from the `ReaderResult`,
    keyed by the raw source id.  Parallel to ``element_to_annotations``
    but preserves per-source granularity across reader deduplication."""
    source_id_to_notes: dict | None
    """Per-source-id notes carried over from the `ReaderResult`; see
    ``source_id_to_annotations``."""
    with_annotations: bool = dataclasses.field(
        metadata={"description": "Whether to write annotations."}
    )
    with_notes: bool = dataclasses.field(
        metadata={"description": "Whether to write notes."}
    )
    element_to_xml_id: dict = dataclasses.field(default_factory=dict)
    """Memo of the unique, format-valid XML id assigned to each element,
    keyed by ``id(element)``.  Seeded with grammar-valid source ids in
    the phase-1 reservation pass (``reserve_source_xml_ids``) and
    filled lazily for the rest in each format's ``get_xml_id``.
    Identity-keyed for the same reason the format memos are: model
    elements use ``compare=False`` on ``id_``, so two content-equal
    objects must stay distinct."""
    used_xml_ids: set = dataclasses.field(default_factory=set)
    """Set of XML id strings already emitted in this document.  Drives
    ``make_unique_xml_id``'s collision suffixing.  Document-global:
    stricter than SBML's per-namespace SId rule, but always valid."""
    candidate_to_xml_id: dict = dataclasses.field(default_factory=dict)
    """Maps a raw candidate id (an element's ``id_``, or a source id) to
    the emitted XML id it resolved to.  Elements that share a raw
    candidate are the same logical reference and must emit the same id —
    e.g. CellDesigner registers several distinct objects for one included
    species, all carrying the same ``id_``.  Only *distinct* candidates
    that happen to project to the same grammar-valid string get suffixed
    apart by ``make_unique_xml_id``; a repeated candidate returns its
    earlier result, preserving the pre-projection writers' behaviour of
    emitting ``id_`` verbatim."""


def choose_compartment_layout(
    compartment_layouts: list[LayoutElement], point: Point
) -> LayoutElement:
    """Return the compartment layout a point belongs to.

    With one layout, return it. Otherwise return the smallest layout whose
    bounding box contains the point, or else the nearest one.

    Args:
        compartment_layouts: The layouts of one compartment (not empty).
        point: The point, usually the center of a species layout.

    Returns:
        The chosen compartment layout.
    """
    if len(compartment_layouts) == 1:
        return compartment_layouts[0]
    best_compartment_layout = None
    best_key = None
    for compartment_layout in compartment_layouts:
        bbox = compartment_layout.bbox()
        north_west = bbox.north_west()
        south_east = bbox.south_east()
        distance_x = max(north_west.x - point.x, 0, point.x - south_east.x)
        distance_y = max(north_west.y - point.y, 0, point.y - south_east.y)
        key = (math.hypot(distance_x, distance_y), bbox.width * bbox.height)
        if best_key is None or key < best_key:
            best_compartment_layout = compartment_layout
            best_key = key
    return best_compartment_layout


def make_unique_xml_id(candidate: str, used_xml_ids: set) -> str:
    """Return a unique id derived from ``candidate`` and record it.

    Returns ``candidate`` if it is free, else ``candidate_1`` /
    ``candidate_2`` / ... until an unused string is found.  The result is
    added to ``used_xml_ids``.

    This is internal to each format's ``get_xml_id``.  Never call it
    from an emission site with a raw candidate string: an element whose
    id was already reserved in the phase-1 pass (e.g. a metaid) is in
    ``used_xml_ids``, so a second call would bump it to ``_1``.  Emission
    must go through ``get_xml_id``, which checks the element memo first.

    Args:
        candidate: The desired id (already projected to the format
            grammar by the caller).
        used_xml_ids: The set of ids already taken; mutated in place.

    Returns:
        A unique id string not previously in ``used_xml_ids``.
    """
    result = candidate
    counter = 1
    while result in used_xml_ids:
        result = f"{candidate}_{counter}"
        counter += 1
    used_xml_ids.add(result)
    return result


@dataclasses.dataclass
class ReadingContext:
    """Base reading context shared by all format-specific readers.

    Holds the XML id tables, the model elements and pairs read, and the
    annotations and notes.  Format-specific readers subclass this and add
    their own fields.
    """

    xml_root: typing.Any = dataclasses.field(
        default=None,
        metadata={"description": "The root XML element being read."},
    )
    map_key: str | None = dataclasses.field(
        default=None,
        metadata={"description": "Classification key for the map being read."},
    )
    model: typing.Any = dataclasses.field(
        default=None,
        metadata={"description": "The model being built, or None."},
    )
    layout: typing.Any = dataclasses.field(
        default=None,
        metadata={"description": "The layout being built, or None."},
    )
    xml_id_to_model_element: IdentityMultiDict = dataclasses.field(
        default_factory=IdentityMultiDict
    )
    xml_id_to_layout_element: dict[str, MapElement] = dataclasses.field(
        default_factory=dict
    )
    xml_id_to_xml_element: dict = dataclasses.field(default_factory=dict)
    element_to_annotations: dict = dataclasses.field(default_factory=dict)
    element_to_notes: dict = dataclasses.field(default_factory=dict)
    source_id_to_annotations: dict[str, set] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(set)
    )
    """Per-source-id annotations, keyed by the raw XML id of the source
    element.  Parallel to ``element_to_annotations`` but preserves
    per-source granularity even when reader deduplication collapses
    several source elements into a single model element."""
    source_id_to_notes: dict[str, set] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(set)
    )
    """Per-source-id notes, keyed by the raw XML id of the source
    element.  Parallel to ``element_to_notes``; see
    ``source_id_to_annotations``."""
    with_annotations: bool = dataclasses.field(
        default=True,
        metadata={"description": "Whether to read annotations."},
    )
    with_notes: bool = dataclasses.field(
        default=True,
        metadata={"description": "Whether to read notes."},
    )
    layout_model_pairs: list[tuple[LayoutElement, ModelElement]] = dataclasses.field(
        default_factory=list
    )
    """The `(layout_element, model_element)` pairs read, where
    `layout_element` draws `model_element`; the layout-model mapping is
    computed from them at the end of reading."""
    top_level_model_elements: list[ModelElement] = dataclasses.field(
        default_factory=list
    )
    """Top-level model elements in reading order, before merging."""
    dropped_and_kept_child_model_elements: list[tuple[ModelElement, ModelElement]] = (
        dataclasses.field(default_factory=list)
    )
    """The `(dropped_child, kept_child)` pairs of `add_child_model_element`,
    checked for lost references by `merge_read_model_elements`."""


def get_xml_root_element(
    file_path: str | os.PathLike,
) -> lxml.etree._Element | None:
    """Return the root element of an XML file, parsing only its start.

    Used by the readers' `check_file` to detect a format from the root
    element. Only the beginning of the file is parsed, entities are not
    resolved and nothing is fetched from the network.

    Args:
        file_path: Path of the file to inspect.

    Returns:
        The root element (with its tag and namespace map, but no children),
        or `None` if the file cannot be read or does not start as XML.
    """
    try:
        with open(file_path, "rb") as file:
            for _, element in lxml.etree.iterparse(
                file, events=("start",), resolve_entities=False, no_network=True
            ):
                return element
    except (OSError, lxml.etree.LxmlError):
        return None
    return None


def build_id_to_element(obj: MapElement) -> frozendict.frozendict:
    """Build the ``id_to_element`` mapping from a frozen object.

    Walks the model and/or layout descendants of a `Map`, `Model`, or
    `Layout` and maps every element ``id_`` to the element. Requires no
    reading context, so it is reusable both by native readers (through
    `build_id_mappings`) and by the pickle reader, which has no context.

    Args:
        obj: The top-level frozen object — a `Map`, `Model`, or `Layout`.

    Returns:
        A frozen mapping of every element ``id_`` to its element.
    """
    if isinstance(obj, Map):
        model = obj.model
        layout = obj.layout
    elif isinstance(obj, Model):
        model = obj
        layout = None
    elif isinstance(obj, Layout):
        model = None
        layout = obj
    else:
        model = None
        layout = None

    id_to_element: dict[str, MapElement] = {}
    if model is not None:
        id_to_element[model.id_] = model
        for element in model.descendants():
            id_to_element[element.id_] = element
    if layout is not None:
        id_to_element[layout.id_] = layout
        for layout_element in layout.descendants():
            id_to_element[layout_element.id_] = layout_element
    id_to_element[obj.id_] = obj
    return frozendict.frozendict(id_to_element)


def build_id_mappings(
    reading_context: "ReadingContext",
    obj: MapElement,
    real_model_source_ids: set[str] | None = None,
    real_layout_source_ids: set[str] | None = None,
) -> tuple[
    frozendict.frozendict,
    FrozenIdentityMultiDict | None,
    FrozenSurjectionDict | None,
]:
    """Build the three ID mapping dicts for a ReaderResult.

    Args:
        reading_context: The reading context holding
            ``xml_id_to_model_element`` and ``xml_id_to_layout_element``.
        obj: The top-level frozen object returned by the reader — a
            `Map`, `Model`, or `Layout`. When it is a `Map`, its
            ``model`` and ``layout`` are used; otherwise `obj` is
            treated as the model or layout itself.
        real_model_source_ids: If given, only source IDs in this set
            are included in ``source_id_to_model_element``. Lets
            readers exclude synthetic or layout-only keys (e.g.
            CellDesigner alias ids) that were registered in the
            internal model dict for cross-ref resolution but do not
            name a model entity in the source file. When None, all
            IDs from the reading context's model dict are treated as
            real.
        real_layout_source_ids: Same, for
            ``source_id_to_layout_element``.

    Returns:
        A tuple of ``(id_to_element, source_id_to_model_element,
        source_id_to_layout_element)``.
    """
    if isinstance(obj, Map):
        model = obj.model
        layout = obj.layout
    elif isinstance(obj, Model):
        model = obj
        layout = None
    elif isinstance(obj, Layout):
        model = None
        layout = obj
    else:
        model = None
        layout = None

    id_to_element = build_id_to_element(obj)

    if model is not None:
        source_id_to_model_element_set: dict[str, set[ModelElement]] = {}
        for (
            source_id,
            bucket,
        ) in reading_context.xml_id_to_model_element.items():
            if (
                real_model_source_ids is not None
                and source_id not in real_model_source_ids
            ):
                continue
            for registered_element in bucket:
                frozen_element = id_to_element.get(registered_element.id_)
                if frozen_element is not None:
                    source_id_to_model_element_set.setdefault(source_id, set()).add(
                        frozen_element
                    )
        source_id_to_model_element = FrozenIdentityMultiDict(
            source_id_to_model_element_set
        )
    else:
        source_id_to_model_element = None

    if layout is not None:
        source_id_to_layout_element: dict[str, LayoutElement] = {}
        for (
            source_id,
            registered_element,
        ) in reading_context.xml_id_to_layout_element.items():
            if (
                real_layout_source_ids is not None
                and source_id not in real_layout_source_ids
            ):
                continue
            frozen_element = id_to_element.get(registered_element.id_)
            if frozen_element is not None:
                source_id_to_layout_element[source_id] = frozen_element
        source_id_to_layout_element = FrozenSurjectionDict(source_id_to_layout_element)
    else:
        source_id_to_layout_element = None

    return (
        id_to_element,
        source_id_to_model_element,
        source_id_to_layout_element,
    )


def add_top_level_model_element(
    reading_context: ReadingContext,
    model_element: ModelElement,
    xml_id: str,
) -> ModelElement:
    """Record a top-level model element read from an XML element.

    Equal top-level elements are merged at the end of reading, by
    `merge_read_model_elements`.

    Args:
        reading_context: The reading context.
        model_element: The top-level model element.
        xml_id: The id of the XML element it is read from.

    Returns:
        The model element.
    """
    reading_context.top_level_model_elements.append(model_element)
    reading_context.xml_id_to_model_element.add(xml_id, model_element)
    return model_element


def add_child_model_element(
    reading_context: ReadingContext,
    child: ModelElement,
    collection: set,
) -> ModelElement:
    """Add a child model element to a collection of its owner.

    If the collection already holds an equal child, it keeps the one with the
    smallest `id_` (the held one on equal ids). The dropped one and each of
    its descendants are replaced by their matching descendants in the kept
    one, in the values of `xml_id_to_model_element` and in the model elements
    of `layout_model_pairs`.

    Args:
        reading_context: The reading context.
        child: The child to add.
        collection: The collection of the owner (a set of a builder).

    Returns:
        The child the collection holds.
    """
    held_child = get_element_from_collection(child, collection)
    if held_child is child:
        return child
    if held_child is None:
        collection.add(child)
        return child
    if child.id_ < held_child.id_:
        collection.remove(held_child)
        collection.add(child)
        kept_child, dropped_child = child, held_child
    else:
        kept_child, dropped_child = held_child, child
    descendant_id_to_matching_descendant = get_matching_descendant_map_elements(
        dropped_child, kept_child
    )
    for descendant in [dropped_child] + dropped_child.descendants():
        reading_context.xml_id_to_model_element.replace_value(
            descendant, descendant_id_to_matching_descendant[id(descendant)]
        )
    reading_context.layout_model_pairs[:] = [
        (
            layout_element,
            descendant_id_to_matching_descendant.get(id(model_element), model_element),
        )
        for layout_element, model_element in reading_context.layout_model_pairs
    ]
    reading_context.dropped_and_kept_child_model_elements.append(
        (dropped_child, kept_child)
    )
    return kept_child


def merge_read_model_elements(reading_context: ReadingContext) -> None:
    """Merge the model elements read and put them into the model builder.

    Equal top-level model elements are merged (see
    `momapy.core._assembling.merge_equal_map_elements`), and the elements of
    `top_level_model_elements`, the model elements of `layout_model_pairs` and
    the values of `xml_id_to_model_element` are replaced by their new
    elements.

    Args:
        reading_context: The reading context, whose model is not `None`.

    Raises:
        ValueError: If a model element of a pair or of
            `xml_id_to_model_element` is not under the top-level model
            elements, or if merging would lose a reference.
    """
    model_element_id_to_new_model_element = merge_equal_map_elements(
        reading_context.top_level_model_elements
    )

    def get_new_model_element(model_element: ModelElement) -> ModelElement:
        new_model_element = model_element_id_to_new_model_element.get(id(model_element))
        if new_model_element is None:
            raise ValueError(
                f"{type(model_element).__name__} {model_element.id_!r} is not "
                "a top-level model element read or one of their descendants"
            )
        return new_model_element

    for (
        dropped_child,
        kept_child,
    ) in reading_context.dropped_and_kept_child_model_elements:
        check_lost_references(dropped_child, kept_child, get_new_model_element)
    reading_context.top_level_model_elements[:] = get_new_top_level_map_elements(
        reading_context.top_level_model_elements,
        model_element_id_to_new_model_element,
    )
    reading_context.layout_model_pairs[:] = [
        (layout_element, get_new_model_element(model_element))
        for layout_element, model_element in reading_context.layout_model_pairs
    ]
    model_elements = {
        id(model_element): model_element
        for bucket in reading_context.xml_id_to_model_element.values()
        for model_element in bucket
    }
    for model_element in model_elements.values():
        new_model_element = get_new_model_element(model_element)
        if new_model_element is not model_element:
            reading_context.xml_id_to_model_element.replace_value(
                model_element, new_model_element
            )
    model = make_model_from_merged_model_elements(
        reading_context.model._cls_to_build,
        reading_context.top_level_model_elements,
    )
    for field in dataclasses.fields(model):
        field_value = getattr(model, field.name)
        if isinstance(field_value, frozenset):
            getattr(reading_context.model, field.name).update(field_value)
