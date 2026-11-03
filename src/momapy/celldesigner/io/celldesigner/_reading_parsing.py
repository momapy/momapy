"""CellDesigner XML parsing utilities.

Pure XML traversal and data-extraction functions for CellDesigner documents.
No momapy object construction happens here: all functions work with lxml
objectify trees and return raw Python / geometry values.
"""

import collections
import typing

import lxml.objectify

from momapy.celldesigner.io.celldesigner._constants import (
    CD_NAMESPACE,
    LINK_ANCHOR_POSITION_TO_ANCHOR_NAME,
    TEXT_TO_CHARACTER,
)
from momapy.sbml.io.sbml._reading_parsing import _RDF_NAMESPACE, get_prefix_and_name


def get_annotation(
    cd_element: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    return getattr(cd_element, "annotation", None)


def get_extension(
    cd_element: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_annotation = get_annotation(cd_element)
    if cd_annotation is None:
        return None
    cd_extension = getattr(cd_element.annotation, f"{{{CD_NAMESPACE}}}extension", None)
    return cd_extension


def get_species(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    list_of_species = getattr(cd_model, "listOfSpecies", None)
    if list_of_species is None:
        return []
    return list(getattr(list_of_species, "species", []))


def get_reactions(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    list_of_reactions = getattr(cd_model, "listOfReactions", None)
    if list_of_reactions is None:
        return []
    return list(getattr(list_of_reactions, "reaction", []))


def get_species_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    # only the non-included ones
    extension = get_extension(cd_model)
    species_aliases = list(getattr(extension.listOfSpeciesAliases, "speciesAlias", []))
    species_aliases = [
        species_alias
        for species_alias in species_aliases
        if species_alias.get("complexSpeciesAlias") is None
    ]
    return species_aliases


def get_included_species_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    species_aliases = list(getattr(extension.listOfSpeciesAliases, "speciesAlias", []))
    species_aliases = [
        species_alias
        for species_alias in species_aliases
        if species_alias.get("complexSpeciesAlias") is not None
    ]
    return species_aliases


def get_complex_species_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    # only the non-included ones
    extension = get_extension(cd_model)
    complex_species_aliases = list(
        getattr(
            extension.listOfComplexSpeciesAliases,
            "complexSpeciesAlias",
            [],
        )
    )
    complex_species_aliases = [
        complex_species_alias
        for complex_species_alias in complex_species_aliases
        if complex_species_alias.get("complexSpeciesAlias") is None
    ]
    return complex_species_aliases


def get_included_complex_species_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    complex_species_aliases = list(
        getattr(
            extension.listOfComplexSpeciesAliases,
            "complexSpeciesAlias",
            [],
        )
    )
    complex_species_aliases = [
        complex_species_alias
        for complex_species_alias in complex_species_aliases
        if complex_species_alias.get("complexSpeciesAlias") is not None
    ]
    return complex_species_aliases


def get_compartments(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    return list(getattr(cd_model.listOfCompartments, "compartment", []))


def get_compartment_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    return list(getattr(extension.listOfCompartmentAliases, "compartmentAlias", []))


def get_protein_templates(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    return list(getattr(extension.listOfProteins, "protein", []))


def get_gene_templates(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    return list(getattr(extension.listOfGenes, "gene", []))


def get_rna_templates(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    return list(getattr(extension.listOfRNAs, "RNA", []))


def get_antisense_rna_templates(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    return list(getattr(extension.listOfAntisenseRNAs, "AntisenseRNA", []))


def get_species_templates(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    return (
        get_protein_templates(cd_model)
        + get_gene_templates(cd_model)
        + get_rna_templates(cd_model)
        + get_antisense_rna_templates(cd_model)
    )


def get_modification_residues(
    cd_species_template: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    list_of_modification_residues = getattr(
        cd_species_template, "listOfModificationResidues", None
    )
    if list_of_modification_residues is not None:
        modification_residues = list(
            getattr(list_of_modification_residues, "modificationResidue", [])
        )
    else:
        modification_residues = []
    return modification_residues


def get_regions(
    cd_species_template: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    list_of_regions = getattr(cd_species_template, "listOfRegions", None)
    if list_of_regions is not None:
        regions = list(getattr(list_of_regions, "region", []))
    else:
        regions = []
    return regions


def get_included_species(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_model)
    list_of_included_species = getattr(extension, "listOfIncludedSpecies", None)
    if list_of_included_species is None:
        return []
    return list(getattr(list_of_included_species, "species", []))


def get_reaction_type(cd_reaction: lxml.objectify.ObjectifiedElement) -> str:
    cd_extension = get_extension(cd_reaction)
    return cd_extension.reactionType.text


def get_gate_members(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    cd_extension = get_extension(cd_reaction)
    list_of_gate_member = getattr(cd_extension, "listOfGateMember", None)
    if list_of_gate_member is not None:
        gate_members = list(getattr(list_of_gate_member, "GateMember", []))
    else:
        gate_members = []
    return gate_members


def get_key_from_reaction(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> tuple[str, str | None]:
    cd_reaction_type = get_reaction_type(cd_reaction)
    if cd_reaction_type == "BOOLEAN_LOGIC_GATE":
        cd_gate_member = get_gate_members(cd_reaction)[0]
        cd_reaction_type = cd_gate_member.get("modificationType")
    return ("REACTION", cd_reaction_type)


_TEMPLATE_LOCALNAME_TO_TYPE = {
    "gene": "GENE",
    "RNA": "RNA",
    "AntisenseRNA": "ANTISENSE_RNA",
}


def get_key_from_species_template(
    cd_species_template: lxml.objectify.ObjectifiedElement,
) -> tuple[str, str | None]:
    template_type = cd_species_template.get("type")
    if template_type is None:
        _, localname = get_prefix_and_name(cd_species_template.tag)
        template_type = _TEMPLATE_LOCALNAME_TO_TYPE.get(localname)
    return (
        "TEMPLATE",
        template_type,
    )


def get_key_from_region(
    cd_region: lxml.objectify.ObjectifiedElement,
) -> tuple[str, str | None]:
    return (
        "REGION",
        cd_region.get("type"),
    )


def get_key_from_species(
    cd_species: lxml.objectify.ObjectifiedElement,
    cd_id_to_cd_element: dict[str, lxml.objectify.ObjectifiedElement],
) -> tuple[str, str | None]:
    cd_species_template = get_template_from_species(cd_species, cd_id_to_cd_element)
    if cd_species_template is None:
        key = get_class_from_species(cd_species).text
    else:
        key = cd_species_template.get("type")
        if key is None:
            _, localname = get_prefix_and_name(cd_species_template.tag)
            key = _TEMPLATE_LOCALNAME_TO_TYPE.get(localname)
    return ("SPECIES", key)


def get_key_from_reaction_modification(
    cd_reaction_modification: lxml.objectify.ObjectifiedElement,
) -> tuple[str, str | None]:
    if has_boolean_input_from_modification(cd_reaction_modification):
        cd_reaction_modification_type = cd_reaction_modification.get("modificationType")
    else:
        cd_reaction_modification_type = cd_reaction_modification.get("type")
    return ("MODIFIER", cd_reaction_modification_type)


def get_key_from_gate_member(
    cd_reaction_modification: lxml.objectify.ObjectifiedElement,
) -> tuple[str, str | None]:
    return ("GATE", cd_reaction_modification.get("type"))


def get_identity(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_extension = get_extension(cd_species)
    if cd_extension is not None:
        cd_identity = cd_extension.speciesIdentity
    else:
        cd_identity = cd_species.annotation.speciesIdentity
    return cd_identity


def get_class_from_species(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_identity = get_identity(cd_species)
    if cd_identity is None:
        return None
    cd_class = getattr(cd_identity, "class", None)
    return cd_class


def get_state(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_species_identity = get_identity(cd_species)
    if cd_species_identity is None:
        return None
    cd_species_state = getattr(cd_species_identity, "state", None)
    return cd_species_state


def get_activity(
    cd_species_alias: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    return getattr(cd_species_alias, "activity", None)


def get_homodimer(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_species_state = get_state(cd_species)
    if cd_species_state is None:
        return None
    return getattr(cd_species_state, "homodimer", None)


def get_hypothetical(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    cd_species_identity = get_identity(cd_species)
    if cd_species_identity is None:
        return None
    return getattr(cd_species_identity, "hypothetical", None)


def get_species_modifications(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    cd_species_state = get_state(cd_species)
    if cd_species_state is None:
        return []
    cd_list_of_modifications = getattr(cd_species_state, "listOfModifications", None)
    if cd_list_of_modifications is None:
        return []
    return list(getattr(cd_list_of_modifications, "modification", []))


def get_species_structural_state(
    cd_species: lxml.objectify.ObjectifiedElement,
) -> typing.Any:
    cd_species_state = get_state(cd_species)
    if cd_species_state is None:
        return None
    cd_list_of_structural_states = getattr(
        cd_species_state, "listOfStructuralStates", None
    )
    if cd_list_of_structural_states is None:
        return None
    cd_structural_states = list(cd_list_of_structural_states.structuralState)
    if len(cd_structural_states) > 1:
        raise ValueError(
            f"species '{cd_species.get('id')}' has several structural states"
        )
    return cd_structural_states[0]


def get_template_from_species(
    cd_species: lxml.objectify.ObjectifiedElement,
    cd_id_to_cd_element: dict[str, lxml.objectify.ObjectifiedElement],
) -> lxml.objectify.ObjectifiedElement | None:
    cd_species_identity = get_identity(cd_species)
    for cd_species_template_type in [
        "proteinReference",
        "rnaReference",
        "geneReference",
        "antisensernaReference",
    ]:
        cd_reference = getattr(cd_species_identity, cd_species_template_type, None)
        if cd_reference is not None:
            cd_species_template = cd_id_to_cd_element[cd_reference.text]
            return cd_species_template
    return None


def get_template_from_species_alias(
    cd_species_alias: lxml.objectify.ObjectifiedElement,
    cd_id_to_cd_element: dict[str, lxml.objectify.ObjectifiedElement],
) -> lxml.objectify.ObjectifiedElement | None:
    cd_species_id = cd_species_alias.get("species")
    cd_species = cd_id_to_cd_element[cd_species_id]
    return get_template_from_species(cd_species, cd_id_to_cd_element)


def get_bounds(
    cd_element: lxml.objectify.ObjectifiedElement,
) -> tuple[str | None, str | None, str | None, str | None]:
    cd_x = cd_element.bounds.get("x")
    cd_y = cd_element.bounds.get("y")
    cd_w = cd_element.bounds.get("w")
    cd_h = cd_element.bounds.get("h")
    return cd_x, cd_y, cd_w, cd_h


def get_anchor_name_for_frame(cd_element: lxml.objectify.ObjectifiedElement) -> str:
    if getattr(cd_element, "linkAnchor", None) is not None:
        cd_element_anchor = cd_element.linkAnchor.get("position")
        anchor_name = LINK_ANCHOR_POSITION_TO_ANCHOR_NAME.get(
            cd_element_anchor, "center"
        )
    else:
        anchor_name = "center"
    return anchor_name


def get_reactants(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    return list(getattr(cd_reaction.listOfReactants, "speciesReference", []))


def get_base_reactants(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_reaction)
    return list(getattr(extension.baseReactants, "baseReactant", []))


def get_reactant_links(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_reaction)
    list_of_reactant_links = getattr(extension, "listOfReactantLinks", None)
    if list_of_reactant_links is None:
        return []
    return list(getattr(list_of_reactant_links, "reactantLink", []))


def get_products(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    return list(getattr(cd_reaction.listOfProducts, "speciesReference", []))


def get_base_products(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_reaction)
    return list(getattr(extension.baseProducts, "baseProduct", []))


def get_product_links(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_reaction)
    list_of_product_links = getattr(extension, "listOfProductLinks", None)
    if list_of_product_links is None:
        return []
    return list(getattr(list_of_product_links, "productLink", []))


def get_edit_points_from_reaction(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    extension = get_extension(cd_reaction)
    return getattr(extension, "editPoints", None)


def get_edit_points_from_participant_link(
    cd_participant_link: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    return getattr(cd_participant_link, "editPoints", None)


def get_rectangle_index(cd_reaction: lxml.objectify.ObjectifiedElement) -> str | None:
    extension = get_extension(cd_reaction)
    return extension.connectScheme.get("rectangleIndex")


def get_t_shape_index(cd_reaction: lxml.objectify.ObjectifiedElement) -> str | None:
    cd_edit_points = get_edit_points_from_reaction(cd_reaction)
    return cd_edit_points.get("tShapeIndex")


def has_boolean_input_from_modification(
    cd_reaction_modification: lxml.objectify.ObjectifiedElement,
) -> bool:
    return cd_reaction_modification.get("type") in [
        "BOOLEAN_LOGIC_GATE_AND",
        "BOOLEAN_LOGIC_GATE_OR",
        "BOOLEAN_LOGIC_GATE_NOT",
        "BOOLEAN_LOGIC_GATE_UNKNOWN",
    ]


def has_boolean_input_from_reaction(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> bool:
    return get_reaction_type(cd_reaction) == "BOOLEAN_LOGIC_GATE"


def get_modifier_species_references(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    """Return the list of SBML modifierSpeciesReference elements.

    Args:
        cd_reaction: The SBML reaction XML element.

    Returns:
        A list of modifierSpeciesReference XML elements.
    """
    list_of_modifiers = getattr(cd_reaction, "listOfModifiers", None)
    if list_of_modifiers is None:
        return []
    return list(getattr(list_of_modifiers, "modifierSpeciesReference", []))


def get_reaction_modifications(
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> list[lxml.objectify.ObjectifiedElement]:
    extension = get_extension(cd_reaction)
    list_of_modification = getattr(extension, "listOfModification", None)
    if list_of_modification is None:
        return []
    modifications = list(getattr(list_of_modification, "modification", []))
    true_modifications = []
    cd_input_ids = set([])
    for modification in modifications:
        if has_boolean_input_from_modification(modification):
            true_modifications.append(modification)
            cd_input_ids.update(modification.get("modifiers").split(","))
    for modification in modifications:
        if (
            modification not in true_modifications
            and modification.get("modifiers") not in cd_input_ids
        ):
            true_modifications.append(modification)
    return true_modifications


def get_width(cd_model: lxml.objectify.ObjectifiedElement) -> str | None:
    extension = get_extension(cd_model)
    return extension.modelDisplay.get("sizeX")


def get_height(cd_model: lxml.objectify.ObjectifiedElement) -> str | None:
    extension = get_extension(cd_model)
    return extension.modelDisplay.get("sizeY")


def get_name(name: str | None) -> str | None:
    if name is None:
        return name
    for s, char in TEXT_TO_CHARACTER.items():
        name = name.replace(s, char)
    return name


def get_notes(
    cd_element: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    return getattr(cd_element, "notes", None)


def get_rdf_from_notes(
    cd_notes: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    rdfs = list(cd_notes.iter(f"{{{_RDF_NAMESPACE}}}RDF"))
    if rdfs:
        return rdfs[0]
    return None


def get_rdf(
    cd_element: lxml.objectify.ObjectifiedElement,
) -> lxml.objectify.ObjectifiedElement | None:
    annotation = get_annotation(cd_element)
    if annotation is None:
        return None
    return getattr(annotation, f"{{{_RDF_NAMESPACE}}}RDF", None)


def get_id_to_element_mapping(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> dict[str, lxml.objectify.ObjectifiedElement]:
    cd_id_to_cd_element = {}
    # compartments
    for cd_compartment in get_compartments(cd_model):
        cd_id_to_cd_element[cd_compartment.get("id")] = cd_compartment
    # compartment aliases
    for cd_compartment_alias in get_compartment_aliases(cd_model):
        cd_id_to_cd_element[cd_compartment_alias.get("id")] = cd_compartment_alias
    # species templates
    for cd_species_template in get_species_templates(cd_model):
        cd_id_to_cd_element[cd_species_template.get("id")] = cd_species_template
        for cd_modification_residue in get_modification_residues(cd_species_template):
            cd_modification_residue_id = (
                f"{cd_species_template.get('id')}_{cd_modification_residue.get('id')}"
            )
            cd_id_to_cd_element[cd_modification_residue_id] = cd_modification_residue
        for cd_region in get_regions(cd_species_template):
            cd_region_id = f"{cd_species_template.get('id')}_{cd_region.get('id')}"
            cd_id_to_cd_element[cd_region_id] = cd_region
    # species
    for cd_species in get_species(cd_model):
        cd_id_to_cd_element[cd_species.get("id")] = cd_species
    # included species
    for cd_included_species in get_included_species(cd_model):
        cd_id_to_cd_element[cd_included_species.get("id")] = cd_included_species
    # species aliases
    for cd_species_alias in get_species_aliases(cd_model):
        cd_id_to_cd_element[cd_species_alias.get("id")] = cd_species_alias
    # complex species aliases
    for cd_complex_species_alias in get_complex_species_aliases(cd_model):
        cd_id_to_cd_element[cd_complex_species_alias.get("id")] = (
            cd_complex_species_alias
        )
    # included species aliases
    for cd_species_alias in get_included_species_aliases(cd_model):
        cd_id_to_cd_element[cd_species_alias.get("id")] = cd_species_alias
    # included complex species aliases
    for cd_complex_species_alias in get_included_complex_species_aliases(cd_model):
        cd_id_to_cd_element[cd_complex_species_alias.get("id")] = (
            cd_complex_species_alias
        )
    return cd_id_to_cd_element


def get_complex_alias_to_included_ids_mapping(
    cd_model: lxml.objectify.ObjectifiedElement,
) -> dict[str, list[str]]:
    cd_complex_alias_id_to_cd_included_species_ids = collections.defaultdict(list)
    for cd_species_alias in get_included_species_aliases(cd_model):
        cd_complex_species_alias_id = cd_species_alias.get("complexSpeciesAlias")
        if cd_complex_species_alias_id is not None:
            cd_complex_alias_id_to_cd_included_species_ids[
                cd_complex_species_alias_id
            ].append(cd_species_alias.get("id"))

    for cd_species_alias in get_included_complex_species_aliases(cd_model):
        cd_complex_species_alias_id = cd_species_alias.get("complexSpeciesAlias")
        if cd_complex_species_alias_id is not None:
            cd_complex_alias_id_to_cd_included_species_ids[
                cd_complex_species_alias_id
            ].append(cd_species_alias.get("id"))
    return cd_complex_alias_id_to_cd_included_species_ids


def get_ordered_compartment_aliases(
    cd_model: lxml.objectify.ObjectifiedElement,
    cd_id_to_cd_element: dict[str, lxml.objectify.ObjectifiedElement],
) -> list[lxml.objectify.ObjectifiedElement]:
    cd_compartments = get_compartments(cd_model)
    cd_compartment_id_to_cd_outside_id = {}
    for cd_compartment in cd_compartments:
        cd_compartment_id = cd_compartment.get("id")
        cd_outside_id = cd_compartment.get("outside")
        cd_compartment_id_to_cd_outside_id[cd_compartment_id] = cd_outside_id
    ordered_cd_compartments = []
    while cd_compartment_id_to_cd_outside_id:
        for (
            cd_compartment_id,
            cd_outside_id,
        ) in cd_compartment_id_to_cd_outside_id.items():
            if cd_outside_id is None:
                ordered_cd_compartments.append(cd_compartment_id)
                to_delete = cd_compartment_id
                break
        del cd_compartment_id_to_cd_outside_id[to_delete]
        for (
            cd_compartment_id,
            cd_outside_id,
        ) in cd_compartment_id_to_cd_outside_id.items():
            if cd_outside_id == to_delete:
                cd_compartment_id_to_cd_outside_id[cd_compartment_id] = None
    cd_compartment_aliases = get_compartment_aliases(cd_model)
    ordered_cd_compartment_aliases = sorted(
        cd_compartment_aliases,
        key=lambda cd_compartment_alias: ordered_cd_compartments.index(
            cd_id_to_cd_element[cd_compartment_alias.get("compartment")].get("id")
        ),
    )
    return ordered_cd_compartment_aliases


def get_species_reference(
    cd_participant: lxml.objectify.ObjectifiedElement,
    cd_species_references: list[lxml.objectify.ObjectifiedElement],
) -> lxml.objectify.ObjectifiedElement | None:
    """Return the species reference of a participant entry.

    The participant entry is a base participant, a participant link or a
    modification. The species reference is matched by its
    ``celldesigner:alias``. When none matches, the first one with the same
    species is returned.

    Args:
        cd_participant: The base participant, participant link or
            modification element.
        cd_species_references: The speciesReference or
            modifierSpeciesReference elements of the reaction.

    Returns:
        The matching speciesReference element, or ``None``.
    """
    alias_id = cd_participant.get("alias") or cd_participant.get("aliases")
    for cd_species_reference in cd_species_references:
        cd_extension = get_extension(cd_species_reference)
        cd_alias = getattr(cd_extension, f"{{{CD_NAMESPACE}}}alias", None)
        if cd_alias is not None and cd_alias.text == alias_id:
            return cd_species_reference
    cd_species_id = (
        cd_participant.get("species")
        or cd_participant.get("reactant")
        or cd_participant.get("product")
        or cd_participant.get("modifiers")
    )
    for cd_species_reference in cd_species_references:
        if cd_species_reference.get("species") == cd_species_id:
            return cd_species_reference
    return None


def get_reactant_id(
    cd_base_reactant_or_link: lxml.objectify.ObjectifiedElement,
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> str:
    """Compute a deterministic ID for a reactant arc from XML data.

    Uses the metaid of the speciesReference matched by alias if available,
    otherwise falls back to ``f"{reaction_id}_{alias_id}"``.

    Args:
        cd_base_reactant_or_link: The base reactant or reactant link element.
        cd_reaction: The parent reaction element.

    Returns:
        A deterministic ID string.
    """
    cd_reactant = get_species_reference(
        cd_base_reactant_or_link, get_reactants(cd_reaction)
    )
    if cd_reactant is not None and cd_reactant.get("metaid") is not None:
        return cd_reactant.get("metaid")
    return f"{cd_reaction.get('id')}_{cd_base_reactant_or_link.get('alias')}"


def get_product_id(
    cd_base_product_or_link: lxml.objectify.ObjectifiedElement,
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> str:
    """Compute a deterministic ID for a product arc from XML data.

    Uses the metaid of the speciesReference matched by alias if available,
    otherwise falls back to ``f"{reaction_id}_{alias_id}"``.

    Args:
        cd_base_product_or_link: The base product or product link element.
        cd_reaction: The parent reaction element.

    Returns:
        A deterministic ID string.
    """
    cd_product = get_species_reference(
        cd_base_product_or_link, get_products(cd_reaction)
    )
    if cd_product is not None and cd_product.get("metaid") is not None:
        return cd_product.get("metaid")
    return f"{cd_reaction.get('id')}_{cd_base_product_or_link.get('alias')}"


def get_modifier_metaid(
    cd_reaction_modification: lxml.objectify.ObjectifiedElement,
    cd_reaction: lxml.objectify.ObjectifiedElement,
) -> str | None:
    """Resolve the SBML modifierSpeciesReference metaid for a modifier.

    The modifierSpeciesReference is the one matched by alias, else the first
    one with the same species.

    Args:
        cd_reaction_modification: The modification element.
        cd_reaction: The parent reaction element.

    Returns:
        The metaid string, or None if not found.
    """
    cd_modifier_species_reference = get_species_reference(
        cd_reaction_modification, get_modifier_species_references(cd_reaction)
    )
    if cd_modifier_species_reference is None:
        return None
    return cd_modifier_species_reference.get("metaid")
