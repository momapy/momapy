"""Model classes for SBGN Activity Flow (AF) maps."""

import dataclasses
import typing

from momapy.sbgn.elements import (
    SBGNAuxiliaryUnit,
    SBGNModelElement,
    SBGNRole,
)
from momapy.sbgn.model import SBGNModel


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnitOfInformation(SBGNAuxiliaryUnit):
    """Abstract base class for units of information."""

    label: str | None = dataclasses.field(
        default=None,
        metadata={"description": "The label of the unit of information."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Compartment(SBGNModelElement):
    """Compartment."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the compartment."}
    )
    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The units of information of the compartment."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class MacromoleculeUnitOfInformation(UnitOfInformation):
    """Macromolecule unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NucleicAcidFeatureUnitOfInformation(UnitOfInformation):
    """Nucleic acid feature unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ComplexUnitOfInformation(UnitOfInformation):
    """Complex unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleChemicalUnitOfInformation(UnitOfInformation):
    """Simple chemical unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnspecifiedEntityUnitOfInformation(UnitOfInformation):
    """Unspecified entity unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class PerturbationUnitOfInformation(UnitOfInformation):
    """Perturbation unit of information."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Activity(SBGNModelElement):
    """Abstract base class for activities."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the activity."}
    )
    compartment: Compartment | None = dataclasses.field(
        default=None,
        metadata={
            "description": "The compartment containing this activity.",
            "reference": True,
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class BiologicalActivity(Activity):
    """Biological activity."""

    units_of_information: frozenset[UnitOfInformation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "Units of information for the activity."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Phenotype(Activity):
    """Phenotype."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogicalOperatorInput(SBGNRole):
    """Logical operator input."""

    referred_element: typing.Union[
        BiologicalActivity,
        typing.ForwardRef("LogicalOperator", module=__name__),
    ] = dataclasses.field(
        metadata={
            "description": "The biological activity or logical operator providing the input."
        }
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class LogicalOperator(SBGNModelElement):
    """Abstract base class for logical operators."""

    inputs: frozenset[LogicalOperatorInput] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "Input connections to the logical operator."},
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
class DelayOperator(LogicalOperator):
    """Delay operator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Influence(SBGNModelElement):
    """Abstract base class for influences."""

    source: BiologicalActivity | LogicalOperator = dataclasses.field(
        metadata={
            "description": "The source activity or logical operator.",
            "reference": True,
        }
    )
    target: Activity = dataclasses.field(
        metadata={
            "description": "The target activity being influenced.",
            "reference": True,
        }
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownInfluence(Influence):
    """Unknown influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class PositiveInfluence(Influence):
    """Positive influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NegativeInfluence(Influence):
    """Negative influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NecessaryStimulation(Influence):
    """Necessary stimulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class TerminalReference(SBGNRole):
    """Terminal reference."""

    referred_element: Activity | Compartment = dataclasses.field(
        metadata={"description": "The activity or compartment being referenced."}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class TagReference(SBGNRole):
    """Tag reference."""

    referred_element: Activity | Compartment = dataclasses.field(
        metadata={"description": "The activity or compartment being referenced."}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Terminal(SBGNAuxiliaryUnit):
    """Terminal."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the terminal."}
    )
    referred_element: TerminalReference | None = dataclasses.field(
        default=None,
        metadata={"description": "The element referred to by the terminal."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Tag(SBGNModelElement):
    """Tag."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the tag."}
    )
    referred_element: TagReference | None = dataclasses.field(
        default=None,
        metadata={"description": "The element referred to by the tag."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Submap(SBGNModelElement):
    """Submap."""

    label: str | None = dataclasses.field(
        default=None, metadata={"description": "The label of the submap."}
    )
    terminals: frozenset[Terminal] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The terminals of the submap."},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBGNAFModel(SBGNModel):
    """SBGN AF model."""

    activities: frozenset[Activity] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The activities of the SBGN-AF model."},
    )
    compartments: frozenset[Compartment] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The compartments of the SBGN-AF model."},
    )
    influences: frozenset[Influence] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The influences of the SBGN-AF model."},
    )
    logical_operators: frozenset[LogicalOperator] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The logical operators of the SBGN-AF model."},
    )
    submaps: frozenset[Submap] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The submaps of the SBGN-AF model."},
    )
    tags: frozenset[Tag] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The tags of the SBGN-AF model."},
    )

    def is_submodel(self, other: "SBGNAFModel") -> bool:
        """Check if this model is a submodel of another model.

        Args:
            other: Another SBGN-AF model to compare against.

        Returns:
            True if this model is a submodel of `other`, False otherwise.
        """
        return (
            self.activities.issubset(other.activities)
            and self.compartments.issubset(other.compartments)
            and self.influences.issubset(other.influences)
            and self.logical_operators.issubset(other.logical_operators)
            and self.submaps.issubset(other.submaps)
            and self.tags.issubset(other.tags)
        )
