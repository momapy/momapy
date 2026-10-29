"""Utility functions for SBGN map manipulation.

This module provides helper functions for adjusting and tidying SBGN maps,
including fitting compartments, complexes, and submaps to their content,
adjusting arc endpoints, and applying various layout optimizations.
"""

import collections
import collections.abc
import typing

from momapy.positioning import fit
from momapy.positioning import set_fit
from momapy.positioning import set_position
from momapy.builder import Builder
from momapy.builder import builder_from_object
from momapy.builder import isinstance_or_builder
from momapy.builder import object_from_builder
from momapy.sbgn import SBGNMap
from momapy.core.layout import Node
from momapy.sbgn.pd import AndOperatorLayout as PDAndOperatorLayout
from momapy.sbgn.pd import CatalysisLayout
from momapy.sbgn.pd import Complex
from momapy.sbgn.pd import ComplexLayout
from momapy.sbgn.pd import ConsumptionLayout
from momapy.sbgn.pd import EquivalenceArcLayout as PDEquivalenceArcLayout
from momapy.sbgn.pd import EquivalenceOperatorLayout
from momapy.sbgn.pd import InhibitionLayout
from momapy.sbgn.pd import LogicArcLayout as PDLogicArcLayout
from momapy.sbgn.pd import ModulationLayout
from momapy.sbgn.pd import NecessaryStimulationLayout as PDNecessaryStimulationLayout
from momapy.sbgn.pd import NotOperatorLayout as PDNotOperatorLayout
from momapy.sbgn.pd import OrOperatorLayout as PDOrOperatorLayout
from momapy.sbgn.pd import Product
from momapy.sbgn.pd import ProductionLayout
from momapy.sbgn.pd import SBGNPDMap
from momapy.sbgn.pd import SBGNPDModel
from momapy.sbgn.pd import StateVariableLayout
from momapy.sbgn.pd import StimulationLayout
from momapy.sbgn.pd import UnitOfInformationLayout as PDUnitOfInformationLayout
from momapy.sbgn.af import AndOperatorLayout as AFAndOperatorLayout
from momapy.sbgn.af import ComplexUnitOfInformationLayout
from momapy.sbgn.af import DelayOperatorLayout
from momapy.sbgn.af import EquivalenceArcLayout as AFEquivalenceArcLayout
from momapy.sbgn.af import LogicArcLayout as AFLogicArcLayout
from momapy.sbgn.af import MacromoleculeUnitOfInformationLayout
from momapy.sbgn.af import NecessaryStimulationLayout as AFNecessaryStimulationLayout
from momapy.sbgn.af import NegativeInfluenceLayout
from momapy.sbgn.af import NotOperatorLayout as AFNotOperatorLayout
from momapy.sbgn.af import NucleicAcidFeatureUnitOfInformationLayout
from momapy.sbgn.af import OrOperatorLayout as AFOrOperatorLayout
from momapy.sbgn.af import PerturbationUnitOfInformationLayout
from momapy.sbgn.af import PositiveInfluenceLayout
from momapy.sbgn.af import SBGNAFMap
from momapy.sbgn.af import SBGNAFModel
from momapy.sbgn.af import SimpleChemicalUnitOfInformationLayout
from momapy.sbgn.af import UnitOfInformationLayout as AFUnitOfInformationLayout
from momapy.sbgn.af import UnknownInfluenceLayout
from momapy.sbgn.af import UnspecifiedEntityUnitOfInformationLayout


__all__ = [
    "get_info",
    "newt_tidy",
    "sbgned_tidy",
    "set_arcs_to_borders",
    "set_auxiliary_units_label_font_size",
    "set_auxiliary_units_to_borders",
    "set_compartments_to_fit_content",
    "set_complexes_to_fit_content",
    "set_layout_to_fit_content",
    "set_nodes_to_fit_labels",
    "set_submaps_to_fit_content",
    "tidy",
]


_AUXILIARY_UNIT_LAYOUT_CLASSES = (
    StateVariableLayout,
    PDUnitOfInformationLayout,
    AFUnitOfInformationLayout,
    UnspecifiedEntityUnitOfInformationLayout,
    SimpleChemicalUnitOfInformationLayout,
    MacromoleculeUnitOfInformationLayout,
    NucleicAcidFeatureUnitOfInformationLayout,
    ComplexUnitOfInformationLayout,
    PerturbationUnitOfInformationLayout,
)


def set_compartments_to_fit_content(
    map_: SBGNMap | Builder,
    xsep: float = 0.0,
    ysep: float = 0.0,
    snap_arcs: bool = False,
) -> SBGNMap | Builder:
    """Resize compartments to fit their content.

    Adjusts compartment dimensions to tightly enclose their contained
    entity pools or activities.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        xsep: Horizontal separation padding. Defaults to 0.
        ysep: Vertical separation padding. Defaults to 0.
        snap_arcs: If True, snap arc endpoints to node borders after
            resizing. Defaults to False.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    compartment_entities_mapping = collections.defaultdict(list)
    model = map_builder.model
    if isinstance_or_builder(map_builder, SBGNPDMap):
        for entity_pool in model.entity_pools:
            compartment = entity_pool.compartment
            if compartment is not None:
                compartment_entities_mapping[compartment].append(entity_pool)
    else:
        for activity in model.activities:
            compartment = activity.compartment
            if compartment is not None:
                compartment_entities_mapping[compartment].append(activity)
    for compartment in compartment_entities_mapping:
        for compartment_layout in map_builder.get_mapping(compartment):
            elements = []
            for entity in compartment_entities_mapping[compartment]:
                for entity_layout in map_builder.get_mapping(entity):
                    elements.append(entity_layout)
            set_fit(compartment_layout, elements, xsep, ysep)
            if compartment_layout.label is not None:
                compartment_layout.label.position = compartment_layout.south() - (
                    0.0,
                    compartment_layout.label.font_size,
                )
    if snap_arcs:
        set_arcs_to_borders(map_builder)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_complexes_to_fit_content(
    map_: SBGNMap | Builder,
    xsep: float = 0.0,
    ysep: float = 0.0,
    snap_arcs: bool = False,
) -> SBGNMap | Builder:
    """Resize complexes to fit their subunits.

    Adjusts complex dimensions to tightly enclose their contained subunits.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        xsep: Horizontal separation padding. Defaults to 0.
        ysep: Vertical separation padding. Defaults to 0.
        snap_arcs: If True, snap arc endpoints to node borders after
            resizing. Defaults to False.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    for entity_pool in map_builder.model.entity_pools:
        if isinstance_or_builder(entity_pool, Complex):
            for complex_layout in map_builder.get_mapping(entity_pool):
                elements = []
                for subunit in entity_pool.subunits:
                    subunit_layouts = (
                        map_builder.layout_model_mapping.get_child_layout_elements(
                            subunit, entity_pool
                        )
                    )
                    for subunit_layout in subunit_layouts:
                        if subunit_layout in complex_layout.layout_elements:
                            elements.append(subunit_layout)
                if elements:
                    set_fit(complex_layout, elements, xsep, ysep)
                    if complex_layout.label is not None:
                        complex_layout.label.position = complex_layout.position
    if snap_arcs:
        set_arcs_to_borders(map_builder)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_submaps_to_fit_content(
    map_: SBGNMap | Builder,
    xsep: float = 0.0,
    ysep: float = 0.0,
    snap_arcs: bool = False,
) -> SBGNMap | Builder:
    """Resize submaps to fit their terminals.

    Adjusts submap dimensions to tightly enclose their terminal elements.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        xsep: Horizontal separation padding. Defaults to 0.
        ysep: Vertical separation padding. Defaults to 0.
        snap_arcs: If True, snap arc endpoints to node borders after
            resizing. Defaults to False.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    for submap in map_builder.model.submaps:
        for submap_layout in map_builder.get_mapping(submap):
            elements = []
            for terminal in submap.terminals:
                terminal_layouts = (
                    map_builder.layout_model_mapping.get_child_layout_elements(
                        terminal, submap
                    )
                )
                for terminal_layout in terminal_layouts:
                    if terminal_layout in submap_layout.layout_elements:
                        elements.append(terminal_layout.childless())
            if elements:
                bbox = fit(elements, xsep, ysep)
                if bbox.width > submap_layout.width:
                    submap_layout.width = bbox.width
                if bbox.height > submap_layout.height:
                    submap_layout.height = bbox.height
                if submap_layout.label is not None:
                    submap_layout.label.position = submap_layout.position
    if snap_arcs:
        set_arcs_to_borders(map_builder)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_nodes_to_fit_labels(
    map_: SBGNMap | Builder,
    xsep: float = 0.0,
    ysep: float = 0.0,
    omit_width: bool = False,
    omit_height: bool = False,
    restrict_to: collections.abc.Sequence[type] | None = None,
    exclude: collections.abc.Sequence[type] | None = None,
    snap_arcs: bool = False,
) -> SBGNMap | Builder:
    """Resize nodes to fit their labels.

    Adjusts node dimensions to accommodate label text.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        xsep: Horizontal separation padding. Defaults to 0.
        ysep: Vertical separation padding. Defaults to 0.
        omit_width: If True, do not adjust width. Defaults to False.
        omit_height: If True, do not adjust height. Defaults to False.
        restrict_to: Node types to include. Defaults to all nodes.
        exclude: Node types to exclude. Defaults to none.
        snap_arcs: If True, snap arc endpoints to node borders after
            resizing. Defaults to False.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    if restrict_to is None:
        restrict_to = []
    if not restrict_to:
        restrict_to = [Node]
    if exclude is None:
        exclude = []
    exclude = tuple(exclude)
    restrict_to = tuple(restrict_to)
    if not (omit_width and omit_height):
        for layout_element in map_builder.layout.descendants():
            if (
                isinstance_or_builder(layout_element, restrict_to)
                and not isinstance_or_builder(layout_element, exclude)
                and hasattr(layout_element, "label")
                and layout_element.label is not None
            ):
                bbox = fit([layout_element.label.bbox()], xsep, ysep)
                if not omit_width:
                    if bbox.width > layout_element.width:
                        layout_element.width = bbox.width
                if not omit_height:
                    if bbox.height > layout_element.height:
                        layout_element.height = bbox.height
                set_position(layout_element, bbox.position, anchor="label_center")
    if snap_arcs:
        set_arcs_to_borders(map_builder)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_arcs_to_borders(
    map_: SBGNMap | Builder,
) -> SBGNMap | Builder:
    """Adjust arc endpoints to node borders.

    Updates arc start and end points to connect at the borders of
    their source and target nodes rather than centers.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """

    def _set_arc_to_borders(
        arc_layout_element: typing.Any,
        source: typing.Any,
        source_type: str,
        target: typing.Any,
        target_type: str,
    ) -> None:
        points = arc_layout_element.points()
        if source_type == "left":
            start_point = source.left_connector_tip()
        elif source_type == "right":
            start_point = source.right_connector_tip()
        else:
            if len(arc_layout_element.segments) > 1:
                start_reference_point = points[1]
            else:
                if target_type == "border":
                    start_reference_point = target.center()
                elif target_type == "left":
                    start_reference_point = target.left_connector_tip()
                else:
                    start_reference_point = target.right_connector_tip()
            start_point = source.border(start_reference_point)
            if start_point is None:
                start_point = source.center()
        if target_type == "left":
            end_point = target.left_connector_tip()
        elif target_type == "right":
            end_point = target.right_connector_tip()
        else:
            if len(arc_layout_element.segments) > 1:
                end_reference_point = points[-2]
            else:
                if source_type == "border":
                    end_reference_point = source.center()
                elif source_type == "left":
                    end_reference_point = source.left_connector_tip()
                else:
                    end_reference_point = source.right_connector_tip()
            end_point = target.border(end_reference_point)
            if end_point is None:
                end_point = target.center()
        arc_layout_element.segments[0].p1 = builder_from_object(start_point)
        arc_layout_element.segments[-1].p2 = builder_from_object(end_point)

    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    for layout_element in map_builder.layout.layout_elements:
        # Flux arcs - Consumption
        if isinstance_or_builder(layout_element, ConsumptionLayout):
            source = layout_element.source
            if source.left_to_right:
                source_type = "left"
            else:
                source_type = "right"
            _set_arc_to_borders(
                layout_element,
                source,
                source_type,
                layout_element.target,
                "border",
            )
        # Flux arcs - Production
        elif isinstance_or_builder(layout_element, ProductionLayout):
            source = layout_element.source
            product = map_builder.get_mapping(layout_element)
            if isinstance_or_builder(product, Product):
                if source.left_to_right:
                    source_type = "right"
                else:
                    source_type = "left"
            else:
                if source.left_to_right:
                    source_type = "left"
                else:
                    source_type = "right"
            _set_arc_to_borders(
                layout_element,
                source,
                source_type,
                layout_element.target,
                "border",
            )
        # Logic arcs
        elif isinstance_or_builder(
            layout_element,
            (
                PDLogicArcLayout,
                AFLogicArcLayout,
            ),
        ):
            source = layout_element.source
            target = layout_element.target
            if source.left_to_right:
                source_type = "left"
            else:
                source_type = "right"
            if isinstance_or_builder(
                target,
                (
                    PDAndOperatorLayout,
                    PDOrOperatorLayout,
                    PDNotOperatorLayout,
                    AFAndOperatorLayout,
                    AFOrOperatorLayout,
                    AFNotOperatorLayout,
                    DelayOperatorLayout,
                    EquivalenceOperatorLayout,
                ),
            ):
                if target.left_to_right:
                    target_type = "right"
                else:
                    target_type = "left"
            else:
                target_type = "border"
            _set_arc_to_borders(
                layout_element,
                source,
                source_type,
                target,
                target_type,
            )
        # Equivalence arcs
        elif isinstance_or_builder(
            layout_element,
            (
                PDEquivalenceArcLayout,
                AFEquivalenceArcLayout,
            ),
        ):
            _set_arc_to_borders(
                layout_element,
                layout_element.source,
                "border",
                layout_element.target,
                "border",
            )
        # Modulations
        elif isinstance_or_builder(
            layout_element,
            (
                ModulationLayout,
                StimulationLayout,
                CatalysisLayout,
                PDNecessaryStimulationLayout,
                InhibitionLayout,
                UnknownInfluenceLayout,
                PositiveInfluenceLayout,
                AFNecessaryStimulationLayout,
                NegativeInfluenceLayout,
            ),
        ):
            source = layout_element.source
            if isinstance_or_builder(
                source,
                (
                    PDAndOperatorLayout,
                    PDOrOperatorLayout,
                    PDNotOperatorLayout,
                    AFAndOperatorLayout,
                    AFOrOperatorLayout,
                    AFNotOperatorLayout,
                    DelayOperatorLayout,
                ),
            ):
                if source.left_to_right:
                    source_type = "right"
                else:
                    source_type = "left"
            else:
                source_type = "border"
            _set_arc_to_borders(
                layout_element,
                source,
                source_type,
                layout_element.target,
                "border",
            )
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_auxiliary_units_to_borders(
    map_: SBGNMap | Builder,
    snap_arcs: bool = False,
) -> SBGNMap | Builder:
    """Position auxiliary units at node borders.

    Moves state variables and units of information to the borders
    of their parent nodes.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        snap_arcs: If True, snap arc endpoints to node borders after
            repositioning. Defaults to False.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """

    def _rec_set_auxiliary_units_to_borders(layout_element: typing.Any) -> None:
        for child in layout_element.children():
            if isinstance_or_builder(child, _AUXILIARY_UNIT_LAYOUT_CLASSES):
                position = layout_element.own_border(child.position)
                child.position = position
                if child.label is not None:
                    child.label.position = position
            _rec_set_auxiliary_units_to_borders(child)

    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    _rec_set_auxiliary_units_to_borders(map_builder.layout)
    if snap_arcs:
        set_arcs_to_borders(map_builder)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_auxiliary_units_label_font_size(
    map_: SBGNMap | Builder,
    font_size: float,
) -> SBGNMap | Builder:
    """Set font size for auxiliary unit labels.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        font_size: The font size to apply.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """

    def _rec_set_auxiliary_units_label_font_size(
        layout_element: typing.Any, font_size: float
    ) -> None:
        for child in layout_element.children():
            if isinstance_or_builder(child, _AUXILIARY_UNIT_LAYOUT_CLASSES):
                if child.label is not None:
                    child.label.font_size = font_size
            _rec_set_auxiliary_units_label_font_size(child, font_size)

    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    _rec_set_auxiliary_units_label_font_size(map_builder.layout, font_size)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def set_layout_to_fit_content(
    map_: SBGNMap | Builder,
    xsep: float = 0.0,
    ysep: float = 0.0,
) -> SBGNMap | Builder:
    """Resize layout to fit all elements.

    Adjusts the layout dimensions to contain all layout elements.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        xsep: Horizontal separation padding. Defaults to 0.
        ysep: Vertical separation padding. Defaults to 0.

    Returns:
        The modified map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    set_fit(map_builder.layout, map_builder.layout.layout_elements, xsep, ysep)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def tidy(
    map_: SBGNMap | Builder,
    auxiliary_units_omit_width: bool = False,
    auxiliary_units_omit_height: bool = True,
    nodes_xsep: float = 4.0,
    nodes_ysep: float = 4.0,
    auxiliary_units_xsep: float = 1.0,
    auxiliary_units_ysep: float = 1.0,
    complexes_xsep: float = 10.0,
    complexes_ysep: float = 10.0,
    compartments_xsep: float = 25.0,
    compartments_ysep: float = 25.0,
    layout_xsep: float = 0.0,
    layout_ysep: float = 0.0,
) -> SBGNMap | Builder:
    """Apply comprehensive layout tidying to an SBGN map.

    Performs multiple layout optimization steps including fitting nodes to
    labels, positioning auxiliary units, resizing complexes and compartments,
    and adjusting arc endpoints.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.
        auxiliary_units_omit_width: Do not adjust auxiliary unit widths.
            Defaults to False.
        auxiliary_units_omit_height: Do not adjust auxiliary unit heights,
            so units only ever grow in width to fit their label and keep
            their default height. Defaults to True.
        nodes_xsep: Horizontal padding for node sizing. Defaults to 4.
        nodes_ysep: Vertical padding for node sizing. Defaults to 4.
        auxiliary_units_xsep: Horizontal padding for auxiliary units.
            Defaults to 1.
        auxiliary_units_ysep: Vertical padding for auxiliary units.
            Defaults to 1.
        complexes_xsep: Horizontal padding for complexes. Defaults to 10.
        complexes_ysep: Vertical padding for complexes. Defaults to 10.
        compartments_xsep: Horizontal padding for compartments.
            Defaults to 25.
        compartments_ysep: Vertical padding for compartments.
            Defaults to 25.
        layout_xsep: Horizontal padding for overall layout. Defaults to 0.
        layout_ysep: Vertical padding for overall layout. Defaults to 0.

    Returns:
        The tidied map or map builder. If a frozen map was given,
            a new map is returned.
    """
    if isinstance(map_, SBGNMap):
        map_builder = builder_from_object(map_)
    else:
        map_builder = map_
    set_nodes_to_fit_labels(
        map_builder,
        xsep=nodes_xsep,
        ysep=nodes_ysep,
        exclude=[
            *_AUXILIARY_UNIT_LAYOUT_CLASSES,
            ComplexLayout,
        ],
        snap_arcs=True,
    )
    set_auxiliary_units_to_borders(map_builder, snap_arcs=True)
    set_nodes_to_fit_labels(
        map_builder,
        xsep=auxiliary_units_xsep,
        ysep=auxiliary_units_ysep,
        omit_width=auxiliary_units_omit_width,
        omit_height=auxiliary_units_omit_height,
        restrict_to=list(_AUXILIARY_UNIT_LAYOUT_CLASSES),
        snap_arcs=True,
    )
    if isinstance_or_builder(map_builder, SBGNPDMap):
        set_complexes_to_fit_content(
            map_builder, complexes_xsep, complexes_ysep, snap_arcs=True
        )
    set_submaps_to_fit_content(map_builder, 0, 0, snap_arcs=True)
    set_compartments_to_fit_content(
        map_builder, compartments_xsep, compartments_ysep, snap_arcs=True
    )
    set_layout_to_fit_content(map_builder, layout_xsep, layout_ysep)
    if isinstance(map_, SBGNMap):
        return object_from_builder(map_builder)
    return map_builder


def sbgned_tidy(
    map_: SBGNMap | Builder,
) -> SBGNMap | Builder:
    """Apply SBGN-ED style tidying to an SBGN map.

    Uses preset parameters matching the SBGN-ED tool layout.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.

    Returns:
        The tidied map or map builder. If a frozen map was given,
            a new map is returned.
    """
    return tidy(
        map_,
        auxiliary_units_omit_width=False,
        auxiliary_units_omit_height=True,
        nodes_xsep=0,
        nodes_ysep=0,
        auxiliary_units_xsep=10,
        auxiliary_units_ysep=0,
        complexes_xsep=5,
        complexes_ysep=5,
        compartments_xsep=10,
        compartments_ysep=10,
        layout_xsep=0,
        layout_ysep=0,
    )


def newt_tidy(
    map_: SBGNMap | Builder,
) -> SBGNMap | Builder:
    """Apply Newt style tidying to an SBGN map.

    Uses preset parameters matching the Newt tool layout.

    Args:
        map_: An SBGN map or map builder. If a builder is given,
            it is modified in place.

    Returns:
        The tidied map or map builder. If a frozen map was given,
            a new map is returned.
    """
    return tidy(
        map_,
        auxiliary_units_omit_width=False,
        auxiliary_units_omit_height=True,
        nodes_xsep=0,
        nodes_ysep=0,
        auxiliary_units_xsep=1,
        auxiliary_units_ysep=0,
        complexes_xsep=10,
        complexes_ysep=10,
        compartments_xsep=14,
        compartments_ysep=14,
        layout_xsep=0,
        layout_ysep=0,
    )


def get_info(map_: SBGNMap) -> dict[str, typing.Any]:
    """Get a summary of the contents of an SBGN map.

    Returns a dictionary with the map type, model element counts,
    and layout dimensions.

    Args:
        map_: An SBGN map.

    Returns:
        A dictionary with keys ``map_type``, ``model``, and ``layout``.
        The ``model`` and ``layout`` entries are ``None`` when the map has
        no model or no layout, respectively.

    Raises:
        ValueError: If the map type, or a non-None model type, is not
            recognized.
    """
    model = map_.model
    layout = map_.layout
    if isinstance(map_, SBGNPDMap):
        map_type = "SBGN PD"
    elif isinstance(map_, SBGNAFMap):
        map_type = "SBGN AF"
    else:
        raise ValueError(f"unknown SBGN map type: {type(map_).__name__}")
    if model is None:
        model_info = None
    elif isinstance(model, SBGNPDModel):
        model_info = {
            "compartments": len(model.compartments),
            "entity_pools": len(model.entity_pools),
            "processes": len(model.processes),
            "modulations": len(model.modulations),
            "logical_operators": len(model.logical_operators),
            "equivalence_operators": len(model.equivalence_operators),
            "submaps": len(model.submaps),
            "tags": len(model.tags),
        }
    elif isinstance(model, SBGNAFModel):
        model_info = {
            "compartments": len(model.compartments),
            "activities": len(model.activities),
            "influences": len(model.influences),
            "logical_operators": len(model.logical_operators),
            "submaps": len(model.submaps),
            "tags": len(model.tags),
        }
    else:
        raise ValueError(f"unknown SBGN model type: {type(model).__name__}")
    if layout is None:
        layout_info = None
    else:
        layout_info = {
            "width": layout.width,
            "height": layout.height,
            "elements": len(layout.descendants()),
        }
    return {
        "map_type": map_type,
        "model": model_info,
        "layout": layout_info,
    }
