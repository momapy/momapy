"""CellDesigner XML writing helper functions.

Encoding, coordinate inversions, reverse mappings, and XML element
construction used by the CellDesigner writer.
"""

import dataclasses
import math
import re
import typing

import lxml.etree

from momapy.coloring import Color
from momapy.geometry import Point, Rotation, get_transformation_for_frame
from momapy.io._utils import make_unique_xml_id
from momapy.sbml.io.sbml._qualifiers import QUALIFIER_MEMBER_TO_QUALIFIER_ATTRIBUTE
from momapy.celldesigner.elements import CellDesignerNode
from momapy.celldesigner.io.celldesigner._constants import (
    CD_NAMESPACE,
    LINK_ANCHOR_POSITION_TO_ANCHOR_NAME,
    TEXT_TO_CHARACTER,
)
from momapy.celldesigner.model import (
    AndGate,
    AntisenseRNA,
    AntisenseRNATemplate,
    BooleanLogicGate,
    Catalysis,
    Catalyzer,
    CodingRegion,
    Complex,
    Dissociation,
    Drug,
    Gene,
    GeneTemplate,
    GenericProtein,
    HeterodimerAssociation,
    Inhibition,
    Inhibitor,
    Ion,
    IonChannel,
    IonChannelTemplate,
    KnownTransitionOmitted,
    ModificationSite,
    Modulation,
    Modulator,
    NegativeInfluence,
    NotGate,
    OrGate,
    Phenotype,
    PhysicalStimulation,
    PhysicalStimulator,
    PositiveInfluence,
    ProteinBindingDomain,
    ProteinTemplate,
    RNA,
    RNATemplate,
    Receptor,
    ReceptorTemplate,
    RegulatoryRegion,
    SimpleMolecule,
    StateTransition,
    Transcription,
    TranscriptionStartingSiteL,
    TranscriptionStartingSiteR,
    Translation,
    Transport,
    Trigger,
    Triggering,
    TruncatedProtein,
    TruncatedProteinTemplate,
    Truncation,
    Unknown,
    UnknownCatalysis,
    UnknownCatalyzer,
    UnknownGate,
    UnknownInhibition,
    UnknownInhibitor,
    UnknownModulation,
    UnknownNegativeInfluence,
    UnknownPhysicalStimulation,
    UnknownPositiveInfluence,
    UnknownTransition,
    UnknownTriggering,
)
from momapy.celldesigner.layout import (
    AndGateLayout,
    AntisenseRNAActiveLayout,
    CompartmentCorner,
    CompartmentSide,
    ComplexActiveLayout,
    ComplexLayout,
    ConsumptionLayout,
    CornerCompartmentLayout,
    DegradedActiveLayout,
    DegradedLayout,
    DrugActiveLayout,
    GeneActiveLayout,
    GenericProteinActiveLayout,
    IonActiveLayout,
    IonChannelActiveLayout,
    LineCompartmentLayout,
    LogicArcLayout,
    ModificationLayout,
    NotGateLayout,
    OrGateLayout,
    OvalCompartmentLayout,
    PhenotypeActiveLayout,
    ProductionLayout,
    RNAActiveLayout,
    ReactionLayout,
    ReceptorActiveLayout,
    RectangleCompartmentLayout,
    SimpleMoleculeActiveLayout,
    TruncatedProteinActiveLayout,
    UnknownActiveLayout,
    UnknownGateLayout,
)


def are_collinear(
    p1: typing.Any, p2: typing.Any, p3: typing.Any, epsilon: float = 1e-6
) -> bool:
    """Check if three points are collinear (Minerva compatibility).

    Args:
        p1: First point (maps to Minerva's pointA).
        p2: Second point (maps to Minerva's pointB).
        p3: Third point / origin (maps to Minerva's pointC).
        epsilon: Tolerance for the cross product test.

    Returns:
        True if the three points are collinear.
    """
    dx1 = p1.x - p3.x
    dy1 = p1.y - p3.y
    dx2 = p2.x - p3.x
    dy2 = p2.y - p3.y
    cross = dx1 * dy2 - dy1 * dx2
    return abs(cross) < epsilon


def is_degenerate_frame(
    origin: typing.Any, unit_x: typing.Any, unit_y: typing.Any, epsilon: float = 1e-6
) -> bool:
    """Check whether a (origin, unit_x, unit_y) frame is singular.

    The frame is singular when the basis vectors (unit_x - origin) and
    (unit_y - origin) are parallel, which includes the cases where any
    two of the three points coincide.

    Args:
        origin: Origin point.
        unit_x: Unit x-axis point.
        unit_y: Unit y-axis point.
        epsilon: Tolerance on the determinant.

    Returns:
        True if the frame would produce a singular transformation.
    """
    determinant = (unit_x.x - origin.x) * (unit_y.y - origin.y) - (
        unit_y.x - origin.x
    ) * (unit_x.y - origin.y)
    return abs(determinant) < epsilon


def make_non_degenerate_frame(
    origin: typing.Any,
    unit_x: typing.Any,
    unit_y: typing.Any,
    epsilon: float = 1e-6,
    scale: float = 1.0,
) -> tuple[typing.Any, typing.Any, typing.Any]:
    """Return a well-conditioned (origin, unit_x, unit_y) triple.

    When the supplied frame is singular (coincident or collinear points),
    the origin is nudged perpendicular to the dominant available axis so
    the resulting basis becomes non-singular. When all three points
    coincide, an orthonormal basis around the nudged origin is
    synthesized. A non-degenerate input is returned unchanged.

    Args:
        origin: Origin point.
        unit_x: Unit x-axis point.
        unit_y: Unit y-axis point.
        epsilon: Tolerance on the determinant.
        scale: Magnitude of the perturbation, in input-coordinate units.

    Returns:
        A (origin, unit_x, unit_y) triple forming a non-singular frame.
    """
    if not is_degenerate_frame(origin, unit_x, unit_y, epsilon):
        return origin, unit_x, unit_y
    candidate_axes = [
        (unit_y.x - unit_x.x, unit_y.y - unit_x.y),
        (unit_x.x - origin.x, unit_x.y - origin.y),
        (unit_y.x - origin.x, unit_y.y - origin.y),
    ]
    direction_x = 1.0
    direction_y = 0.0
    for candidate_x, candidate_y in candidate_axes:
        length = math.hypot(candidate_x, candidate_y)
        if length >= epsilon:
            direction_x = candidate_x / length
            direction_y = candidate_y / length
            break
    perpendicular_x = -direction_y * scale
    perpendicular_y = direction_x * scale
    new_origin = Point(origin.x + perpendicular_x, origin.y + perpendicular_y)
    if not is_degenerate_frame(new_origin, unit_x, unit_y, epsilon):
        return new_origin, unit_x, unit_y
    new_unit_x = Point(
        new_origin.x + direction_x * scale,
        new_origin.y + direction_y * scale,
    )
    new_unit_y = Point(
        new_origin.x + perpendicular_x,
        new_origin.y + perpendicular_y,
    )
    return new_origin, new_unit_x, new_unit_y


_SBML_SID_INVALID_CHAR_RE = re.compile(r"[^a-zA-Z0-9_]")

# Reverse of _constants.LINK_ANCHOR_POSITION_TO_ANCHOR_NAME
_ANCHOR_NAME_TO_LINK_ANCHOR_POSITION = {
    v: k for k, v in LINK_ANCHOR_POSITION_TO_ANCHOR_NAME.items()
}

# Reverse of _constants.TEXT_TO_CHARACTER (pick first occurrence as canonical)
_CHARACTER_TO_TEXT = {}
for (
    _text,
    _char,
) in TEXT_TO_CHARACTER.items():
    if _char not in _CHARACTER_TO_TEXT:
        _CHARACTER_TO_TEXT[_char] = _text


_CLASS_TO_CD_STRING = {
    GenericProtein: "PROTEIN",
    TruncatedProtein: "PROTEIN",
    Receptor: "PROTEIN",
    IonChannel: "PROTEIN",
    Gene: "GENE",
    RNA: "RNA",
    AntisenseRNA: "ANTISENSE_RNA",
    SimpleMolecule: "SIMPLE_MOLECULE",
    Ion: "ION",
    Drug: "DRUG",
    Phenotype: "PHENOTYPE",
    Unknown: "UNKNOWN",
    Complex: "COMPLEX",
}

_CLASS_TO_REACTION_TYPE = {
    StateTransition: "STATE_TRANSITION",
    KnownTransitionOmitted: "KNOWN_TRANSITION_OMITTED",
    UnknownTransition: "UNKNOWN_TRANSITION",
    Transcription: "TRANSCRIPTION",
    Translation: "TRANSLATION",
    Transport: "TRANSPORT",
    HeterodimerAssociation: "HETERODIMER_ASSOCIATION",
    Dissociation: "DISSOCIATION",
    Truncation: "TRUNCATION",
}

_CLASS_TO_MODIFIER_TYPE = {
    Catalyzer: "CATALYSIS",
    UnknownCatalyzer: "UNKNOWN_CATALYSIS",
    Inhibitor: "INHIBITION",
    UnknownInhibitor: "UNKNOWN_INHIBITION",
    PhysicalStimulator: "PHYSICAL_STIMULATION",
    Modulator: "MODULATION",
    Trigger: "TRIGGER",
}

# Reaction type per modulation class: (plain form, reduced-notation form).
# `None` means the class has no reduced form and is always written plainly.
CLASS_TO_MODULATION_REACTION_TYPES = {
    Catalysis: ("CATALYSIS", None),
    UnknownCatalysis: ("UNKNOWN_CATALYSIS", None),
    Inhibition: ("INHIBITION", "NEGATIVE_INFLUENCE"),
    UnknownInhibition: ("UNKNOWN_INHIBITION", "UNKNOWN_NEGATIVE_INFLUENCE"),
    PhysicalStimulation: ("PHYSICAL_STIMULATION", "REDUCED_PHYSICAL_STIMULATION"),
    UnknownPhysicalStimulation: (
        "UNKNOWN_PHYSICAL_STIMULATION",
        "UNKNOWN_REDUCED_PHYSICAL_STIMULATION",
    ),
    Modulation: ("MODULATION", "REDUCED_MODULATION"),
    UnknownModulation: ("UNKNOWN_MODULATION", "UNKNOWN_REDUCED_MODULATION"),
    Triggering: ("TRIGGER", "REDUCED_TRIGGER"),
    UnknownTriggering: ("UNKNOWN_TRIGGER", "UNKNOWN_REDUCED_TRIGGER"),
    PositiveInfluence: ("POSITIVE_INFLUENCE", None),
    NegativeInfluence: ("NEGATIVE_INFLUENCE", None),
    UnknownPositiveInfluence: ("UNKNOWN_POSITIVE_INFLUENCE", None),
    UnknownNegativeInfluence: ("UNKNOWN_NEGATIVE_INFLUENCE", None),
}

_MODIFICATION_STATE_TO_CD = {
    "PHOSPHORYLATED": "phosphorylated",
    "UBIQUITINATED": "ubiquitinated",
    "ACETYLATED": "acetylated",
    "METHYLATED": "methylated",
    "HYDROXYLATED": "hydroxylated",
    "GLYCOSYLATED": "glycosylated",
    "MYRISTOYLATED": "myristoylated",
    "PALMITOYLATED": "palmitoylated",
    "PRENYLATED": "prenylated",
    "PROTONATED": "protonated",
    "SULFATED": "sulfated",
    "DON_T_CARE": "don't care",
    "UNKNOWN": "unknown",
    "none": "empty",
}


def ensure_sbml_sid(id_str: str | None) -> str:
    """Ensure a string conforms to SBML SId syntax.

    SBML Level 2 Version 4 SId: ``[a-zA-Z_][a-zA-Z0-9_]*``.
    Invalid characters are replaced with underscores, and a leading
    digit is prefixed with an underscore.

    Args:
        id_str: The raw ID string.

    Returns:
        A valid SId string, or empty string if input is None or empty.
    """
    if not id_str:
        return ""
    result = _SBML_SID_INVALID_CHAR_RE.sub("_", id_str)
    if result[0].isdigit():
        result = "_" + result
    return result


def encode_name(name: str | None) -> str | None:
    """Reverse of _parsing.get_name(): replace special chars with CD tokens.

    Args:
        name: Human-readable name string.

    Returns:
        CellDesigner-encoded name string, or None if name is None.
    """
    if name is None:
        return name
    for char, text in _CHARACTER_TO_TEXT.items():
        name = name.replace(char, text)
    return name


def color_to_cd_hex(color: typing.Any) -> str:
    """Convert momapy Color (RRGGBBAA) to CellDesigner hex (AARRGGBB).

    Args:
        color: A Color instance.

    Returns:
        CellDesigner AARRGGBB hex string (e.g. "FFCC0000").
    """
    hexa = color.to_hexa().lstrip("#").lower()
    # hexa is RRGGBBAA, CellDesigner expects AARRGGBB
    return hexa[-2:] + hexa[:-2]


def node_to_bounds_attrs(node: typing.Any) -> dict[str, str]:
    """Extract CellDesigner bounds attributes from a layout node.

    Args:
        node: A layout element with position, width, height.

    Returns:
        Dict with "x", "y", "w", "h" string attributes.
    """
    return {
        "x": str(node.position.x - node.width / 2),
        "y": str(node.position.y - node.height / 2),
        "w": str(node.width),
        "h": str(node.height),
    }


def points_to_edit_points_text(points: typing.Any) -> str:
    """Format a list of Points as CellDesigner edit points text.

    Args:
        points: List of Point.

    Returns:
        Space-separated "x,y" pairs, e.g. "0.5,0.3 0.7,-0.1".
    """
    return " ".join(f"{p.x},{p.y}" for p in points)


_ALL_ANCHOR_NAMES = list(LINK_ANCHOR_POSITION_TO_ANCHOR_NAME.values())


def infer_anchor_name(
    species_layout: typing.Any, point: typing.Any, tol: float = 1e-3
) -> str:
    """Try all 16 named anchors; return closest if within tolerance, else 'center'.

    Args:
        species_layout: A layout element with anchor_point() method.
        point: The Point to match.
        tol: Absolute tolerance for coordinate matching.

    Returns:
        Anchor name string (e.g. "north", "south_east", or "center").
    """
    for anchor_name in _ALL_ANCHOR_NAMES:
        anchor_point = species_layout.anchor_point(anchor_name)
        if math.isclose(anchor_point.x, point.x, abs_tol=tol) and math.isclose(
            anchor_point.y, point.y, abs_tol=tol
        ):
            return anchor_name
    return "center"


def compute_cd_angle(
    modification_position: typing.Any, species_layout: typing.Any
) -> float:
    """Compute the CellDesigner angle for a modification residue position.

    Reverses the forward transform in _layout.make_species_modification:
    cd_angle -> Point(W*cos, H*sin) -> atan2 -> own_angle -> position.

    The y-axis is negated because screen coordinates (y-down) differ from
    the math convention (y-up) used in own_angle. The result is normalized
    to [0, 2*pi) to match CellDesigner's angle convention.

    Args:
        modification_position: The position of the modification layout.
        species_layout: The parent species layout element.

    Returns:
        The CellDesigner angle as a float (radians), in [0, 2*pi).
    """
    center = species_layout.center()
    delta_x = modification_position.x - center.x
    delta_y = -(modification_position.y - center.y)
    if abs(delta_x) < 1e-10 and abs(delta_y) < 1e-10:
        return 0.0
    intermediate_angle = math.atan2(delta_y, delta_x)
    width = species_layout.width
    height = species_layout.height
    cd_angle = math.atan2(
        width * math.sin(intermediate_angle),
        height * math.cos(intermediate_angle),
    )
    if cd_angle < 0.0:
        cd_angle += 2 * math.pi
    return cd_angle + 0.0  # normalize -0.0 to 0.0


def build_frame_and_inverse(
    origin: typing.Any, unit_x: typing.Any, unit_y: typing.Any
) -> typing.Any:
    """Build a coordinate frame and return its inverse transformation.

    Perturbs the frame points when they are degenerate (coincident or
    collinear) so the returned transformation is always invertible.

    Args:
        origin: Origin point.
        unit_x: Unit x-axis point.
        unit_y: Unit y-axis point.

    Returns:
        The inverse MatrixTransformation.
    """
    origin, unit_x, unit_y = make_non_degenerate_frame(origin, unit_x, unit_y)
    transformation = get_transformation_for_frame(origin, unit_x, unit_y)
    return transformation.inverted()


def perp_point(origin: typing.Any, unit_x: typing.Any) -> typing.Any:
    """Compute the perpendicular (90 degree rotation) of unit_x around origin.

    Args:
        origin: Rotation center.
        unit_x: Point to rotate.

    Returns:
        Rotated point.
    """
    return unit_x.transformed(Rotation(math.radians(90), origin))


def inverse_edit_points_non_t_shape(
    reaction_layout: typing.Any, reactant_layout: typing.Any, product_layout: typing.Any
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a non-T-shape (1->1) reaction.

    Mirrors make_segments_non_t_shape in _layout.py but runs the inverse
    transformation.

    Args:
        reaction_layout: The reaction layout element with segments.
        reactant_layout: The base reactant species layout.
        product_layout: The base product species layout.

    Returns:
        Tuple of (edit_points, reactant_anchor_name, product_anchor_name,
        rectangle_index).
    """
    points = reaction_layout.points()
    start_point = points[0]
    end_point = points[-1]
    intermediate_points = points[1:-1]
    reactant_anchor_name = infer_anchor_name(reactant_layout, start_point)
    product_anchor_name = infer_anchor_name(product_layout, end_point)
    origin = reactant_layout.anchor_point(reactant_anchor_name)
    unit_x = product_layout.anchor_point(product_anchor_name)
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    rectangle_index = reaction_layout.reaction_node_segment
    return edit_points, reactant_anchor_name, product_anchor_name, rectangle_index


def inverse_edit_points_left_t_shape(
    reaction_layout: typing.Any,
    reactant_layouts: typing.Any,
    product_layout: typing.Any,
    base_reactant_consumption_layouts: typing.Any,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a left-T-shape (2+->1) reaction.

    Args:
        reaction_layout: The reaction layout element with segments.
        reactant_layouts: List of base reactant species layouts (len >= 2).
        product_layout: The base product species layout.
        base_reactant_consumption_layouts: List of consumption layouts for the
            base reactants.

    Returns:
        Tuple of (all_edit_points_text, num0, num1, num2, t_shape_index,
        product_anchor_name, reactant_anchor_names).
    """
    reactant_layout_0 = reactant_layouts[0]
    reactant_layout_1 = reactant_layouts[1]
    # Frame 1: used to encode the T-junction position
    origin_f1 = reactant_layout_0.center()
    unit_x_f1 = reactant_layout_1.center()
    unit_y_f1 = product_layout.center()
    inverse_f1 = build_frame_and_inverse(origin_f1, unit_x_f1, unit_y_f1)
    # The T-junction is the start point of the main reaction path
    t_junction = reaction_layout.points()[0]
    t_junction_in_frame = t_junction.transformed(inverse_f1)
    # Frame 2: main path from T-junction to product
    product_anchor_name = infer_anchor_name(
        product_layout, reaction_layout.points()[-1]
    )
    origin_f2 = t_junction
    unit_x_f2 = product_layout.anchor_point(product_anchor_name)
    unit_y_f2 = perp_point(origin_f2, unit_x_f2)
    inverse_f2 = build_frame_and_inverse(origin_f2, unit_x_f2, unit_y_f2)
    # Main path intermediate points (excluding start and end)
    main_points = reaction_layout.points()
    main_intermediate = main_points[1:-1]
    main_edit_points = [p.transformed(inverse_f2) for p in main_intermediate]
    num2 = len(main_edit_points)
    # Branch edit points for each base reactant
    branch_edit_points_list = []
    reactant_anchor_names = []
    for i, (reactant_layout, consumption_layout) in enumerate(
        zip(reactant_layouts, base_reactant_consumption_layouts)
    ):
        reactant_anchor_name = infer_anchor_name(
            reactant_layout, consumption_layout.points()[0]
        )
        reactant_anchor_names.append(reactant_anchor_name)
        branch_origin = t_junction
        branch_unit_x = reactant_layout.anchor_point(reactant_anchor_name)
        branch_unit_y = perp_point(branch_origin, branch_unit_x)
        branch_inverse = build_frame_and_inverse(
            branch_origin, branch_unit_x, branch_unit_y
        )
        # Branch intermediate points (consumption layouts go from species
        # to T-junction, so we reverse and strip endpoints)
        branch_points = consumption_layout.points()
        # The consumption layout goes: species_border -> ... -> reaction_border
        # We need the intermediate points in the direction species -> t_junction
        branch_intermediate = branch_points[1:-1]
        # Reverse since consumption is species->reaction but the frame is
        # t_junction->species
        branch_intermediate = list(reversed(branch_intermediate))
        branch_edit = [p.transformed(branch_inverse) for p in branch_intermediate]
        branch_edit_points_list.append(branch_edit)
    num0 = len(branch_edit_points_list[0]) if len(branch_edit_points_list) > 0 else 0
    num1 = len(branch_edit_points_list[1]) if len(branch_edit_points_list) > 1 else 0
    # Concatenate: branch0 + branch1 + main + t_junction
    all_edit_points = []
    for branch_edit in branch_edit_points_list:
        all_edit_points.extend(branch_edit)
    all_edit_points.extend(main_edit_points)
    all_edit_points.append(t_junction_in_frame)
    t_shape_index = reaction_layout.reaction_node_segment
    return (
        all_edit_points,
        num0,
        num1,
        num2,
        t_shape_index,
        product_anchor_name,
        reactant_anchor_names,
    )


def inverse_edit_points_right_t_shape(
    reaction_layout: typing.Any,
    reactant_layout: typing.Any,
    product_layouts: typing.Any,
    base_product_production_layouts: typing.Any,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a right-T-shape (1->2+) reaction.

    Args:
        reaction_layout: The reaction layout element with segments.
        reactant_layout: The base reactant species layout.
        product_layouts: List of base product species layouts (len >= 2).
        base_product_production_layouts: List of production layouts for the
            base products.

    Returns:
        Tuple of (all_edit_points_text, num0, num1, num2, t_shape_index,
        reactant_anchor_name, product_anchor_names).
    """
    product_layout_0 = product_layouts[0]
    product_layout_1 = product_layouts[1]
    # Frame 1: used to encode the T-junction position
    origin_f1 = reactant_layout.center()
    unit_x_f1 = product_layout_0.center()
    unit_y_f1 = product_layout_1.center()
    inverse_f1 = build_frame_and_inverse(origin_f1, unit_x_f1, unit_y_f1)
    # The T-junction is the end point of the main reaction path
    t_junction = reaction_layout.points()[-1]
    t_junction_in_frame = t_junction.transformed(inverse_f1)
    # Frame 2: main path from reactant to T-junction
    reactant_anchor_name = infer_anchor_name(
        reactant_layout, reaction_layout.points()[0]
    )
    origin_f2 = t_junction
    unit_x_f2 = reactant_layout.anchor_point(reactant_anchor_name)
    unit_y_f2 = perp_point(origin_f2, unit_x_f2)
    inverse_f2 = build_frame_and_inverse(origin_f2, unit_x_f2, unit_y_f2)
    # Main path intermediate points in reversed order (excluding start and end)
    main_points = reaction_layout.points()
    main_intermediate = main_points[1:-1]
    main_intermediate_reversed = list(reversed(main_intermediate))
    main_edit_points = [p.transformed(inverse_f2) for p in main_intermediate_reversed]
    # num0 for right T-shape corresponds to main path points
    num0 = len(main_edit_points)
    # Branch edit points for each base product
    branch_edit_points_list = []
    product_anchor_names = []
    for i, (product_layout_elem, production_layout) in enumerate(
        zip(product_layouts, base_product_production_layouts)
    ):
        product_anchor_name = infer_anchor_name(
            product_layout_elem, production_layout.points()[-1]
        )
        product_anchor_names.append(product_anchor_name)
        branch_origin = t_junction
        branch_unit_x = product_layout_elem.anchor_point(product_anchor_name)
        branch_unit_y = perp_point(branch_origin, branch_unit_x)
        branch_inverse = build_frame_and_inverse(
            branch_origin, branch_unit_x, branch_unit_y
        )
        branch_points = production_layout.points()
        branch_intermediate = branch_points[1:-1]
        branch_edit = [p.transformed(branch_inverse) for p in branch_intermediate]
        branch_edit_points_list.append(branch_edit)
    num1 = len(branch_edit_points_list[0]) if len(branch_edit_points_list) > 0 else 0
    num2 = len(branch_edit_points_list[1]) if len(branch_edit_points_list) > 1 else 0
    # Concatenate: main + branch0 + branch1 + t_junction
    all_edit_points = []
    all_edit_points.extend(main_edit_points)
    for branch_edit in branch_edit_points_list:
        all_edit_points.extend(branch_edit)
    all_edit_points.append(t_junction_in_frame)
    # t_shape_index for right T-shape: reader computes
    # len(segments) - 1 - t_shape_index_from_xml
    # so we need: t_shape_index_from_xml = len(segments) - 1 - reaction_node_segment
    n_segments = len(reaction_layout.segments)
    t_shape_index = n_segments - 1 - reaction_layout.reaction_node_segment
    return (
        all_edit_points,
        num0,
        num1,
        num2,
        t_shape_index,
        reactant_anchor_name,
        product_anchor_names,
    )


def inverse_edit_points_modifier(
    modifier_layout: typing.Any,
    source_layout: typing.Any,
    reaction_layout: typing.Any,
    has_boolean_input: bool,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a modifier arc.

    Uses the arc's endpoint on the reaction side as the coordinate
    frame basis (unit_x), matching the reader's use of the target
    anchor point.  Falls back to the reaction node center when the
    endpoint equals the reaction node position (no targetLineIndex
    offset).

    Args:
        modifier_layout: The modifier layout element with segments.
        source_layout: The source species or gate layout.
        reaction_layout: The parent reaction layout.
        has_boolean_input: Whether the modifier has boolean gate input.

    Returns:
        Tuple of (edit_points, source_anchor_name).
    """
    points = modifier_layout.points()
    intermediate_points = points[1:-1]
    if has_boolean_input:
        source_anchor_name = "center"
    else:
        source_anchor_name = infer_anchor_name(source_layout, points[0])
    origin = source_layout.anchor_point(source_anchor_name)
    target_point = points[-1]
    unit_x = target_point
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points, source_anchor_name


def inverse_edit_points_reactant_link(
    reactant_link_layout: typing.Any,
    species_layout: typing.Any,
    reaction_layout: typing.Any,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a reactant link.

    Args:
        reactant_link_layout: The consumption layout for the link.
        species_layout: The species layout for the reactant.
        reaction_layout: The parent reaction layout.

    Returns:
        Tuple of (edit_points, anchor_name).
    """
    points = reactant_link_layout.points()
    anchor_name = infer_anchor_name(species_layout, points[0])
    if anchor_name == "center":
        origin = species_layout.center()
    else:
        origin = species_layout.anchor_point(anchor_name)
    unit_x = reaction_layout.left_connector_tip()
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    intermediate_points = points[1:-1]
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points, anchor_name


def inverse_edit_points_product_link(
    product_link_layout: typing.Any,
    species_layout: typing.Any,
    reaction_layout: typing.Any,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a product link.

    Args:
        product_link_layout: The production layout for the link.
        species_layout: The species layout for the product.
        reaction_layout: The parent reaction layout.

    Returns:
        Tuple of (edit_points, anchor_name).
    """
    points = product_link_layout.points()
    anchor_name = infer_anchor_name(species_layout, points[-1])
    origin = reaction_layout.right_connector_tip()
    if anchor_name == "center":
        unit_x = species_layout.center()
    else:
        unit_x = species_layout.anchor_point(anchor_name)
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    intermediate_points = points[1:-1]
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points, anchor_name


def inverse_edit_points_reactant_from_base(
    consumption_layout: typing.Any,
    species_layout: typing.Any,
    reaction_layout: typing.Any,
    reactant_anchor_name: typing.Any,
) -> list[typing.Any]:
    """Compute frame-space edit points for a base reactant in T-shape.

    Args:
        consumption_layout: The consumption layout.
        species_layout: The species layout.
        reaction_layout: The parent reaction layout.
        reactant_anchor_name: Pre-computed anchor name.

    Returns:
        List of frame-space edit points.
    """
    origin = reaction_layout.points()[0]
    unit_x = species_layout.anchor_point(reactant_anchor_name)
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    points = consumption_layout.points()
    intermediate_points = list(reversed(points[1:-1]))
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points


def inverse_edit_points_product_from_base(
    production_layout: typing.Any,
    species_layout: typing.Any,
    reaction_layout: typing.Any,
    product_anchor_name: typing.Any,
) -> list[typing.Any]:
    """Compute frame-space edit points for a base product in T-shape.

    Args:
        production_layout: The production layout.
        species_layout: The species layout.
        reaction_layout: The parent reaction layout.
        product_anchor_name: Pre-computed anchor name.

    Returns:
        List of frame-space edit points.
    """
    origin = reaction_layout.points()[-1]
    unit_x = species_layout.anchor_point(product_anchor_name)
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    points = production_layout.points()
    intermediate_points = points[1:-1]
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points


def inverse_edit_points_modulation(
    modulation_layout: typing.Any,
    source_layout: typing.Any,
    target_layout: typing.Any,
    has_boolean_input: bool,
) -> tuple[typing.Any, ...]:
    """Compute frame-space edit points for a modulation (false reaction).

    Args:
        modulation_layout: The modulation layout element with segments.
        source_layout: The source species or gate layout.
        target_layout: The target species layout.
        has_boolean_input: Whether the modulation has boolean gate input.

    Returns:
        Tuple of (edit_points, source_anchor_name, target_anchor_name).
    """
    points = modulation_layout.points()
    intermediate_points = points[1:-1]
    if has_boolean_input:
        source_anchor_name = "center"
    else:
        source_anchor_name = infer_anchor_name(source_layout, points[0])
    target_anchor_name = infer_anchor_name(target_layout, points[-1])
    origin = source_layout.anchor_point(source_anchor_name)
    unit_x = target_layout.anchor_point(target_anchor_name)
    unit_y = perp_point(origin, unit_x)
    inverse = build_frame_and_inverse(origin, unit_x, unit_y)
    edit_points = [p.transformed(inverse) for p in intermediate_points]
    return edit_points, source_anchor_name, target_anchor_name


# ---------------------------------------------------------------------------
# RDF annotation helpers
# ---------------------------------------------------------------------------

_RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"

_RDF_NSMAP = {
    "rdf": _RDF_NAMESPACE,
    "bqbiol": "http://biomodels.net/biology-qualifiers/",
    "bqmodel": "http://biomodels.net/model-qualifiers/",
}


def make_rdf_annotation(
    annotations: typing.Any, about_id: str
) -> lxml.etree._Element | None:
    """Build an ``<rdf:RDF>`` element holding BioModels.net annotations.

    Args:
        annotations: Iterable of ``momapy.sbml.model.RDFAnnotation``.
        about_id: The id referenced by
            ``<rdf:Description rdf:about="#...">``.

    Returns:
        An lxml element, or ``None`` if ``annotations`` is empty.
    """
    annotations = list(annotations)
    if not annotations:
        return None
    rdf_element = lxml.etree.Element(f"{{{_RDF_NAMESPACE}}}RDF", nsmap=_RDF_NSMAP)
    description = lxml.etree.SubElement(
        rdf_element,
        f"{{{_RDF_NAMESPACE}}}Description",
        attrib={f"{{{_RDF_NAMESPACE}}}about": f"#{about_id}"},
    )
    sorted_annotations = sorted(
        annotations,
        key=lambda annotation: (
            annotation.qualifier.__class__.__name__,
            annotation.qualifier.name,
            sorted(annotation.resources),
        ),
    )
    for annotation in sorted_annotations:
        qualifier_namespace, qualifier_tag = QUALIFIER_MEMBER_TO_QUALIFIER_ATTRIBUTE[
            annotation.qualifier
        ]
        bq_element = lxml.etree.SubElement(
            description, f"{{{qualifier_namespace}}}{qualifier_tag}"
        )
        bag_element = lxml.etree.SubElement(bq_element, f"{{{_RDF_NAMESPACE}}}Bag")
        for resource in sorted(annotation.resources):
            lxml.etree.SubElement(
                bag_element,
                f"{{{_RDF_NAMESPACE}}}li",
                attrib={f"{{{_RDF_NAMESPACE}}}resource": resource},
            )
    return rdf_element


def inject_rdf_into_celldesigner_notes(
    notes_element: lxml.etree._Element, rdf_element: lxml.etree._Element
) -> None:
    """Append an ``<rdf:RDF>`` element into the ``<body>`` of a CellDesigner notes.

    CellDesigner embeds RDF annotations for included species (subunits)
    inside the ``<html>/<body>`` of their ``<celldesigner:notes>`` element,
    alongside human-readable text. This helper ensures the scaffold exists
    and appends ``rdf_element`` as a child of the ``<body>``.

    Args:
        notes_element: The ``<celldesigner:notes>`` element.
        rdf_element: The ``<rdf:RDF>`` element to inject.
    """
    html = notes_element.find(f"{{{_XHTML_NAMESPACE}}}html")
    if html is None:
        html = lxml.etree.SubElement(notes_element, f"{{{_XHTML_NAMESPACE}}}html")
    body = html.find(f"{{{_XHTML_NAMESPACE}}}body")
    if body is None:
        body = lxml.etree.SubElement(html, f"{{{_XHTML_NAMESPACE}}}body")
    body.append(rdf_element)


ACTIVE_OVERLAY_LAYOUT_CLASSES = (
    AntisenseRNAActiveLayout,
    ComplexActiveLayout,
    DegradedActiveLayout,
    DrugActiveLayout,
    GeneActiveLayout,
    GenericProteinActiveLayout,
    IonActiveLayout,
    IonChannelActiveLayout,
    PhenotypeActiveLayout,
    RNAActiveLayout,
    ReceptorActiveLayout,
    SimpleMoleculeActiveLayout,
    TruncatedProteinActiveLayout,
    UnknownActiveLayout,
)

SBML_NS = "http://www.sbml.org/sbml/level2/version4"
XHTML_NS = "http://www.w3.org/1999/xhtml"

NSMAP = {
    None: SBML_NS,
    "celldesigner": CD_NAMESPACE,
}


def get_modulation_reaction_type(modulation: typing.Any) -> str:
    """Return the CellDesigner reaction type to write for a modulation.

    Inverse of ``normalize_modulation_class`` in ``_reading_classification.py``:
    a modulation whose target is not a `Phenotype` is written in CellDesigner's
    reduced notation where the class has one (`Inhibition` gives
    ``NEGATIVE_INFLUENCE``, `Modulation` gives ``REDUCED_MODULATION``), and in
    the plain form otherwise.

    Args:
        modulation: The modulation model element.

    Returns:
        The ``<celldesigner:reactionType>`` text.
    """
    reaction_types = CLASS_TO_MODULATION_REACTION_TYPES.get(type(modulation))
    if reaction_types is None:
        return "MODULATION"
    plain_reaction_type, reduced_reaction_type = reaction_types
    if reduced_reaction_type is not None and not isinstance(
        modulation.target, Phenotype
    ):
        return reduced_reaction_type
    return plain_reaction_type


@dataclasses.dataclass
class DegradedEntry:
    """One degraded participant emitted from layout (no model peer).

    ``link_arc`` is ``None`` when the degraded glyph is the reaction's
    base source/target (1-to-1 case); it is the connecting arc layout
    when the degraded glyph is reached via a separate Consumption /
    Production link arc (T-shape link case).
    """

    reaction: typing.Any = dataclasses.field(
        metadata={"description": "The reaction model element owning the participant."}
    )
    side: str = dataclasses.field(
        metadata={"description": 'The participant side, "reactant" or "product".'}
    )
    degraded_layout: typing.Any = dataclasses.field(
        metadata={"description": "The degraded glyph layout element."}
    )
    reaction_layout: typing.Any = dataclasses.field(
        metadata={"description": "The reaction layout element."}
    )
    link_arc: typing.Any = dataclasses.field(
        default=None,
        metadata={
            "description": "The connecting Consumption/Production link arc layout, or None when the degraded glyph is the reaction's base source/target."
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_lxml_element(
    tag: str,
    namespace: str | None = None,
    attributes: dict[str, str] | None = None,
    text: typing.Any = None,
    nsmap: dict[str | None, str] | None = None,
) -> lxml.etree._Element:
    """Create an lxml element."""
    lxml_tag = f"{{{namespace}}}{tag}" if namespace is not None else tag
    if nsmap is None:
        nsmap = {}
    if attributes is None:
        attributes = {}
    elem = lxml.etree.Element(lxml_tag, nsmap=nsmap, **attributes)
    if text is not None:
        elem.text = str(text)
    return elem


def make_celldesigner_element(
    tag: str, attributes: dict[str, str] | None = None, text: typing.Any = None
) -> lxml.etree._Element:
    """Shortcut for CellDesigner-namespaced element."""
    return make_lxml_element(
        tag, namespace=CD_NAMESPACE, attributes=attributes, text=text
    )


def make_sbml_element(
    tag: str,
    attributes: dict[str, str] | None = None,
    text: typing.Any = None,
    nsmap: dict[str | None, str] | None = None,
) -> lxml.etree._Element:
    """Shortcut for SBML-namespaced element."""
    return make_lxml_element(
        tag, namespace=SBML_NS, attributes=attributes, text=text, nsmap=nsmap
    )


def strip_active(species: typing.Any) -> str:
    """Raw species id derivation: strip the reader's ``_active`` suffixes.

    The reader appends ``_active`` to the model ``id_`` of active species
    aliases.  This recovers the underlying species id.  It is the
    phase-2 candidate derivation for a from-scratch species (a
    round-tripped species keeps its reserved source id instead).
    """
    if species is None:
        return ""
    id_str = species.id_ or ""
    while id_str.endswith("_active"):
        id_str = id_str[: -len("_active")]
    return id_str


def reserve_source_xml_ids(writing_context: typing.Any) -> None:
    """Reserve grammar-valid source ids before any projection (phase 1).

    For every model and layout element that carries a source id, reserve
    that id verbatim in ``element_to_xml_id`` (and mark it used) when it
    is already a valid SId.  Reservation is done *without* deduplication,
    so round-trips are byte-identical and several elements that share a
    source id (e.g. CellDesigner active/inactive species, both named
    ``s1``) keep sharing the emitted id.  Must run before any id is
    emitted.

    Args:
        writing_context: The current writing context.
    """
    model_map = writing_context.source_id_to_model_element
    if model_map is not None:
        for element_id, source_ids in model_map.inverse.items():
            chosen = min(source_ids, key=lambda source_id: (len(source_id), source_id))
            if chosen and ensure_sbml_sid(chosen) == chosen:
                writing_context.element_to_xml_id[element_id] = chosen
                writing_context.used_xml_ids.add(chosen)
                writing_context.candidate_to_xml_id[chosen] = chosen
    layout_map = writing_context.source_id_to_layout_element
    if layout_map is not None:
        element_id_to_source_ids = {}
        for source_id, layout_element in layout_map.items():
            if not source_id:
                continue
            element_id_to_source_ids.setdefault(id(layout_element), set()).add(
                source_id
            )
        for element_id, source_ids in element_id_to_source_ids.items():
            chosen = min(source_ids, key=lambda source_id: (len(source_id), source_id))
            if ensure_sbml_sid(chosen) == chosen:
                writing_context.element_to_xml_id[element_id] = chosen
                writing_context.used_xml_ids.add(chosen)
                writing_context.candidate_to_xml_id[chosen] = chosen


def get_xml_id(
    writing_context: typing.Any,
    element: typing.Any,
    candidate: str | None = None,
    share: bool = True,
    memoize: bool = True,
) -> str:
    """Return the valid SId to emit for ``element`` (phase 2).

    Resolution order: the per-object memo (a phase-1 reservation or an
    earlier call), then — when ``share`` — the per-candidate memo (so an
    emission matches a reserved source id by *string* even if it is keyed
    by a different object, e.g. a reaction emitted via its layout glyph
    whose source id was reserved on the reaction model), then projection
    of ``candidate`` to the SBML SId grammar made unique.  This single
    chokepoint is what enforces id consistency — every id-emitting site
    must go through it (never a bare ``make_unique_xml_id``, which would
    re-suffix a reserved source id).

    Args:
        writing_context: The current writing context.
        element: The element to emit an id for (keyed by ``id(element)``).
        candidate: Optional raw id to project instead of ``element.id_``
            (e.g. the ``_active``-stripped species id, or a participant's
            preferred metaid).  Ignored on a memo hit.
        share: When ``True`` (default), elements with the same
            ``candidate`` emit the *same* id — they name one entity (an
            SId, referenced from many sites; CellDesigner also holds
            several distinct model objects for one included species).
            Pass ``False`` for ``metaid``, an ``xsd:ID`` that must differ
            across the several XML elements that may serialize one
            participant.
        memoize: When ``True`` (default), the assigned id is stored so the
            same object always re-emits it.  Pass ``False`` for ``metaid``
            so each call re-uniquifies; a phase-1 reservation is still
            honoured (the object memo is read), so round-tripped source
            metaids stay verbatim.

    Returns:
        The XML id string to emit.
    """
    element_id = id(element)
    existing = writing_context.element_to_xml_id.get(element_id)
    if existing is not None:
        return existing
    if candidate is None:
        candidate = element.id_ or ""
    if share:
        shared = writing_context.candidate_to_xml_id.get(candidate)
        if shared is not None:
            if memoize:
                writing_context.element_to_xml_id[element_id] = shared
            return shared
    final = make_unique_xml_id(ensure_sbml_sid(candidate), writing_context.used_xml_ids)
    if share:
        writing_context.candidate_to_xml_id[candidate] = final
    if memoize:
        writing_context.element_to_xml_id[element_id] = final
    return final


def get_species_id(species: typing.Any, writing_context: typing.Any) -> str:
    """Canonical SBML species id for a model species.

    Thin wrapper over ``get_xml_id`` with ``share=True``: a round-tripped
    species returns its reserved source id; a from-scratch one returns
    its ``_active``-stripped ``id_`` projected to an SId.  Sharing makes
    the several distinct model objects CellDesigner holds for one
    included species emit a single species id, so the included-species
    dedup (``seen_ids``) collapses them to one ``<species>``.
    """
    if species is None:
        return ""
    return get_xml_id(
        writing_context, species, candidate=strip_active(species), share=True
    )


def get_alias_id(writing_context: typing.Any, alias_layout: typing.Any) -> str:
    """XML id to emit for a reference to an alias layout element.

    Routes through ``get_xml_id`` so the reference matches the alias
    definition (``<speciesAlias id=...>`` etc.); returns ``""`` when the
    alias layout is missing, preserving the writer's prior behaviour.
    """
    if alias_layout is None:
        return ""
    return get_xml_id(writing_context, alias_layout)


def get_line_attributes(
    layout: typing.Any, include_type: bool = False
) -> dict[str, str]:
    """Build attributes dict for a ``<cd:line>`` element from a layout.

    Reads ``path_stroke_width`` and ``path_stroke`` from the layout,
    falling back to sensible defaults.

    Args:
        layout: A layout element with path_stroke / path_stroke_width.
        include_type: Whether to include ``type="Straight"``.

    Returns:
        A dict of XML attributes.
    """
    width = "1.0"
    color = "ff000000"
    if layout is not None:
        if getattr(layout, "path_stroke_width", None) is not None:
            width = str(layout.path_stroke_width)
        stroke = getattr(layout, "path_stroke", None)
        if isinstance(stroke, Color):
            color = color_to_cd_hex(stroke)
    attrs = {"width": width, "color": color}
    if include_type:
        attrs["type"] = "Straight"
    return attrs


def get_layout_model_mapping(writing_context: typing.Any) -> typing.Any:
    """Shortcut to access layout_model_mapping."""
    return writing_context.map_.layout_model_mapping


def degraded_species_id(
    writing_context: typing.Any, degraded_layout: typing.Any
) -> str:
    """Synthetic SBML species id for a degraded layout glyph.

    Derived (class (d)) from the glyph's *projected* alias id, so the
    degraded species id and its alias id stay consistent and valid even
    for a from-scratch (UUID) layout.
    """
    return f"degraded_{get_xml_id(writing_context, degraded_layout)}"


def is_degraded_layout(layout_element: typing.Any) -> bool:
    return isinstance(layout_element, (DegradedLayout, DegradedActiveLayout))


def collect_degraded_entries(writing_context: typing.Any) -> list["DegradedEntry"]:
    """Build the list of degraded-side participants for flagged reactions.

    A flagged reaction (``has_external_source`` or ``has_external_sink``)
    has a corresponding ``DegradedLayout`` / ``DegradedActiveLayout`` on
    the affected side. That degraded glyph may be the reaction layout's
    base source/target (1-to-1 case) or be linked via a separate
    Consumption / Production arc (T-shape link case).
    """
    entries = []
    layout = writing_context.map_.layout
    if layout is None:
        return entries
    for reaction in writing_context.map_.model.reactions:
        flagged_source = getattr(reaction, "has_external_source", False)
        flagged_sink = getattr(reaction, "has_external_sink", False)
        if not flagged_source and not flagged_sink:
            continue
        for layout_key in get_layouts(writing_context, reaction):
            if not isinstance(layout_key, frozenset):
                continue
            reaction_layout = get_reaction_layout(layout_key)
            if reaction_layout is None:
                continue
            if flagged_source:
                if is_degraded_layout(reaction_layout.source):
                    entries.append(
                        DegradedEntry(
                            reaction=reaction,
                            side="reactant",
                            degraded_layout=reaction_layout.source,
                            reaction_layout=reaction_layout,
                            link_arc=None,
                        )
                    )
                else:
                    for arc in layout.layout_elements:
                        if (
                            isinstance(arc, ConsumptionLayout)
                            and arc.source is reaction_layout
                            and is_degraded_layout(arc.target)
                        ):
                            entries.append(
                                DegradedEntry(
                                    reaction=reaction,
                                    side="reactant",
                                    degraded_layout=arc.target,
                                    reaction_layout=reaction_layout,
                                    link_arc=arc,
                                )
                            )
            if flagged_sink:
                if is_degraded_layout(reaction_layout.target):
                    entries.append(
                        DegradedEntry(
                            reaction=reaction,
                            side="product",
                            degraded_layout=reaction_layout.target,
                            reaction_layout=reaction_layout,
                            link_arc=None,
                        )
                    )
                else:
                    for arc in layout.layout_elements:
                        if (
                            isinstance(arc, ProductionLayout)
                            and arc.source is reaction_layout
                            and is_degraded_layout(arc.target)
                        ):
                            entries.append(
                                DegradedEntry(
                                    reaction=reaction,
                                    side="product",
                                    degraded_layout=arc.target,
                                    reaction_layout=reaction_layout,
                                    link_arc=arc,
                                )
                            )
    return entries


def degraded_entries_for_reaction(
    writing_context: typing.Any, reaction: typing.Any, side: str
) -> list["DegradedEntry"]:
    return [
        e
        for e in writing_context.degraded_entries
        if e.reaction is reaction and e.side == side
    ]


def sort_modifications_by_layout(
    writing_context: typing.Any, species: typing.Any
) -> list[typing.Any]:
    """Sort a species' modifications by their layout child order.

    The modification layout children of the species' alias layout
    preserve the original XML order.  We use that to sort the
    frozenset of model modifications.
    """
    modifications = list(species.modifications)
    # Find any alias layout for this species — search both top-level
    # and complex children.
    alias_layout = find_any_alias_layout(writing_context, species)
    if alias_layout is None:
        return modifications
    # Build residue_id -> position from layout children.
    # The layout id = f"{alias_species_id}_{xml_residue_id}_layout"
    # where alias_species_id may differ from the model species id
    # for subunit aliases.
    residue_order = {}
    suffix = "_layout"
    for i, child in enumerate(alias_layout.layout_elements):
        if isinstance(child, ModificationLayout):
            layout_id = child.id_
            if layout_id.endswith(suffix):
                # Strip the suffix and the species prefix to get residue id
                # The prefix is everything up to the first residue id part
                core = layout_id[: -len(suffix)]
                # Match against known residue ids from the template
                for mod in modifications:
                    if mod.residue is not None:
                        xml_residue_id = strip_template_prefix(mod.residue, species)
                        if core.endswith(f"_{xml_residue_id}"):
                            residue_order[xml_residue_id] = i
                            break
    # Sort by layout order
    modifications.sort(
        key=lambda m: residue_order.get(
            strip_template_prefix(m.residue, species) if m.residue else "",
            float("inf"),
        )
    )
    return modifications


def find_any_alias_layout(
    writing_context: typing.Any, species: typing.Any
) -> typing.Any:
    """Find any alias layout for a species, including inside complexes."""
    # Try direct lookup first
    for layout_key in get_layouts(writing_context, species):
        if isinstance(layout_key, frozenset):
            continue
        if isinstance(layout_key, CellDesignerNode):
            return layout_key
    # Search in layout_model_mapping for this species
    mapping = get_layout_model_mapping(writing_context)
    for layout_element in writing_context.map_.layout.layout_elements:
        if not isinstance(layout_element, CellDesignerNode):
            continue
        if not hasattr(layout_element, "layout_elements"):
            continue
        # Search children of complexes
        for child in layout_element.layout_elements:
            if not isinstance(child, CellDesignerNode):
                continue
            model_info = mapping.get_mapping(child)
            if model_info is species:
                return child
            if hasattr(child, "layout_elements"):
                for grandchild in child.layout_elements:
                    if not isinstance(
                        grandchild,
                        CellDesignerNode,
                    ):
                        continue
                    model_info2 = mapping.get_mapping(grandchild)
                    if model_info2 is species:
                        return grandchild
    return None


def strip_template_prefix(residue_or_region: typing.Any, owner: typing.Any) -> str:
    """Strip the template id prefix from a residue or region id.

    Model ids for ModificationResidue and Region are composite:
    ``f"{template_id}_{local_id}"``.  CellDesigner XML expects just
    the local id.  *owner* can be a species (with a `template`
    attribute) or the template itself.
    """
    template = getattr(owner, "template", owner)
    if template is not None and hasattr(template, "id_"):
        prefix = f"{template.id_}_"
        if residue_or_region.id_.startswith(prefix):
            return residue_or_region.id_[len(prefix) :]
    return residue_or_region.id_


def build_layout_order_index(layout: typing.Any) -> dict[str, int]:
    """Build a mapping from layout element id to position index.

    Walks the layout tree recursively so that both top-level and
    nested (complex children) elements get an index reflecting
    their original ordering.
    """
    index = {}
    counter = [0]

    def _walk(elements: typing.Any) -> None:
        for element in elements:
            index[element.id_] = counter[0]
            counter[0] += 1
            if hasattr(element, "layout_elements"):
                _walk(element.layout_elements)

    _walk(layout.layout_elements)
    return index


def sort_aliases_by_layout_order(
    list_elem: lxml.etree._Element, layout_order_index: dict[str, int]
) -> None:
    """Sort alias XML children of list_elem by layout element order."""
    sort_xml_children_by_key(
        list_elem,
        key_func=lambda alias: layout_order_index.get(alias.get("id"), float("inf")),
    )


def sort_xml_children_by_key(
    list_elem: lxml.etree._Element, key_func: typing.Any
) -> None:
    """Sort XML children of list_elem using the given key function."""
    children = list(list_elem)
    if len(children) <= 1:
        return
    for child in children:
        list_elem.remove(child)
    children.sort(key=key_func)
    for child in children:
        list_elem.append(child)


def participant_layout_position(
    writing_context: typing.Any,
    participant: typing.Any,
    reaction: typing.Any,
    frozenset_mapping: typing.Any,
    reaction_layout: typing.Any,
    is_start: bool,
    arc_order: typing.Any,
) -> float:
    """Get the layout position for a reaction participant.

    Uses the arc alias order mapping to determine position.
    Falls back to infinity for participants without a layout arc.
    """
    alias_layout = find_layout_for_participant(
        writing_context,
        participant,
        reaction,
        frozenset_mapping,
        reaction_layout,
        is_start,
    )
    if alias_layout is not None:
        return arc_order.get(alias_layout.id_, float("inf"))
    return float("inf")


def build_arc_alias_order(
    writing_context: typing.Any, reaction_layout: typing.Any, arc_cls: typing.Any
) -> dict[str, int]:
    """Build a mapping from alias id to layout position for arcs of a reaction.

    For each arc of the given class connected to the reaction layout,
    maps the arc's target alias id to its position in the layout.
    """
    order = {}
    for i, element in enumerate(writing_context.map_.layout.layout_elements):
        if (
            isinstance(element, arc_cls)
            and element.source is reaction_layout
            and element.target is not None
        ):
            order[element.target.id_] = i
    return order


def sort_reactions_by_layout_order(
    list_elem: lxml.etree._Element, layout_order_index: dict[str, int]
) -> None:
    """Sort reaction XML children of list_elem by layout element order.

    Each reaction's layout element id follows the pattern
    ``f"{reaction_id}_layout"``, so we derive the sort key from
    the reaction's ``id`` attribute.
    """
    sort_xml_children_by_key(
        list_elem,
        key_func=lambda reaction: layout_order_index.get(
            f"{reaction.get('id')}_layout", float("inf")
        ),
    )


def get_layouts(
    writing_context: typing.Any, model_element: typing.Any
) -> list[typing.Any]:
    """Get layout elements for a model element.

    Returns a list. Items can be single layout elements or frozensets.
    """
    result = get_layout_model_mapping(writing_context).get_mapping(model_element)
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return [result]


def find_layout_for_species_in_frozenset(
    writing_context: typing.Any, species: typing.Any, frozenset_mapping: typing.Any
) -> typing.Any:
    """Find the layout element for a species within a reaction frozenset."""
    for elem in frozenset_mapping:
        model = get_layout_model_mapping(writing_context).get_mapping(elem)
        if model is species:
            return elem
    return None


def find_layout_for_participant(
    writing_context: typing.Any,
    participant: typing.Any,
    reaction: typing.Any,
    frozenset_mapping: typing.Any,
    reaction_layout: typing.Any,
    is_start: bool,
) -> typing.Any:
    """Find the alias layout for a specific reaction participant.

    For base participants, the alias is the reaction layout's source
    (reactants) or target (products).  For link participants, the alias
    is resolved via the ConsumptionLayout/ProductionLayout stored in the
    layout-model mapping for the (participant, reaction) tuple.

    Falls back to ``find_layout_for_species_in_frozenset`` when the
    more precise lookup fails.

    Args:
        writing_context: The writing context.
        participant: The Reactant or Product model element.
        reaction: The reaction model element.
        frozenset_mapping: The frozenset key for this reaction.
        reaction_layout: The ReactionLayout element.
        is_start: True for reactants, False for products.

    Returns:
        The alias layout element, or None.
    """
    if participant.base and reaction_layout is not None:
        result = reaction_layout.source if is_start else reaction_layout.target
        if result is not None:
            return result
    arc_layouts = get_layout_model_mapping(writing_context).get_child_layout_elements(
        participant, reaction
    )
    for arc_layout in arc_layouts:
        if hasattr(arc_layout, "target"):
            if frozenset_mapping is not None and arc_layout not in frozenset_mapping:
                continue
            return arc_layout.target
    species = participant.referred_element
    if frozenset_mapping is not None:
        return find_layout_for_species_in_frozenset(
            writing_context, species, frozenset_mapping
        )
    return None


def get_reaction_layout(frozenset_mapping: typing.Any) -> typing.Any:
    """Extract the ReactionLayout from a frozenset."""
    for elem in frozenset_mapping:
        if isinstance(elem, ReactionLayout):
            return elem
    return None


def collect_arcs_for_reaction(
    writing_context: typing.Any,
    reaction_layout: typing.Any,
    arc_cls: typing.Any,
    exclude_alias: typing.Any = None,
) -> list[typing.Any]:
    """Collect arc layouts of a given type connected to a reaction layout.

    Args:
        writing_context: The writing context.
        reaction_layout: The ReactionLayout element.
        arc_cls: The arc class to filter (ConsumptionLayout or ProductionLayout).
        exclude_alias: An optional alias layout to exclude (e.g. the base
            reactant/product alias which is already handled separately).

    Returns:
        A list of arc layouts.
    """
    arcs = []
    for layout_element_item in writing_context.map_.layout.layout_elements:
        if (
            isinstance(layout_element_item, arc_cls)
            and layout_element_item.source is reaction_layout
            and (
                exclude_alias is None or layout_element_item.target is not exclude_alias
            )
        ):
            arcs.append(layout_element_item)
    return arcs


def species_class_string(species: typing.Any) -> str:
    """Map a species model class to its CellDesigner class string."""
    return _CLASS_TO_CD_STRING.get(type(species), "UNKNOWN")


def template_ref_tag(template: typing.Any) -> str:
    """Map a template to its XML reference tag name."""
    if isinstance(template, ProteinTemplate):
        return "proteinReference"
    if isinstance(template, GeneTemplate):
        return "geneReference"
    if isinstance(template, RNATemplate):
        return "rnaReference"
    if isinstance(template, AntisenseRNATemplate):
        return "antisensernaReference"
    return "proteinReference"


def modification_state_string(state: typing.Any) -> str:
    """Convert modification state to CellDesigner string."""
    if state is None:
        return "empty"
    name = state.name if hasattr(state, "name") else str(state)
    return _MODIFICATION_STATE_TO_CD.get(name, "empty")


def anchor_name_to_position(anchor_name: typing.Any) -> str | None:
    """Convert an anchor name to CellDesigner link anchor position string."""
    return _ANCHOR_NAME_TO_LINK_ANCHOR_POSITION.get(anchor_name)


def compute_target_line_index(
    reaction_layout: typing.Any, modifier_arc: typing.Any
) -> str:
    """Compute the CellDesigner targetLineIndex for a modifier.

    The targetLineIndex is "segmentIndex,anchorId" where anchorId identifies
    which corner/side of the reaction rectangle the modifier connects to.
    The reaction rectangle is 10x10 centered on the reaction node, rotated
    by the reaction line angle.

    Anchor positions:
        2=top, 3=bottom, 4=top-left, 5=top-right, 6=bottom-left, 7=bottom-right
    """
    import math

    RECT_HALF = 5.0
    mid = reaction_layout._get_reaction_node_position()
    # Reaction line angle from the center segment
    points = reaction_layout.points()
    n_segments = len(reaction_layout.segments)
    seg_idx = reaction_layout.reaction_node_segment
    if seg_idx < n_segments:
        segment = reaction_layout.segments[seg_idx]
        delta_x = segment.p2.x - segment.p1.x
        delta_y = segment.p2.y - segment.p1.y
    else:
        delta_x = points[-1].x - points[0].x
        delta_y = points[-1].y - points[0].y
    angle = math.atan2(delta_y, delta_x)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    # Build the 6 anchor points (offsets rotated by angle)
    offsets = {
        "2": (0, -RECT_HALF),
        "3": (0, RECT_HALF),
        "4": (-RECT_HALF, -RECT_HALF),
        "5": (RECT_HALF, -RECT_HALF),
        "6": (-RECT_HALF, RECT_HALF),
        "7": (RECT_HALF, RECT_HALF),
    }
    # Modifier arc endpoint (the end closest to the reaction)
    arc_pts = modifier_arc.points()
    end_point = arc_pts[-1]
    best_id = "2"
    best_dist = float("inf")
    for anchor_id, (offset_x, offset_y) in offsets.items():
        rotated_x = mid.x + offset_x * cos_a - offset_y * sin_a
        rotated_y = mid.y + offset_x * sin_a + offset_y * cos_a
        dist = (rotated_x - end_point.x) ** 2 + (rotated_y - end_point.y) ** 2
        if dist < best_dist:
            best_dist = dist
            best_id = anchor_id
    return f"0,{best_id}"


def infer_anchor_position(
    species_layout: typing.Any, point: typing.Any, tol: float = 0.5
) -> str | None:
    """Find the CellDesigner linkAnchor position for a point on a species."""
    import math

    for (
        cd_position,
        anchor_name,
    ) in LINK_ANCHOR_POSITION_TO_ANCHOR_NAME.items():
        anchor_point = species_layout.anchor_point(anchor_name)
        if anchor_point is None:
            continue
        if math.isclose(anchor_point.x, point.x, abs_tol=tol) and math.isclose(
            anchor_point.y, point.y, abs_tol=tol
        ):
            return cd_position
    return None


# ---------------------------------------------------------------------------
# Module-level functions (extracted from CellDesignerWriter classmethods)
# ---------------------------------------------------------------------------


def make_sbml_document(writing_context: typing.Any) -> lxml.etree._Element:
    sbml = make_lxml_element(
        "sbml",
        attributes={"level": "2", "version": "4"},
        nsmap=NSMAP,
    )
    sbml.append(make_celldesigner_model(writing_context))
    return sbml


def make_celldesigner_model(writing_context: typing.Any) -> lxml.etree._Element:
    model_id = get_xml_id(
        writing_context,
        writing_context.map_,
        candidate=writing_context.map_.id_ or "untitled",
    )
    model = make_lxml_element("model", attributes={"metaid": model_id, "id": model_id})
    # notes
    notes_element = build_sbml_notes(writing_context, writing_context.map_)
    if notes_element is not None:
        model.append(notes_element)
    # annotation
    annotation = make_lxml_element("annotation")
    annotation.append(make_celldesigner_extension(writing_context))
    append_rdf_to_annotation(
        writing_context, annotation, writing_context.map_, model_id
    )
    model.append(annotation)
    model.append(make_celldesigner_list_of_compartments(writing_context))
    model.append(make_celldesigner_list_of_species(writing_context))
    model.append(make_celldesigner_list_of_reactions(writing_context))
    return model


def build_sbml_notes(
    writing_context: typing.Any, model_element: typing.Any
) -> lxml.etree._Element | None:
    """Build a plain ``<notes>`` element for an SBML-namespaced element.

    Returns None when ``with_notes`` is disabled or no notes are stored for
    ``model_element``.
    """
    if not writing_context.with_notes:
        return None
    notes = writing_context.element_to_notes.get(model_element)
    if not notes:
        return None
    notes_element = make_lxml_element("notes")
    for note in notes:
        try:
            parsed = lxml.etree.fromstring(note)
        except lxml.etree.XMLSyntaxError:
            continue
        notes_element.append(parsed)
        break
    if len(notes_element) == 0:
        return None
    return notes_element


def append_rdf_to_annotation(
    writing_context: typing.Any,
    annotation_element: lxml.etree._Element,
    model_element: typing.Any,
    about_id: str,
) -> None:
    """Append an ``<rdf:RDF>`` block to an ``<annotation>`` element.

    No-op when ``with_annotations`` is disabled or the element has no
    annotations.
    """
    if not writing_context.with_annotations:
        return
    annotations = writing_context.element_to_annotations.get(model_element)
    if not annotations:
        return
    rdf_element = make_rdf_annotation(annotations, about_id)
    if rdf_element is not None:
        annotation_element.append(rdf_element)


# --- Extension (CD annotation) ---


def make_celldesigner_extension(writing_context: typing.Any) -> lxml.etree._Element:
    extension = make_celldesigner_element("extension")
    extension.append(make_celldesigner_element("modelVersion", text="4.0"))
    display_attrs = {
        "sizeX": str(int(writing_context.map_.layout.width)),
        "sizeY": str(int(writing_context.map_.layout.height)),
    }
    extension.append(
        make_celldesigner_element("modelDisplay", attributes=display_attrs)
    )
    extension.append(make_celldesigner_list_of_included_species(writing_context))
    extension.append(make_celldesigner_list_of_compartment_aliases(writing_context))
    extension.append(make_celldesigner_list_of_complex_species_aliases(writing_context))
    extension.append(make_celldesigner_list_of_species_aliases(writing_context))
    extension.append(make_celldesigner_list_of_proteins(writing_context))
    extension.append(make_celldesigner_list_of_genes(writing_context))
    extension.append(make_celldesigner_list_of_rnas(writing_context))
    extension.append(make_celldesigner_list_of_antisense_rnas(writing_context))
    extension.append(make_celldesigner_element("listOfLayers"))
    return extension


# --- Compartment aliases ---


COMPARTMENT_LAYOUT_CLASSES = (
    RectangleCompartmentLayout,
    OvalCompartmentLayout,
    CornerCompartmentLayout,
    LineCompartmentLayout,
)


def compartment_class_name(layout_key: typing.Any) -> str:
    if isinstance(layout_key, OvalCompartmentLayout):
        return "OVAL"
    if isinstance(layout_key, CornerCompartmentLayout):
        return f"SQUARE_CLOSEUP_{layout_key.corner.value}"
    if isinstance(layout_key, LineCompartmentLayout):
        return f"SQUARE_CLOSEUP_{layout_key.side.value}"
    return "SQUARE"


def compartment_closeup_point(layout_key: typing.Any) -> tuple[float, float]:
    bbox = layout_key.bbox()
    left = bbox.north_west().x
    top = bbox.north_west().y
    right = bbox.south_east().x
    bottom = bbox.south_east().y
    if isinstance(layout_key, CornerCompartmentLayout):
        corner = layout_key.corner
        Corner = CompartmentCorner
        if corner is Corner.NORTHWEST:
            return left, top
        if corner is Corner.NORTHEAST:
            return right, top
        if corner is Corner.SOUTHWEST:
            return left, bottom
        return right, bottom
    side = layout_key.side
    Side = CompartmentSide
    if side is Side.NORTH:
        return layout_key.position.x, top
    if side is Side.SOUTH:
        return layout_key.position.x, bottom
    if side is Side.EAST:
        return right, layout_key.position.y
    return left, layout_key.position.y


def make_celldesigner_list_of_compartment_aliases(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_celldesigner_element("listOfCompartmentAliases")
    for comp in sorted(
        writing_context.map_.model.compartments, key=lambda c: c.id_ or ""
    ):
        for layout_key in get_layouts(writing_context, comp):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, COMPARTMENT_LAYOUT_CLASSES):
                alias = make_celldesigner_element(
                    "compartmentAlias",
                    attributes={
                        "id": get_xml_id(writing_context, layout_key),
                        "compartment": get_xml_id(writing_context, comp),
                    },
                )
                class_name = compartment_class_name(layout_key)
                alias.append(make_celldesigner_element("class", text=class_name))
                if isinstance(
                    layout_key,
                    (
                        CornerCompartmentLayout,
                        LineCompartmentLayout,
                    ),
                ):
                    px, py = compartment_closeup_point(layout_key)
                    alias.append(
                        make_celldesigner_element(
                            "point",
                            attributes={"x": str(px), "y": str(py)},
                        )
                    )
                else:
                    alias.append(
                        make_celldesigner_element(
                            "bounds", attributes=node_to_bounds_attrs(layout_key)
                        )
                    )
                # namePoint (label position)
                label = getattr(layout_key, "label", None)
                if label is not None:
                    alias.append(
                        make_celldesigner_element(
                            "namePoint",
                            attributes={
                                "x": str(label.position.x),
                                "y": str(label.position.y),
                            },
                        )
                    )
                # doubleLine
                sep = getattr(layout_key, "sep", None)
                stroke_width = getattr(layout_key, "stroke_width", None)
                inner_stroke_width = getattr(layout_key, "inner_stroke_width", None)
                alias.append(
                    make_celldesigner_element(
                        "doubleLine",
                        attributes={
                            "thickness": str(sep) if sep else "12.0",
                            "outerWidth": str(stroke_width) if stroke_width else "2.0",
                            "innerWidth": str(inner_stroke_width)
                            if inner_stroke_width
                            else "1.0",
                        },
                    )
                )
                # paint — the reader derives fill as stroke.with_alpha(0.5),
                # so we write back the stroke color directly to preserve
                # the original alpha.
                stroke = getattr(layout_key, "stroke", None)
                if isinstance(stroke, Color):
                    paint_color = color_to_cd_hex(stroke)
                else:
                    paint_color = "ffcccccc"
                alias.append(
                    make_celldesigner_element(
                        "paint", attributes={"color": paint_color, "scheme": "Color"}
                    )
                )
                alias.append(
                    make_celldesigner_element(
                        "info",
                        attributes={"state": "empty", "angle": "-1.5707963267948966"},
                    )
                )
                list_elem.append(alias)
    return list_elem


# --- Included species (complex subunits) ---


def make_celldesigner_list_of_included_species(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_celldesigner_element("listOfIncludedSpecies")
    seen_ids = set()
    for species in sorted(
        writing_context.map_.model.species, key=lambda s: s.id_ or ""
    ):
        if isinstance(species, Complex):
            collect_included_species(
                writing_context, species, species, list_elem, seen_ids
            )
    return list_elem


def collect_included_species(
    writing_context: typing.Any,
    complex_: typing.Any,
    root_complex: typing.Any,
    list_elem: lxml.etree._Element,
    seen_ids: set[str],
) -> None:
    """Recursively collect included species from a complex."""
    for sub in sorted(complex_.subunits, key=lambda s: s.id_ or ""):
        sub_id = get_species_id(sub, writing_context)
        if sub_id not in seen_ids:
            seen_ids.add(sub_id)
            list_elem.append(
                make_celldesigner_included_species(writing_context, sub, complex_)
            )
        if isinstance(sub, Complex):
            collect_included_species(
                writing_context, sub, root_complex, list_elem, seen_ids
            )


def make_celldesigner_included_species(
    writing_context: typing.Any, species: typing.Any, parent_complex: typing.Any
) -> lxml.etree._Element:
    species_id = get_species_id(species, writing_context)
    species_element = make_celldesigner_element(
        "species",
        attributes={
            "id": species_id,
            "name": encode_name(species.name) or "",
        },
    )
    # notes (CellDesigner expects exactly one <html> child)
    notes = make_celldesigner_element("notes")
    species_notes = (
        writing_context.element_to_notes.get(species, set())
        if writing_context.with_notes
        else set()
    )
    parsed_one = False
    if species_notes:
        for note in species_notes:
            try:
                parsed = lxml.etree.fromstring(note)
                notes.append(parsed)
                parsed_one = True
                break
            except lxml.etree.XMLSyntaxError:
                pass
    if not parsed_one:
        html = lxml.etree.SubElement(notes, f"{{{XHTML_NS}}}html")
        head = lxml.etree.SubElement(html, f"{{{XHTML_NS}}}head")
        lxml.etree.SubElement(head, f"{{{XHTML_NS}}}title")
        lxml.etree.SubElement(html, f"{{{XHTML_NS}}}body")
    # Included species round-trip their RDF inside <celldesigner:notes>,
    # embedded in the <body> alongside human-readable text.
    if writing_context.with_annotations:
        species_annotations = writing_context.element_to_annotations.get(species)
        if species_annotations:
            rdf_element = make_rdf_annotation(species_annotations, species_id)
            if rdf_element is not None:
                inject_rdf_into_celldesigner_notes(notes, rdf_element)
    species_element.append(notes)
    # annotation
    annotation = make_celldesigner_element("annotation")
    annotation.append(
        make_celldesigner_element(
            "complexSpecies", text=get_species_id(parent_complex, writing_context)
        )
    )
    annotation.append(make_celldesigner_species_identity(writing_context, species))
    species_element.append(annotation)
    return species_element


# --- Species identity ---


def make_celldesigner_species_identity(
    writing_context: typing.Any, species: typing.Any
) -> lxml.etree._Element:
    identity = make_celldesigner_element("speciesIdentity")
    identity.append(
        make_celldesigner_element("class", text=species_class_string(species))
    )
    template = getattr(species, "template", None)
    if template is not None:
        tag = template_ref_tag(template)
        ref_id = get_xml_id(writing_context, template, share=True)
        identity.append(make_celldesigner_element(tag, text=ref_id))
    identity.append(
        make_celldesigner_element("name", text=encode_name(species.name) or "")
    )
    if species.hypothetical:
        identity.append(make_celldesigner_element("hypothetical", text="true"))
    state = make_celldesigner_species_state(writing_context, species)
    if state is not None:
        identity.append(state)
    return identity


def make_celldesigner_species_state(
    writing_context: typing.Any, species: typing.Any
) -> lxml.etree._Element | None:
    has_mods = hasattr(species, "modifications") and species.modifications
    has_homo = hasattr(species, "homomultimer") and species.homomultimer > 1
    has_struct = hasattr(species, "structural_states") and species.structural_states
    if not has_mods and not has_homo and not has_struct:
        return None
    state = make_celldesigner_element("state")
    if has_homo:
        state.append(
            make_celldesigner_element("homodimer", text=str(species.homomultimer))
        )
    if has_struct:
        ss_list = make_celldesigner_element("listOfStructuralStates")
        for ss in species.structural_states:
            if ss.value is not None:
                ss_list.append(
                    make_celldesigner_element(
                        "structuralState",
                        attributes={"structuralState": ss.value},
                        text=ss.value,
                    )
                )
        state.append(ss_list)
    if has_mods:
        mod_list = make_celldesigner_element("listOfModifications")
        # Sort modifications by their layout child order to preserve
        # the original XML order (modifications is a frozenset).
        sorted_mods = sort_modifications_by_layout(writing_context, species)
        for modification in sorted_mods:
            mod_attrs = {}
            if modification.residue is not None:
                mod_attrs["residue"] = strip_template_prefix(
                    modification.residue, species
                )
            mod_attrs["state"] = modification_state_string(modification.state)
            mod_list.append(
                make_celldesigner_element("modification", attributes=mod_attrs)
            )
        state.append(mod_list)
    return state


# --- Complex species aliases ---


def get_layouts_for_subunit(
    writing_context: typing.Any, subunit: typing.Any, parent_complex: typing.Any
) -> typing.Any:
    """Return layouts of ``subunit`` recorded under ``parent_complex``.

    Thin wrapper around
    [LayoutModelMapping.get_child_layout_elements][momapy.core.mapping.LayoutModelMapping.get_child_layout_elements].
    """
    return get_layout_model_mapping(writing_context).get_child_layout_elements(
        subunit, parent_complex
    )


def make_celldesigner_list_of_complex_species_aliases(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_celldesigner_element("listOfComplexSpeciesAliases")
    for species in writing_context.map_.model.species:
        if not isinstance(species, Complex):
            continue
        collect_complex_aliases(
            writing_context,
            species,
            complex_alias_list=list_elem,
            species_alias_list=None,
        )
    layout_order_index = build_layout_order_index(writing_context.map_.layout)
    sort_aliases_by_layout_order(list_elem, layout_order_index)
    return list_elem


def collect_complex_aliases(
    writing_context: typing.Any,
    target_complex: typing.Any,
    complex_alias_list: lxml.etree._Element | None,
    species_alias_list: lxml.etree._Element | None,
    parent_layout: typing.Any = None,
    parent_complex: typing.Any = None,
) -> None:
    """Walk ``target_complex`` and emit alias entries from the model.

    Walks the model tree starting at ``target_complex``: for each layout
    of ``target_complex`` (scoped to children of ``parent_layout`` when
    nested), emit a ``complexSpeciesAlias`` into ``complex_alias_list``,
    then iterate ``target_complex.subunits`` and emit each one — leaf
    species into ``species_alias_list``, nested complexes by recursion.

    Identifiers emitted into XML come from the in-scope model element
    (``target_complex`` and ``subunit``). The mapping is consulted only
    to find the layouts that pair with each model element.

    Pass ``complex_alias_list=None`` (or ``species_alias_list=None``) to
    skip emission for that side; the walk is unchanged.
    """
    mapping = get_layout_model_mapping(writing_context)
    if parent_layout is None:
        target_layouts = [
            layout
            for layout in get_layouts(writing_context, target_complex)
            if isinstance(layout, ComplexLayout)
        ]
        parent_alias_id = None
    else:
        siblings = set(parent_layout.layout_elements)
        target_layouts = [
            layout
            for layout in mapping.get_child_layout_elements(
                target_complex, parent_complex
            )
            if isinstance(layout, ComplexLayout) and layout in siblings
        ]
        parent_alias_id = get_alias_id(writing_context, parent_layout)
    for target_layout in target_layouts:
        if complex_alias_list is not None:
            complex_alias_list.append(
                make_celldesigner_alias(
                    writing_context,
                    target_layout,
                    target_complex,
                    "complexSpeciesAlias",
                    complex_alias_id=parent_alias_id,
                )
            )
        children_in_layout = set(target_layout.layout_elements)
        for subunit in target_complex.subunits:
            if isinstance(subunit, Complex):
                collect_complex_aliases(
                    writing_context,
                    subunit,
                    complex_alias_list,
                    species_alias_list,
                    parent_layout=target_layout,
                    parent_complex=target_complex,
                )
            elif species_alias_list is not None:
                for child_layout in get_layouts_for_subunit(
                    writing_context, subunit, target_complex
                ):
                    if child_layout not in children_in_layout:
                        continue
                    species_alias_list.append(
                        make_celldesigner_alias(
                            writing_context,
                            child_layout,
                            subunit,
                            "speciesAlias",
                            complex_alias_id=target_layout.id_,
                        )
                    )


# --- Species aliases ---


def make_celldesigner_list_of_species_aliases(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_celldesigner_element("listOfSpeciesAliases")
    # Top-level species (non-complex, non-subunit)
    for species in writing_context.map_.model.species:
        if isinstance(species, Complex):
            continue
        if id(species) in writing_context.subunit_to_complex:
            continue
        for layout_key in get_layouts(writing_context, species):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, CellDesignerNode):
                list_elem.append(
                    make_celldesigner_alias(
                        writing_context, layout_key, species, "speciesAlias"
                    )
                )
    # Subunit species (inside complexes), recursively
    for species in writing_context.map_.model.species:
        if not isinstance(species, Complex):
            continue
        collect_complex_aliases(
            writing_context,
            species,
            complex_alias_list=None,
            species_alias_list=list_elem,
        )
    seen_degraded = set()
    for entry in writing_context.degraded_entries:
        key = id(entry.degraded_layout)
        if key in seen_degraded:
            continue
        seen_degraded.add(key)
        list_elem.append(
            make_celldesigner_degraded_alias(writing_context, entry.degraded_layout)
        )
    layout_order_index = build_layout_order_index(writing_context.map_.layout)
    sort_aliases_by_layout_order(list_elem, layout_order_index)
    return list_elem


def make_celldesigner_degraded_alias(
    writing_context: typing.Any, degraded_layout: typing.Any
) -> lxml.etree._Element:
    species_id = degraded_species_id(writing_context, degraded_layout)
    attrs = {
        "id": get_xml_id(writing_context, degraded_layout),
        "species": species_id,
    }
    alias = make_celldesigner_element("speciesAlias", attributes=attrs)
    activity_text = (
        "active" if isinstance(degraded_layout, DegradedActiveLayout) else "inactive"
    )
    alias.append(make_celldesigner_element("activity", text=activity_text))
    alias.append(
        make_celldesigner_element(
            "bounds", attributes=node_to_bounds_attrs(degraded_layout)
        )
    )
    alias.append(make_celldesigner_element("font", attributes={"size": "12"}))
    alias.append(make_celldesigner_element("view", attributes={"state": "usual"}))
    usual = make_celldesigner_element("usualView")
    usual.append(
        make_celldesigner_element("innerPosition", attributes={"x": "0.0", "y": "0.0"})
    )
    usual.append(
        make_celldesigner_element(
            "boxSize",
            attributes={
                "width": str(degraded_layout.width),
                "height": str(degraded_layout.height),
            },
        )
    )
    usual.append(make_celldesigner_element("singleLine", attributes={"width": "1.0"}))
    usual.append(
        make_celldesigner_element(
            "paint", attributes={"color": "ffccffcc", "scheme": "Color"}
        )
    )
    alias.append(usual)
    brief = make_celldesigner_element("briefView")
    brief.append(
        make_celldesigner_element("innerPosition", attributes={"x": "0.0", "y": "0.0"})
    )
    brief.append(
        make_celldesigner_element(
            "boxSize",
            attributes={
                "width": str(degraded_layout.width),
                "height": str(degraded_layout.height),
            },
        )
    )
    brief.append(make_celldesigner_element("singleLine", attributes={"width": "1.0"}))
    brief.append(
        make_celldesigner_element(
            "paint", attributes={"color": "ffccffcc", "scheme": "Color"}
        )
    )
    alias.append(brief)
    alias.append(
        make_celldesigner_element(
            "info",
            attributes={
                "state": "empty",
                "angle": "-1.5707963267948966",
            },
        )
    )
    return alias


def find_compartment_alias_id(
    writing_context: typing.Any, species_layout: typing.Any
) -> str | None:
    """Find the compartment alias containing this species layout."""
    species_center = species_layout.center()
    best_id = None
    best_area = float("inf")
    for comp in writing_context.map_.model.compartments:
        if comp.id_ == "default":
            continue
        for layout_key in get_layouts(writing_context, comp):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, COMPARTMENT_LAYOUT_CLASSES):
                bbox = layout_key.bbox()
                north_west = bbox.north_west()
                south_east = bbox.south_east()
                if (
                    north_west.x <= species_center.x <= south_east.x
                    and north_west.y <= species_center.y <= south_east.y
                ):
                    area = bbox.width * bbox.height
                    if area < best_area:
                        best_area = area
                        best_id = get_xml_id(writing_context, layout_key)
    return best_id


def make_celldesigner_alias(
    writing_context: typing.Any,
    layout: typing.Any,
    model: typing.Any,
    tag: str,
    complex_alias_id: str | None = None,
) -> lxml.etree._Element:
    attrs = {
        "id": get_xml_id(writing_context, layout),
        "species": get_species_id(model, writing_context),
    }
    if complex_alias_id is not None:
        attrs["complexSpeciesAlias"] = complex_alias_id
    elif tag == "speciesAlias" or tag == "complexSpeciesAlias":
        comp_alias = find_compartment_alias_id(writing_context, layout)
        if comp_alias is not None:
            attrs["compartmentAlias"] = comp_alias
    alias = make_celldesigner_element(tag, attributes=attrs)
    activity_text = "active" if model.active else "inactive"
    alias.append(make_celldesigner_element("activity", text=activity_text))
    alias.append(
        make_celldesigner_element("bounds", attributes=node_to_bounds_attrs(layout))
    )
    font_size = "12"
    if layout.label is not None and layout.label.font_size is not None:
        font_size = str(int(layout.label.font_size))
    alias.append(make_celldesigner_element("font", attributes={"size": font_size}))
    alias.append(make_celldesigner_element("view", attributes={"state": "usual"}))
    if tag == "complexSpeciesAlias":
        alias.append(
            make_celldesigner_element("backupSize", attributes={"w": "0.0", "h": "0.0"})
        )
        alias.append(
            make_celldesigner_element("backupView", attributes={"state": "none"})
        )
    # usualView
    usual = make_celldesigner_element("usualView")
    usual.append(
        make_celldesigner_element("innerPosition", attributes={"x": "0.0", "y": "0.0"})
    )
    usual.append(
        make_celldesigner_element(
            "boxSize",
            attributes={
                "width": str(layout.width),
                "height": str(layout.height),
            },
        )
    )
    line_width = "2.0" if tag == "complexSpeciesAlias" else "1.0"
    usual.append(
        make_celldesigner_element("singleLine", attributes={"width": line_width})
    )
    fill = getattr(layout, "fill", None)
    if isinstance(fill, Color):
        paint_color = color_to_cd_hex(fill)
    else:
        paint_color = "fff7f7f7" if tag == "complexSpeciesAlias" else "ffccffcc"
    usual.append(
        make_celldesigner_element(
            "paint", attributes={"color": paint_color, "scheme": "Color"}
        )
    )
    alias.append(usual)
    # briefView (same as usualView)
    brief = make_celldesigner_element("briefView")
    brief.append(
        make_celldesigner_element("innerPosition", attributes={"x": "0.0", "y": "0.0"})
    )
    brief.append(
        make_celldesigner_element(
            "boxSize",
            attributes={
                "width": str(layout.width),
                "height": str(layout.height),
            },
        )
    )
    brief.append(
        make_celldesigner_element("singleLine", attributes={"width": line_width})
    )
    brief.append(
        make_celldesigner_element(
            "paint", attributes={"color": paint_color, "scheme": "Color"}
        )
    )
    alias.append(brief)
    alias.append(
        make_celldesigner_element(
            "info",
            attributes={
                "state": "empty",
                "angle": "-1.5707963267948966",
            },
        )
    )
    return alias


# --- Proteins (templates) ---


def make_celldesigner_list_of_proteins(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_celldesigner_element("listOfProteins")
    for tmpl in sorted(
        writing_context.map_.model.species_templates, key=lambda t: t.id_ or ""
    ):
        if not isinstance(tmpl, ProteinTemplate):
            continue
        protein_type = "GENERIC"
        if isinstance(tmpl, ReceptorTemplate):
            protein_type = "RECEPTOR"
        elif isinstance(tmpl, IonChannelTemplate):
            protein_type = "ION_CHANNEL"
        elif isinstance(tmpl, TruncatedProteinTemplate):
            protein_type = "TRUNCATED"
        attrs = {
            "id": get_xml_id(writing_context, tmpl, share=True),
            "name": encode_name(tmpl.name) or "",
            "type": protein_type,
        }
        protein = make_celldesigner_element("protein", attributes=attrs)
        if tmpl.modification_residues:
            mr_list = make_celldesigner_element("listOfModificationResidues")
            for residue in sorted(tmpl.modification_residues, key=lambda r: r.id_):
                mr_attrs = {"id": strip_template_prefix(residue, tmpl)}
                if residue.name is not None:
                    mr_attrs["name"] = residue.name
                # Compute angle from layout if available
                mr_attrs["angle"] = find_residue_angle(writing_context, tmpl, residue)
                mr_list.append(
                    make_celldesigner_element(
                        "modificationResidue", attributes=mr_attrs
                    )
                )
            protein.append(mr_list)
        list_elem.append(protein)
    return list_elem


def find_residue_angle(
    writing_context: typing.Any, template: typing.Any, residue: typing.Any
) -> str:
    """Find the CellDesigner angle for a modification residue from layout data.

    CellDesigner stores the badge angle on the (shared) template, while
    momapy keeps it implicit in each ``ModificationLayout``'s position.
    We recover it by finding a species that uses this template and
    carries a ``Modification`` for this residue, looking up that
    modification's layout through the layout-model mapping, and
    computing the angle of the badge relative to its containing node.
    Searches both top-level species and subunits of complexes.

    Args:
        writing_context: The writing context.
        template: The protein template.
        residue: The modification residue to find the angle for.

    Returns:
        The CellDesigner angle as a string.
    """
    mapping = get_layout_model_mapping(writing_context)
    all_species = list(writing_context.map_.model.species)
    for species in writing_context.map_.model.species:
        subunits = getattr(species, "subunits", None)
        if subunits:
            all_species.extend(collect_subunits(species))
    for species in all_species:
        if getattr(species, "template", None) is not template:
            continue
        for modification in getattr(species, "modifications", None) or ():
            if modification.residue is not residue:
                continue
            # The modification's layout(s) are registered in the mapping;
            # find the one living under one of the species' alias nodes
            # and measure its angle relative to that node.
            modification_layouts = set(
                mapping.get_child_layout_elements(modification, species)
            )
            if not modification_layouts:
                continue
            for layout_key in get_layouts(writing_context, species):
                if not isinstance(layout_key, CellDesignerNode):
                    continue
                for child in layout_key.layout_elements or ():
                    if child in modification_layouts:
                        return str(compute_cd_angle(child.position, layout_key))
    return "0.0"


def collect_subunits(species: typing.Any) -> list[typing.Any]:
    """Recursively collect all subunits of a species.

    Args:
        species: The parent species.

    Returns:
        A list of all nested subunit species.
    """
    result = []
    subunits = getattr(species, "subunits", None)
    if subunits:
        for subunit in subunits:
            result.append(subunit)
            result.extend(collect_subunits(subunit))
    return result


def build_subunit_to_complex(map_: typing.Any) -> dict[int, typing.Any]:
    """Map each complex subunit to its top-level complex ancestor.

    Subunits are not top-level SBML species; participant references to a
    subunit must resolve to the enclosing top-level complex. The returned
    dict is keyed by ``id(subunit)`` (subunits use ``compare=False`` on
    ``id_``, so two content-equal ones must stay distinct).

    Args:
        map_: The CellDesigner map being written.

    Returns:
        A dict mapping ``id(subunit)`` to its top-level complex ancestor.
    """
    subunit_to_complex: dict[int, typing.Any] = {}

    def _map_subunits(species: typing.Any) -> None:
        if isinstance(species, Complex):
            for subunit in species.subunits:
                # Map to the top-level ancestor, not the immediate parent.
                # If the parent is itself a subunit, its entry was already
                # set (parent before children).
                ancestor = species
                while id(ancestor) in subunit_to_complex:
                    ancestor = subunit_to_complex[id(ancestor)]
                subunit_to_complex[id(subunit)] = ancestor
                _map_subunits(subunit)

    for species in map_.model.species:
        _map_subunits(species)
    return subunit_to_complex


# --- Genes, RNAs, AntisenseRNAs (templates) ---


def make_celldesigner_list_of_genes(writing_context: typing.Any) -> lxml.etree._Element:
    """Build listOfGenes — one entry per GeneTemplate."""
    list_elem = make_celldesigner_element("listOfGenes")
    for tmpl in sorted(
        writing_context.map_.model.species_templates, key=lambda t: t.id_ or ""
    ):
        if not isinstance(tmpl, GeneTemplate):
            continue
        gene_elem = make_celldesigner_element(
            "gene",
            attributes={
                "type": "GENE",
                "id": get_xml_id(writing_context, tmpl, share=True),
                "name": encode_name(tmpl.name) or "",
            },
        )
        append_template_regions(gene_elem, tmpl)
        list_elem.append(gene_elem)
    return list_elem


def make_celldesigner_list_of_rnas(writing_context: typing.Any) -> lxml.etree._Element:
    """Build listOfRNAs — one entry per RNATemplate."""
    list_elem = make_celldesigner_element("listOfRNAs")
    for tmpl in sorted(
        writing_context.map_.model.species_templates, key=lambda t: t.id_ or ""
    ):
        if not isinstance(tmpl, RNATemplate):
            continue
        rna_elem = make_celldesigner_element(
            "RNA",
            attributes={
                "type": "RNA",
                "id": get_xml_id(writing_context, tmpl, share=True),
                "name": encode_name(tmpl.name) or "",
            },
        )
        append_template_regions(rna_elem, tmpl)
        list_elem.append(rna_elem)
    return list_elem


def make_celldesigner_list_of_antisense_rnas(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    """Build listOfAntisenseRNAs — one entry per AntisenseRNATemplate."""
    list_elem = make_celldesigner_element("listOfAntisenseRNAs")
    for tmpl in sorted(
        writing_context.map_.model.species_templates, key=lambda t: t.id_ or ""
    ):
        if not isinstance(tmpl, AntisenseRNATemplate):
            continue
        arna_elem = make_celldesigner_element(
            "antisenseRNA",
            attributes={
                "type": "ANTISENSE_RNA",
                "id": get_xml_id(writing_context, tmpl, share=True),
                "name": encode_name(tmpl.name) or "",
            },
        )
        append_template_regions(arna_elem, tmpl)
        list_elem.append(arna_elem)
    return list_elem


REGION_CLASS_TO_CD_TYPE = {
    ModificationSite: "Modification Site",
    RegulatoryRegion: "RegulatoryRegion",
    TranscriptionStartingSiteL: "transcriptionStartingSiteL",
    TranscriptionStartingSiteR: "transcriptionStartingSiteR",
    CodingRegion: "CodingRegion",
    ProteinBindingDomain: "proteinBindingDomain",
}


def append_template_regions(elem: lxml.etree._Element, tmpl: typing.Any) -> None:
    """Append listOfRegions to a gene/RNA/antisenseRNA element if regions exist."""
    regions = getattr(tmpl, "regions", None)
    if not regions:
        return
    region_list = make_celldesigner_element("listOfRegions")
    for region in sorted(regions, key=lambda r: r.id_ or ""):
        region_type = REGION_CLASS_TO_CD_TYPE.get(type(region), "proteinBindingDomain")
        region_attrs = {
            "id": strip_template_prefix(region, tmpl),
            "name": region.name or "",
            "size": "0.1",
            "pos": "0.5",
            "type": region_type,
        }
        region_list.append(make_celldesigner_element("region", attributes=region_attrs))
    elem.append(region_list)


def all_species_recursive(writing_context: typing.Any) -> list[typing.Any]:
    """Return all species including subunits, sorted by id."""
    result = []

    def _collect(species: typing.Any) -> None:
        result.append(species)
        if isinstance(species, Complex):
            for sub in species.subunits:
                _collect(sub)

    for species in writing_context.map_.model.species:
        _collect(species)
    return sorted(result, key=lambda s: s.id_ or "")


# --- Compartments ---


def make_celldesigner_list_of_compartments(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_lxml_element("listOfCompartments")
    for comp in sorted(
        writing_context.map_.model.compartments, key=lambda c: c.id_ or ""
    ):
        comp_name = encode_name(comp.name)
        comp_id = get_xml_id(writing_context, comp)
        attrs = {
            "id": comp_id,
            "metaid": comp_id,
            "size": "1",
            "units": "volume",
        }
        if comp_name is not None:
            attrs["name"] = comp_name
        outside = getattr(comp, "outside", None)
        if outside is not None:
            attrs["outside"] = get_xml_id(writing_context, outside)
        compartment_element = make_lxml_element("compartment", attributes=attrs)
        notes_element = build_sbml_notes(writing_context, comp)
        if notes_element is not None:
            compartment_element.append(notes_element)
        append_compartment_annotation(writing_context, compartment_element, comp)
        list_elem.append(compartment_element)
    return list_elem


def append_compartment_annotation(
    writing_context: typing.Any,
    compartment_element: lxml.etree._Element,
    compartment: typing.Any,
) -> None:
    """Append ``<annotation>`` with CD extension + optional RDF to a compartment.

    Every annotated compartment in the CellDesigner corpus carries a
    ``<celldesigner:extension>`` sibling to the ``<rdf:RDF>`` block, with a
    ``<celldesigner:name>`` child when the compartment has a non-empty name.
    We emit this whenever the compartment has annotations or a non-empty
    name, and skip the whole ``<annotation>`` otherwise.
    """
    has_rdf = writing_context.with_annotations and bool(
        writing_context.element_to_annotations.get(compartment)
    )
    comp_name = encode_name(compartment.name)
    if not has_rdf and not comp_name:
        return
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    if comp_name:
        extension.append(make_celldesigner_element("name", text=comp_name))
    annotation.append(extension)
    append_rdf_to_annotation(
        writing_context,
        annotation,
        compartment,
        get_xml_id(writing_context, compartment),
    )
    compartment_element.append(annotation)


# --- SBML species ---


def make_celldesigner_list_of_species(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_lxml_element("listOfSpecies")
    seen_ids = set()
    for species in sorted(
        writing_context.map_.model.species, key=lambda s: s.id_ or ""
    ):
        # Skip subunits — they are only in listOfIncludedSpecies
        if id(species) in writing_context.subunit_to_complex:
            continue
        species_id = get_species_id(species, writing_context)
        if species_id in seen_ids:
            continue
        seen_ids.add(species_id)
        list_elem.append(make_sbml_document_species(writing_context, species))
    seen_degraded = set()
    for entry in writing_context.degraded_entries:
        key = id(entry.degraded_layout)
        if key in seen_degraded:
            continue
        seen_degraded.add(key)
        list_elem.append(
            make_sbml_document_degraded_species(writing_context, entry.degraded_layout)
        )
    return list_elem


def make_sbml_document_degraded_species(
    writing_context: typing.Any, degraded_layout: typing.Any
) -> lxml.etree._Element:
    species_id = degraded_species_id(writing_context, degraded_layout)
    attrs = {
        "metaid": species_id,
        "id": species_id,
        "name": "",
        "compartment": "default",
        "initialAmount": "0",
        "hasOnlySubstanceUnits": "false",
        "constant": "false",
        "boundaryCondition": "false",
    }
    species_element = make_lxml_element("species", attributes=attrs)
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    extension.append(make_celldesigner_element("positionToCompartment", text="inside"))
    identity = make_celldesigner_element("speciesIdentity")
    identity.append(make_celldesigner_element("class", text="DEGRADED"))
    identity.append(make_celldesigner_element("name"))
    extension.append(identity)
    annotation.append(extension)
    species_element.append(annotation)
    return species_element


def make_sbml_document_species(
    writing_context: typing.Any, species: typing.Any
) -> lxml.etree._Element:
    species_id = get_species_id(species, writing_context)
    comp = getattr(species, "compartment", None)
    comp_id = get_xml_id(writing_context, comp) if comp is not None else "default"
    attrs = {
        "metaid": species_id,
        "id": species_id,
        "name": encode_name(species.name) or "",
        "compartment": comp_id,
        "initialAmount": "0",
        "hasOnlySubstanceUnits": "false",
        "constant": "false",
        "boundaryCondition": "false",
    }
    species_element = make_lxml_element("species", attributes=attrs)
    # notes
    notes_element = build_sbml_notes(writing_context, species)
    if notes_element is not None:
        species_element.append(notes_element)
    # annotation with CD extension
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    extension.append(make_celldesigner_element("positionToCompartment", text="inside"))
    extension.append(make_celldesigner_species_identity(writing_context, species))
    # listOfCatalyzedReactions
    catalyzed = find_catalyzed_reactions(writing_context, species)
    if catalyzed:
        cat_list = make_celldesigner_element("listOfCatalyzedReactions")
        for rxn_id in catalyzed:
            cat_list.append(
                make_celldesigner_element("catalyzed", attributes={"reaction": rxn_id})
            )
        extension.append(cat_list)
    annotation.append(extension)
    append_rdf_to_annotation(writing_context, annotation, species, species_id)
    species_element.append(annotation)
    return species_element


def reaction_xml_id(writing_context: typing.Any, reaction: typing.Any) -> str:
    """Return the XML id a reaction is emitted with.

    Computed as the ``<reaction>`` definition does: from the reaction's layout
    (stripping ``_layout``) when available, else from the reaction model. Used so
    references to a reaction (e.g. a species' ``catalyzed`` list) match its
    definition.
    """
    for layout_key in get_layouts(writing_context, reaction):
        if isinstance(layout_key, frozenset):
            reaction_layout = get_reaction_layout(layout_key)
            if reaction_layout is not None:
                return get_xml_id(
                    writing_context,
                    reaction_layout,
                    candidate=reaction_layout.id_.removesuffix("_layout"),
                )
    return get_xml_id(writing_context, reaction)


def find_catalyzed_reactions(
    writing_context: typing.Any, species: typing.Any
) -> list[str]:
    """Find reactions catalyzed by this species."""
    result = []
    for reaction in writing_context.map_.model.reactions:
        for modifier in reaction.modifiers:
            if isinstance(modifier, Catalyzer) and modifier.referred_element is species:
                result.append(reaction_xml_id(writing_context, reaction))
    return sorted(result)


# --- Reactions ---


def make_celldesigner_list_of_reactions(
    writing_context: typing.Any,
) -> lxml.etree._Element:
    list_elem = make_lxml_element("listOfReactions")
    for reaction in writing_context.map_.model.reactions:
        layout_keys = get_layouts(writing_context, reaction)
        frozensets = [lk for lk in layout_keys if isinstance(lk, frozenset)]
        if not frozensets:
            list_elem.append(
                make_celldesigner_reaction(writing_context, reaction, None, None)
            )
        else:
            for frozenset_mapping in frozensets:
                reaction_layout = get_reaction_layout(frozenset_mapping)
                list_elem.append(
                    make_celldesigner_reaction(
                        writing_context,
                        reaction,
                        frozenset_mapping,
                        reaction_layout,
                    )
                )
    for modulation in writing_context.map_.model.modulations:
        layout_keys = get_layouts(writing_context, modulation)
        frozensets = [lk for lk in layout_keys if isinstance(lk, frozenset)]
        if not frozensets:
            mod_rxn = make_celldesigner_modulation_reaction(
                writing_context, modulation, None
            )
            if mod_rxn is not None:
                list_elem.append(mod_rxn)
        else:
            for frozenset_mapping in frozensets:
                mod_rxn = make_celldesigner_modulation_reaction(
                    writing_context, modulation, frozenset_mapping
                )
                if mod_rxn is not None:
                    list_elem.append(mod_rxn)
    layout_order_index = build_layout_order_index(writing_context.map_.layout)
    sort_reactions_by_layout_order(list_elem, layout_order_index)
    return list_elem


def make_celldesigner_reaction(
    writing_context: typing.Any,
    reaction: typing.Any,
    frozenset_mapping: typing.Any,
    reaction_layout: typing.Any,
) -> lxml.etree._Element:
    # Derive the XML id from the layout when available (supports
    # multiple visual copies of the same reaction).
    if reaction_layout is not None:
        xml_id = get_xml_id(
            writing_context,
            reaction_layout,
            candidate=reaction_layout.id_.removesuffix("_layout"),
        )
    else:
        xml_id = get_xml_id(writing_context, reaction)
    attrs = {
        "metaid": xml_id,
        "id": xml_id,
        "reversible": "true" if reaction.reversible else "false",
    }
    reaction_element = make_lxml_element("reaction", attributes=attrs)

    # notes
    notes_element = build_sbml_notes(writing_context, reaction)
    if notes_element is not None:
        reaction_element.append(notes_element)

    # CD extension
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    reaction_type = _CLASS_TO_REACTION_TYPE.get(type(reaction), "STATE_TRANSITION")
    extension.append(make_celldesigner_element("reactionType", text=reaction_type))

    # Split reactants/products into base + links using the base flag.
    # Sort by layout arc order since reaction.reactants/products are
    # frozensets with no guaranteed iteration order.
    all_reactants = list(reaction.reactants)
    all_products = list(reaction.products)
    if reaction_layout is not None:
        reactant_arc_order = build_arc_alias_order(
            writing_context,
            reaction_layout,
            ConsumptionLayout,
        )
        product_arc_order = build_arc_alias_order(
            writing_context,
            reaction_layout,
            ProductionLayout,
        )
        all_reactants.sort(
            key=lambda r: participant_layout_position(
                writing_context,
                r,
                reaction,
                frozenset_mapping,
                reaction_layout,
                True,
                reactant_arc_order,
            )
        )
        all_products.sort(
            key=lambda p: participant_layout_position(
                writing_context,
                p,
                reaction,
                frozenset_mapping,
                reaction_layout,
                False,
                product_arc_order,
            )
        )
    base_reactants, link_reactants = split_base_and_links(all_reactants)
    base_products, link_products = split_base_and_links(all_products)
    is_left_t = isinstance(reaction, HeterodimerAssociation)
    is_right_t = isinstance(
        reaction,
        (
            Dissociation,
            Truncation,
        ),
    )

    # baseReactants — for left-T with 1 model reactant but 2 visual
    # copies (stoichiometry), use consumption arcs to find all aliases.
    base_reactants_element = make_celldesigner_element("baseReactants")
    if is_left_t and len(base_reactants) == 1 and reaction_layout is not None:
        base_species = base_reactants[0].referred_element
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, ConsumptionLayout)
                and layout_element_item.source is reaction_layout
            ):
                # Only base arcs: target must map to the base species
                target_model = get_layout_model_mapping(writing_context).get_mapping(
                    layout_element_item.target
                )
                if target_model is not None:
                    if target_model is not base_species:
                        continue
                alias_layout = layout_element_item.target
                base_reactants_element.append(
                    make_celldesigner_base_participant_from_layout(
                        writing_context,
                        base_species,
                        alias_layout,
                        "baseReactant",
                        reaction_layout,
                        is_start=True,
                    )
                )
    else:
        for reactant in base_reactants:
            base_reactants_element.append(
                make_celldesigner_base_participant(
                    writing_context,
                    reactant,
                    "baseReactant",
                    frozenset_mapping,
                    reaction_layout,
                    is_start=True,
                    reaction=reaction,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "reactant"):
        if entry.link_arc is None:
            base_reactants_element.append(
                make_celldesigner_degraded_base_participant(
                    writing_context,
                    entry.degraded_layout,
                    "baseReactant",
                    entry.reaction_layout,
                    is_start=True,
                )
            )
    extension.append(base_reactants_element)

    # baseProducts — same for right-T with 1 model product but 2 aliases.
    base_products_element = make_celldesigner_element("baseProducts")
    if is_right_t and len(base_products) == 1 and reaction_layout is not None:
        base_species = base_products[0].referred_element
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, ProductionLayout)
                and layout_element_item.source is reaction_layout
            ):
                target_model = get_layout_model_mapping(writing_context).get_mapping(
                    layout_element_item.target
                )
                if target_model is not None:
                    if target_model is not base_species:
                        continue
                alias_layout = layout_element_item.target
                base_products_element.append(
                    make_celldesigner_base_participant_from_layout(
                        writing_context,
                        base_species,
                        alias_layout,
                        "baseProduct",
                        reaction_layout,
                        is_start=False,
                    )
                )
    else:
        for product in base_products:
            base_products_element.append(
                make_celldesigner_base_participant(
                    writing_context,
                    product,
                    "baseProduct",
                    frozenset_mapping,
                    reaction_layout,
                    is_start=False,
                    reaction=reaction,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "product"):
        if entry.link_arc is None:
            base_products_element.append(
                make_celldesigner_degraded_base_participant(
                    writing_context,
                    entry.degraded_layout,
                    "baseProduct",
                    entry.reaction_layout,
                    is_start=False,
                )
            )
    extension.append(base_products_element)

    # For left-T reactions, compute base reactant aliases to distinguish
    # base arcs from link arcs (both are ConsumptionLayout).
    base_reactant_aliases = set()
    if is_left_t and reaction_layout is not None:
        base_species_set = {r.referred_element for r in base_reactants}
        for arc in writing_context.map_.layout.layout_elements:
            if (
                isinstance(arc, ConsumptionLayout)
                and arc.source is reaction_layout
                and arc.target is not None
            ):
                target_model = get_layout_model_mapping(writing_context).get_mapping(
                    arc.target
                )
                if target_model is not None and target_model in base_species_set:
                    base_reactant_aliases.add(arc.target)

    # listOfReactantLinks — derive from layout arcs to handle
    # multiple visual copies of the same model element.
    reactant_links_element = make_celldesigner_element("listOfReactantLinks")
    if reaction_layout is not None:
        if is_left_t:
            link_consumption_arcs = [
                arc
                for arc in collect_arcs_for_reaction(
                    writing_context,
                    reaction_layout,
                    ConsumptionLayout,
                )
                if arc.target not in base_reactant_aliases
            ]
        else:
            base_reactant_alias = reaction_layout.source
            link_consumption_arcs = collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ConsumptionLayout,
                exclude_alias=base_reactant_alias,
            )
        for arc_layout in link_consumption_arcs:
            if is_degraded_layout(arc_layout.target):
                continue
            reactant_links_element.append(
                make_celldesigner_participant_link_from_layout(
                    writing_context,
                    arc_layout,
                    "reactantLink",
                    "reactant",
                    reaction_layout,
                )
            )
    else:
        for reactant in link_reactants:
            reactant_links_element.append(
                make_celldesigner_participant_link(
                    writing_context,
                    reactant,
                    "reactantLink",
                    "reactant",
                    frozenset_mapping,
                    reaction_layout=reaction_layout,
                    reaction=reaction,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "reactant"):
        if entry.link_arc is not None:
            reactant_links_element.append(
                make_celldesigner_degraded_participant_link(
                    writing_context,
                    entry.link_arc,
                    entry.degraded_layout,
                    "reactantLink",
                    "reactant",
                    reaction_layout,
                )
            )
    extension.append(reactant_links_element)

    # listOfProductLinks — same arc-driven approach.
    product_links_element = make_celldesigner_element("listOfProductLinks")
    if reaction_layout is not None:
        if is_right_t:
            # Right-T: exclude all base product arcs by their target alias
            base_product_aliases = set()
            base_product_species_set = {p.referred_element for p in base_products}
            for arc in writing_context.map_.layout.layout_elements:
                if (
                    isinstance(arc, ProductionLayout)
                    and arc.source is reaction_layout
                    and arc.target is not None
                ):
                    target_model = get_layout_model_mapping(
                        writing_context
                    ).get_mapping(arc.target)
                    if (
                        target_model is not None
                        and target_model in base_product_species_set
                    ):
                        base_product_aliases.add(arc.target)
            link_production_arcs = [
                arc
                for arc in collect_arcs_for_reaction(
                    writing_context,
                    reaction_layout,
                    ProductionLayout,
                )
                if arc.target not in base_product_aliases
            ]
        else:
            base_product_alias = reaction_layout.target
            link_production_arcs = collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ProductionLayout,
                exclude_alias=base_product_alias,
            )
        for arc_layout in link_production_arcs:
            if is_degraded_layout(arc_layout.target):
                continue
            product_links_element.append(
                make_celldesigner_participant_link_from_layout(
                    writing_context,
                    arc_layout,
                    "productLink",
                    "product",
                    reaction_layout,
                )
            )
    else:
        for product in link_products:
            product_links_element.append(
                make_celldesigner_participant_link(
                    writing_context,
                    product,
                    "productLink",
                    "product",
                    frozenset_mapping,
                    reaction_layout=reaction_layout,
                    reaction=reaction,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "product"):
        if entry.link_arc is not None:
            product_links_element.append(
                make_celldesigner_degraded_participant_link(
                    writing_context,
                    entry.link_arc,
                    entry.degraded_layout,
                    "productLink",
                    "product",
                    reaction_layout,
                )
            )
    extension.append(product_links_element)

    # connectScheme + editPoints
    make_celldesigner_connect_scheme(
        writing_context,
        extension,
        reaction,
        reaction_layout,
        frozenset_mapping,
        base_reactants,
        base_products,
        is_left_t,
        is_right_t,
    )

    # listOfModification
    mod_list = make_celldesigner_element("listOfModification")
    modifiers = sorted(reaction.modifiers, key=lambda m: m.id_ or "")
    for modifier in modifiers:
        species = modifier.referred_element
        if isinstance(species, BooleanLogicGate):
            # Write gate entry + per-input entries
            gate_mods = make_celldesigner_gate_modifications(
                writing_context, modifier, species, reaction_layout, frozenset_mapping
            )
            for gm in gate_mods:
                mod_list.append(gm)
        else:
            modification_element = make_celldesigner_modification(
                writing_context, modifier, reaction_layout, frozenset_mapping
            )
            if modification_element is not None:
                mod_list.append(modification_element)
    extension.append(mod_list)

    # line
    extension.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(reaction_layout, include_type=True)
        )
    )

    annotation.append(extension)
    append_rdf_to_annotation(writing_context, annotation, reaction, xml_id)
    reaction_element.append(annotation)

    # SBML listOfReactants — base first, then links.
    # For left-T with stoichiometry, duplicate from arcs.
    list_of_reactants = make_lxml_element("listOfReactants")
    if is_left_t and len(base_reactants) == 1 and reaction_layout is not None:
        base_species = base_reactants[0].referred_element
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, ConsumptionLayout)
                and layout_element_item.source is reaction_layout
            ):
                target_model = get_layout_model_mapping(writing_context).get_mapping(
                    layout_element_item.target
                )
                if target_model is not None:
                    if target_model is not base_species:
                        continue
                sbml_species = writing_context.subunit_to_complex.get(
                    id(base_species), base_species
                )
                alias_id = get_alias_id(writing_context, layout_element_item.target)
                species_reference = make_lxml_element(
                    "speciesReference",
                    attributes={
                        "species": get_species_id(sbml_species, writing_context)
                    },
                )
                species_reference_annotation = make_lxml_element("annotation")
                species_reference_extension = make_celldesigner_element("extension")
                species_reference_extension.append(
                    make_celldesigner_element("alias", text=alias_id)
                )
                species_reference_annotation.append(species_reference_extension)
                species_reference.append(species_reference_annotation)
                list_of_reactants.append(species_reference)
    else:
        for reactant in base_reactants:
            list_of_reactants.append(
                make_sbml_document_species_reference(
                    writing_context,
                    reactant,
                    frozenset_mapping,
                    reaction=reaction,
                    reaction_layout=reaction_layout,
                    is_start=True,
                )
            )
    if reaction_layout is not None:
        if is_left_t:
            # Reuse already-computed base reactant aliases to exclude
            for arc_layout in collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ConsumptionLayout,
            ):
                if arc_layout.target in base_reactant_aliases:
                    continue
                if is_degraded_layout(arc_layout.target):
                    continue
                list_of_reactants.append(
                    make_sbml_document_species_reference_from_layout(
                        writing_context,
                        arc_layout,
                    )
                )
        else:
            base_reactant_alias = reaction_layout.source
            for arc_layout in collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ConsumptionLayout,
                exclude_alias=base_reactant_alias,
            ):
                if is_degraded_layout(arc_layout.target):
                    continue
                list_of_reactants.append(
                    make_sbml_document_species_reference_from_layout(
                        writing_context,
                        arc_layout,
                    )
                )
    else:
        for reactant in link_reactants:
            list_of_reactants.append(
                make_sbml_document_species_reference(
                    writing_context,
                    reactant,
                    frozenset_mapping,
                    reaction=reaction,
                    reaction_layout=reaction_layout,
                    is_start=True,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "reactant"):
        list_of_reactants.append(
            make_sbml_document_degraded_species_reference(
                writing_context, entry.degraded_layout
            )
        )
    reaction_element.append(list_of_reactants)

    # SBML listOfProducts — same for right-T.
    list_of_products = make_lxml_element("listOfProducts")
    if is_right_t and len(base_products) == 1 and reaction_layout is not None:
        base_species = base_products[0].referred_element
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, ProductionLayout)
                and layout_element_item.source is reaction_layout
            ):
                target_model = get_layout_model_mapping(writing_context).get_mapping(
                    layout_element_item.target
                )
                if target_model is not None:
                    if target_model is not base_species:
                        continue
                sbml_species = writing_context.subunit_to_complex.get(
                    id(base_species), base_species
                )
                alias_id = get_alias_id(writing_context, layout_element_item.target)
                species_reference = make_lxml_element(
                    "speciesReference",
                    attributes={
                        "species": get_species_id(sbml_species, writing_context)
                    },
                )
                species_reference_annotation = make_lxml_element("annotation")
                species_reference_extension = make_celldesigner_element("extension")
                species_reference_extension.append(
                    make_celldesigner_element("alias", text=alias_id)
                )
                species_reference_annotation.append(species_reference_extension)
                species_reference.append(species_reference_annotation)
                list_of_products.append(species_reference)
    else:
        for product in base_products:
            list_of_products.append(
                make_sbml_document_species_reference(
                    writing_context,
                    product,
                    frozenset_mapping,
                    reaction=reaction,
                    reaction_layout=reaction_layout,
                    is_start=False,
                )
            )
    if reaction_layout is not None:
        if is_right_t:
            # Reuse already-computed base product aliases to exclude
            for arc_layout in collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ProductionLayout,
            ):
                if arc_layout.target in base_product_aliases:
                    continue
                if is_degraded_layout(arc_layout.target):
                    continue
                list_of_products.append(
                    make_sbml_document_species_reference_from_layout(
                        writing_context,
                        arc_layout,
                    )
                )
        else:
            base_product_alias = reaction_layout.target
            for arc_layout in collect_arcs_for_reaction(
                writing_context,
                reaction_layout,
                ProductionLayout,
                exclude_alias=base_product_alias,
            ):
                if is_degraded_layout(arc_layout.target):
                    continue
                list_of_products.append(
                    make_sbml_document_species_reference_from_layout(
                        writing_context,
                        arc_layout,
                    )
                )
    else:
        for product in link_products:
            list_of_products.append(
                make_sbml_document_species_reference(
                    writing_context,
                    product,
                    frozenset_mapping,
                    reaction=reaction,
                    reaction_layout=reaction_layout,
                    is_start=False,
                )
            )
    for entry in degraded_entries_for_reaction(writing_context, reaction, "product"):
        list_of_products.append(
            make_sbml_document_degraded_species_reference(
                writing_context, entry.degraded_layout
            )
        )
    reaction_element.append(list_of_products)

    # SBML listOfModifiers
    if modifiers:
        list_of_modifiers = make_lxml_element("listOfModifiers")
        for modifier in modifiers:
            species = modifier.referred_element
            if isinstance(species, BooleanLogicGate):
                # Write each input species as a separate modifier
                for inp in sorted(species.inputs, key=lambda s: s.id_ or ""):
                    input_species = inp.referred_element
                    sbml_inp = writing_context.subunit_to_complex.get(
                        id(input_species), input_species
                    )
                    alias_layout = (
                        find_layout_for_species_in_frozenset(
                            writing_context, input_species, frozenset_mapping
                        )
                        if frozenset_mapping
                        else None
                    )
                    if alias_layout is None:
                        for layout_key in get_layouts(writing_context, input_species):
                            if isinstance(layout_key, frozenset):
                                continue
                            if isinstance(layout_key, CellDesignerNode):
                                alias_layout = layout_key
                                break
                    alias_id = get_alias_id(writing_context, alias_layout)
                    modifier_species_reference = make_lxml_element(
                        "modifierSpeciesReference",
                        attributes={
                            "species": get_species_id(sbml_inp, writing_context)
                        },
                    )
                    modifier_reference_annotation = make_lxml_element("annotation")
                    modifier_reference_extension = make_celldesigner_element(
                        "extension"
                    )
                    modifier_reference_extension.append(
                        make_celldesigner_element("alias", text=alias_id)
                    )
                    modifier_reference_annotation.append(modifier_reference_extension)
                    modifier_species_reference.append(modifier_reference_annotation)
                    list_of_modifiers.append(modifier_species_reference)
                continue
            sbml_species = writing_context.subunit_to_complex.get(id(species), species)
            alias_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context, species, frozenset_mapping
                )
                if frozenset_mapping
                else None
            )
            alias_id = get_alias_id(writing_context, alias_layout)
            modifier_reference_attributes = {
                "species": get_species_id(sbml_species, writing_context)
            }
            if modifier.metaid is not None:
                modifier_reference_attributes["metaid"] = get_xml_id(
                    writing_context,
                    modifier,
                    candidate=modifier.metaid,
                    share=False,
                    memoize=False,
                )
            modifier_species_reference = make_lxml_element(
                "modifierSpeciesReference", attributes=modifier_reference_attributes
            )
            modifier_reference_annotation = make_lxml_element("annotation")
            modifier_reference_extension = make_celldesigner_element("extension")
            modifier_reference_extension.append(
                make_celldesigner_element("alias", text=alias_id)
            )
            modifier_reference_annotation.append(modifier_reference_extension)
            modifier_species_reference.append(modifier_reference_annotation)
            list_of_modifiers.append(modifier_species_reference)
        reaction_element.append(list_of_modifiers)

    return reaction_element


def split_base_and_links(
    participants: typing.Any,
) -> tuple[list[typing.Any], list[typing.Any]]:
    """Split participants into base and link using the base flag."""
    base = [p for p in participants if p.base]
    link = [p for p in participants if not p.base]
    return base, link


def make_sbml_document_species_reference(
    writing_context: typing.Any,
    participant: typing.Any,
    frozenset_mapping: typing.Any,
    reaction: typing.Any = None,
    reaction_layout: typing.Any = None,
    is_start: bool = True,
) -> lxml.etree._Element:
    """Build an SBML speciesReference element."""
    species = participant.referred_element
    sbml_species = writing_context.subunit_to_complex.get(id(species), species)
    if reaction is not None:
        alias_layout = find_layout_for_participant(
            writing_context,
            participant,
            reaction,
            frozenset_mapping,
            reaction_layout,
            is_start,
        )
    else:
        alias_layout = (
            find_layout_for_species_in_frozenset(
                writing_context, species, frozenset_mapping
            )
            if frozenset_mapping
            else None
        )
    alias_id = get_alias_id(writing_context, alias_layout)
    sr_attrs = {"species": get_species_id(sbml_species, writing_context)}
    # Write the participant id_ as metaid so the reader can recover it.
    # The reader prefers metaid over composite ids for reactant/product ids.
    participant_metaid = participant.metaid or participant.id_
    if participant_metaid:
        sr_attrs["metaid"] = get_xml_id(
            writing_context,
            participant,
            candidate=participant_metaid,
            share=False,
            memoize=False,
        )
    if participant.stoichiometry is not None:
        sr_attrs["stoichiometry"] = str(participant.stoichiometry)
    species_reference = make_lxml_element("speciesReference", attributes=sr_attrs)
    species_reference_annotation = make_lxml_element("annotation")
    species_reference_extension = make_celldesigner_element("extension")
    species_reference_extension.append(
        make_celldesigner_element("alias", text=alias_id)
    )
    species_reference_annotation.append(species_reference_extension)
    species_reference.append(species_reference_annotation)
    return species_reference


def make_sbml_document_species_reference_from_layout(
    writing_context: typing.Any, arc_layout: typing.Any
) -> lxml.etree._Element:
    """Build an SBML speciesReference from a known arc layout.

    Used when deriving link participants from layout arcs rather than
    from model participants (which may have been deduplicated).

    Args:
        writing_context: The writing context.
        arc_layout: The ConsumptionLayout or ProductionLayout arc.

    Returns:
        The lxml speciesReference element.
    """
    alias_layout = arc_layout.target
    alias_id = get_alias_id(writing_context, alias_layout)
    species = get_layout_model_mapping(writing_context).get_mapping(alias_layout)
    sbml_species = writing_context.subunit_to_complex.get(id(species), species)
    sr_attrs = {"species": get_species_id(sbml_species, writing_context)}
    arc_model = get_layout_model_mapping(writing_context).get_mapping(arc_layout)
    if arc_model is not None and hasattr(arc_model, "id_"):
        participant_metaid = arc_model.metaid or arc_model.id_
        if participant_metaid:
            sr_attrs["metaid"] = get_xml_id(
                writing_context,
                arc_model,
                candidate=participant_metaid,
                share=False,
                memoize=False,
            )
    species_reference = make_lxml_element("speciesReference", attributes=sr_attrs)
    species_reference_annotation = make_lxml_element("annotation")
    species_reference_extension = make_celldesigner_element("extension")
    species_reference_extension.append(
        make_celldesigner_element("alias", text=alias_id)
    )
    species_reference_annotation.append(species_reference_extension)
    species_reference.append(species_reference_annotation)
    return species_reference


def make_celldesigner_base_participant_from_layout(
    writing_context: typing.Any,
    species: typing.Any,
    alias_layout: typing.Any,
    tag: str,
    reaction_layout: typing.Any,
    is_start: bool,
) -> lxml.etree._Element:
    """Build a baseReactant/baseProduct from a known alias layout."""
    alias_id = get_alias_id(writing_context, alias_layout)
    elem = make_celldesigner_element(
        tag,
        attributes={
            "species": get_species_id(species, writing_context),
            "alias": alias_id,
        },
    )
    if reaction_layout is not None and alias_layout is not None:
        ref_point = find_arc_endpoint_for_species(
            writing_context, reaction_layout, alias_layout, is_start
        )
        if ref_point is not None:
            anchor = infer_anchor_position(alias_layout, ref_point)
            if anchor is not None:
                elem.append(
                    make_celldesigner_element(
                        "linkAnchor", attributes={"position": anchor}
                    )
                )
    return elem


def make_celldesigner_base_participant(
    writing_context: typing.Any,
    participant: typing.Any,
    tag: str,
    frozenset_mapping: typing.Any,
    reaction_layout: typing.Any,
    is_start: bool,
    reaction: typing.Any = None,
) -> lxml.etree._Element:
    """Build a baseReactant or baseProduct element."""
    species = participant.referred_element
    if reaction is not None:
        alias_layout = find_layout_for_participant(
            writing_context,
            participant,
            reaction,
            frozenset_mapping,
            reaction_layout,
            is_start,
        )
    else:
        alias_layout = (
            find_layout_for_species_in_frozenset(
                writing_context, species, frozenset_mapping
            )
            if frozenset_mapping
            else None
        )
    alias_id = get_alias_id(writing_context, alias_layout)
    elem = make_celldesigner_element(
        tag,
        attributes={
            "species": get_species_id(species, writing_context),
            "alias": alias_id,
        },
    )
    if reaction_layout is not None and alias_layout is not None:
        ref_point = find_arc_endpoint_for_species(
            writing_context, reaction_layout, alias_layout, is_start
        )
        if ref_point is not None:
            anchor = infer_anchor_position(alias_layout, ref_point)
            if anchor is not None:
                elem.append(
                    make_celldesigner_element(
                        "linkAnchor", attributes={"position": anchor}
                    )
                )
    return elem


def make_celldesigner_degraded_participant_link(
    writing_context: typing.Any,
    arc_layout: typing.Any,
    degraded_layout: typing.Any,
    tag: str,
    attr_name: str,
    reaction_layout: typing.Any,
) -> lxml.etree._Element:
    """Build a reactantLink/productLink for a degraded link arc."""
    species_id = degraded_species_id(writing_context, degraded_layout)
    link = make_celldesigner_element(
        tag,
        attributes={
            attr_name: species_id,
            "alias": get_xml_id(writing_context, degraded_layout),
        },
    )
    is_reactant = tag == "reactantLink"
    if is_reactant:
        edit_points, anchor_name = inverse_edit_points_reactant_link(
            arc_layout, degraded_layout, reaction_layout
        )
    else:
        edit_points, anchor_name = inverse_edit_points_product_link(
            arc_layout, degraded_layout, reaction_layout
        )
    if anchor_name is not None:
        anchor_pos = anchor_name_to_position(anchor_name)
        if anchor_pos is not None:
            link.append(
                make_celldesigner_element(
                    "linkAnchor", attributes={"position": anchor_pos}
                )
            )
    connect_scheme = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(len(edit_points) + 1):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection", attributes={"index": str(i), "value": "unknown"}
            )
        )
    connect_scheme.append(line_direction_list)
    link.append(connect_scheme)
    if edit_points:
        link.append(
            make_celldesigner_element(
                "editPoints",
                text=points_to_edit_points_text(edit_points),
            )
        )
    link.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(arc_layout, include_type=True)
        )
    )
    return link


def make_sbml_document_degraded_species_reference(
    writing_context: typing.Any, degraded_layout: typing.Any
) -> lxml.etree._Element:
    """Build a speciesReference for a degraded layout (no model peer)."""
    species_id = degraded_species_id(writing_context, degraded_layout)
    species_reference = make_lxml_element(
        "speciesReference", attributes={"species": species_id}
    )
    species_reference_annotation = make_lxml_element("annotation")
    species_reference_extension = make_celldesigner_element("extension")
    species_reference_extension.append(
        make_celldesigner_element(
            "alias", text=get_xml_id(writing_context, degraded_layout)
        )
    )
    species_reference_annotation.append(species_reference_extension)
    species_reference.append(species_reference_annotation)
    return species_reference


def make_celldesigner_degraded_base_participant(
    writing_context: typing.Any,
    degraded_layout: typing.Any,
    tag: str,
    reaction_layout: typing.Any,
    is_start: bool,
) -> lxml.etree._Element:
    """Build a baseReactant/baseProduct for a degraded layout glyph."""
    elem = make_celldesigner_element(
        tag,
        attributes={
            "species": degraded_species_id(writing_context, degraded_layout),
            "alias": get_xml_id(writing_context, degraded_layout),
        },
    )
    if reaction_layout is not None:
        ref_point = find_arc_endpoint_for_species(
            writing_context, reaction_layout, degraded_layout, is_start
        )
        if ref_point is not None:
            anchor = infer_anchor_position(degraded_layout, ref_point)
            if anchor is not None:
                elem.append(
                    make_celldesigner_element(
                        "linkAnchor", attributes={"position": anchor}
                    )
                )
    return elem


def find_arc_endpoint_for_species(
    writing_context: typing.Any,
    reaction_layout: typing.Any,
    species_layout: typing.Any,
    is_start: bool,
) -> typing.Any:
    """Find the arc endpoint connecting a species to a reaction.

    Uses the arc's source/target to find the correct arc for this
    species, then returns the endpoint closest to the species.
    """
    arc_cls = ConsumptionLayout if is_start else ProductionLayout
    # source is always the reaction, target is always the species
    for layout_element_item in writing_context.map_.layout.layout_elements:
        if not isinstance(layout_element_item, arc_cls):
            continue
        if (
            layout_element_item.source is reaction_layout
            and layout_element_item.target is species_layout
        ):
            return (
                layout_element_item.points()[0]
                if is_start
                else layout_element_item.points()[-1]
            )
    # Fallback to reaction path start/end
    points = reaction_layout.points()
    return points[0] if is_start else points[-1]


def make_celldesigner_connect_scheme(
    writing_context: typing.Any,
    extension: lxml.etree._Element,
    reaction: typing.Any,
    reaction_layout: typing.Any,
    frozenset_mapping: typing.Any,
    base_reactants: typing.Any,
    base_products: typing.Any,
    is_left_t: bool,
    is_right_t: bool,
) -> None:
    """Build connectScheme and editPoints for a reaction."""
    if reaction_layout is None:
        # No layout — write minimal fallback
        connect_scheme = make_celldesigner_element(
            "connectScheme",
            attributes={
                "connectPolicy": "direct",
                "rectangleIndex": "0",
            },
        )
        line_direction_list = make_celldesigner_element("listOfLineDirection")
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection",
                attributes={
                    "index": "0",
                    "value": "unknown",
                },
            )
        )
        connect_scheme.append(line_direction_list)
        extension.append(connect_scheme)
        return
    if is_left_t:
        # Find base reactant layouts and their consumption arcs
        reactant_layouts = []
        consumption_layouts = []
        for base_reactant in base_reactants:
            br_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context, base_reactant.referred_element, frozenset_mapping
                )
                if frozenset_mapping
                else None
            )
            if br_layout is None:
                continue
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    isinstance(layout_element_item, ConsumptionLayout)
                    and layout_element_item.source is reaction_layout
                    and layout_element_item.target is br_layout
                ):
                    reactant_layouts.append(br_layout)
                    consumption_layouts.append(layout_element_item)
                    break
        product_layout = None
        if base_products:
            product_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context,
                    base_products[0].referred_element,
                    frozenset_mapping,
                )
                if frozenset_mapping
                else None
            )
        computed = False
        if len(reactant_layouts) >= 2 and product_layout is not None:
            # Try both reactant orderings; pick the one whose
            # roundtrip T-junction position is closest.
            t_junction = reaction_layout.points()[0]
            best_result = None
            best_dist = float("inf")
            for perm in [
                (reactant_layouts, consumption_layouts),
                (reactant_layouts[::-1], consumption_layouts[::-1]),
            ]:
                rl, cl = perm
                result = inverse_edit_points_left_t_shape(
                    reaction_layout,
                    rl,
                    product_layout,
                    cl,
                )
                ep = result[0][-1]
                origin = rl[0].center()
                unit_x = rl[1].center()
                unit_y = product_layout.center()
                origin, unit_x, unit_y = make_non_degenerate_frame(
                    origin, unit_x, unit_y
                )
                trans = get_transformation_for_frame(origin, unit_x, unit_y)
                roundtrip = ep.transformed(trans)
                dist = (roundtrip.x - t_junction.x) ** 2 + (
                    roundtrip.y - t_junction.y
                ) ** 2
                if math.isfinite(dist) and dist < best_dist:
                    best_dist = dist
                    best_result = result
            if best_result is None:
                best_result = inverse_edit_points_left_t_shape(
                    reaction_layout,
                    reactant_layouts,
                    product_layout,
                    consumption_layouts,
                )
            (
                all_edit_points,
                num0,
                num1,
                num2,
                t_shape_index,
                product_anchor_name,
                reactant_anchor_names,
            ) = best_result
            connect_scheme = make_celldesigner_element(
                "connectScheme", attributes={"connectPolicy": "direct"}
            )
            line_direction_list = make_celldesigner_element("listOfLineDirection")
            for arm_idx, arm_count in enumerate([num0, num1, num2]):
                for i in range(arm_count + 1):
                    line_direction_list.append(
                        make_celldesigner_element(
                            "lineDirection",
                            attributes={
                                "arm": str(arm_idx),
                                "index": str(i),
                                "value": "unknown",
                            },
                        )
                    )
            connect_scheme.append(line_direction_list)
            extension.append(connect_scheme)
            edit_points_attributes = {
                "num0": str(num0),
                "num1": str(num1),
                "num2": str(num2),
                "tShapeIndex": str(t_shape_index),
            }
            extension.append(
                make_celldesigner_element(
                    "editPoints",
                    attributes=edit_points_attributes,
                    text=points_to_edit_points_text(all_edit_points),
                )
            )
            computed = True
        if not computed:
            # Fallback
            connect_scheme = make_celldesigner_element(
                "connectScheme", attributes={"connectPolicy": "direct"}
            )
            line_direction_list = make_celldesigner_element("listOfLineDirection")
            for arm in range(3):
                line_direction_list.append(
                    make_celldesigner_element(
                        "lineDirection",
                        attributes={
                            "arm": str(arm),
                            "index": "0",
                            "value": "unknown",
                        },
                    )
                )
            connect_scheme.append(line_direction_list)
            extension.append(connect_scheme)
            extension.append(
                make_celldesigner_element(
                    "editPoints",
                    attributes={
                        "num0": "0",
                        "num1": "0",
                        "num2": "0",
                        "tShapeIndex": "0",
                    },
                    text="0.5,0.5",
                )
            )
    elif is_right_t:
        reactant_layout = None
        if base_reactants:
            reactant_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context,
                    base_reactants[0].referred_element,
                    frozenset_mapping,
                )
                if frozenset_mapping
                else None
            )
        product_layouts = []
        production_layouts = []
        for base_product in base_products:
            bp_species = base_product.referred_element
            bp_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context, bp_species, frozenset_mapping
                )
                if frozenset_mapping
                else None
            )
            if bp_layout is None:
                continue
            # Find the production arc for this product
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    isinstance(layout_element_item, ProductionLayout)
                    and layout_element_item.source is reaction_layout
                    and layout_element_item.target is bp_layout
                ):
                    product_layouts.append(bp_layout)
                    production_layouts.append(layout_element_item)
                    break
        computed = False
        if reactant_layout is not None and len(product_layouts) >= 2:
            # Try both product orderings; pick the one whose
            # roundtrip T-junction position is closest to the actual one.
            t_junction = reaction_layout.points()[-1]
            best_result = None
            best_dist = float("inf")
            for perm in [
                (product_layouts, production_layouts),
                (product_layouts[::-1], production_layouts[::-1]),
            ]:
                pl, prl = perm
                result = inverse_edit_points_right_t_shape(
                    reaction_layout,
                    reactant_layout,
                    pl,
                    prl,
                )
                # Roundtrip: transform T-junction back to absolute
                ep = result[0][-1]  # last edit point = T-junction in frame
                origin = reactant_layout.center()
                unit_x = pl[0].center()
                unit_y = pl[1].center()
                origin, unit_x, unit_y = make_non_degenerate_frame(
                    origin, unit_x, unit_y
                )
                trans = get_transformation_for_frame(origin, unit_x, unit_y)
                roundtrip = ep.transformed(trans)
                dist = (roundtrip.x - t_junction.x) ** 2 + (
                    roundtrip.y - t_junction.y
                ) ** 2
                if math.isfinite(dist) and dist < best_dist:
                    best_dist = dist
                    best_result = result
            if best_result is None:
                best_result = inverse_edit_points_right_t_shape(
                    reaction_layout,
                    reactant_layout,
                    product_layouts,
                    production_layouts,
                )
            (
                all_edit_points,
                num0,
                num1,
                num2,
                t_shape_index,
                reactant_anchor_name,
                product_anchor_names,
            ) = best_result
            connect_scheme = make_celldesigner_element(
                "connectScheme", attributes={"connectPolicy": "direct"}
            )
            line_direction_list = make_celldesigner_element("listOfLineDirection")
            for arm_idx, arm_count in enumerate([num0, num1, num2]):
                for i in range(arm_count + 1):
                    line_direction_list.append(
                        make_celldesigner_element(
                            "lineDirection",
                            attributes={
                                "arm": str(arm_idx),
                                "index": str(i),
                                "value": "unknown",
                            },
                        )
                    )
            connect_scheme.append(line_direction_list)
            extension.append(connect_scheme)
            edit_points_attributes = {
                "num0": str(num0),
                "num1": str(num1),
                "num2": str(num2),
                "tShapeIndex": str(t_shape_index),
            }
            extension.append(
                make_celldesigner_element(
                    "editPoints",
                    attributes=edit_points_attributes,
                    text=points_to_edit_points_text(all_edit_points),
                )
            )
            computed = True
        if not computed:
            connect_scheme = make_celldesigner_element(
                "connectScheme", attributes={"connectPolicy": "direct"}
            )
            line_direction_list = make_celldesigner_element("listOfLineDirection")
            for arm in range(3):
                line_direction_list.append(
                    make_celldesigner_element(
                        "lineDirection",
                        attributes={
                            "arm": str(arm),
                            "index": "0",
                            "value": "unknown",
                        },
                    )
                )
            connect_scheme.append(line_direction_list)
            extension.append(connect_scheme)
            extension.append(
                make_celldesigner_element(
                    "editPoints",
                    attributes={
                        "num0": "0",
                        "num1": "0",
                        "num2": "0",
                        "tShapeIndex": "0",
                    },
                    text="0.5,0.5",
                )
            )
    else:
        # Non-T-shape (1→1)
        # lineDirection count = reactant_arc_segments + product_arc_segments + 1
        reactant_layout = None
        product_layout = None
        if base_reactants:
            reactant_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context,
                    base_reactants[0].referred_element,
                    frozenset_mapping,
                )
                if frozenset_mapping
                else None
            )
        if base_products:
            product_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context,
                    base_products[0].referred_element,
                    frozenset_mapping,
                )
                if frozenset_mapping
                else None
            )
        if reactant_layout is not None:
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    isinstance(layout_element_item, ConsumptionLayout)
                    and layout_element_item.source is reaction_layout
                    and layout_element_item.target is reactant_layout
                ):
                    break
        if product_layout is not None:
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    isinstance(layout_element_item, ProductionLayout)
                    and layout_element_item.source is reaction_layout
                    and layout_element_item.target is product_layout
                ):
                    break
        computed = False
        if reactant_layout is not None and product_layout is not None:
            reactant_anchor = reactant_layout.anchor_point("center")
            product_anchor = product_layout.anchor_point("center")
            if (
                abs(reactant_anchor.x - product_anchor.x) > 1e-6
                or abs(reactant_anchor.y - product_anchor.y) > 1e-6
            ):
                (
                    edit_points,
                    reactant_anchor_name,
                    product_anchor_name,
                    rectangle_index,
                ) = inverse_edit_points_non_t_shape(
                    reaction_layout,
                    reactant_layout,
                    product_layout,
                )
                # lineDirection count: n_edit_points + 3
                n_line_dirs = len(edit_points) + 3
                connect_scheme = make_celldesigner_element(
                    "connectScheme",
                    attributes={
                        "connectPolicy": "direct",
                        "rectangleIndex": str(rectangle_index),
                    },
                )
                line_direction_list = make_celldesigner_element("listOfLineDirection")
                for i in range(n_line_dirs):
                    line_direction_list.append(
                        make_celldesigner_element(
                            "lineDirection",
                            attributes={
                                "index": str(i),
                                "value": "unknown",
                            },
                        )
                    )
                connect_scheme.append(line_direction_list)
                extension.append(connect_scheme)
                if edit_points:
                    extension.append(
                        make_celldesigner_element(
                            "editPoints",
                            text=points_to_edit_points_text(edit_points),
                        )
                    )
                computed = True
        if not computed:
            connect_scheme = make_celldesigner_element(
                "connectScheme",
                attributes={
                    "connectPolicy": "direct",
                    "rectangleIndex": "0",
                },
            )
            line_direction_list = make_celldesigner_element("listOfLineDirection")
            line_direction_list.append(
                make_celldesigner_element(
                    "lineDirection",
                    attributes={
                        "index": "0",
                        "value": "unknown",
                    },
                )
            )
            connect_scheme.append(line_direction_list)
            extension.append(connect_scheme)


def make_celldesigner_participant_link(
    writing_context: typing.Any,
    participant: typing.Any,
    tag: str,
    attr_name: str,
    frozenset_mapping: typing.Any,
    reaction_layout: typing.Any = None,
    reaction: typing.Any = None,
) -> lxml.etree._Element:
    """Build a reactantLink or productLink element."""
    species = participant.referred_element
    is_start = tag == "reactantLink"
    if reaction is not None:
        alias_layout = find_layout_for_participant(
            writing_context,
            participant,
            reaction,
            frozenset_mapping,
            reaction_layout,
            is_start,
        )
    else:
        alias_layout = (
            find_layout_for_species_in_frozenset(
                writing_context, species, frozenset_mapping
            )
            if frozenset_mapping
            else None
        )
    alias_id = get_alias_id(writing_context, alias_layout)
    link = make_celldesigner_element(
        tag,
        attributes={
            attr_name: get_species_id(species, writing_context),
            "alias": alias_id,
        },
    )
    # Compute edit points from arc layout
    edit_points = []
    anchor_name = None
    arc_layout = None
    if reaction_layout is not None and alias_layout is not None:
        is_reactant = tag == "reactantLink"
        arc_cls = ConsumptionLayout if is_reactant else ProductionLayout
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, arc_cls)
                and layout_element_item.source is reaction_layout
                and layout_element_item.target is alias_layout
            ):
                arc_layout = layout_element_item
                if is_reactant:
                    edit_points, anchor_name = inverse_edit_points_reactant_link(
                        layout_element_item,
                        alias_layout,
                        reaction_layout,
                    )
                else:
                    edit_points, anchor_name = inverse_edit_points_product_link(
                        layout_element_item,
                        alias_layout,
                        reaction_layout,
                    )
                break
    if anchor_name is not None:
        anchor_pos = anchor_name_to_position(anchor_name)
        if anchor_pos is not None:
            link.append(
                make_celldesigner_element(
                    "linkAnchor",
                    attributes={
                        "position": anchor_pos,
                    },
                )
            )
    connect_scheme = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(len(edit_points) + 1):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection", attributes={"index": str(i), "value": "unknown"}
            )
        )
    connect_scheme.append(line_direction_list)
    link.append(connect_scheme)
    if edit_points:
        link.append(
            make_celldesigner_element(
                "editPoints",
                text=points_to_edit_points_text(edit_points),
            )
        )
    link.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(arc_layout, include_type=True)
        )
    )
    return link


def make_celldesigner_participant_link_from_layout(
    writing_context: typing.Any,
    arc_layout: typing.Any,
    tag: str,
    attr_name: str,
    reaction_layout: typing.Any,
) -> lxml.etree._Element:
    """Build a reactantLink or productLink from a known arc layout.

    Used when deriving link participants from layout arcs rather than
    from model participants (which may have been deduplicated).

    Args:
        writing_context: The writing context.
        arc_layout: The ConsumptionLayout or ProductionLayout arc.
        tag: XML tag name ("reactantLink" or "productLink").
        attr_name: Attribute name for the species ("reactant" or "product").
        reaction_layout: The ReactionLayout element.

    Returns:
        The lxml element for the link.
    """
    alias_layout = arc_layout.target
    alias_id = get_alias_id(writing_context, alias_layout)
    species = get_layout_model_mapping(writing_context).get_mapping(alias_layout)
    link = make_celldesigner_element(
        tag,
        attributes={
            attr_name: get_species_id(species, writing_context),
            "alias": alias_id,
        },
    )
    edit_points = []
    anchor_name = None
    is_reactant = tag == "reactantLink"
    if is_reactant:
        edit_points, anchor_name = inverse_edit_points_reactant_link(
            arc_layout,
            alias_layout,
            reaction_layout,
        )
    else:
        edit_points, anchor_name = inverse_edit_points_product_link(
            arc_layout,
            alias_layout,
            reaction_layout,
        )
    if anchor_name is not None:
        anchor_pos = anchor_name_to_position(anchor_name)
        if anchor_pos is not None:
            link.append(
                make_celldesigner_element(
                    "linkAnchor",
                    attributes={
                        "position": anchor_pos,
                    },
                )
            )
    connect_scheme = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(len(edit_points) + 1):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection", attributes={"index": str(i), "value": "unknown"}
            )
        )
    connect_scheme.append(line_direction_list)
    link.append(connect_scheme)
    if edit_points:
        link.append(
            make_celldesigner_element(
                "editPoints",
                text=points_to_edit_points_text(edit_points),
            )
        )
    link.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(arc_layout, include_type=True)
        )
    )
    return link


def make_celldesigner_modification(
    writing_context: typing.Any,
    modifier: typing.Any,
    reaction_layout: typing.Any,
    frozenset_mapping: typing.Any,
) -> lxml.etree._Element | None:
    """Build a CD modification element for a reaction modifier."""
    species = modifier.referred_element
    if isinstance(species, BooleanLogicGate):
        return None
    alias_layout = (
        find_layout_for_species_in_frozenset(
            writing_context, species, frozenset_mapping
        )
        if frozenset_mapping
        else None
    )
    alias_id = get_alias_id(writing_context, alias_layout)
    modifier_type = _CLASS_TO_MODIFIER_TYPE.get(type(modifier), "CATALYSIS")
    # Find modifier arc layout and compute edit points
    edit_points = []
    source_anchor_name = None
    modifier_arc = None
    if reaction_layout is not None and alias_layout is not None:
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                hasattr(layout_element_item, "source")
                and hasattr(layout_element_item, "target")
                and layout_element_item.source is alias_layout
                and layout_element_item.target is reaction_layout
            ):
                modifier_arc = layout_element_item
                edit_points, source_anchor_name = inverse_edit_points_modifier(
                    layout_element_item,
                    alias_layout,
                    reaction_layout,
                    has_boolean_input=False,
                )
                break
    target_line_index = "-1,2"
    if modifier_arc is not None and reaction_layout is not None:
        target_line_index = compute_target_line_index(reaction_layout, modifier_arc)
    attrs = {
        "type": modifier_type,
        "modifiers": get_species_id(species, writing_context),
        "aliases": alias_id,
        "targetLineIndex": target_line_index,
    }
    if edit_points:
        attrs["editPoints"] = points_to_edit_points_text(edit_points)
    modification_element = make_celldesigner_element("modification", attributes=attrs)
    # connectScheme
    connect_scheme = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(len(edit_points) + 1):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection", attributes={"index": str(i), "value": "unknown"}
            )
        )
    connect_scheme.append(line_direction_list)
    modification_element.append(connect_scheme)
    # linkTarget
    link_target_attributes = {
        "species": get_species_id(species, writing_context),
        "alias": alias_id,
    }
    link_target = make_celldesigner_element(
        "linkTarget", attributes=link_target_attributes
    )
    if source_anchor_name is not None:
        anchor_pos = anchor_name_to_position(source_anchor_name)
        if anchor_pos is not None:
            link_target.append(
                make_celldesigner_element(
                    "linkAnchor", attributes={"position": anchor_pos}
                )
            )
    modification_element.append(link_target)
    # line
    modification_element.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(modifier_arc, include_type=True)
        )
    )
    return modification_element


def make_celldesigner_gate_modifications(
    writing_context: typing.Any,
    modifier: typing.Any,
    gate: typing.Any,
    reaction_layout: typing.Any,
    frozenset_mapping: typing.Any,
) -> list[lxml.etree._Element]:
    """Build CD modification entries for a boolean logic gate modifier.

    Returns a list of modification elements: first the gate entry,
    then one per input species.
    """
    result = []
    modifier_type = _CLASS_TO_MODIFIER_TYPE.get(type(modifier), "CATALYSIS")
    gate_type_map = {
        AndGate: "BOOLEAN_LOGIC_GATE_AND",
        OrGate: "BOOLEAN_LOGIC_GATE_OR",
        NotGate: "BOOLEAN_LOGIC_GATE_NOT",
        UnknownGate: "BOOLEAN_LOGIC_GATE_UNKNOWN",
    }
    gate_type = gate_type_map.get(type(gate), "BOOLEAN_LOGIC_GATE_AND")

    # Find the gate layout in the reaction's frozenset.
    gate_layout = None
    if frozenset_mapping is not None:
        for elem in frozenset_mapping:
            if isinstance(
                elem,
                (
                    AndGateLayout,
                    OrGateLayout,
                    NotGateLayout,
                    UnknownGateLayout,
                ),
            ):
                gate_layout = elem
                break

    # Build list of (model_element, alias_layout) from LogicArcLayouts
    # to resolve the correct alias for each gate input.
    logic_arc_inputs = []
    if gate_layout is not None:
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, LogicArcLayout)
                and layout_element_item.source is gate_layout
            ):
                input_alias_layout = layout_element_item.target
                input_model = get_layout_model_mapping(writing_context).get_mapping(
                    input_alias_layout
                )
                if input_model is not None:
                    logic_arc_inputs.append((input_model, input_alias_layout))

    # Collect input aliases using LogicArcLayout when available,
    # falling back to frozenset/global lookup.
    input_species_ids = []
    input_alias_ids = []
    for inp in sorted(gate.inputs, key=lambda s: s.id_ or ""):
        input_species = inp.referred_element
        sbml_inp = writing_context.subunit_to_complex.get(
            id(input_species), input_species
        )
        input_species_ids.append(get_species_id(sbml_inp, writing_context))
        # Try LogicArcLayout first (correct alias for multi-alias species)
        alias_layout = None
        for arc_model, arc_layout in logic_arc_inputs:
            if arc_model is input_species:
                alias_layout = arc_layout
                logic_arc_inputs.remove((arc_model, arc_layout))
                break
        # Fallback: try frozenset, then global
        if alias_layout is None:
            alias_layout = (
                find_layout_for_species_in_frozenset(
                    writing_context, input_species, frozenset_mapping
                )
                if frozenset_mapping
                else None
            )
        if alias_layout is None:
            for layout_key in get_layouts(writing_context, input_species):
                if isinstance(layout_key, frozenset):
                    continue
                if isinstance(layout_key, CellDesignerNode):
                    alias_layout = layout_key
                    break
        input_alias_ids.append(get_alias_id(writing_context, alias_layout))
    gate_edit_points = ""
    if gate_layout is not None:
        pos = gate_layout.position
        gate_edit_points = f"{pos.x},{pos.y}"
    gate_attrs = {
        "type": gate_type,
        "modificationType": modifier_type,
        "modifiers": ",".join(input_species_ids),
        "aliases": ",".join(input_alias_ids),
        "targetLineIndex": "-1,2",
    }
    if gate_edit_points:
        gate_attrs["editPoints"] = gate_edit_points
    gate_mod = make_celldesigner_element("modification", attributes=gate_attrs)
    gate_cs = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    gate_lld = make_celldesigner_element("listOfLineDirection")
    gate_lld.append(
        make_celldesigner_element(
            "lineDirection", attributes={"index": "0", "value": "unknown"}
        )
    )
    gate_cs.append(gate_lld)
    gate_mod.append(gate_cs)
    # Find the gate-to-reaction arc for line attributes
    gate_to_reaction_arc = None
    if gate_layout is not None and reaction_layout is not None:
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                hasattr(layout_element_item, "source")
                and hasattr(layout_element_item, "target")
                and layout_element_item.source is gate_layout
                and layout_element_item.target is reaction_layout
            ):
                gate_to_reaction_arc = layout_element_item
                break
    gate_mod.append(
        make_celldesigner_element(
            "line",
            attributes=get_line_attributes(gate_to_reaction_arc, include_type=True),
        )
    )
    result.append(gate_mod)

    # Per-input entries
    for i, inp in enumerate(sorted(gate.inputs, key=lambda s: s.id_ or "")):
        input_species = inp.referred_element
        sbml_inp = writing_context.subunit_to_complex.get(
            id(input_species), input_species
        )
        inp_attrs = {
            "type": modifier_type,
            "modifiers": get_species_id(sbml_inp, writing_context),
            "aliases": input_alias_ids[i],
            "targetLineIndex": "-1,2",
        }
        inp_mod = make_celldesigner_element("modification", attributes=inp_attrs)
        connect_scheme = make_celldesigner_element(
            "connectScheme", attributes={"connectPolicy": "direct"}
        )
        line_direction_list = make_celldesigner_element("listOfLineDirection")
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection", attributes={"index": "0", "value": "unknown"}
            )
        )
        connect_scheme.append(line_direction_list)
        inp_mod.append(connect_scheme)
        # linkTarget — find the input-to-gate arc for line attributes
        input_to_gate_arc = None
        if input_alias_ids[i]:
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    hasattr(layout_element_item, "source")
                    and hasattr(layout_element_item, "target")
                    and layout_element_item.target is gate_layout
                    and getattr(layout_element_item.source, "id_", None)
                    == input_alias_ids[i]
                ):
                    input_to_gate_arc = layout_element_item
                    break
        link_target = make_celldesigner_element(
            "linkTarget",
            attributes={
                "species": get_species_id(sbml_inp, writing_context),
                "alias": input_alias_ids[i],
            },
        )
        inp_mod.append(link_target)
        inp_mod.append(
            make_celldesigner_element(
                "line",
                attributes=get_line_attributes(input_to_gate_arc, include_type=True),
            )
        )
        result.append(inp_mod)

    return result


def make_celldesigner_modulation_reaction(
    writing_context: typing.Any, modulation: typing.Any, frozenset_mapping: typing.Any
) -> lxml.etree._Element | None:
    """Build a modulation as a fake SBML reaction."""
    source = modulation.source
    target = modulation.target

    if isinstance(source, BooleanLogicGate):
        return make_celldesigner_gate_modulation_reaction(writing_context, modulation)

    # Resolve layouts from the given frozenset
    modulation_layout = None
    source_layout = None
    target_layout = None
    if frozenset_mapping is not None:
        for layout_element in frozenset_mapping:
            if (
                get_layout_model_mapping(writing_context).get_mapping(layout_element)
                is modulation
            ):
                modulation_layout = layout_element
                break
        if modulation_layout is not None and hasattr(modulation_layout, "source"):
            source_layout = modulation_layout.source
            target_layout = modulation_layout.target
    else:
        for layout_key in get_layouts(writing_context, modulation):
            if not isinstance(layout_key, frozenset):
                modulation_layout = layout_key

    # Derive XML id from layout when available
    if modulation_layout is not None:
        xml_id = get_xml_id(
            writing_context,
            modulation_layout,
            candidate=modulation_layout.id_.removesuffix("_layout"),
        )
    else:
        xml_id = get_xml_id(writing_context, modulation)
    attrs = {
        "metaid": xml_id,
        "id": xml_id,
        "reversible": "false",
    }
    reaction_element = make_lxml_element("reaction", attributes=attrs)

    # notes
    notes_element = build_sbml_notes(writing_context, modulation)
    if notes_element is not None:
        reaction_element.append(notes_element)

    if source_layout is None and source is not None:
        for layout_key in get_layouts(writing_context, source):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, CellDesignerNode):
                source_layout = layout_key
                break

    if target_layout is None and target is not None:
        for layout_key in get_layouts(writing_context, target):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, CellDesignerNode):
                target_layout = layout_key
                break

    source_alias = get_alias_id(writing_context, source_layout)
    target_alias = get_alias_id(writing_context, target_layout)
    source_id = get_species_id(source, writing_context) if source else ""
    target_id = get_species_id(target, writing_context) if target else ""

    # CD extension
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    reaction_type = get_modulation_reaction_type(modulation)
    extension.append(make_celldesigner_element("reactionType", text=reaction_type))

    # Compute edit points for the modulation
    edit_points = []
    source_anchor_name = None
    target_anchor_name = None
    if (
        modulation_layout is not None
        and source_layout is not None
        and target_layout is not None
    ):
        edit_points, source_anchor_name, target_anchor_name = (
            inverse_edit_points_modulation(
                modulation_layout,
                source_layout,
                target_layout,
                has_boolean_input=False,
            )
        )

    # baseReactants (source)
    base_reactants_element = make_celldesigner_element("baseReactants")
    base_reactant = make_celldesigner_element(
        "baseReactant", attributes={"species": source_id, "alias": source_alias}
    )
    if source_anchor_name is not None:
        anchor_pos = anchor_name_to_position(source_anchor_name)
        if anchor_pos is not None:
            base_reactant.append(
                make_celldesigner_element(
                    "linkAnchor", attributes={"position": anchor_pos}
                )
            )
    base_reactants_element.append(base_reactant)
    extension.append(base_reactants_element)

    # baseProducts (target)
    base_products_element = make_celldesigner_element("baseProducts")
    base_product = make_celldesigner_element(
        "baseProduct", attributes={"species": target_id, "alias": target_alias}
    )
    if target_anchor_name is not None:
        anchor_pos = anchor_name_to_position(target_anchor_name)
        if anchor_pos is not None:
            base_product.append(
                make_celldesigner_element(
                    "linkAnchor", attributes={"position": anchor_pos}
                )
            )
    base_products_element.append(base_product)
    extension.append(base_products_element)

    extension.append(make_celldesigner_element("listOfReactantLinks"))
    extension.append(make_celldesigner_element("listOfProductLinks"))

    # connectScheme — for modulations-as-reactions:
    # ld = n_edit_points + 3, rectangleIndex = n_edit_points
    num_edit_points = len(edit_points)
    connect_scheme = make_celldesigner_element(
        "connectScheme",
        attributes={
            "connectPolicy": "direct",
            "rectangleIndex": str(num_edit_points),
        },
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(num_edit_points + 3):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection",
                attributes={
                    "index": str(i),
                    "value": "unknown",
                },
            )
        )
    connect_scheme.append(line_direction_list)
    extension.append(connect_scheme)

    if edit_points:
        extension.append(
            make_celldesigner_element(
                "editPoints",
                text=points_to_edit_points_text(edit_points),
            )
        )

    extension.append(make_celldesigner_element("listOfModification"))
    extension.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(modulation_layout, include_type=True)
        )
    )

    annotation.append(extension)
    append_rdf_to_annotation(writing_context, annotation, modulation, xml_id)
    reaction_element.append(annotation)

    # SBML listOfReactants (use complex ID for subunits)
    sbml_source = (
        writing_context.subunit_to_complex.get(id(source), source) if source else source
    )
    list_of_reactants = make_lxml_element("listOfReactants")
    species_reference = make_lxml_element(
        "speciesReference",
        attributes={
            "species": get_species_id(sbml_source, writing_context)
            if sbml_source
            else ""
        },
    )
    species_reference_annotation = make_lxml_element("annotation")
    species_reference_extension = make_celldesigner_element("extension")
    species_reference_extension.append(
        make_celldesigner_element("alias", text=source_alias)
    )
    species_reference_annotation.append(species_reference_extension)
    species_reference.append(species_reference_annotation)
    list_of_reactants.append(species_reference)
    reaction_element.append(list_of_reactants)

    # SBML listOfProducts (use complex ID for subunits)
    sbml_target = (
        writing_context.subunit_to_complex.get(id(target), target) if target else target
    )
    list_of_products = make_lxml_element("listOfProducts")
    pr = make_lxml_element(
        "speciesReference",
        attributes={
            "species": get_species_id(sbml_target, writing_context)
            if sbml_target
            else ""
        },
    )
    product_reference_annotation = make_lxml_element("annotation")
    product_reference_extension = make_celldesigner_element("extension")
    product_reference_extension.append(
        make_celldesigner_element("alias", text=target_alias)
    )
    product_reference_annotation.append(product_reference_extension)
    pr.append(product_reference_annotation)
    list_of_products.append(pr)
    reaction_element.append(list_of_products)

    return reaction_element


def make_celldesigner_gate_modulation_reaction(
    writing_context: typing.Any, modulation: typing.Any
) -> lxml.etree._Element:
    """Build a boolean gate modulation as a fake SBML reaction.

    Structure: reactionType=BOOLEAN_LOGIC_GATE, baseReactants=gate inputs,
    baseProducts=target, listOfGateMember for gate+per-input entries.
    """
    gate = modulation.source
    target = modulation.target

    gate_type_map = {
        AndGate: "BOOLEAN_LOGIC_GATE_AND",
        OrGate: "BOOLEAN_LOGIC_GATE_OR",
        NotGate: "BOOLEAN_LOGIC_GATE_NOT",
        UnknownGate: "BOOLEAN_LOGIC_GATE_UNKNOWN",
    }
    gate_type = gate_type_map.get(type(gate), "BOOLEAN_LOGIC_GATE_AND")

    # Determine the modification type from the modulation type
    modifier_type = get_modulation_reaction_type(modulation)

    modulation_id = get_xml_id(writing_context, modulation)
    attrs = {
        "metaid": modulation_id,
        "id": modulation_id,
        "reversible": "false",
    }
    reaction_element = make_lxml_element("reaction", attributes=attrs)

    # notes
    notes_element = build_sbml_notes(writing_context, modulation)
    if notes_element is not None:
        reaction_element.append(notes_element)

    # Find the gate layout
    gate_layout = None
    for layout_element_item in writing_context.map_.layout.layout_elements:
        if isinstance(
            layout_element_item,
            (
                AndGateLayout,
                OrGateLayout,
                NotGateLayout,
                UnknownGateLayout,
            ),
        ):
            gate_model = get_layout_model_mapping(writing_context).get_mapping(
                layout_element_item
            )
            if gate_model is gate:
                gate_layout = layout_element_item
                break

    # Find inputs via logic arcs (preserves duplicates unlike gate.inputs)
    input_layouts = []
    if gate_layout is not None:
        for layout_element_item in writing_context.map_.layout.layout_elements:
            if (
                isinstance(layout_element_item, LogicArcLayout)
                and layout_element_item.source is gate_layout
            ):
                inp_layout = layout_element_item.target
                model_info = get_layout_model_mapping(writing_context).get_mapping(
                    inp_layout
                )
                inp_model = (
                    (model_info[0] if isinstance(model_info, tuple) else model_info)
                    if model_info is not None
                    else None
                )
                if inp_model is not None:
                    input_layouts.append((inp_model, inp_layout))
    if not input_layouts:
        # Fallback to gate.inputs if no logic arcs found
        for inp in sorted(gate.inputs, key=lambda s: s.id_ or ""):
            inp_layout = None
            for layout_key in get_layouts(writing_context, inp.referred_element):
                if isinstance(layout_key, frozenset):
                    continue
                if isinstance(layout_key, CellDesignerNode):
                    inp_layout = layout_key
                    break
            input_layouts.append((inp.referred_element, inp_layout))

    target_layout = None
    if target is not None:
        for layout_key in get_layouts(writing_context, target):
            if isinstance(layout_key, frozenset):
                continue
            if isinstance(layout_key, CellDesignerNode):
                target_layout = layout_key
                break

    gate_edit_points = ""
    if gate_layout is not None:
        gate_edit_points = f"{gate_layout.position.x},{gate_layout.position.y}"

    target_alias = get_alias_id(writing_context, target_layout)

    # CD extension
    annotation = make_lxml_element("annotation")
    extension = make_celldesigner_element("extension")
    extension.append(
        make_celldesigner_element("reactionType", text="BOOLEAN_LOGIC_GATE")
    )

    # baseReactants (gate inputs)
    base_reactants_element = make_celldesigner_element("baseReactants")
    for inp, inp_layout in input_layouts:
        sbml_inp = writing_context.subunit_to_complex.get(id(inp), inp)
        alias_id = get_alias_id(writing_context, inp_layout)
        base_reactant = make_celldesigner_element(
            "baseReactant",
            attributes={
                "species": get_species_id(sbml_inp, writing_context),
                "alias": alias_id,
            },
        )
        # Try to find linkAnchor from logic arcs
        if gate_layout is not None and inp_layout is not None:
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    hasattr(layout_element_item, "source")
                    and hasattr(layout_element_item, "target")
                    and layout_element_item.source is gate_layout
                    and layout_element_item.target is inp_layout
                ):
                    endpoint = layout_element_item.points()[-1]
                    anchor = infer_anchor_position(inp_layout, endpoint)
                    if anchor is not None:
                        base_reactant.append(
                            make_celldesigner_element(
                                "linkAnchor", attributes={"position": anchor}
                            )
                        )
                    break
        base_reactants_element.append(base_reactant)
    extension.append(base_reactants_element)

    # baseProducts (target)
    base_products_element = make_celldesigner_element("baseProducts")
    sbml_target = (
        writing_context.subunit_to_complex.get(id(target), target) if target else target
    )
    base_product = make_celldesigner_element(
        "baseProduct",
        attributes={
            "species": get_species_id(sbml_target, writing_context)
            if sbml_target
            else "",
            "alias": target_alias,
        },
    )
    base_products_element.append(base_product)
    extension.append(base_products_element)

    extension.append(make_celldesigner_element("listOfReactantLinks"))
    extension.append(make_celldesigner_element("listOfProductLinks"))

    # Compute editPoints: intermediate points from modulation layout + gate position
    modulation_layout = None
    for layout_key in get_layouts(writing_context, modulation):
        if isinstance(layout_key, frozenset):
            for elem in layout_key:
                model = get_layout_model_mapping(writing_context).get_mapping(elem)
                if model is modulation:
                    modulation_layout = elem
                    break
        elif not isinstance(layout_key, frozenset):
            modulation_layout = layout_key

    edit_points_parts = []
    if (
        gate_layout is not None
        and modulation_layout is not None
        and target_layout is not None
    ):
        mod_edit_points, _, _ = inverse_edit_points_modulation(
            modulation_layout,
            gate_layout,
            target_layout,
            has_boolean_input=True,
        )
        edit_points_parts.extend(f"{p.x},{p.y}" for p in mod_edit_points)
    if gate_edit_points:
        edit_points_parts.append(gate_edit_points)
    edit_points_text = " ".join(edit_points_parts)

    # connectScheme — gate modulations use rectangleIndex=1
    # and lineDirection count = len(inputs) + 3
    num_line_directions = len(input_layouts) + 3
    connect_scheme = make_celldesigner_element(
        "connectScheme",
        attributes={
            "connectPolicy": "direct",
            "rectangleIndex": "1",
        },
    )
    line_direction_list = make_celldesigner_element("listOfLineDirection")
    for i in range(num_line_directions):
        line_direction_list.append(
            make_celldesigner_element(
                "lineDirection",
                attributes={
                    "index": str(i),
                    "value": "unknown",
                },
            )
        )
    connect_scheme.append(line_direction_list)
    extension.append(connect_scheme)

    # editPoints — always write, even if empty, to avoid reader crash
    extension.append(
        make_celldesigner_element("editPoints", text=edit_points_text or "0.0,0.0")
    )

    extension.append(make_celldesigner_element("listOfModification"))

    # listOfGateMember
    gate_member_list = make_celldesigner_element("listOfGateMember")
    input_alias_ids = [get_alias_id(writing_context, il) for _, il in input_layouts]
    # Gate entry
    gate_attrs = {
        "type": gate_type,
        "aliases": ",".join(input_alias_ids),
        "modificationType": modifier_type,
    }
    gate_attrs["editPoints"] = gate_edit_points or "0.0,0.0"
    gate_member = make_celldesigner_element("GateMember", attributes=gate_attrs)
    gate_member_connect_scheme = make_celldesigner_element(
        "connectScheme", attributes={"connectPolicy": "direct"}
    )
    gate_member_line_direction_list = make_celldesigner_element("listOfLineDirection")
    gate_member_line_direction_list.append(
        make_celldesigner_element(
            "lineDirection",
            attributes={
                "index": "0",
                "value": "unknown",
            },
        )
    )
    gate_member_connect_scheme.append(gate_member_line_direction_list)
    gate_member.append(gate_member_connect_scheme)
    gate_member.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(modulation_layout, include_type=True)
        )
    )
    gate_member_list.append(gate_member)

    # Per-input entries
    for inp, inp_layout in input_layouts:
        sbml_inp = writing_context.subunit_to_complex.get(id(inp), inp)
        alias_id = get_alias_id(writing_context, inp_layout)
        inp_member = make_celldesigner_element(
            "GateMember",
            attributes={
                "type": modifier_type,
                "aliases": alias_id,
            },
        )
        inp_cs = make_celldesigner_element(
            "connectScheme", attributes={"connectPolicy": "direct"}
        )
        inp_lld = make_celldesigner_element("listOfLineDirection")
        inp_lld.append(
            make_celldesigner_element(
                "lineDirection",
                attributes={
                    "index": "0",
                    "value": "unknown",
                },
            )
        )
        inp_cs.append(inp_lld)
        inp_member.append(inp_cs)
        link_target = make_celldesigner_element(
            "linkTarget",
            attributes={
                "species": get_species_id(sbml_inp, writing_context),
                "alias": alias_id,
            },
        )
        input_arc_layout = None
        if gate_layout is not None and inp_layout is not None:
            for layout_element_item in writing_context.map_.layout.layout_elements:
                if (
                    hasattr(layout_element_item, "source")
                    and hasattr(layout_element_item, "target")
                    and layout_element_item.source is gate_layout
                    and layout_element_item.target is inp_layout
                ):
                    input_arc_layout = layout_element_item
                    endpoint = layout_element_item.points()[-1]
                    anchor = infer_anchor_position(inp_layout, endpoint)
                    if anchor is not None:
                        link_target.append(
                            make_celldesigner_element(
                                "linkAnchor", attributes={"position": anchor}
                            )
                        )
                    break
        inp_member.append(link_target)
        inp_member.append(
            make_celldesigner_element(
                "line",
                attributes=get_line_attributes(input_arc_layout, include_type=True),
            )
        )
        gate_member_list.append(inp_member)

    extension.append(gate_member_list)
    extension.append(
        make_celldesigner_element(
            "line", attributes=get_line_attributes(modulation_layout, include_type=True)
        )
    )

    annotation.append(extension)
    append_rdf_to_annotation(
        writing_context,
        annotation,
        modulation,
        get_xml_id(writing_context, modulation),
    )
    reaction_element.append(annotation)

    # SBML listOfReactants (gate inputs)
    list_of_reactants = make_lxml_element("listOfReactants")
    for inp, inp_layout in input_layouts:
        sbml_inp = writing_context.subunit_to_complex.get(id(inp), inp)
        alias_id = get_alias_id(writing_context, inp_layout)
        species_reference = make_lxml_element(
            "speciesReference",
            attributes={
                "species": get_species_id(sbml_inp, writing_context),
            },
        )
        species_reference_annotation = make_lxml_element("annotation")
        species_reference_extension = make_celldesigner_element("extension")
        species_reference_extension.append(
            make_celldesigner_element("alias", text=alias_id)
        )
        species_reference_annotation.append(species_reference_extension)
        species_reference.append(species_reference_annotation)
        list_of_reactants.append(species_reference)
    reaction_element.append(list_of_reactants)

    # SBML listOfProducts (target)
    list_of_products = make_lxml_element("listOfProducts")
    pr = make_lxml_element(
        "speciesReference",
        attributes={
            "species": get_species_id(sbml_target, writing_context)
            if sbml_target
            else "",
        },
    )
    product_reference_annotation = make_lxml_element("annotation")
    product_reference_extension = make_celldesigner_element("extension")
    product_reference_extension.append(
        make_celldesigner_element("alias", text=target_alias)
    )
    product_reference_annotation.append(product_reference_extension)
    pr.append(product_reference_annotation)
    list_of_products.append(pr)
    reaction_element.append(list_of_products)

    return reaction_element


# ---------------------------------------------------------------------------
# Writer class
# ---------------------------------------------------------------------------
