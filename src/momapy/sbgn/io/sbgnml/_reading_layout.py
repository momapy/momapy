"""Layout-building functions for SBGN-ML reader.

Each ``make_*`` function takes a ``reading_context`` as its first
argument, checks whether ``reading_context.layout`` is ``None``, and
returns ``None`` early when no layout is being built.
"""

import typing

from momapy.geometry import Point
from momapy.geometry import Segment
from momapy.core.elements import HAlignment
from momapy.core.layout import TextLayout
from momapy.builder import new_builder_object
from momapy.builder import object_from_builder
from momapy.coloring import black
from momapy.drawing import DEFAULT_FONT_FAMILY
from momapy.drawing import NoneValue
from momapy.sbgn.pd import CardinalityLayout
from momapy.sbgn.pd import ConsumptionLayout
from momapy.sbgn.pd import EquivalenceArcLayout
from momapy.sbgn.pd import LogicArcLayout
from momapy.sbgn.pd import ProductionLayout
from momapy.sbgn.pd import StateVariableLayout
from momapy.sbgn.pd import TagLayout
from momapy.sbgn.pd import TerminalLayout
from momapy.sbgn.io.sbgnml._reading_classification import get_module_from_object
from momapy.sbgn.io.sbgnml._reading_parsing import get_connectors_length
from momapy.sbgn.io.sbgnml._reading_parsing import get_direction
from momapy.sbgn.io.sbgnml._reading_parsing import get_process_orientation
from momapy.sbgn.io.sbgnml._reading_parsing import get_sbgnml_points
from momapy.sbgn.io.sbgnml._reading_parsing import get_stoichiometry
from momapy.sbgn.io.sbgnml._reading_parsing import is_operator_left_to_right
from momapy.sbgn.io.sbgnml._reading_parsing import is_process_left_to_right
from momapy.sbgn.layout import DEFAULT_AUXILIARY_UNIT_FONT_SIZE
from momapy.sbgn.layout import DEFAULT_FONT_SIZE

if typing.TYPE_CHECKING:
    import lxml.objectify

    from momapy.core.elements import LayoutElement
    from momapy.sbgn.io.sbgnml._reading_context import SBGNMLReadingContext


def make_text_layout(
    text: str | None,
    position: Point,
    font_size: float = DEFAULT_FONT_SIZE,
) -> TextLayout:
    if text is None:
        text = ""
    return TextLayout(
        text=text,
        font_size=font_size,
        font_family=DEFAULT_FONT_FAMILY,
        fill=black,
        stroke=NoneValue,
        position=position,
        horizontal_alignment=HAlignment.CENTER,
    )


def make_points(
    sbgnml_points: "list[lxml.objectify.ObjectifiedElement]",
) -> list[Point]:
    return [
        Point(float(sbgnml_point.get("x")), float(sbgnml_point.get("y")))
        for sbgnml_point in sbgnml_points
    ]


def make_segments(points: list[Point]) -> list[Segment]:
    segments = []
    for current_point, following_point in zip(points[:-1], points[1:]):
        segment = Segment(current_point, following_point)
        segments.append(segment)
    return segments


def make_arc_segments(
    sbgnml_arc: "lxml.objectify.ObjectifiedElement",
    reverse: bool = False,
) -> list[Segment]:
    sbgnml_points = get_sbgnml_points(sbgnml_arc)
    if reverse:
        sbgnml_points.reverse()
    points = make_points(sbgnml_points)
    return make_segments(points)


def make_stoichiometry_layout(
    sbgnml_stoichiometry: "lxml.objectify.ObjectifiedElement | None",
    layout_element: typing.Any,
) -> None:
    if sbgnml_stoichiometry is None:
        return
    stoichiometry_layout_element = new_builder_object(CardinalityLayout)
    set_position_and_size(stoichiometry_layout_element, sbgnml_stoichiometry)
    sbgnml_label = getattr(sbgnml_stoichiometry, "label", None)
    if sbgnml_label is not None:
        stoichiometry_layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(
                sbgnml_label, stoichiometry_layout_element.position
            ),
        )
    layout_element.layout_elements.append(stoichiometry_layout_element)


def set_connector_lengths(
    layout_element: typing.Any,
    sbgnml_element: "lxml.objectify.ObjectifiedElement",
) -> None:
    left_connector_length, right_connector_length = get_connectors_length(
        sbgnml_element
    )
    if left_connector_length is not None:
        layout_element.left_connector_length = left_connector_length
    if right_connector_length is not None:
        layout_element.right_connector_length = right_connector_length


def set_position_and_size(
    layout_element: typing.Any,
    sbgnml_glyph: "lxml.objectify.ObjectifiedElement",
) -> None:
    sbgnml_bbox = sbgnml_glyph.bbox
    x = float(sbgnml_bbox.get("x"))
    y = float(sbgnml_bbox.get("y"))
    w = float(sbgnml_bbox.get("w"))
    h = float(sbgnml_bbox.get("h"))
    layout_element.position = Point(x + w / 2, y + h / 2)
    layout_element.width = w
    layout_element.height = h


def get_label_position(
    sbgnml_label: "lxml.objectify.ObjectifiedElement",
    default_position: Point,
) -> Point:
    sbgnml_bbox = getattr(sbgnml_label, "bbox", None)
    if sbgnml_bbox is None:
        return default_position
    x = float(sbgnml_bbox.get("x"))
    y = float(sbgnml_bbox.get("y"))
    width = float(sbgnml_bbox.get("w"))
    height = float(sbgnml_bbox.get("h"))
    return Point(x + width / 2, y + height / 2)


def make_compartment(
    reading_context: "SBGNMLReadingContext",
    sbgnml_compartment: "lxml.objectify.ObjectifiedElement",
) -> "LayoutElement | None":
    """Create a compartment layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_compartment: The SBGN-ML compartment XML element.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    module = get_module_from_object(reading_context.layout)
    sbgnml_label = getattr(sbgnml_compartment, "label", None)
    layout_element = new_builder_object(module.CompartmentLayout)
    layout_element.id_ = sbgnml_compartment.get("id")
    set_position_and_size(layout_element, sbgnml_compartment)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.center()),
        )
    return layout_element


def make_entity_pool_or_subunit(
    reading_context: "SBGNMLReadingContext",
    sbgnml_entity_pool_or_subunit: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create an entity pool or subunit layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_entity_pool_or_subunit: The SBGN-ML element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_label = getattr(sbgnml_entity_pool_or_subunit, "label", None)
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_entity_pool_or_subunit.get("id")
    set_position_and_size(layout_element, sbgnml_entity_pool_or_subunit)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.label_center()),
        )
    return layout_element


def make_activity(
    reading_context: "SBGNMLReadingContext",
    sbgnml_activity: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create an activity layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_activity: The SBGN-ML activity XML element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_label = getattr(sbgnml_activity, "label", None)
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_activity.get("id")
    set_position_and_size(layout_element, sbgnml_activity)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.label_center()),
        )
    return layout_element


def make_state_variable(
    reading_context: "SBGNMLReadingContext",
    sbgnml_state_variable: "lxml.objectify.ObjectifiedElement",
    text: str | None,
) -> "LayoutElement | None":
    """Create a frozen state variable layout element.

    Args:
        reading_context: The reading context.
        sbgnml_state_variable: The SBGN-ML state variable element.
        text: The display text for the state variable.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_id = sbgnml_state_variable.get("id")
    layout_element = new_builder_object(StateVariableLayout)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_state_variable)
    layout_element.label = make_text_layout(
        text=text,
        position=layout_element.label_center(),
        font_size=DEFAULT_AUXILIARY_UNIT_FONT_SIZE,
    )
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_unit_of_information(
    reading_context: "SBGNMLReadingContext",
    sbgnml_unit_of_information: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create a frozen unit of information layout element.

    Args:
        reading_context: The reading context.
        sbgnml_unit_of_information: The SBGN-ML unit of information element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_label = getattr(sbgnml_unit_of_information, "label", None)
    sbgnml_id = sbgnml_unit_of_information.get("id")
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_unit_of_information)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.label_center()),
            font_size=DEFAULT_AUXILIARY_UNIT_FONT_SIZE,
        )
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_submap(
    reading_context: "SBGNMLReadingContext",
    sbgnml_submap: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create a submap layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_submap: The SBGN-ML submap XML element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_label = getattr(sbgnml_submap, "label", None)
    sbgnml_id = sbgnml_submap.get("id")
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_submap)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.center()),
        )
    return layout_element


def make_terminal_or_tag(
    reading_context: "SBGNMLReadingContext",
    sbgnml_terminal_or_tag: "lxml.objectify.ObjectifiedElement",
    is_terminal: bool,
) -> "LayoutElement | None":
    """Create a terminal or tag layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_terminal_or_tag: The SBGN-ML terminal or tag element.
        is_terminal: True for terminal, False for tag.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_id = sbgnml_terminal_or_tag.get("id")
    sbgnml_label = getattr(sbgnml_terminal_or_tag, "label", None)
    if is_terminal:
        layout_element_cls = TerminalLayout
    else:
        layout_element_cls = TagLayout
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_terminal_or_tag)
    layout_element.direction = get_direction(sbgnml_terminal_or_tag)
    if sbgnml_label is not None:
        layout_element.label = make_text_layout(
            text=sbgnml_label.get("text"),
            position=get_label_position(sbgnml_label, layout_element.label_center()),
        )
    return layout_element


def make_reference(
    reading_context: "SBGNMLReadingContext",
    sbgnml_equivalence_arc: "lxml.objectify.ObjectifiedElement",
    super_layout_element: typing.Any,
) -> "LayoutElement | None":
    """Create a frozen reference (equivalence arc) layout element.

    Args:
        reading_context: The reading context.
        sbgnml_equivalence_arc: The SBGN-ML equivalence arc element.
        super_layout_element: The frozen parent terminal/tag layout element.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_id = sbgnml_equivalence_arc.get("id")
    # For terminals and tags, equivalence arc go from the referred node
    # to the terminal or tag. We invert the arc, so that the arc goes
    # from the reference to the referred node.
    sbgnml_target_id = sbgnml_equivalence_arc.get("source")
    layout_element = new_builder_object(EquivalenceArcLayout)
    layout_element.id_ = sbgnml_id
    layout_element.source = super_layout_element
    for segment in make_arc_segments(sbgnml_equivalence_arc, reverse=True):
        layout_element.segments.append(segment)
    target_layout_element = reading_context.xml_id_to_layout_element[sbgnml_target_id]
    layout_element.target = target_layout_element
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_stoichiometric_process(
    reading_context: "SBGNMLReadingContext",
    sbgnml_process: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create a stoichiometric process layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_process: The SBGN-ML process XML element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_id = sbgnml_process.get("id")
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_process)
    layout_element.orientation = get_process_orientation(
        sbgnml_process, reading_context.sbgnml_glyph_id_to_sbgnml_arcs
    )
    layout_element.left_to_right = is_process_left_to_right(
        sbgnml_process, reading_context.sbgnml_glyph_id_to_sbgnml_arcs
    )
    set_connector_lengths(layout_element, sbgnml_process)
    return layout_element


def make_reactant(
    reading_context: "SBGNMLReadingContext",
    sbgnml_consumption_arc: "lxml.objectify.ObjectifiedElement",
    super_layout_element: typing.Any,
) -> "LayoutElement | None":
    """Create a frozen reactant (consumption) layout element.

    Args:
        reading_context: The reading context.
        sbgnml_consumption_arc: The SBGN-ML consumption arc element.
        super_layout_element: The parent process layout element.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_source_id = sbgnml_consumption_arc.get("source")
    sbgnml_stoichiometry = get_stoichiometry(sbgnml_consumption_arc)
    layout_element = new_builder_object(ConsumptionLayout)
    layout_element.id_ = sbgnml_consumption_arc.get("id")
    # The source becomes the target: in momapy flux arcs go from the process
    # to the entity pool node; this way reversible consumptions can be
    # represented with production layouts.
    for segment in make_arc_segments(sbgnml_consumption_arc, reverse=True):
        layout_element.segments.append(segment)
    layout_element.source = super_layout_element
    source_layout_element = reading_context.xml_id_to_layout_element[sbgnml_source_id]
    layout_element.target = source_layout_element
    make_stoichiometry_layout(sbgnml_stoichiometry, layout_element)
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_product(
    reading_context: "SBGNMLReadingContext",
    sbgnml_production_arc: "lxml.objectify.ObjectifiedElement",
    super_layout_element: typing.Any,
) -> "LayoutElement | None":
    """Create a frozen product (production) layout element.

    Args:
        reading_context: The reading context.
        sbgnml_production_arc: The SBGN-ML production arc element.
        super_layout_element: The parent process layout element.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_target_id = sbgnml_production_arc.get("target")
    sbgnml_stoichiometry = get_stoichiometry(sbgnml_production_arc)
    layout_element = new_builder_object(ProductionLayout)
    layout_element.id_ = sbgnml_production_arc.get("id")
    layout_element.source = super_layout_element
    for segment in make_arc_segments(sbgnml_production_arc):
        layout_element.segments.append(segment)
    target_layout_element = reading_context.xml_id_to_layout_element[sbgnml_target_id]
    layout_element.target = target_layout_element
    make_stoichiometry_layout(sbgnml_stoichiometry, layout_element)
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_logical_operator(
    reading_context: "SBGNMLReadingContext",
    sbgnml_logical_operator: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
) -> "LayoutElement | None":
    """Create a logical operator layout builder.

    Args:
        reading_context: The reading context.
        sbgnml_logical_operator: The SBGN-ML logical operator element.
        layout_element_cls: The layout element class to instantiate.

    Returns:
        A layout element builder, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    sbgnml_id = sbgnml_logical_operator.get("id")
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_id
    set_position_and_size(layout_element, sbgnml_logical_operator)
    layout_element.orientation = get_process_orientation(
        sbgnml_logical_operator, reading_context.sbgnml_glyph_id_to_sbgnml_arcs
    )
    layout_element.left_to_right = is_operator_left_to_right(
        sbgnml_operator=sbgnml_logical_operator,
        sbgnml_id_to_sbgnml_element=reading_context.xml_id_to_xml_element,
        sbgnml_glyph_id_to_sbgnml_arcs=reading_context.sbgnml_glyph_id_to_sbgnml_arcs,
    )
    set_connector_lengths(layout_element, sbgnml_logical_operator)
    return layout_element


def make_logical_operator_input(
    reading_context: "SBGNMLReadingContext",
    sbgnml_logic_arc: "lxml.objectify.ObjectifiedElement",
    source_layout_element: typing.Any,
    super_layout_element: typing.Any,
) -> "LayoutElement | None":
    """Create a frozen logical operator input (logic arc) layout element.

    Args:
        reading_context: The reading context.
        sbgnml_logic_arc: The SBGN-ML logic arc element.
        source_layout_element: The resolved source layout element.
        super_layout_element: The parent operator layout element.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    layout_element = new_builder_object(LogicArcLayout)
    layout_element.id_ = sbgnml_logic_arc.get("id")
    # The source becomes the target: in momapy logic arcs go from
    # the operator to the input node.
    layout_element.source = super_layout_element
    for segment in make_arc_segments(sbgnml_logic_arc, reverse=True):
        layout_element.segments.append(segment)
    layout_element.target = source_layout_element
    layout_element = object_from_builder(layout_element)
    return layout_element


def make_modulation(
    reading_context: "SBGNMLReadingContext",
    sbgnml_modulation: "lxml.objectify.ObjectifiedElement",
    layout_element_cls: type,
    source_layout_element: typing.Any,
    target_layout_element: typing.Any,
) -> "LayoutElement | None":
    """Create a frozen modulation layout element.

    Args:
        reading_context: The reading context.
        sbgnml_modulation: The SBGN-ML modulation arc element.
        layout_element_cls: The layout element class to instantiate.
        source_layout_element: The resolved source layout element.
        target_layout_element: The resolved target layout element.

    Returns:
        A frozen layout element, or None if reading_context.layout is None.
    """
    if reading_context.layout is None:
        return None
    layout_element = new_builder_object(layout_element_cls)
    layout_element.id_ = sbgnml_modulation.get("id")
    for segment in make_arc_segments(sbgnml_modulation):
        layout_element.segments.append(segment)
    layout_element.source = source_layout_element
    layout_element.target = target_layout_element
    layout_element = object_from_builder(layout_element)
    return layout_element
