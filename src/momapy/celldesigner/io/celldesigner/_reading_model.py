"""CellDesigner model-building functions.

Each ``make_*`` function takes a ``reading_context`` as its first
argument, checks whether ``reading_context.model`` is ``None``, and
returns ``None`` early when no model is being built.
"""

import typing

from momapy.celldesigner.io.celldesigner._reading_parsing import (
    get_base_products,
    get_base_reactants,
    get_notes,
    get_product_links,
    get_products,
    get_rdf,
    get_rdf_from_notes,
    get_reactant_links,
    get_reactants,
    get_species_reference,
    get_template_from_species,
    get_name,
)

from momapy.sbml.io.sbml._reading_model import make_annotations, make_notes
from momapy.builder import new_builder_object
from momapy.celldesigner.model import (
    BooleanLogicGateInput,
    Compartment,
    Modification,
    ModificationResidue,
    Reactant,
    StructuralState,
)

if typing.TYPE_CHECKING:
    from momapy.celldesigner.io.celldesigner._reading_context import (
        CellDesignerReadingContext,
    )


def make_annotations_from_element(cd_element: typing.Any) -> list[typing.Any]:
    """Extract RDF annotations from a CellDesigner XML element.

    Args:
        cd_element: The CellDesigner XML element.

    Returns:
        List of annotations (empty if no RDF block).
    """
    cd_rdf = get_rdf(cd_element)
    if cd_rdf is None:
        return []
    return make_annotations(cd_rdf)


def make_annotations_from_notes(cd_notes: typing.Any) -> list[typing.Any]:
    """Extract RDF annotations embedded in an SBML notes element.

    Args:
        cd_notes: The SBML notes XML element.

    Returns:
        List of annotations (empty if the notes contain no RDF).
    """
    cd_rdf = get_rdf_from_notes(cd_notes)
    if cd_rdf is None:
        return []
    return make_annotations(cd_rdf)


def make_notes_from_element(cd_element: typing.Any) -> typing.Any:
    """Extract the notes block from a CellDesigner XML element.

    Args:
        cd_element: The CellDesigner XML element.

    Returns:
        The parsed notes, or an empty notes object if absent.
    """
    cd_notes = get_notes(cd_element)
    return make_notes(cd_notes)


def make_and_add_annotations(
    reading_context: "CellDesignerReadingContext",
    cd_element: typing.Any,
    model_element: typing.Any,
    source_id: str | None = None,
) -> None:
    """Add annotations from an XML element to the reading context.

    Populates both ``element_to_annotations`` (keyed by model element,
    merged view) and ``source_id_to_annotations`` (keyed by source XML
    id, per-source granularity) when ``source_id`` is given.

    Args:
        reading_context: The reading context.
        cd_element: The CellDesigner XML element.
        model_element: The frozen model element to associate with.
        source_id: The raw source XML id of ``cd_element``.  When
            ``None``, the per-source side table is not populated (used
            for elements without a stable source id, e.g. the SBML
            ``<model>`` root).
    """
    if reading_context.with_annotations:
        annotations = make_annotations_from_element(cd_element)
        if annotations:
            reading_context.element_to_annotations[model_element].update(annotations)
            if source_id is not None:
                reading_context.source_id_to_annotations[source_id].update(annotations)


def make_and_add_notes(
    reading_context: "CellDesignerReadingContext",
    cd_element: typing.Any,
    model_element: typing.Any,
    source_id: str | None = None,
) -> None:
    """Add notes from an XML element to the reading context.

    Populates both ``element_to_notes`` (merged view) and
    ``source_id_to_notes`` (per-source granularity) when ``source_id``
    is given.

    Args:
        reading_context: The reading context.
        cd_element: The CellDesigner XML element.
        model_element: The frozen model element to associate with.
        source_id: The raw source XML id of ``cd_element``.  When
            ``None``, the per-source side table is not populated.
    """
    if reading_context.with_notes:
        notes = make_notes_from_element(cd_element)
        if notes:
            reading_context.element_to_notes[model_element].update(notes)
            if source_id is not None:
                reading_context.source_id_to_notes[source_id].update(notes)


def make_and_add_annotations_from_notes(
    reading_context: "CellDesignerReadingContext",
    cd_notes: typing.Any,
    model_element: typing.Any,
    source_id: str | None = None,
) -> None:
    """Add RDF annotations embedded in a ``<notes>`` block.

    Used by the CellDesigner reader for included species, where RDF
    annotations are nested inside the notes block instead of a
    top-level ``<annotation>`` element.

    Args:
        reading_context: The reading context.
        cd_notes: The SBML notes XML element.
        model_element: The frozen model element to associate with.
        source_id: The raw source XML id of the enclosing element.
            When ``None``, the per-source side table is not populated.
    """
    if reading_context.with_annotations and cd_notes is not None:
        annotations = make_annotations_from_notes(cd_notes)
        if annotations:
            reading_context.element_to_annotations[model_element].update(annotations)
            if source_id is not None:
                reading_context.source_id_to_annotations[source_id].update(annotations)


def make_compartment(
    reading_context: "CellDesignerReadingContext", cd_compartment: typing.Any
) -> typing.Any:
    """Create a compartment model builder from a CellDesigner compartment.

    Args:
        reading_context: The reading context.
        cd_compartment: The CellDesigner compartment XML element.

    Returns:
        A compartment model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(Compartment)
    model_element.id_ = cd_compartment.get("id")
    model_element.name = get_name(cd_compartment.get("name"))
    model_element.metaid = cd_compartment.get("metaid")
    return model_element


def make_species_template(
    reading_context: "CellDesignerReadingContext",
    cd_species_template: typing.Any,
    model_element_cls: typing.Any,
) -> typing.Any:
    """Create a species template model builder.

    Args:
        reading_context: The reading context.
        cd_species_template: The CellDesigner species template XML element.
        model_element_cls: The model element class to instantiate.

    Returns:
        A species template model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    model_element.id_ = cd_species_template.get("id")
    model_element.name = get_name(cd_species_template.get("name"))
    return model_element


def make_modification_residue(
    reading_context: "CellDesignerReadingContext",
    cd_modification_residue: typing.Any,
    super_cd_element: typing.Any,
    order: int,
) -> typing.Any:
    """Create a modification residue model builder.

    Args:
        reading_context: The reading context.
        cd_modification_residue: The CellDesigner modification residue XML element.
        super_cd_element: The parent template XML element, used to compose a
            globally unique residue id.
        order: The residue index within its parent template.

    Returns:
        A modification residue model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(ModificationResidue)
    cd_modification_residue_id = (
        f"{super_cd_element.get('id')}_{cd_modification_residue.get('id')}"
    )
    model_element.id_ = cd_modification_residue_id
    model_element.name = get_name(cd_modification_residue.get("name"))
    model_element.order = order
    return model_element


def make_region(
    reading_context: "CellDesignerReadingContext",
    cd_region: typing.Any,
    model_element_cls: typing.Any,
    super_cd_element: typing.Any,
    order: int,
) -> typing.Any:
    """Create a region model builder.

    Args:
        reading_context: The reading context.
        cd_region: The CellDesigner region XML element.
        model_element_cls: The model element class to instantiate.
        super_cd_element: The parent template XML element, used to compose a
            globally unique region id.
        order: The region index within its parent template.

    Returns:
        A region model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    cd_region_id = f"{super_cd_element.get('id')}_{cd_region.get('id')}"
    model_element.id_ = cd_region_id
    model_element.name = get_name(cd_region.get("name"))
    active = cd_region.get("active")
    if active is not None:
        model_element.active = True if active == "true" else False
    model_element.order = order
    return model_element


def make_species(
    reading_context: "CellDesignerReadingContext",
    cd_species: typing.Any,
    model_element_cls: typing.Any,
    name: str | None,
    homomultimer: int,
    hypothetical: bool,
    active: bool,
) -> typing.Any:
    """Create a species model builder.

    Args:
        reading_context: The reading context.
        cd_species: The CellDesigner species XML element.
        model_element_cls: The model element class to instantiate. May be
            None for species with no model representation (e.g. Degraded).
        name: The species display name.
        homomultimer: Multimer count (``1`` if not a multimer).
        hypothetical: Whether the species is marked hypothetical.
        active: Whether the species is active.

    Returns:
        A species model builder, or ``None`` if no model element should be
        created.
    """
    if reading_context.model is None or model_element_cls is None:
        return None
    model_element = new_builder_object(model_element_cls)
    species_xml_id = cd_species.get("id")
    model_element.id_ = f"{species_xml_id}_active" if active else species_xml_id
    model_element.name = name
    model_element.metaid = cd_species.get("metaid")
    cd_compartment_id = cd_species.get("compartment")
    if cd_compartment_id is not None:
        compartment_model_element = next(
            iter(reading_context.xml_id_to_model_element.get(cd_compartment_id, ())),
            None,
        )
        model_element.compartment = compartment_model_element
    cd_species_template = get_template_from_species(
        cd_species, reading_context.xml_id_to_xml_element
    )
    if cd_species_template is not None:
        model_element.template = next(
            iter(
                reading_context.xml_id_to_model_element.get(
                    cd_species_template.get("id"), ()
                )
            ),
            None,
        )
    model_element.homomultimer = homomultimer
    model_element.hypothetical = hypothetical
    model_element.active = active
    return model_element


def make_species_modification(
    reading_context: "CellDesignerReadingContext",
    modification_state: typing.Any,
    cd_modification_residue_id: str,
) -> typing.Any:
    """Create a species modification model builder.

    Args:
        reading_context: The reading context.
        modification_state: The modification state (e.g. ``"phosphorylated"``).
        cd_modification_residue_id: The composite id of the target residue.

    Returns:
        A modification model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(Modification)
    modification_residue_model_element = next(
        iter(
            reading_context.xml_id_to_model_element.get(cd_modification_residue_id, ())
        ),
        None,
    )
    model_element.residue = modification_residue_model_element
    model_element.state = modification_state
    return model_element


def make_species_structural_state(
    reading_context: "CellDesignerReadingContext",
    cd_species_structural_state: typing.Any,
) -> typing.Any:
    """Create a species structural state model builder.

    Args:
        reading_context: The reading context.
        cd_species_structural_state: The CellDesigner structural state XML element.

    Returns:
        A structural state model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(StructuralState)
    model_element.value = cd_species_structural_state.get("structuralState")
    return model_element


def make_reaction(
    reading_context: "CellDesignerReadingContext",
    cd_reaction: typing.Any,
    model_element_cls: typing.Any,
) -> typing.Any:
    """Create a reaction model builder.

    Args:
        reading_context: The reading context.
        cd_reaction: The CellDesigner reaction XML element.
        model_element_cls: The reaction model element class to instantiate.

    Returns:
        A reaction model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    model_element.id_ = cd_reaction.get("id")
    model_element.reversible = cd_reaction.get("reversible") == "true"
    return model_element


def get_outermost_species_model_element(
    reading_context: "CellDesignerReadingContext",
    cd_alias_id: str,
) -> typing.Any:
    """Return the species model element of the outermost alias holding an alias.

    The outermost alias is found by following the `complexSpeciesAlias`
    attributes from the alias; it is the alias itself if the alias is not in
    a complex. The lookup goes through aliases because the species model
    element depends on the alias (its activity).

    Args:
        reading_context: The reading context.
        cd_alias_id: The id of the species alias.

    Returns:
        The species model element, or ``None`` if no model element is
        registered for the outermost alias.
    """
    cd_complex_alias_id = reading_context.xml_id_to_xml_element[cd_alias_id].get(
        "complexSpeciesAlias"
    )
    while cd_complex_alias_id is not None:
        cd_alias_id = cd_complex_alias_id
        cd_complex_alias_id = reading_context.xml_id_to_xml_element[cd_alias_id].get(
            "complexSpeciesAlias"
        )
    return next(
        iter(reading_context.xml_id_to_model_element.get(cd_alias_id, ())), None
    )


def make_participant(
    reading_context: "CellDesignerReadingContext",
    model_element_cls: type,
    cd_participant: typing.Any,
    cd_reaction: typing.Any,
) -> typing.Any:
    """Create a reactant or product model builder from a participant entry.

    The participant refers to the species of the outermost alias holding the
    alias of the entry (see `get_outermost_species_model_element`). The
    entries of one reaction side whose referred species are equal give one
    participant: it is a base participant if one of the entries is a base
    entry, and its stoichiometry is the number of references (a reference
    with a stoichiometry counting for that value).

    Args:
        reading_context: The reading context.
        model_element_cls: ``Reactant`` or ``Product``.
        cd_participant: The base participant or participant link element.
        cd_reaction: The enclosing reaction XML element, used to locate the
            participant entries and ``speciesReference`` elements.

    Returns:
        A reactant or product model builder, or ``None`` if no model is being
        built or the referred alias is a Degraded species.
    """
    if reading_context.model is None:
        return None
    if cd_participant.get("alias") in reading_context.cd_degraded_alias_ids:
        return None
    if model_element_cls is Reactant:
        cd_base_participants = get_base_reactants(cd_reaction)
        cd_participant_links = get_reactant_links(cd_reaction)
        cd_species_references = get_reactants(cd_reaction)
    else:
        cd_base_participants = get_base_products(cd_reaction)
        cd_participant_links = get_product_links(cd_reaction)
        cd_species_references = get_products(cd_reaction)
    species_model_element = get_outermost_species_model_element(
        reading_context, cd_participant.get("alias")
    )
    cd_base_group = [
        cd_base_participant
        for cd_base_participant in cd_base_participants
        if get_outermost_species_model_element(
            reading_context, cd_base_participant.get("alias")
        )
        == species_model_element
    ]
    cd_link_group = [
        cd_participant_link
        for cd_participant_link in cd_participant_links
        if get_outermost_species_model_element(
            reading_context, cd_participant_link.get("alias")
        )
        == species_model_element
    ]
    cd_species_reference_group = [
        get_species_reference(cd_member, cd_species_references)
        for cd_member in cd_base_group + cd_link_group
    ]
    model_element = new_builder_object(model_element_cls)
    model_element.base = bool(cd_base_group)
    model_element.referred_element = species_model_element
    cd_first_species_reference = cd_species_reference_group[0]
    if cd_first_species_reference is not None:
        model_element.id_ = cd_first_species_reference.get("metaid")
    if model_element.id_ is None:
        cd_species_id = (
            cd_participant.get("species")
            or cd_participant.get("reactant")
            or cd_participant.get("product")
        )
        model_element.id_ = f"{cd_reaction.get('id')}_{cd_species_id}"
    if len(cd_species_reference_group) == 1:
        if cd_first_species_reference is not None:
            cd_stoichiometry = cd_first_species_reference.get("stoichiometry")
            if cd_stoichiometry is not None:
                model_element.stoichiometry = float(cd_stoichiometry)
    else:
        model_element.stoichiometry = sum(
            float(cd_species_reference.get("stoichiometry") or 1)
            if cd_species_reference is not None
            else 1.0
            for cd_species_reference in cd_species_reference_group
        )
    return model_element


def make_modifier(
    reading_context: "CellDesignerReadingContext",
    model_element_cls: typing.Any,
    source_model_element: typing.Any,
    id_: str,
    metaid: str | None,
) -> typing.Any:
    """Create a modifier model builder.

    Args:
        reading_context: The reading context.
        model_element_cls: The modifier model element class to instantiate.
        source_model_element: The species model element referred to by the modifier.
        id_: The id of the modifier.
        metaid: The SBML ``metaid`` of the modifier reference, or ``None``.

    Returns:
        A modifier model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    model_element.referred_element = source_model_element
    model_element.id_ = id_
    model_element.metaid = metaid
    return model_element


def make_logic_gate(
    reading_context: "CellDesignerReadingContext", model_element_cls: typing.Any
) -> typing.Any:
    """Create a boolean logic gate model builder.

    Args:
        reading_context: The reading context.
        model_element_cls: The logic gate model element class to instantiate.

    Returns:
        A logic gate model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    return model_element


def make_logic_gate_input(
    reading_context: "CellDesignerReadingContext", input_model_element: typing.Any
) -> typing.Any:
    """Create a logic gate input model builder.

    Args:
        reading_context: The reading context.
        input_model_element: The species model element feeding the gate.

    Returns:
        A logic gate input model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(BooleanLogicGateInput)
    model_element.referred_element = input_model_element
    return model_element


def make_modulation(
    reading_context: "CellDesignerReadingContext",
    cd_reaction: typing.Any,
    model_element_cls: typing.Any,
    source_model_element: typing.Any,
    target_model_element: typing.Any,
) -> typing.Any:
    """Create a modulation model builder.

    CellDesigner encodes modulations as fake SBML reactions.

    Args:
        reading_context: The reading context.
        cd_reaction: The CellDesigner reaction XML element encoding the modulation.
        model_element_cls: The modulation model element class to instantiate.
        source_model_element: The source (modulator) model element.
        target_model_element: The target (modulated) model element.

    Returns:
        A modulation model builder, or ``None`` if no model is being built.
    """
    if reading_context.model is None:
        return None
    model_element = new_builder_object(model_element_cls)
    model_element.id_ = cd_reaction.get("id")
    model_element.source = source_model_element
    model_element.target = target_model_element
    return model_element
