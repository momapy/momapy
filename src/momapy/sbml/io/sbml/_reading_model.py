"""SBML model-building functions.

Each ``make_*`` element builder takes a ``reading_context`` as its first
argument, returns ``None`` early when ``reading_context.model`` is ``None``,
and returns a model element builder (the caller freezes and registers it).
Mirrors the SBGN-ML / CellDesigner ``_reading_model`` modules.
"""

import typing

import lxml.etree

from momapy.builder import new_builder_object
from momapy.builder import object_from_builder
from momapy.sbml.model import Compartment
from momapy.sbml.model import ModifierSpeciesReference
from momapy.sbml.model import RDFAnnotation
from momapy.sbml.model import Reaction
from momapy.sbml.model import Species
from momapy.sbml.model import SpeciesReference
from momapy.sbml.io.sbml._reading_parsing import _RDF_NAMESPACE
from momapy.sbml.io.sbml._reading_parsing import get_bags
from momapy.sbml.io.sbml._reading_parsing import get_description
from momapy.sbml.io.sbml._reading_parsing import get_list_items
from momapy.sbml.io.sbml._reading_parsing import get_notes
from momapy.sbml.io.sbml._reading_parsing import get_prefix_and_name
from momapy.sbml.io.sbml._reading_parsing import get_rdf
from momapy.sbml.io.sbml._qualifiers import (
    QUALIFIER_ATTRIBUTE_TO_QUALIFIER_MEMBER,
)

if typing.TYPE_CHECKING:
    from momapy.sbml.io.sbml._reading_context import SBMLReadingContext


def make_annotations(rdf: typing.Any) -> list[RDFAnnotation]:
    """Build RDF annotations from an ``rdf:RDF`` element.

    Shared across SBML, CellDesigner and SBGN-ML readers.

    Args:
        rdf: The ``rdf:RDF`` lxml.objectify element.

    Returns:
        A list of ``momapy.sbml.model.RDFAnnotation`` objects.
    """
    annotations = []
    description = get_description(rdf)
    if description is not None:
        for bq_element in description.iterchildren():
            key = get_prefix_and_name(bq_element.tag)
            qualifier = QUALIFIER_ATTRIBUTE_TO_QUALIFIER_MEMBER.get(key)
            if qualifier is not None:
                bags = get_bags(bq_element)
                for bag in bags:
                    lis = get_list_items(bag)
                    resources = [li.get(f"{{{_RDF_NAMESPACE}}}resource") for li in lis]
                    annotation = RDFAnnotation(
                        qualifier=qualifier,
                        resources=frozenset(resources),
                    )
                    annotations.append(annotation)
    return annotations


def make_notes(notes_element: typing.Any) -> list[str]:
    """Serialize the first XML child of a ``notes`` element.

    Shared across SBML, CellDesigner and SBGN-ML readers.

    Args:
        notes_element: The ``notes`` lxml.objectify element, or ``None``.

    Returns:
        A list containing the serialized first child, or an empty list.
    """
    if notes_element is None:
        return []
    first_child = next(notes_element.iterchildren(), None)
    if first_child is None:
        return []
    return [lxml.etree.tostring(first_child, encoding="unicode")]


def make_annotations_from_element(
    sbml_element: typing.Any,
) -> list[RDFAnnotation]:
    sbml_rdf = get_rdf(sbml_element)
    if sbml_rdf is not None:
        annotations = make_annotations(sbml_rdf)
    else:
        annotations = []
    return annotations


def make_notes_from_element(sbml_element: typing.Any) -> list[str]:
    sbml_notes = get_notes(sbml_element)
    return make_notes(sbml_notes)


def make_and_add_annotations_and_notes(
    reading_context: "SBMLReadingContext",
    sbml_element: typing.Any,
    model_element: typing.Any,
    source_id: str | None = None,
) -> None:
    """Add the annotations and notes of an SBML element to the context.

    Args:
        reading_context: The reading context.
        sbml_element: The source SBML lxml element.
        model_element: The momapy element the annotations/notes attach to.
        source_id: The source XML id, used to populate the per-source-id
            annotation/note mappings. Defaults to None.
    """
    if reading_context.with_annotations:
        annotations = make_annotations_from_element(sbml_element)
        if annotations:
            reading_context.element_to_annotations[model_element].update(annotations)
            if source_id is not None:
                reading_context.source_id_to_annotations[source_id].update(annotations)
    if reading_context.with_notes:
        notes = make_notes_from_element(sbml_element)
        if notes:
            reading_context.element_to_notes[model_element].update(notes)
            if source_id is not None:
                reading_context.source_id_to_notes[source_id].update(notes)


def make_compartment(
    reading_context: "SBMLReadingContext", sbml_compartment: typing.Any
) -> typing.Any:
    if reading_context.model is None:
        return None
    model_element = new_builder_object(Compartment)
    model_element.id_ = sbml_compartment.get("id")
    model_element.name = sbml_compartment.get("name")
    model_element.metaid = sbml_compartment.get("metaid")
    model_element.sbo_term = sbml_compartment.get("sboTerm")
    return model_element


def make_species(
    reading_context: "SBMLReadingContext", sbml_species: typing.Any
) -> typing.Any:
    if reading_context.model is None:
        return None
    model_element = new_builder_object(Species)
    model_element.name = sbml_species.get("name")
    model_element.id_ = sbml_species.get("id")
    model_element.metaid = sbml_species.get("metaid")
    model_element.sbo_term = sbml_species.get("sboTerm")
    sbml_compartment_id = sbml_species.get("compartment")
    if sbml_compartment_id is not None:
        model_element.compartment = reading_context.sbml_id_to_model_element[
            sbml_compartment_id
        ]
    return model_element


def make_reaction(
    reading_context: "SBMLReadingContext", sbml_reaction: typing.Any
) -> typing.Any:
    if reading_context.model is None:
        return None
    model_element = new_builder_object(Reaction)
    model_element.id_ = sbml_reaction.get("id")
    model_element.name = sbml_reaction.get("name")
    model_element.sbo_term = sbml_reaction.get("sboTerm")
    model_element.reversible = sbml_reaction.get("reversible") == "true"
    return model_element


def make_species_reference(
    reading_context: "SBMLReadingContext",
    sbml_species_reference: typing.Any,
    reaction_id: str,
) -> typing.Any:
    if reading_context.model is None:
        return None
    model_element = new_builder_object(SpeciesReference)
    sbml_species_id = sbml_species_reference.get("species")
    # metaid is optional in SBML; fall back to a composite id so id_ is
    # always a str (mirrors the CellDesigner reader).
    model_element.id_ = sbml_species_reference.get("metaid")
    if model_element.id_ is None:
        model_element.id_ = f"{reaction_id}_{sbml_species_id}"
    sbml_stoichiometry = sbml_species_reference.get("stoichiometry")
    if sbml_stoichiometry is not None:
        model_element.stoichiometry = float(sbml_stoichiometry)
    model_element.referred_element = reading_context.sbml_id_to_model_element[
        sbml_species_id
    ]
    model_element = object_from_builder(model_element)
    return model_element


def make_modifier_species_reference(
    reading_context: "SBMLReadingContext",
    sbml_modifier_species_reference: typing.Any,
    reaction_id: str,
) -> typing.Any:
    if reading_context.model is None:
        return None
    model_element = new_builder_object(ModifierSpeciesReference)
    sbml_species_id = sbml_modifier_species_reference.get("species")
    # metaid is optional in SBML; fall back to a composite id so id_ is
    # always a str (mirrors the CellDesigner reader).
    model_element.id_ = sbml_modifier_species_reference.get("metaid")
    if model_element.id_ is None:
        model_element.id_ = f"{reaction_id}_{sbml_species_id}"
    model_element.referred_element = reading_context.sbml_id_to_model_element[
        sbml_species_id
    ]
    model_element = object_from_builder(model_element)
    return model_element
