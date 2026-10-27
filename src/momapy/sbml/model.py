"""Concrete SBML model classes.

This module provides dataclasses representing SBML model elements including
compartments, species, reactions, and annotations using BioModels qualifiers.

Examples:
    ```python
    from momapy.sbml.model import Compartment, Species, SBMLModel
    compartment = Compartment(name="cytosol")
    species = Species(name="glucose", compartment=compartment)
    model = SBMLModel(
        name="glycolysis",
        compartments=frozenset({compartment}),
        species=frozenset({species}),
    )
    ```
"""

import dataclasses
import enum
import typing

from momapy.core.model import Model
from momapy.sbml.elements import SBMLModelElement


class BiomodelQualifier(enum.Enum):
    """BioModels.net qualifiers."""

    pass


class BQModel(BiomodelQualifier):
    """BioModels.net model qualifiers."""

    HAS_INSTANCE = "hasInstance"
    IS = "is"
    IS_DERIVED_FROM = "isDerivedFrom"
    IS_DESCRIBED_BY = "isDescribedBy"
    IS_INSTANCE_OF = "isInstanceOf"


class BQBiol(BiomodelQualifier):
    """BioModels.net biology qualifiers."""

    ENCODES = "encodes"
    HAS_PART = "hasPart"
    HAS_PROPERTY = "hasProperty"
    HAS_VERSION = "hasVersion"
    IS = "is"
    IS_DESCRIBED_BY = "isDescribedBy"
    IS_ENCODED_BY = "isEncodedBy"
    IS_HOMOLOG_TO = "isHomologTo"
    IS_PART_OF = "isPartOf"
    IS_PROPERTY_OF = "isPropertyOf"
    IS_VERSION_OF = "isVersionOf"
    OCCURS_IN = "occursIn"
    HAS_TAXON = "hasTaxon"


@dataclasses.dataclass(frozen=True, kw_only=True)
class RDFAnnotation:
    """RDF annotation.

    RDF annotations are metadata attached to model elements, not model
    entities themselves, and are therefore plain frozen dataclasses rather
    than ``ModelElement`` subclasses.
    """

    qualifier: BiomodelQualifier = dataclasses.field(
        metadata={"description": "The BioModels qualifier describing the relationship."}
    )
    resources: frozenset[str] = dataclasses.field(default_factory=frozenset)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Compartment(SBMLModelElement):
    """Compartment."""

    outside: typing.Optional[
        typing.ForwardRef("Compartment", module="momapy.sbml.model")
    ] = dataclasses.field(
        default=None,
        metadata={
            "description": "Optional outer compartment for hierarchical nesting.",
            "reference": True,
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Species(SBMLModelElement):
    """Species."""

    compartment: Compartment | None = dataclasses.field(
        default=None,
        metadata={
            "description": "The compartment containing this species.",
            "reference": True,
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleSpeciesReference(SBMLModelElement):
    """Abstract base class for simple species references."""

    referred_element: Species = dataclasses.field(
        metadata={"description": "The species being referenced.", "reference": True}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModifierSpeciesReference(SimpleSpeciesReference):
    """Modifier species reference."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SpeciesReference(SimpleSpeciesReference):
    """Species reference."""

    stoichiometry: float | None = dataclasses.field(
        default=None,
        metadata={"description": "Optional stoichiometric coefficient."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Reaction(SBMLModelElement):
    """Reaction."""

    reversible: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether the reaction can proceed in both directions."
        },
    )
    compartment: Compartment | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Optional compartment where the reaction occurs.",
            "reference": True,
        },
    )
    reactants: frozenset[SpeciesReference] = dataclasses.field(
        default_factory=frozenset
    )
    products: frozenset[SpeciesReference] = dataclasses.field(default_factory=frozenset)
    modifiers: frozenset[ModifierSpeciesReference] = dataclasses.field(
        default_factory=frozenset
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBMLModel(Model):
    """SBML model."""

    name: str | None = dataclasses.field(
        default=None,
        metadata={"description": "Human-readable name of the model."},
    )
    sbo_term: str | None = dataclasses.field(
        default=None,
        metadata={
            "description": "Optional SBO term identifier for semantic annotation."
        },
    )
    metaid: str | None = dataclasses.field(
        default=None,
        compare=False,
        hash=False,
        metadata={"description": "Optional metadata identifier for RDF annotations."},
    )
    compartments: frozenset[Compartment] = dataclasses.field(default_factory=frozenset)
    species: frozenset[Species] = dataclasses.field(default_factory=frozenset)
    reactions: frozenset[Reaction] = dataclasses.field(default_factory=frozenset)

    def is_submodel(self, other: "SBMLModel") -> bool:
        """Check if this model is a submodel of another model.

        Args:
            other: Another SBML model to compare against.

        Returns:
            True if this model is a submodel of `other`, False otherwise.
        """
        return (
            self.compartments.issubset(other.compartments)
            and self.species.issubset(other.species)
            and self.reactions.issubset(other.reactions)
        )
