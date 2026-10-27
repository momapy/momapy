"""Model classes for SBGN Process Description (PD) maps."""

import dataclasses
import typing

from momapy.sbgn.elements import (
    SBGNAuxiliaryUnit,
    SBGNModelElement,
    SBGNRole,
)
from momapy.sbgn.model import SBGNModel


@dataclasses.dataclass(frozen=True, kw_only=True)
class StateVariable(SBGNAuxiliaryUnit):
    """State variable."""

    variable: str | None = dataclasses.field(
        default=None, metadata={"description": "The variable of the state variable"}
    )
    value: str | None = dataclasses.field(
        default=None, metadata={"description": "The value of the state variable"}
    )
    order: int | None = dataclasses.field(
        default=None,
        metadata={
            "description": "The order of the state variable. This is used to distinguish between two or more state variables with undefined variable (i.e., set to `None`)"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnitOfInformation(SBGNAuxiliaryUnit):
    """Unit of information."""

    value: str = dataclasses.field(
        metadata={"description": "The value of the unit of information"},
    )
    prefix: str | None = dataclasses.field(
        default=None,
        metadata={"description": "The prefix of the unit of information"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Subunit(SBGNAuxiliaryUnit):
    """Abstract base class for subunits."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the subunit"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnspecifiedEntitySubunit(Subunit):
    """Unspecified entity subunit."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class MacromoleculeSubunit(Subunit):
    """Macromolecule subunit."""

    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the macromolecule subunit"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={
            "description": "The units of information of the macromolecule subunit"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class NucleicAcidFeatureSubunit(Subunit):
    """Nucleic acid feature subunit."""

    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={
            "description": "The state variables of the nucleic acid feature subunit"
        },
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={
            "description": "The units of information of the nucleic acid feature subunit"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleChemicalSubunit(Subunit):
    """Simple chemical subunit."""

    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the simple chemical subunit"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={
            "description": "The units of information of the simple chemical subunit"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexSubunit(Subunit):
    """Complex subunit."""

    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the complex subunit"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the complex subunit"},
    )
    subunits: frozenset[Subunit] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The subunits of the complex subunit"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class MultimerSubunit(ComplexSubunit):
    """Abstract base class for multimer subunits."""

    cardinality: int | None = dataclasses.field(
        default=None,
        metadata={"description": "The cardinality of the multimer subunit"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class MacromoleculeMultimerSubunit(MultimerSubunit):
    """Macromolecule multimer subunit."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NucleicAcidFeatureMultimerSubunit(MultimerSubunit):
    """Nucleic acid feature multimer subunit."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleChemicalMultimerSubunit(MultimerSubunit):
    """Simple chemical multimer subunit."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexMultimerSubunit(MultimerSubunit):
    """Complex multimer subunit."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Compartment(SBGNModelElement):
    """Compartment."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the compartment"}
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the compartment"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class EntityPool(SBGNModelElement):
    """Abstract base class for entity pools."""

    compartment: Compartment | None = dataclasses.field(
        default=None,
        metadata={
            "description": "The compartment of the entity pool",
            "reference": True,
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class PerturbingAgent(EntityPool):
    """Perturbing agent."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the perturbing agent"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnspecifiedEntity(EntityPool):
    """Unspecified entity."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the unspecified entity"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Macromolecule(EntityPool):
    """Macromolecule."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the macromolecule"}
    )
    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the macromolecule"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the macromolecule"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class NucleicAcidFeature(EntityPool):
    """Nucleic acid feature."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the nucleic acid feature"}
    )
    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the nucleic acid feature"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={
            "description": "The units of information of the nucleic acid feature"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleChemical(EntityPool):
    """Simple chemical."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the simple chemical"}
    )
    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the simple chemical"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the simple chemical"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Complex(EntityPool):
    """Complex."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the complex"}
    )
    state_variables: frozenset[StateVariable] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The state variables of the complex"},
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the complex"},
    )
    subunits: frozenset[Subunit] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The subunits of the complex"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Multimer(Complex):
    """Abstract base class for multimers."""

    cardinality: int | None = dataclasses.field(
        default=None, metadata={"description": "The cardinality of the multimer"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class MacromoleculeMultimer(Multimer):
    """Macromolecule multimer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NucleicAcidFeatureMultimer(Multimer):
    """Nucleic acid feature multimer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleChemicalMultimer(Multimer):
    """Simple chemical multimer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexMultimer(Multimer):
    """Complex multimer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class FluxRole(SBGNRole):
    """Abstract base class for flux roles."""

    referred_element: EntityPool = dataclasses.field(
        metadata={"description": "The entity pool of the flux role"}
    )
    stoichiometry: float | None = dataclasses.field(
        default=None, metadata={"description": "The stoichiometry of the flux role"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Reactant(FluxRole):
    """Reactant."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Product(FluxRole):
    """Product."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogicalOperatorInput(SBGNRole):
    """Logical operator input."""

    referred_element: typing.Union[
        EntityPool,
        typing.ForwardRef("LogicalOperator", module=__name__),
    ] = dataclasses.field(
        metadata={"description": "The element of the logical operator input"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class EquivalenceOperatorInput(SBGNRole):
    """Equivalence operator input."""

    referred_element: EntityPool = dataclasses.field(
        metadata={"description": "The element of the equivalence operator input"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class EquivalenceOperatorOutput(SBGNRole):
    """Equivalence operator output."""

    referred_element: EntityPool = dataclasses.field(
        metadata={"description": "The element of the equivalence operator output"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Process(SBGNModelElement):
    """Abstract base class for processes."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class StoichiometricProcess(Process):
    """Abstract base class for stoichiometric processes.

    SBGN PD's empty-set glyph (used as a source-and-sink for unspecified
    external flux) is *not* represented as a member of ``reactants`` or
    ``products``. Instead, it is encoded as the boolean flags
    ``has_external_source`` (an empty-set on the reactant side) and
    ``has_external_sink`` (an empty-set on the product side).
    """

    reactants: frozenset[Reactant] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The reactants of the stoichiometric process"},
    )
    products: frozenset[Product] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The products of the stoichiometric process"},
    )
    reversible: bool = dataclasses.field(
        default=False,
        metadata={
            "description": "Whether the stoichiometric process is reversible or not"
        },
    )
    has_external_source: bool = dataclasses.field(
        default=False,
        metadata={
            "description": (
                "Whether the process has an unspecified external source "
                "(an empty-set / source-and-sink reactant in SBGN PD)."
            )
        },
    )
    has_external_sink: bool = dataclasses.field(
        default=False,
        metadata={
            "description": (
                "Whether the process has an unspecified external sink "
                "(an empty-set / source-and-sink product in SBGN PD)."
            )
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class GenericProcess(StoichiometricProcess):
    """Generic process."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UncertainProcess(StoichiometricProcess):
    """Uncertain process."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Association(GenericProcess):
    """Association."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Dissociation(GenericProcess):
    """Dissociation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class OmittedProcess(GenericProcess):
    """Omitted process."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Phenotype(Process):
    """Phenotype."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the phenotype"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogicalOperator(SBGNModelElement):
    """Abstract base class for logical operators."""

    inputs: frozenset[LogicalOperatorInput] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The inputs of the logical operator"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class OrOperator(LogicalOperator):
    """OR operator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class AndOperator(LogicalOperator):
    """AND operator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NotOperator(LogicalOperator):
    """NOT operator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class EquivalenceOperator(SBGNModelElement):
    """Equivalence operator."""

    inputs: frozenset[EquivalenceOperatorInput] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The inputs of the equivalence operator"},
    )
    output: EquivalenceOperatorOutput | None = dataclasses.field(
        default=None, metadata={"description": "The output of the equivalence operator"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Modulation(SBGNModelElement):
    """Modulation."""

    source: EntityPool | LogicalOperator = dataclasses.field(
        metadata={"description": "The source of the modulation", "reference": True}
    )
    target: Process = dataclasses.field(
        metadata={"description": "The target of the modulation", "reference": True}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Inhibition(Modulation):
    """Inhibition."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Stimulation(Modulation):
    """Stimulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Catalysis(Stimulation):
    """Catalysis."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NecessaryStimulation(Stimulation):
    """Necessary stimulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class TagReference(SBGNRole):
    """Tag reference."""

    referred_element: EntityPool | Compartment = dataclasses.field(
        metadata={"description": "The element of the tag reference"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Tag(SBGNModelElement):
    """Tag."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the tag"}
    )
    referred_element: TagReference | None = dataclasses.field(
        default=None,
        metadata={"description": "The element referred to by the tag"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class TerminalReference(SBGNRole):
    """Terminal reference."""

    referred_element: EntityPool | Compartment = dataclasses.field(
        metadata={"description": "The element of the terminal reference"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Terminal(SBGNAuxiliaryUnit):
    """Terminal."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the terminal"}
    )
    referred_element: TerminalReference | None = dataclasses.field(
        default=None,
        metadata={"description": "The element referred to by the terminal"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Submap(SBGNModelElement):
    """Submap."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the submap"}
    )
    terminals: frozenset[Terminal] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The terminals of the submap"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNPDModel(SBGNModel):
    """SBGN PD model."""

    entity_pools: frozenset[EntityPool] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The entity pools of the SBGN-PD model"},
    )
    processes: frozenset[Process] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The processes of the SBGN-PD model"},
    )
    compartments: frozenset[Compartment] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The compartments of the SBGN-PD model"},
    )
    modulations: frozenset[Modulation] = dataclasses.field(
        metadata={"description": "The modulations of the SBGN-PD model"},
        default_factory=frozenset,
    )
    logical_operators: frozenset[LogicalOperator] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The logical operators of the SBGN-PD model"},
    )
    equivalence_operators: frozenset[EquivalenceOperator] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The equivalence operators of the SBGN-PD model"},
    )
    submaps: frozenset[Submap] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The submaps of the SBGN-PD model"},
    )
    tags: frozenset[Tag] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The tags of the SBGN-PD model"},
    )

    def is_ovav(self) -> bool:
        """Check if the model respects the Once a Variable Always a Variable (OVAV) rule.

        Returns:
            True if the SBGN-PD model respects the OVAV rule, False otherwise.
        """
        subunit_cls_entity_pool_cls_mapping = {
            MacromoleculeSubunit: Macromolecule,
            NucleicAcidFeatureSubunit: NucleicAcidFeature,
            ComplexSubunit: Complex,
            SimpleChemicalSubunit: SimpleChemical,
            MacromoleculeMultimerSubunit: MacromoleculeMultimer,
            NucleicAcidFeatureMultimerSubunit: NucleicAcidFeatureMultimer,
            ComplexMultimerSubunit: ComplexMultimer,
            SimpleChemicalMultimerSubunit: SimpleChemicalMultimer,
        }

        def _check_entities(
            entities: typing.Iterable[typing.Any],
            entity_variables_mapping: dict[typing.Any, set[typing.Any]] | None = None,
        ) -> bool:
            if entity_variables_mapping is None:
                entity_variables_mapping = {}
            for entity in entities:
                if hasattr(entity, "state_variables"):
                    variables = set([sv.variable for sv in entity.state_variables])
                    attributes = []
                    for field in dataclasses.fields(entity):
                        if field.name != "state_variables":
                            attributes.append(field.name)
                    args = {attr: getattr(entity, attr) for attr in attributes}
                    if isinstance(entity, Subunit):
                        cls = subunit_cls_entity_pool_cls_mapping[type(entity)]
                    else:
                        cls = type(entity)
                    entity_no_svs = cls(**args)
                    if entity_no_svs not in entity_variables_mapping:
                        entity_variables_mapping[entity_no_svs] = variables
                    else:
                        if entity_variables_mapping[entity_no_svs] != variables:
                            return False
                if hasattr(entity, "subunits"):
                    is_ovav = _check_entities(entity.subunits, entity_variables_mapping)
                    if not is_ovav:
                        return False
            return True

        return _check_entities(self.entity_pools)

    def is_submodel(self, other: "SBGNPDModel") -> bool:
        """Check if this model is a submodel of another model.

        Args:
            other: Another SBGN-PD model to compare against.

        Returns:
            True if this model is a submodel of `other`, False otherwise.
        """
        return (
            self.entity_pools.issubset(other.entity_pools)
            and self.processes.issubset(other.processes)
            and self.compartments.issubset(other.compartments)
            and self.modulations.issubset(other.modulations)
            and self.logical_operators.issubset(other.logical_operators)
            and self.equivalence_operators.issubset(other.equivalence_operators)
            and self.submaps.issubset(other.submaps)
            and self.tags.issubset(other.tags)
        )
