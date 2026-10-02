"""Pure helper functions for SBGN-ML XML element construction."""

import re
import typing

import lxml.etree

from momapy.core.layout import DoubleHeadedArc
from momapy.core.layout import Node
from momapy.core.layout import SingleHeadedArc
from momapy.io._utils import make_unique_xml_id
from momapy.sbgn.pd import CardinalityLayout
from momapy.sbgn.pd import ConsumptionLayout
from momapy.sbgn.pd import EmptySetLayout
from momapy.sbgn.pd import EntityPool
from momapy.sbgn.pd import LogicArcLayout as PDLogicArcLayout
from momapy.sbgn.pd import Phenotype
from momapy.sbgn.pd import ProductionLayout
from momapy.sbgn.pd import SBGNPDModel
from momapy.sbgn.pd import StateVariableLayout
from momapy.sbgn.pd import StoichiometricProcess
from momapy.sbgn.af import Activity
from momapy.sbgn.af import LogicArcLayout as AFLogicArcLayout
from momapy.sbgn.io.sbgnml._writing_classification import CLASS_TO_SBGNML_CLASS
from momapy.sbgn.io.sbgnml._writing_classification import (
    CLASS_TO_SBGNML_ENTITY_NAME,
)
from momapy.sbgn.io.sbgnml._writing_classification import (
    DIRECTION_TO_SBGNML_ORIENTATION,
)
from momapy.sbgn.io.sbgnml._writing_classification import REVERSED_ARC_TYPES
from momapy.sbml.io.sbml._qualifiers import (
    QUALIFIER_MEMBER_TO_QUALIFIER_ATTRIBUTE,
)

if typing.TYPE_CHECKING:
    from momapy.core.elements import LayoutElement
    from momapy.core.elements import ModelElement
    from momapy.core.layout import TextLayout
    from momapy.geometry import Point
    from momapy.io._utils import WritingContext

NSMAP = {
    None: "http://sbgn.org/libsbgn/0.3",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "bqmodel": "http://biomodels.net/model-qualifiers/",
    "bqbiol": "http://biomodels.net/biology-qualifiers/",
}

_NCNAME_INVALID_CHAR_RE = re.compile(r"[^A-Za-z0-9_.\-]")
_NCNAME_INVALID_START_RE = re.compile(r"^[^A-Za-z_]")


def make_lxml_element(
    tag: str,
    namespace: str | None = None,
    attributes: dict | None = None,
    text: str | None = None,
    nsmap: dict | None = None,
) -> lxml.etree._Element:
    if namespace is not None:
        lxml_tag = f"{{{namespace}}}{tag}"
    else:
        lxml_tag = tag
    if nsmap is None:
        nsmap = {}
    if attributes is None:
        attributes = {}
    lxml_element = lxml.etree.Element(lxml_tag, nsmap=nsmap, **attributes)
    if text is not None:
        lxml_element.text = text
    return lxml_element


def ensure_ncname(id_str: str | None) -> str:
    """Ensure a string conforms to XML NCName syntax (``xs:ID`` for SBGN-ML).

    NCName starts with a letter or underscore, then allows letters,
    digits, hyphens, underscores, and periods (no colon).  Invalid
    characters are replaced with underscores, and a leading invalid
    character is prefixed with an underscore.  Idempotent on an
    already-valid NCName, so reserved source ids pass through unchanged.

    Args:
        id_str: The raw id string.

    Returns:
        A valid NCName string, or empty string if input is None or empty.
    """
    if not id_str:
        return ""
    result = _NCNAME_INVALID_CHAR_RE.sub("_", id_str)
    if _NCNAME_INVALID_START_RE.match(result):
        result = "_" + result
    return result


def make_sbgnml_bbox_from_node(node: Node) -> lxml.etree._Element:
    attributes = {
        "x": str(node.x - node.width / 2),
        "y": str(node.y - node.height / 2),
        "w": str(node.width),
        "h": str(node.height),
    }
    return make_lxml_element("bbox", attributes=attributes)


def make_sbgnml_bbox_from_text_layout(
    text_layout: "TextLayout",
) -> lxml.etree._Element:
    bbox = text_layout.bbox()
    attributes = {
        "x": str(bbox.x - bbox.width / 2),
        "y": str(bbox.y - bbox.height / 2),
        "w": str(bbox.width),
        "h": str(bbox.height),
    }
    return make_lxml_element("bbox", attributes=attributes)


def make_sbgnml_label(text_layout: "TextLayout") -> lxml.etree._Element:
    attributes = {"text": text_layout.text}
    sbgnml_label = make_lxml_element("label", attributes=attributes)
    sbgnml_bbox = make_sbgnml_bbox_from_text_layout(text_layout)
    sbgnml_label.append(sbgnml_bbox)
    return sbgnml_label


def make_sbgnml_state(text_layout: "TextLayout") -> lxml.etree._Element:
    attributes = {}
    text_split = text_layout.text.split("@")
    if len(text_split) > 1:
        attributes["variable"] = text_split[-1]
    if text_split[0]:
        attributes["value"] = text_split[0]
    return make_lxml_element("state", attributes=attributes)


def make_sbgnml_entity(name: str) -> lxml.etree._Element:
    """Create an ``<entity>`` element naming an AF unit-of-information type.

    Args:
        name: The entity name (e.g. ``"macromolecule"``).

    Returns:
        The lxml ``<entity>`` element.
    """
    return make_lxml_element("entity", attributes={"name": name})


def make_sbgnml_port(point: "Point", port_id: str) -> lxml.etree._Element:
    attributes = {"id": port_id, "x": str(point.x), "y": str(point.y)}
    return make_lxml_element("port", attributes=attributes)


def make_sbgnml_points(points: "list[Point]") -> list[lxml.etree._Element]:
    sbgnml_elements = []
    start_point = points[0]
    sbgnml_elements.append(
        make_lxml_element(
            "start", attributes={"x": str(start_point.x), "y": str(start_point.y)}
        )
    )
    for point in points[1:-1]:
        sbgnml_elements.append(
            make_lxml_element("next", attributes={"x": str(point.x), "y": str(point.y)})
        )
    end_point = points[-1]
    sbgnml_elements.append(
        make_lxml_element(
            "end", attributes={"x": str(end_point.x), "y": str(end_point.y)}
        )
    )
    return sbgnml_elements


def make_sbgnml_annotation(
    annotations: typing.Any,
    sbgnml_id: str,
) -> lxml.etree._Element:
    sbgnml_annotation = make_lxml_element("annotation")
    sbgnml_rdf = make_lxml_element(tag="RDF", namespace=NSMAP["rdf"], nsmap=NSMAP)
    sbgnml_annotation.append(sbgnml_rdf)
    sbgnml_description = make_lxml_element(
        tag="Description",
        namespace=NSMAP["rdf"],
        attributes={f"{{{NSMAP['rdf']}}}about": f"#{sbgnml_id}"},
    )
    sbgnml_rdf.append(sbgnml_description)
    for annotation in annotations:
        namespace, tag = QUALIFIER_MEMBER_TO_QUALIFIER_ATTRIBUTE[annotation.qualifier]
        sbgnml_bq = make_lxml_element(tag=tag, namespace=namespace)
        sbgnml_description.append(sbgnml_bq)
        sbgnml_bag = make_lxml_element(tag="Bag", namespace=NSMAP["rdf"])
        sbgnml_bq.append(sbgnml_bag)
        for resource in annotation.resources:
            sbgnml_li = make_lxml_element(
                tag="li",
                namespace=NSMAP["rdf"],
                attributes={f"{{{NSMAP['rdf']}}}resource": resource},
            )
            sbgnml_bag.append(sbgnml_li)
    return sbgnml_annotation


def add_annotations_and_notes(
    writing_context: "WritingContext",
    sbgnml_element: lxml.etree._Element,
    model_element: "ModelElement",
) -> None:
    """Append annotation and notes XML to an SBGN-ML element if present."""
    if writing_context.with_annotations and writing_context.element_to_annotations:
        element_annotations = writing_context.element_to_annotations.get(model_element)
        if element_annotations:
            sbgnml_annot = make_sbgnml_annotation(
                element_annotations,
                sbgnml_id=sbgnml_element.get("id"),
            )
            sbgnml_extension = make_lxml_element("extension")
            sbgnml_extension.append(sbgnml_annot)
            sbgnml_element.append(sbgnml_extension)
    if writing_context.with_notes and writing_context.element_to_notes:
        element_notes = writing_context.element_to_notes.get(model_element)
        if element_notes:
            for note in element_notes:
                sbgnml_notes = make_lxml_element(tag="notes")
                notes_root = lxml.etree.fromstring(note)
                sbgnml_notes.append(notes_root)
                sbgnml_element.append(sbgnml_notes)


# ---------------------------------------------------------------------------
# Id projection
# ---------------------------------------------------------------------------


def reserve_source_xml_ids(writing_context: "WritingContext") -> None:
    """Reserve grammar-valid source ids before any projection (phase 1).

    For every layout element that carries a source id, reserve that id
    verbatim in ``element_to_xml_id`` (and mark it used) when it is
    already a valid NCName.  Reserving up front, *without* deduplication,
    preserves round-trip fidelity and lets several elements that share a
    source id keep sharing the emitted id.  Must run before any id is
    emitted.

    Args:
        writing_context: The current writing context.
    """
    source_map = writing_context.source_id_to_layout_element
    if source_map is None:
        return
    element_id_to_source_ids = {}
    for source_id, layout_element in source_map.items():
        if not source_id:
            continue
        element_id_to_source_ids.setdefault(id(layout_element), set()).add(source_id)
    for element_id, source_ids in element_id_to_source_ids.items():
        chosen = min(source_ids, key=lambda source_id: (len(source_id), source_id))
        if ensure_ncname(chosen) == chosen:
            writing_context.element_to_xml_id[element_id] = chosen
            writing_context.used_xml_ids.add(chosen)


def get_xml_id(writing_context: "WritingContext", element: typing.Any) -> str:
    """Return the unique, valid NCName id to emit for ``element`` (phase 2).

    Hits the phase-1 memo first (source ids reserved verbatim); on a
    miss, projects ``id_`` to NCName, makes it unique, and memoises so
    every definition and reference of the element agree.  This single
    chokepoint is what enforces id uniqueness and consistency.

    Args:
        writing_context: The current writing context.
        element: Any map element with an ``id_`` (layout element or map).

    Returns:
        The XML id string to emit.
    """
    element_id = id(element)
    existing = writing_context.element_to_xml_id.get(element_id)
    if existing is not None:
        return existing
    projected = ensure_ncname(element.id_)
    final = make_unique_xml_id(projected, writing_context.used_xml_ids)
    writing_context.element_to_xml_id[element_id] = final
    return final


# ---------------------------------------------------------------------------
# Helpers for layout lookup
# ---------------------------------------------------------------------------


def get_layout_elements(
    writing_context: "WritingContext",
    model_element: "ModelElement",
) -> "list[LayoutElement]":
    """Get all layout elements for a model element.

    Returns singleton layouts plus the representatives of any frozenset keys
    mapped to the model element. Duplicates are removed while preserving
    order.

    Args:
        writing_context: The current writing context.
        model_element: The model element to look up.

    Returns:
        A list of layout elements (may be empty).
    """
    mapping = writing_context.map_.layout_model_mapping
    result = mapping.get_mapping(model_element)
    if result is None or not isinstance(result, list):
        return []
    layout_elements = []
    seen = set()
    for item in result:
        if isinstance(item, frozenset):
            for representative in mapping.representative_to_key.inverse.get(item, []):
                if representative not in seen:
                    seen.add(representative)
                    layout_elements.append(representative)
        else:
            if item not in seen:
                seen.add(item)
                layout_elements.append(item)
    return layout_elements


def get_frozenset_keys(
    writing_context: "WritingContext",
    model_element: "ModelElement",
) -> list[frozenset]:
    """Get all frozenset mapping keys for a process, modulation or operator.

    Args:
        writing_context: The current writing context.
        model_element: The model element to look up.

    Returns:
        A list of frozenset keys (may be empty).
    """
    result = writing_context.map_.layout_model_mapping.get_mapping(model_element)
    if result is None or not isinstance(result, list):
        return []
    return [item for item in result if isinstance(item, frozenset)]


def get_child_layout_element(
    writing_context: "WritingContext",
    child_model: "ModelElement",
    parent_model: "ModelElement",
) -> "LayoutElement | None":
    """Get the layout element for a child model element.

    Args:
        writing_context: The current writing context.
        child_model: The child model element.
        parent_model: The parent model element.

    Returns:
        The layout element, or ``None``.
    """
    layout_elements = (
        writing_context.map_.layout_model_mapping.get_child_layout_elements(
            child_model, parent_model
        )
    )
    if layout_elements:
        return layout_elements[0]
    return None


# ---------------------------------------------------------------------------
# Core glyph/arc builders
# ---------------------------------------------------------------------------


def make_sbgnml_glyph(
    writing_context: "WritingContext",
    layout_element: "LayoutElement",
    model_element: "ModelElement | None" = None,
) -> lxml.etree._Element:
    """Create a ``<glyph>`` XML element from a layout element.

    Handles id, class, orientation, compartmentRef, bbox, label/state,
    and ports.

    Args:
        writing_context: The current writing context.
        layout_element: The layout element to serialize.
        model_element: Optional associated model element (for compartmentRef).

    Returns:
        The lxml ``<glyph>`` element.
    """
    sbgnml_id = get_xml_id(writing_context, layout_element)
    sbgnml_class = CLASS_TO_SBGNML_CLASS[type(layout_element)]
    attributes = {"id": sbgnml_id, "class": sbgnml_class}
    orientation_or_direction = getattr(layout_element, "orientation", None)
    if orientation_or_direction is None:
        orientation_or_direction = getattr(layout_element, "direction", None)
    if orientation_or_direction is not None:
        sbgnml_orientation = DIRECTION_TO_SBGNML_ORIENTATION[orientation_or_direction]
        attributes["orientation"] = sbgnml_orientation
    if model_element is not None and isinstance(
        model_element,
        (EntityPool, Activity),
    ):
        compartment = model_element.compartment
        if compartment is not None:
            compartment_layout_elements = get_layout_elements(
                writing_context, compartment
            )
            if compartment_layout_elements:
                compartment_id = get_xml_id(
                    writing_context, compartment_layout_elements[0]
                )
                attributes["compartmentRef"] = compartment_id
    sbgnml_glyph = make_lxml_element("glyph", attributes=attributes)
    entity_name = CLASS_TO_SBGNML_ENTITY_NAME.get(type(layout_element))
    if entity_name is not None:
        sbgnml_entity = make_sbgnml_entity(entity_name)
        sbgnml_glyph.append(sbgnml_entity)
    sbgnml_bbox = make_sbgnml_bbox_from_node(layout_element)
    sbgnml_glyph.append(sbgnml_bbox)
    if layout_element.label is not None:
        if isinstance(layout_element, StateVariableLayout):
            sbgnml_state = make_sbgnml_state(layout_element.label)
            sbgnml_glyph.append(sbgnml_state)
        else:
            sbgnml_label = make_sbgnml_label(layout_element.label)
            sbgnml_glyph.append(sbgnml_label)
    for side, attr in [
        ("left", "left_connector_tip"),
        ("right", "right_connector_tip"),
    ]:
        if hasattr(layout_element, attr):
            connector_tip = getattr(layout_element, attr)()
            sbgnml_port = make_sbgnml_port(connector_tip, port_id=f"{sbgnml_id}_{side}")
            sbgnml_glyph.append(sbgnml_port)
    return sbgnml_glyph


def make_sbgnml_stoichiometry_glyph(
    writing_context: "WritingContext",
    cardinality_layout: CardinalityLayout,
) -> lxml.etree._Element:
    """Create a ``<glyph class="stoichiometry">`` element.

    Args:
        writing_context: The current writing context.
        cardinality_layout: The cardinality layout to serialize.

    Returns:
        The lxml stoichiometry ``<glyph>`` element.
    """
    sbgnml_id = get_xml_id(writing_context, cardinality_layout)
    sbgnml_glyph = make_lxml_element(
        "glyph", attributes={"id": sbgnml_id, "class": "stoichiometry"}
    )
    sbgnml_glyph.append(make_sbgnml_bbox_from_node(cardinality_layout))
    if cardinality_layout.label is not None:
        sbgnml_glyph.append(make_sbgnml_label(cardinality_layout.label))
    return sbgnml_glyph


def make_sbgnml_arc_element(
    writing_context: "WritingContext",
    arc_layout: "LayoutElement",
) -> lxml.etree._Element:
    """Create an ``<arc>`` XML element from an arc layout element.

    Handles id, class, source, target, points, and direction reversal
    for arc types whose direction is inverted in momapy.

    Args:
        writing_context: The current writing context.
        arc_layout: The arc layout element.

    Returns:
        The lxml ``<arc>`` element.
    """
    sbgnml_id = get_xml_id(writing_context, arc_layout)
    sbgnml_class = CLASS_TO_SBGNML_CLASS[type(arc_layout)]
    attributes = {"id": sbgnml_id, "class": sbgnml_class}
    points = arc_layout.points()
    sbgnml_source_id = get_xml_id(writing_context, arc_layout.source)
    sbgnml_target_id = get_xml_id(writing_context, arc_layout.target)
    if isinstance(
        arc_layout,
        REVERSED_ARC_TYPES,
    ):
        attributes["source"] = sbgnml_target_id
        attributes["target"] = sbgnml_source_id
        points.reverse()
    else:
        attributes["source"] = sbgnml_source_id
        attributes["target"] = sbgnml_target_id
    sbgnml_arc = make_lxml_element("arc", attributes=attributes)
    sbgnml_points = make_sbgnml_points(points)
    for sbgnml_point in sbgnml_points:
        sbgnml_arc.append(sbgnml_point)
    for child_layout in arc_layout.layout_elements:
        if isinstance(child_layout, CardinalityLayout):
            sbgnml_arc.append(
                make_sbgnml_stoichiometry_glyph(writing_context, child_layout)
            )
    return sbgnml_arc


def make_sbgnml_child_glyphs(
    writing_context: "WritingContext",
    layout_element: "LayoutElement",
    model_element: "ModelElement",
) -> list[lxml.etree._Element]:
    """Create child ``<glyph>`` elements for the auxiliary units of a node.

    Auxiliary units are state variables, units of information, subunits and
    terminals. This walks the ``layout_elements`` of the *layout_element* and creates
    sub-glyphs for each child node.

    Args:
        writing_context: The current writing context.
        layout_element: The parent layout element.
        model_element: The parent model element (used for mapping lookups).

    Returns:
        A list of child glyph lxml elements.
    """
    child_glyphs = []
    for child_layout in layout_element.layout_elements:
        if isinstance(child_layout, Node):
            child_glyph = make_sbgnml_glyph(
                writing_context, child_layout, model_element=None
            )
            # Recursively add grandchildren (e.g., subunit auxiliary units)
            sub_children = make_sbgnml_child_glyphs(
                writing_context, child_layout, model_element
            )
            for sub_child in sub_children:
                child_glyph.append(sub_child)
            child_glyphs.append(child_glyph)
    return child_glyphs


# ---------------------------------------------------------------------------
# Map orchestrator
# ---------------------------------------------------------------------------


def collect_model_elements(
    writing_context: "WritingContext",
) -> "dict[LayoutElement, list[lxml.etree._Element]]":
    """Build a dict mapping layout elements to their serialized XML elements.

    Iterates model collections in dependency order, serializes each
    model element via the appropriate ``make_sbgnml_*`` function, and
    collects the resulting XML elements keyed by the layout element
    they originate from.

    Args:
        writing_context: The current writing context.

    Returns:
        A dict ``{layout_element: [lxml_element, ...]}``.
    """
    layout_to_xml = {}
    model = writing_context.map_.model
    is_pd = isinstance(model, SBGNPDModel)

    def _register(layout_el: "LayoutElement", sbgnml_el: lxml.etree._Element) -> None:
        layout_to_xml.setdefault(layout_el, []).append(sbgnml_el)

    # 1. Compartments
    for compartment in model.compartments:
        for layout_el in get_layout_elements(writing_context, compartment):
            sbgnml_glyph = make_sbgnml_glyph(
                writing_context, layout_el, model_element=compartment
            )
            for child_glyph in make_sbgnml_child_glyphs(
                writing_context, layout_el, compartment
            ):
                sbgnml_glyph.append(child_glyph)
            add_annotations_and_notes(writing_context, sbgnml_glyph, compartment)
            _register(layout_el, sbgnml_glyph)

    # 2. Entity pools (PD) or Activities (AF)
    if is_pd:
        for entity_pool in model.entity_pools:
            for layout_el in get_layout_elements(writing_context, entity_pool):
                sbgnml_glyph = make_sbgnml_glyph(
                    writing_context, layout_el, model_element=entity_pool
                )
                for child_glyph in make_sbgnml_child_glyphs(
                    writing_context, layout_el, entity_pool
                ):
                    sbgnml_glyph.append(child_glyph)
                add_annotations_and_notes(writing_context, sbgnml_glyph, entity_pool)
                _register(layout_el, sbgnml_glyph)
        # 2b. Empty sets — no model element. Driven by the
        # has_external_source / has_external_sink flags on processes:
        # find every EmptySetLayout in a flagged process's frozenset key
        # and emit a glyph for it.
        seen_empty_set_layouts = set()
        for process in model.processes:
            if not isinstance(process, StoichiometricProcess):
                continue
            if not (process.has_external_source or process.has_external_sink):
                continue
            for frozenset_key in get_frozenset_keys(writing_context, process):
                for item in frozenset_key:
                    if isinstance(item, EmptySetLayout):
                        if item in seen_empty_set_layouts:
                            continue
                        seen_empty_set_layouts.add(item)
                        sbgnml_glyph = make_sbgnml_glyph(
                            writing_context, item, model_element=None
                        )
                        _register(item, sbgnml_glyph)
    else:
        for activity in model.activities:
            for layout_el in get_layout_elements(writing_context, activity):
                sbgnml_glyph = make_sbgnml_glyph(
                    writing_context, layout_el, model_element=activity
                )
                for child_glyph in make_sbgnml_child_glyphs(
                    writing_context, layout_el, activity
                ):
                    sbgnml_glyph.append(child_glyph)
                add_annotations_and_notes(writing_context, sbgnml_glyph, activity)
                _register(layout_el, sbgnml_glyph)

    # 3. Logical operators (with logic arcs)
    representative_to_key = (
        writing_context.map_.layout_model_mapping.representative_to_key
    )
    for logical_operator in model.logical_operators:
        for frozenset_key in get_frozenset_keys(writing_context, logical_operator):
            operator_layout = None
            arc_layouts = []
            for item in frozenset_key:
                if isinstance(
                    item,
                    (
                        PDLogicArcLayout,
                        AFLogicArcLayout,
                    ),
                ):
                    arc_layouts.append(item)
                elif (
                    isinstance(item, Node)
                    and representative_to_key.get(item) == frozenset_key
                ):
                    operator_layout = item
            if operator_layout is None:
                continue
            sbgnml_glyph = make_sbgnml_glyph(
                writing_context,
                operator_layout,
                model_element=logical_operator,
            )
            add_annotations_and_notes(writing_context, sbgnml_glyph, logical_operator)
            _register(operator_layout, sbgnml_glyph)
            for arc_layout in arc_layouts:
                sbgnml_arc = make_sbgnml_arc_element(writing_context, arc_layout)
                _register(arc_layout, sbgnml_arc)

    # 4. Submaps (with terminals and equivalence arcs)
    for submap in model.submaps:
        for layout_el in get_layout_elements(writing_context, submap):
            sbgnml_glyph = make_sbgnml_glyph(
                writing_context, layout_el, model_element=submap
            )
            for child_glyph in make_sbgnml_child_glyphs(
                writing_context, layout_el, submap
            ):
                sbgnml_glyph.append(child_glyph)
            add_annotations_and_notes(writing_context, sbgnml_glyph, submap)
            _register(layout_el, sbgnml_glyph)
        if hasattr(submap, "terminals"):
            for terminal in submap.terminals:
                if (
                    hasattr(terminal, "referred_element")
                    and terminal.referred_element is not None
                ):
                    reference_layout = get_child_layout_element(
                        writing_context, terminal.referred_element, terminal
                    )
                    if reference_layout is not None and isinstance(
                        reference_layout,
                        (
                            SingleHeadedArc,
                            DoubleHeadedArc,
                        ),
                    ):
                        sbgnml_arc = make_sbgnml_arc_element(
                            writing_context, reference_layout
                        )
                        _register(reference_layout, sbgnml_arc)

    # 5. Tags (with equivalence arcs)
    for tag in model.tags:
        for layout_el in get_layout_elements(writing_context, tag):
            sbgnml_glyph = make_sbgnml_glyph(
                writing_context, layout_el, model_element=tag
            )
            for child_glyph in make_sbgnml_child_glyphs(
                writing_context, layout_el, tag
            ):
                sbgnml_glyph.append(child_glyph)
            add_annotations_and_notes(writing_context, sbgnml_glyph, tag)
            _register(layout_el, sbgnml_glyph)
        if hasattr(tag, "referred_element") and tag.referred_element is not None:
            reference_layout = get_child_layout_element(
                writing_context, tag.referred_element, tag
            )
            if reference_layout is not None and isinstance(
                reference_layout,
                (
                    SingleHeadedArc,
                    DoubleHeadedArc,
                ),
            ):
                sbgnml_arc = make_sbgnml_arc_element(writing_context, reference_layout)
                _register(reference_layout, sbgnml_arc)

    # 6. Processes
    if is_pd:
        for process in model.processes:
            if isinstance(process, Phenotype):
                for layout_el in get_layout_elements(writing_context, process):
                    sbgnml_glyph = make_sbgnml_glyph(
                        writing_context, layout_el, model_element=process
                    )
                    for child_glyph in make_sbgnml_child_glyphs(
                        writing_context, layout_el, process
                    ):
                        sbgnml_glyph.append(child_glyph)
                    add_annotations_and_notes(writing_context, sbgnml_glyph, process)
                    _register(layout_el, sbgnml_glyph)
            elif isinstance(process, StoichiometricProcess):
                for frozenset_key in get_frozenset_keys(writing_context, process):
                    process_layout = None
                    arc_layouts = []
                    for item in frozenset_key:
                        if isinstance(
                            item,
                            (
                                ConsumptionLayout,
                                ProductionLayout,
                            ),
                        ):
                            arc_layouts.append(item)
                        elif (
                            isinstance(item, Node)
                            and representative_to_key.get(item) == frozenset_key
                        ):
                            process_layout = item
                    if process_layout is None:
                        continue
                    sbgnml_glyph = make_sbgnml_glyph(
                        writing_context,
                        process_layout,
                        model_element=process,
                    )
                    for child_glyph in make_sbgnml_child_glyphs(
                        writing_context, process_layout, process
                    ):
                        sbgnml_glyph.append(child_glyph)
                    add_annotations_and_notes(writing_context, sbgnml_glyph, process)
                    _register(process_layout, sbgnml_glyph)
                    for arc_layout in arc_layouts:
                        sbgnml_arc = make_sbgnml_arc_element(
                            writing_context, arc_layout
                        )
                        _register(arc_layout, sbgnml_arc)

    # 7. Modulations (PD) or Influences (AF)
    modulations = model.modulations if is_pd else model.influences
    for modulation in modulations:
        for frozenset_key in get_frozenset_keys(writing_context, modulation):
            arc_layout = None
            for item in frozenset_key:
                if representative_to_key.get(item) == frozenset_key:
                    arc_layout = item
                    break
            if arc_layout is None:
                continue
            sbgnml_arc = make_sbgnml_arc_element(writing_context, arc_layout)
            add_annotations_and_notes(writing_context, sbgnml_arc, modulation)
            _register(arc_layout, sbgnml_arc)

    return layout_to_xml


def make_sbgnml_map(writing_context: "WritingContext") -> lxml.etree._Element:
    """Build the ``<map>`` XML element using a model-first traversal.

    Phase 1: iterates model collections in dependency order, serializes
    each model element and collects XML keyed by layout element.
    Phase 2: iterates ``layout.layout_elements`` in order and appends
    the collected XML to the ``<map>``, preserving the original ordering.

    Args:
        writing_context: The current writing context.

    Returns:
        The lxml ``<map>`` element.
    """
    map_ = writing_context.map_
    reserve_source_xml_ids(writing_context)
    language = CLASS_TO_SBGNML_CLASS[type(map_)]
    id_ = get_xml_id(writing_context, map_)
    attributes = {"id": id_, "language": language}
    sbgnml_map = make_lxml_element("map", attributes=attributes)
    add_annotations_and_notes(writing_context, sbgnml_map, map_)
    sbgnml_bbox = make_sbgnml_bbox_from_node(map_.layout)
    sbgnml_map.append(sbgnml_bbox)

    # Phase 1: model-first serialization
    layout_to_xml = collect_model_elements(writing_context)

    # Phase 2: output in layout order
    for layout_element in map_.layout.layout_elements:
        xml_elements = layout_to_xml.get(layout_element)
        if xml_elements is not None:
            for xml_el in xml_elements:
                sbgnml_map.append(xml_el)

    return sbgnml_map
