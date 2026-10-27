"""Model classes for CellDesigner maps.

This module provides classes for representing the semantic model of a
CellDesigner pathway, including species, reactions, modifications, and
modulations.

Layout-model mapping catalogue
------------------------------

This section lists, for each model-element category in CellDesigner,
the shape of the corresponding key in
[LayoutModelMapping][momapy.core.LayoutModelMapping]. See
[LayoutModelMapping][momapy.core.LayoutModelMapping] for the general concepts
(singleton keys, frozenset keys, representatives).

Singleton keys (one layout element represents the model element):

| Model element | Layout element used as the key |
|---|---|
| [Compartment][momapy.celldesigner.Compartment] | The compartment alias layout (e.g. [OvalCompartmentLayout][momapy.celldesigner.OvalCompartmentLayout], [RectangleCompartmentLayout][momapy.celldesigner.RectangleCompartmentLayout], [CornerCompartmentLayout][momapy.celldesigner.CornerCompartmentLayout], [LineCompartmentLayout][momapy.celldesigner.LineCompartmentLayout]) |
| [Species][momapy.celldesigner.Species] and subclasses (e.g. [GenericProtein][momapy.celldesigner.GenericProtein], [Receptor][momapy.celldesigner.Receptor], [IonChannel][momapy.celldesigner.IonChannel], [Gene][momapy.celldesigner.Gene], [RNA][momapy.celldesigner.RNA], [Complex][momapy.celldesigner.Complex], [SimpleMolecule][momapy.celldesigner.SimpleMolecule], [Ion][momapy.celldesigner.Ion], [Drug][momapy.celldesigner.Drug], [Phenotype][momapy.celldesigner.Phenotype]) | The species alias layout (e.g. [GenericProteinLayout][momapy.celldesigner.GenericProteinLayout], [GeneLayout][momapy.celldesigner.GeneLayout]). Active species use the `*ActiveLayout` variant (e.g. [GenericProteinActiveLayout][momapy.celldesigner.GenericProteinActiveLayout]) |
| [Modification][momapy.celldesigner.Modification] | [ModificationLayout][momapy.celldesigner.ModificationLayout] |
| [StructuralState][momapy.celldesigner.StructuralState] | [StructuralStateLayout][momapy.celldesigner.StructuralStateLayout] |
| [Reactant][momapy.celldesigner.Reactant] | [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout] |
| [Product][momapy.celldesigner.Product] | [ProductionLayout][momapy.celldesigner.ProductionLayout] |
| Modifiers (e.g. [Catalyzer][momapy.celldesigner.Catalyzer], [Trigger][momapy.celldesigner.Trigger], [Inhibitor][momapy.celldesigner.Inhibitor]) | The modifier arc layout (e.g. [CatalysisLayout][momapy.celldesigner.CatalysisLayout], [TriggeringLayout][momapy.celldesigner.TriggeringLayout], [InhibitionLayout][momapy.celldesigner.InhibitionLayout]). One key per drawn arc: a modifier drawn from several aliases has several keys |
| [BooleanLogicGateInput][momapy.celldesigner.BooleanLogicGateInput] | [LogicArcLayout][momapy.celldesigner.LogicArcLayout] |

When a reaction uses the same species through several aliases, there is one
[Reactant][momapy.celldesigner.Reactant] (or
[Product][momapy.celldesigner.Product]) whose `stoichiometry` is the number of
uses, and each drawn [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout]
(or [ProductionLayout][momapy.celldesigner.ProductionLayout]) is a separate
singleton key for it.

Frozenset keys (a cluster of layout elements jointly represents the
model element; the **representative** is the layout that stands for the cluster
on its own and must be passed as ``representative=`` when calling
[add_mapping][momapy.core.LayoutModelMappingBuilder.add_mapping]):

| Model element | Members of the frozenset key | Representative |
|---|---|---|
| [Reaction][momapy.celldesigner.Reaction] and subclasses (e.g. [StateTransition][momapy.celldesigner.StateTransition], [KnownTransitionOmitted][momapy.celldesigner.KnownTransitionOmitted], [UnknownTransition][momapy.celldesigner.UnknownTransition], [Transcription][momapy.celldesigner.Transcription], [Translation][momapy.celldesigner.Translation], [Transport][momapy.celldesigner.Transport], [HeterodimerAssociation][momapy.celldesigner.HeterodimerAssociation], [Dissociation][momapy.celldesigner.Dissociation], [Truncation][momapy.celldesigner.Truncation]) | The reaction layout (e.g. [StateTransitionLayout][momapy.celldesigner.StateTransitionLayout], [TranscriptionLayout][momapy.celldesigner.TranscriptionLayout], [DissociationLayout][momapy.celldesigner.DissociationLayout]) + every [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout] and [ProductionLayout][momapy.celldesigner.ProductionLayout] attached to the reaction + every reactant and product target layout (the species alias layouts those arcs point to) + every modifier arc layout + all layouts in its source cluster (resolved via the source's own frozenset key if it has one, for example when the source is a boolean gate, else the source species alias layout) | The reaction layout |
| [KnownOrUnknownModulation][momapy.celldesigner.KnownOrUnknownModulation] and subclasses (e.g. [Modulation][momapy.celldesigner.Modulation], [Catalysis][momapy.celldesigner.Catalysis], [Inhibition][momapy.celldesigner.Inhibition], [PhysicalStimulation][momapy.celldesigner.PhysicalStimulation], [Triggering][momapy.celldesigner.Triggering], [PositiveInfluence][momapy.celldesigner.PositiveInfluence], [NegativeInfluence][momapy.celldesigner.NegativeInfluence], [UnknownModulation][momapy.celldesigner.UnknownModulation] and its subclasses) | The modulation arc layout (e.g. [CatalysisLayout][momapy.celldesigner.CatalysisLayout], [InhibitionLayout][momapy.celldesigner.InhibitionLayout], [PositiveInfluenceLayout][momapy.celldesigner.PositiveInfluenceLayout]) + all layouts in the source cluster (resolved via the source's own frozenset key if it has one, for example when the source is a boolean gate, else the source layout itself) + all layouts in the target cluster (resolved the same way) | The modulation arc layout |
| [BooleanLogicGate][momapy.celldesigner.BooleanLogicGate] and subclasses (e.g. [AndGate][momapy.celldesigner.AndGate], [OrGate][momapy.celldesigner.OrGate], [NotGate][momapy.celldesigner.NotGate], [UnknownGate][momapy.celldesigner.UnknownGate]) | The gate layout (e.g. [AndGateLayout][momapy.celldesigner.AndGateLayout], [OrGateLayout][momapy.celldesigner.OrGateLayout]) + every [LogicArcLayout][momapy.celldesigner.LogicArcLayout] input + every target species alias layout those logic arcs point to | The gate layout |

Notes:
- [SpeciesTemplate][momapy.celldesigner.SpeciesTemplate] and subclasses (e.g.
  [GenericProteinTemplate][momapy.celldesigner.GenericProteinTemplate], [GeneTemplate][momapy.celldesigner.GeneTemplate]),
  [ModificationResidue][momapy.celldesigner.ModificationResidue], and [Region][momapy.celldesigner.Region] have no layout key:
  templates and their residues or regions are not drawn directly —
  only their [Species][momapy.celldesigner.Species] instances and the
  [Modification][momapy.celldesigner.Modification] or [StructuralState][momapy.celldesigner.StructuralState] objects they carry
  are.
- [KnownOrUnknownModulator][momapy.celldesigner.KnownOrUnknownModulator] and its subclasses (e.g.
  [Catalyzer][momapy.celldesigner.Catalyzer], [Inhibitor][momapy.celldesigner.Inhibitor],
  [PhysicalStimulator][momapy.celldesigner.PhysicalStimulator], [Trigger][momapy.celldesigner.Trigger]) are modifier
  references: the modulation cluster above is what is stored in the
  mapping. Modulator metadata lives on the source side of that
  cluster.
- [Inhibition][momapy.celldesigner.Inhibition] and
  [NegativeInfluence][momapy.celldesigner.NegativeInfluence] (likewise
  [UnknownInhibition][momapy.celldesigner.UnknownInhibition] and
  [UnknownNegativeInfluence][momapy.celldesigner.UnknownNegativeInfluence])
  are distinguished by their target, not by the reaction type read from
  the file: the reader builds an
  [Inhibition][momapy.celldesigner.Inhibition] when the target is a
  [Phenotype][momapy.celldesigner.Phenotype] and a
  [NegativeInfluence][momapy.celldesigner.NegativeInfluence] otherwise,
  and the writer emits the matching reaction type. CellDesigner rewrites
  a phenotype-targeting ``INHIBITION`` to ``NEGATIVE_INFLUENCE`` when it
  saves, so both spellings can name the same arc. Both classes share
  [InhibitionLayout][momapy.celldesigner.InhibitionLayout].
"""

import dataclasses
import enum

from momapy.celldesigner.elements import CellDesignerModelElement
from momapy.sbml.model import Compartment as SBMLCompartment
from momapy.sbml.model import Species as SBMLSpecies
from momapy.sbml.model import SimpleSpeciesReference
from momapy.sbml.model import SpeciesReference
from momapy.sbml.model import ModifierSpeciesReference
from momapy.sbml.model import Reaction as SBMLReaction
from momapy.sbml.model import SBMLModel


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModificationResidue(CellDesignerModelElement):
    """Modification residue."""

    name: str | None = dataclasses.field(
        default=None, metadata={"description": "The name of the residue"}
    )
    order: int | None = dataclasses.field(
        default=None,
        metadata={"description": "The sequential order of the residue"},
    )


class ModificationState(enum.Enum):
    """Modification state."""

    PHOSPHORYLATED = "P"
    ACETYLATED = "Ac"
    UBIQUITINATED = "Ub"
    METHYLATED = "M"
    HYDROXYLATED = "OH"
    GLYCOSYLATED = "G"
    MYRISTOYLATED = "My"
    PALMITOYLATED = "Pa"
    PRENYLATED = "Pr"
    PROTONATED = "H"
    SULFATED = "S"
    DON_T_CARE = "*"
    UNKNOWN = "?"


@dataclasses.dataclass(frozen=True, kw_only=True)
class Region(CellDesignerModelElement):
    """Region."""

    name: str | None = dataclasses.field(
        default=None, metadata={"description": "The name of the region"}
    )
    active: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether the region is active or not"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModificationSite(Region):
    """Modification site."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class CodingRegion(Region):
    """Coding region."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class RegulatoryRegion(Region):
    """Regulatory region."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class TranscriptionStartingSiteL(Region):
    """Transcription starting site L."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class TranscriptionStartingSiteR(Region):
    """Transcription starting site R."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProteinBindingDomain(Region):
    """Protein binding domain."""

    pass


# changed name from reference to template to distinguish from SBML's
# species reference which has a different meaning (reference to a species)
@dataclasses.dataclass(frozen=True, kw_only=True)
class SpeciesTemplate(CellDesignerModelElement):
    """Abstract base class for species templates."""

    name: str = dataclasses.field(
        metadata={"description": "The name of the species template"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ProteinTemplate(SpeciesTemplate):
    """Abstract base class for protein templates."""

    modification_residues: frozenset[ModificationResidue] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modification residues of the protein template"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class GenericProteinTemplate(ProteinTemplate):
    """Generic protein template."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class TruncatedProteinTemplate(ProteinTemplate):
    """Truncated protein template."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class ReceptorTemplate(ProteinTemplate):
    """Receptor template."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonChannelTemplate(ProteinTemplate):
    """Ion channel template."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class GeneTemplate(SpeciesTemplate):
    """Gene template."""

    regions: frozenset[
        ModificationSite
        | CodingRegion
        | RegulatoryRegion
        | TranscriptionStartingSiteL
        | TranscriptionStartingSiteR
    ] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The regions of the gene template"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class RNATemplate(SpeciesTemplate):
    """RNA template."""

    regions: frozenset[ModificationSite | CodingRegion | ProteinBindingDomain] = (
        dataclasses.field(
            default_factory=frozenset,
            metadata={"description": "The regions of the RNA template"},
        )
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AntisenseRNATemplate(SpeciesTemplate):
    """Antisense RNA template."""

    regions: frozenset[ModificationSite | CodingRegion | ProteinBindingDomain] = (
        dataclasses.field(
            default_factory=frozenset,
            metadata={"description": "The regions of the antisense RNA template"},
        )
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Modification(CellDesignerModelElement):
    """Modification."""

    residue: ModificationResidue | ModificationSite | None = dataclasses.field(
        default=None,
        metadata={"description": "The residue of the modification"},
    )
    state: ModificationState | None = dataclasses.field(
        default=None, metadata={"description": "The state of the modification"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class StructuralState(CellDesignerModelElement):
    """Structural state."""

    value: str | None = dataclasses.field(
        default=None,
        metadata={"description": "The value of the structural state"},
    )
    order: int | None = dataclasses.field(
        default=None,
        metadata={
            "description": "The order of the structural state. This is used to distinguish between two or more structural states with no value (i.e., set to `None`)"
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Compartment(SBMLCompartment, CellDesignerModelElement):
    """Compartment."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Species(SBMLSpecies, CellDesignerModelElement):
    """Abstract base class for species."""

    hypothetical: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether the species is hypothetical or not"},
    )
    active: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether the species is active or not"},
    )
    homomultimer: int = dataclasses.field(
        default=1,
        metadata={"description": "The number of subunits forming the species"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Protein(Species):
    """Abstract base class for proteins."""

    template: ProteinTemplate = dataclasses.field(
        metadata={"description": "The template of the species"}
    )
    modifications: frozenset[Modification] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modifications of the protein"},
    )
    structural_states: frozenset[StructuralState] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The structural states of the protein"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class GenericProtein(Protein):
    """Generic protein."""

    template: GenericProteinTemplate = dataclasses.field(
        metadata={"description": "The template of the generic protein"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class TruncatedProtein(Protein):
    """Truncated protein."""

    template: TruncatedProteinTemplate = dataclasses.field(
        metadata={"description": "The template of the truncated protein"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Receptor(Protein):
    """Receptor."""

    template: ReceptorTemplate = dataclasses.field(
        metadata={"description": "The template of the receptor"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class IonChannel(Protein):
    """Ion channel."""

    template: IonChannelTemplate = dataclasses.field(
        metadata={"description": "The template of the ion channel"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Gene(Species):
    """Gene."""

    template: GeneTemplate = dataclasses.field(
        metadata={"description": "The template of the gene"}
    )
    modifications: frozenset[Modification] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modifications of the gene"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class RNA(Species):
    """RNA."""

    template: RNATemplate = dataclasses.field(
        metadata={"description": "The template of the RNA"}
    )
    modifications: frozenset[Modification] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modifications of the RNA"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AntisenseRNA(Species):
    """Antisense RNA."""

    template: AntisenseRNATemplate = dataclasses.field(
        metadata={"description": "The template of the antisense RNA"}
    )
    modifications: frozenset[Modification] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modifications of the antisense RNA"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Phenotype(Species):
    """Phenotype."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Ion(Species):
    """Ion."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class SimpleMolecule(Species):
    """Simple molecule."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Drug(Species):
    """Drug."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Unknown(Species):
    """Unknown."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Complex(Species):
    """Complex."""

    structural_states: frozenset[StructuralState] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The structural states of the complex"},
    )
    subunits: frozenset[Species] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The subunits of the complex"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Reactant(SpeciesReference, CellDesignerModelElement):
    """Reactant."""

    base: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether the reactant is a base reactant or not"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Product(SpeciesReference, CellDesignerModelElement):
    """Product."""

    base: bool = dataclasses.field(
        default=False,
        metadata={"description": "Whether the product is a base product or not"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class BooleanLogicGateInput(SimpleSpeciesReference, CellDesignerModelElement):
    """Boolean logic gate input."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class BooleanLogicGate(CellDesignerModelElement):
    """Abstract base class for boolean logic gates."""

    inputs: frozenset[BooleanLogicGateInput] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The inputs of the Boolean logic gate"},
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class AndGate(BooleanLogicGate):
    """AND gate."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class OrGate(BooleanLogicGate):
    """OR gate."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NotGate(BooleanLogicGate):
    """NOT gate."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownGate(BooleanLogicGate):
    """Unknown gate."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class KnownOrUnknownModulator(ModifierSpeciesReference, CellDesignerModelElement):
    """Abstract base class for known or unknown modulators."""

    # redefined because can be BooleanLogicGate
    referred_element: Species | BooleanLogicGate = dataclasses.field(
        metadata={
            "description": "The species or boolean logic gate the modifier refers to"
        }
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Modulator(KnownOrUnknownModulator):
    """Modulator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownModulator(KnownOrUnknownModulator):
    """Unknown modulator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Inhibitor(Modulator):
    """Inhibitor."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhysicalStimulator(Modulator):
    """Physical stimulator."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Catalyzer(PhysicalStimulator):
    """Catalyzer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Trigger(Modulator):
    """Trigger."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownCatalyzer(UnknownModulator):
    """Unknown catalyzer."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownInhibitor(UnknownModulator):
    """Unknown inhibitor."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Reaction(SBMLReaction, CellDesignerModelElement):
    """Abstract base class for reactions.

    CellDesigner's degraded glyph (a ``<species class="DEGRADED">`` used
    as a source-and-sink for unspecified external flux) is *not*
    represented as a member of ``reactants`` or ``products``. Instead, it
    is encoded as the boolean flags ``has_external_source`` (a degraded
    reactant) and ``has_external_sink`` (a degraded product).
    """

    reactants: frozenset[Reactant] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The reactants of the reaction"},
    )
    products: frozenset[Product] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The products of the reaction"},
    )
    modifiers: frozenset[KnownOrUnknownModulator] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modifiers of the reaction"},
    )
    has_external_source: bool = dataclasses.field(
        default=False,
        metadata={
            "description": (
                "Whether the reaction has an unspecified external source "
                "(a Degraded reactant in CellDesigner)."
            )
        },
    )
    has_external_sink: bool = dataclasses.field(
        default=False,
        metadata={
            "description": (
                "Whether the reaction has an unspecified external sink "
                "(a Degraded product in CellDesigner)."
            )
        },
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class StateTransition(Reaction):
    """State transition."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class KnownTransitionOmitted(Reaction):
    """Known transition omitted."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownTransition(Reaction):
    """Unknown transition."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Transcription(Reaction):
    """Transcription."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Translation(Reaction):
    """Translation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Transport(Reaction):
    """Transport."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class HeterodimerAssociation(Reaction):
    """Heterodimer association."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Dissociation(Reaction):
    """Dissociation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Truncation(Reaction):
    """Truncation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class KnownOrUnknownModulation(CellDesignerModelElement):
    """Abstract base class for known or unknown modulations."""

    source: Species | BooleanLogicGate = dataclasses.field(
        metadata={"description": "The source of the modulation"}
    )
    target: Species | None = dataclasses.field(
        metadata={"description": "The target of the modulation"}
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Modulation(KnownOrUnknownModulation):
    """Modulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Inhibition(Modulation):
    """Inhibition."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class PhysicalStimulation(Modulation):
    """Physical stimulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class Catalysis(PhysicalStimulation):
    """Catalysis."""

    pass


# need to be a different name than the modifier Trigger
@dataclasses.dataclass(frozen=True, kw_only=True)
class Triggering(Modulation):
    """Triggering."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class PositiveInfluence(Modulation):
    """Positive influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class NegativeInfluence(Modulation):
    """Negative influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownModulation(KnownOrUnknownModulation):
    """Unknown modulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownInhibition(UnknownModulation):
    """Unknown inhibition."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownPositiveInfluence(UnknownModulation):
    """Unknown positive influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownNegativeInfluence(UnknownModulation):
    """Unknown negative influence."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownPhysicalStimulation(UnknownModulation):
    """Unknown physical stimulation."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownCatalysis(UnknownPhysicalStimulation):
    """Unknown catalysis."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class UnknownTriggering(UnknownModulation):
    """Unknown triggering."""

    pass


@dataclasses.dataclass(frozen=True, kw_only=True)
class CellDesignerModel(SBMLModel):
    """CellDesigner model."""

    species_templates: frozenset[SpeciesTemplate] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The species templates of the CellDesigner model"},
    )
    boolean_logic_gates: frozenset[BooleanLogicGate] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The boolean logic gates of the CellDesigner model"},
    )
    modulations: frozenset[Modulation | UnknownModulation] = dataclasses.field(
        default_factory=frozenset,
        metadata={"description": "The modulations of the CellDesigner model"},
    )

    def is_submodel(self, other: "CellDesignerModel") -> bool:
        """Check if this model is a submodel of another model.

        Args:
            other: Another CellDesigner model to compare against.

        Returns:
            True if this model is a submodel of `other`, False otherwise.
        """
        return (
            self.compartments.issubset(other.compartments)
            and self.species.issubset(other.species)
            and self.reactions.issubset(other.reactions)
            and self.species_templates.issubset(other.species_templates)
            and self.boolean_logic_gates.issubset(other.boolean_logic_gates)
            and self.modulations.issubset(other.modulations)
        )
