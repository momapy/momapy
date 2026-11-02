"""Classes for CellDesigner maps.

Layout-model mapping catalogue
------------------------------

The table below lists, for each model element category in CellDesigner, the
layout elements of its key in
[LayoutModelMapping][momapy.core.LayoutModelMapping].

| Model element | Key | Representative |
|---|---|---|
| [Compartment][momapy.celldesigner.Compartment] | The `*Layout` (e.g. [RectangleCompartmentLayout][momapy.celldesigner.RectangleCompartmentLayout]) + the key of its container, if it draws the outside of the compartment | The `*Layout` |
| [Species][momapy.celldesigner.Species] and subclasses | The `*Layout` (e.g. [GenericProteinLayout][momapy.celldesigner.GenericProteinLayout]) + the key of its container, if it draws the compartment of the species | The `*Layout` |
| [Modification][momapy.celldesigner.Modification] | The [ModificationLayout][momapy.celldesigner.ModificationLayout] | The [ModificationLayout][momapy.celldesigner.ModificationLayout] |
| [StructuralState][momapy.celldesigner.StructuralState] | The [StructuralStateLayout][momapy.celldesigner.StructuralStateLayout] | The [StructuralStateLayout][momapy.celldesigner.StructuralStateLayout] |
| [Reaction][momapy.celldesigner.Reaction] and subclasses | The `*Layout` (e.g. [StateTransitionLayout][momapy.celldesigner.StateTransitionLayout]) + the key of its source layout element, if any + the key of its target layout element, if any + every [DegradedLayout][momapy.celldesigner.DegradedLayout] that is its source or target layout element + the keys of every [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout] and [ProductionLayout][momapy.celldesigner.ProductionLayout] whose source is the `*Layout` + the keys of every modifier `*Layout` (e.g. [CatalysisLayout][momapy.celldesigner.CatalysisLayout]) whose target is the `*Layout` | The `*Layout` |
| [BooleanLogicGate][momapy.celldesigner.BooleanLogicGate] and subclasses | The `*Layout` (e.g. [AndGateLayout][momapy.celldesigner.AndGateLayout]) + the keys of every [LogicArcLayout][momapy.celldesigner.LogicArcLayout] whose source is the `*Layout` | The `*Layout` |
| [KnownOrUnknownModulation][momapy.celldesigner.KnownOrUnknownModulation] and subclasses | The `*Layout` (e.g. [PositiveInfluenceLayout][momapy.celldesigner.PositiveInfluenceLayout]) + the key of its source layout element + the key of its target layout element | The `*Layout` |
| [Reactant][momapy.celldesigner.Reactant], [Product][momapy.celldesigner.Product] | The [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout] or [ProductionLayout][momapy.celldesigner.ProductionLayout] + the key of its target layout element | The [ConsumptionLayout][momapy.celldesigner.ConsumptionLayout] or [ProductionLayout][momapy.celldesigner.ProductionLayout] |
| [KnownOrUnknownModulator][momapy.celldesigner.KnownOrUnknownModulator] and subclasses | The `*Layout` (e.g. [CatalysisLayout][momapy.celldesigner.CatalysisLayout]) + the key of its source layout element | The `*Layout` |
| [BooleanLogicGateInput][momapy.celldesigner.BooleanLogicGateInput] | The [LogicArcLayout][momapy.celldesigner.LogicArcLayout] + the key of its target layout element | The [LogicArcLayout][momapy.celldesigner.LogicArcLayout] |
"""

from momapy.celldesigner.elements import (
    CellDesignerModelElement as CellDesignerModelElement,
)
from momapy.celldesigner.elements import CellDesignerNode as CellDesignerNode
from momapy.celldesigner.elements import (
    CellDesignerSingleHeadedArc as CellDesignerSingleHeadedArc,
)
from momapy.celldesigner.elements import (
    CellDesignerDoubleHeadedArc as CellDesignerDoubleHeadedArc,
)
from momapy.celldesigner.layout import DEFAULT_ACTIVE_XSEP as DEFAULT_ACTIVE_XSEP
from momapy.celldesigner.layout import DEFAULT_ACTIVE_YSEP as DEFAULT_ACTIVE_YSEP
from momapy.celldesigner.layout import DEFAULT_FONT_SIZE as DEFAULT_FONT_SIZE
from momapy.celldesigner.layout import (
    DEFAULT_MODIFICATION_FONT_SIZE as DEFAULT_MODIFICATION_FONT_SIZE,
)
from momapy.celldesigner.layout import CellDesignerLayout as CellDesignerLayout
from momapy.celldesigner.map import CellDesignerMap as CellDesignerMap

from momapy.celldesigner.model import ModificationResidue as ModificationResidue
from momapy.celldesigner.model import ModificationState as ModificationState
from momapy.celldesigner.model import Region as Region
from momapy.celldesigner.model import ModificationSite as ModificationSite
from momapy.celldesigner.model import CodingRegion as CodingRegion
from momapy.celldesigner.model import RegulatoryRegion as RegulatoryRegion
from momapy.celldesigner.model import (
    TranscriptionStartingSiteL as TranscriptionStartingSiteL,
)
from momapy.celldesigner.model import (
    TranscriptionStartingSiteR as TranscriptionStartingSiteR,
)
from momapy.celldesigner.model import ProteinBindingDomain as ProteinBindingDomain
from momapy.celldesigner.model import SpeciesTemplate as SpeciesTemplate
from momapy.celldesigner.model import ProteinTemplate as ProteinTemplate
from momapy.celldesigner.model import GenericProteinTemplate as GenericProteinTemplate
from momapy.celldesigner.model import (
    TruncatedProteinTemplate as TruncatedProteinTemplate,
)
from momapy.celldesigner.model import ReceptorTemplate as ReceptorTemplate
from momapy.celldesigner.model import IonChannelTemplate as IonChannelTemplate
from momapy.celldesigner.model import GeneTemplate as GeneTemplate
from momapy.celldesigner.model import RNATemplate as RNATemplate
from momapy.celldesigner.model import AntisenseRNATemplate as AntisenseRNATemplate
from momapy.celldesigner.model import Modification as Modification
from momapy.celldesigner.model import StructuralState as StructuralState
from momapy.celldesigner.model import Compartment as Compartment
from momapy.celldesigner.model import Species as Species
from momapy.celldesigner.model import Protein as Protein
from momapy.celldesigner.model import GenericProtein as GenericProtein
from momapy.celldesigner.model import TruncatedProtein as TruncatedProtein
from momapy.celldesigner.model import Receptor as Receptor
from momapy.celldesigner.model import IonChannel as IonChannel
from momapy.celldesigner.model import Gene as Gene
from momapy.celldesigner.model import RNA as RNA
from momapy.celldesigner.model import AntisenseRNA as AntisenseRNA
from momapy.celldesigner.model import Phenotype as Phenotype
from momapy.celldesigner.model import Ion as Ion
from momapy.celldesigner.model import SimpleMolecule as SimpleMolecule
from momapy.celldesigner.model import Drug as Drug
from momapy.celldesigner.model import Unknown as Unknown
from momapy.celldesigner.model import Complex as Complex
from momapy.celldesigner.model import Reactant as Reactant
from momapy.celldesigner.model import Product as Product
from momapy.celldesigner.model import BooleanLogicGateInput as BooleanLogicGateInput
from momapy.celldesigner.model import BooleanLogicGate as BooleanLogicGate
from momapy.celldesigner.model import AndGate as AndGate
from momapy.celldesigner.model import OrGate as OrGate
from momapy.celldesigner.model import NotGate as NotGate
from momapy.celldesigner.model import UnknownGate as UnknownGate
from momapy.celldesigner.model import KnownOrUnknownModulator as KnownOrUnknownModulator
from momapy.celldesigner.model import Modulator as Modulator
from momapy.celldesigner.model import UnknownModulator as UnknownModulator
from momapy.celldesigner.model import Inhibitor as Inhibitor
from momapy.celldesigner.model import PhysicalStimulator as PhysicalStimulator
from momapy.celldesigner.model import Catalyzer as Catalyzer
from momapy.celldesigner.model import Trigger as Trigger
from momapy.celldesigner.model import UnknownCatalyzer as UnknownCatalyzer
from momapy.celldesigner.model import UnknownInhibitor as UnknownInhibitor
from momapy.celldesigner.model import Reaction as Reaction
from momapy.celldesigner.model import StateTransition as StateTransition
from momapy.celldesigner.model import KnownTransitionOmitted as KnownTransitionOmitted
from momapy.celldesigner.model import UnknownTransition as UnknownTransition
from momapy.celldesigner.model import Transcription as Transcription
from momapy.celldesigner.model import Translation as Translation
from momapy.celldesigner.model import Transport as Transport
from momapy.celldesigner.model import HeterodimerAssociation as HeterodimerAssociation
from momapy.celldesigner.model import Dissociation as Dissociation
from momapy.celldesigner.model import Truncation as Truncation
from momapy.celldesigner.model import (
    KnownOrUnknownModulation as KnownOrUnknownModulation,
)
from momapy.celldesigner.model import Modulation as Modulation
from momapy.celldesigner.model import Catalysis as Catalysis
from momapy.celldesigner.model import Inhibition as Inhibition
from momapy.celldesigner.model import PhysicalStimulation as PhysicalStimulation
from momapy.celldesigner.model import Triggering as Triggering
from momapy.celldesigner.model import PositiveInfluence as PositiveInfluence
from momapy.celldesigner.model import NegativeInfluence as NegativeInfluence
from momapy.celldesigner.model import UnknownModulation as UnknownModulation
from momapy.celldesigner.model import UnknownCatalysis as UnknownCatalysis
from momapy.celldesigner.model import UnknownInhibition as UnknownInhibition
from momapy.celldesigner.model import (
    UnknownPositiveInfluence as UnknownPositiveInfluence,
)
from momapy.celldesigner.model import (
    UnknownNegativeInfluence as UnknownNegativeInfluence,
)
from momapy.celldesigner.model import (
    UnknownPhysicalStimulation as UnknownPhysicalStimulation,
)
from momapy.celldesigner.model import UnknownTriggering as UnknownTriggering
from momapy.celldesigner.model import CellDesignerModel as CellDesignerModel

from momapy.celldesigner.layout import GenericProteinLayout as GenericProteinLayout
from momapy.celldesigner.layout import (
    GenericProteinActiveLayout as GenericProteinActiveLayout,
)
from momapy.celldesigner.layout import IonChannelLayout as IonChannelLayout
from momapy.celldesigner.layout import IonChannelActiveLayout as IonChannelActiveLayout
from momapy.celldesigner.layout import ComplexLayout as ComplexLayout
from momapy.celldesigner.layout import ComplexActiveLayout as ComplexActiveLayout
from momapy.celldesigner.layout import SimpleMoleculeLayout as SimpleMoleculeLayout
from momapy.celldesigner.layout import (
    SimpleMoleculeActiveLayout as SimpleMoleculeActiveLayout,
)
from momapy.celldesigner.layout import IonLayout as IonLayout
from momapy.celldesigner.layout import IonActiveLayout as IonActiveLayout
from momapy.celldesigner.layout import UnknownLayout as UnknownLayout
from momapy.celldesigner.layout import UnknownActiveLayout as UnknownActiveLayout
from momapy.celldesigner.layout import DegradedLayout as DegradedLayout
from momapy.celldesigner.layout import DegradedActiveLayout as DegradedActiveLayout
from momapy.celldesigner.layout import GeneLayout as GeneLayout
from momapy.celldesigner.layout import GeneActiveLayout as GeneActiveLayout
from momapy.celldesigner.layout import PhenotypeLayout as PhenotypeLayout
from momapy.celldesigner.layout import PhenotypeActiveLayout as PhenotypeActiveLayout
from momapy.celldesigner.layout import RNALayout as RNALayout
from momapy.celldesigner.layout import RNAActiveLayout as RNAActiveLayout
from momapy.celldesigner.layout import AntisenseRNALayout as AntisenseRNALayout
from momapy.celldesigner.layout import (
    AntisenseRNAActiveLayout as AntisenseRNAActiveLayout,
)
from momapy.celldesigner.layout import TruncatedProteinLayout as TruncatedProteinLayout
from momapy.celldesigner.layout import (
    TruncatedProteinActiveLayout as TruncatedProteinActiveLayout,
)
from momapy.celldesigner.layout import ReceptorLayout as ReceptorLayout
from momapy.celldesigner.layout import ReceptorActiveLayout as ReceptorActiveLayout
from momapy.celldesigner.layout import DrugLayout as DrugLayout
from momapy.celldesigner.layout import DrugActiveLayout as DrugActiveLayout
from momapy.celldesigner.layout import StructuralStateLayout as StructuralStateLayout
from momapy.celldesigner.layout import ModificationLayout as ModificationLayout
from momapy.celldesigner.layout import OvalCompartmentLayout as OvalCompartmentLayout
from momapy.celldesigner.layout import (
    RectangleCompartmentLayout as RectangleCompartmentLayout,
)
from momapy.celldesigner.layout import CompartmentCorner as CompartmentCorner
from momapy.celldesigner.layout import CompartmentSide as CompartmentSide
from momapy.celldesigner.layout import (
    CornerCompartmentLayout as CornerCompartmentLayout,
)
from momapy.celldesigner.layout import LineCompartmentLayout as LineCompartmentLayout
from momapy.celldesigner.layout import ConsumptionLayout as ConsumptionLayout
from momapy.celldesigner.layout import ProductionLayout as ProductionLayout
from momapy.celldesigner.layout import CatalysisLayout as CatalysisLayout
from momapy.celldesigner.layout import UnknownCatalysisLayout as UnknownCatalysisLayout
from momapy.celldesigner.layout import InhibitionLayout as InhibitionLayout
from momapy.celldesigner.layout import (
    UnknownInhibitionLayout as UnknownInhibitionLayout,
)
from momapy.celldesigner.layout import (
    PhysicalStimulationLayout as PhysicalStimulationLayout,
)
from momapy.celldesigner.layout import (
    UnknownPhysicalStimulationLayout as UnknownPhysicalStimulationLayout,
)
from momapy.celldesigner.layout import ModulationLayout as ModulationLayout
from momapy.celldesigner.layout import (
    UnknownModulationLayout as UnknownModulationLayout,
)
from momapy.celldesigner.layout import (
    PositiveInfluenceLayout as PositiveInfluenceLayout,
)
from momapy.celldesigner.layout import (
    UnknownPositiveInfluenceLayout as UnknownPositiveInfluenceLayout,
)
from momapy.celldesigner.layout import TriggeringLayout as TriggeringLayout
from momapy.celldesigner.layout import (
    UnknownTriggeringLayout as UnknownTriggeringLayout,
)
from momapy.celldesigner.layout import ReactionLayout as ReactionLayout
from momapy.celldesigner.layout import StateTransitionLayout as StateTransitionLayout
from momapy.celldesigner.layout import (
    KnownTransitionOmittedLayout as KnownTransitionOmittedLayout,
)
from momapy.celldesigner.layout import (
    UnknownTransitionLayout as UnknownTransitionLayout,
)
from momapy.celldesigner.layout import TranscriptionLayout as TranscriptionLayout
from momapy.celldesigner.layout import TranslationLayout as TranslationLayout
from momapy.celldesigner.layout import TransportLayout as TransportLayout
from momapy.celldesigner.layout import (
    HeterodimerAssociationLayout as HeterodimerAssociationLayout,
)
from momapy.celldesigner.layout import DissociationLayout as DissociationLayout
from momapy.celldesigner.layout import TruncationLayout as TruncationLayout
from momapy.celldesigner.layout import AndGateLayout as AndGateLayout
from momapy.celldesigner.layout import OrGateLayout as OrGateLayout
from momapy.celldesigner.layout import NotGateLayout as NotGateLayout
from momapy.celldesigner.layout import UnknownGateLayout as UnknownGateLayout
from momapy.celldesigner.layout import LogicArcLayout as LogicArcLayout

__all__ = [
    "DEFAULT_ACTIVE_XSEP",
    "DEFAULT_ACTIVE_YSEP",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_MODIFICATION_FONT_SIZE",
    "CellDesignerModelElement",
    "CellDesignerNode",
    "CellDesignerSingleHeadedArc",
    "CellDesignerDoubleHeadedArc",
    "CellDesignerLayout",
    "CellDesignerMap",
    "ModificationResidue",
    "ModificationState",
    "Region",
    "ModificationSite",
    "CodingRegion",
    "RegulatoryRegion",
    "TranscriptionStartingSiteL",
    "TranscriptionStartingSiteR",
    "ProteinBindingDomain",
    "SpeciesTemplate",
    "ProteinTemplate",
    "GenericProteinTemplate",
    "TruncatedProteinTemplate",
    "ReceptorTemplate",
    "IonChannelTemplate",
    "GeneTemplate",
    "RNATemplate",
    "AntisenseRNATemplate",
    "Modification",
    "StructuralState",
    "Compartment",
    "Species",
    "Protein",
    "GenericProtein",
    "TruncatedProtein",
    "Receptor",
    "IonChannel",
    "Gene",
    "RNA",
    "AntisenseRNA",
    "Phenotype",
    "Ion",
    "SimpleMolecule",
    "Drug",
    "Unknown",
    "Complex",
    "Reactant",
    "Product",
    "BooleanLogicGateInput",
    "BooleanLogicGate",
    "AndGate",
    "OrGate",
    "NotGate",
    "UnknownGate",
    "KnownOrUnknownModulator",
    "Modulator",
    "UnknownModulator",
    "Inhibitor",
    "PhysicalStimulator",
    "Catalyzer",
    "Trigger",
    "UnknownCatalyzer",
    "UnknownInhibitor",
    "Reaction",
    "StateTransition",
    "KnownTransitionOmitted",
    "UnknownTransition",
    "Transcription",
    "Translation",
    "Transport",
    "HeterodimerAssociation",
    "Dissociation",
    "Truncation",
    "KnownOrUnknownModulation",
    "Modulation",
    "Catalysis",
    "Inhibition",
    "PhysicalStimulation",
    "Triggering",
    "PositiveInfluence",
    "NegativeInfluence",
    "UnknownModulation",
    "UnknownCatalysis",
    "UnknownInhibition",
    "UnknownPositiveInfluence",
    "UnknownNegativeInfluence",
    "UnknownPhysicalStimulation",
    "UnknownTriggering",
    "CellDesignerModel",
    "GenericProteinLayout",
    "GenericProteinActiveLayout",
    "IonChannelLayout",
    "IonChannelActiveLayout",
    "ComplexLayout",
    "ComplexActiveLayout",
    "SimpleMoleculeLayout",
    "SimpleMoleculeActiveLayout",
    "IonLayout",
    "IonActiveLayout",
    "UnknownLayout",
    "UnknownActiveLayout",
    "DegradedLayout",
    "DegradedActiveLayout",
    "GeneLayout",
    "GeneActiveLayout",
    "PhenotypeLayout",
    "PhenotypeActiveLayout",
    "RNALayout",
    "RNAActiveLayout",
    "AntisenseRNALayout",
    "AntisenseRNAActiveLayout",
    "TruncatedProteinLayout",
    "TruncatedProteinActiveLayout",
    "ReceptorLayout",
    "ReceptorActiveLayout",
    "DrugLayout",
    "DrugActiveLayout",
    "StructuralStateLayout",
    "ModificationLayout",
    "OvalCompartmentLayout",
    "RectangleCompartmentLayout",
    "CompartmentCorner",
    "CompartmentSide",
    "CornerCompartmentLayout",
    "LineCompartmentLayout",
    "ConsumptionLayout",
    "ProductionLayout",
    "CatalysisLayout",
    "UnknownCatalysisLayout",
    "InhibitionLayout",
    "UnknownInhibitionLayout",
    "PhysicalStimulationLayout",
    "UnknownPhysicalStimulationLayout",
    "ModulationLayout",
    "UnknownModulationLayout",
    "PositiveInfluenceLayout",
    "UnknownPositiveInfluenceLayout",
    "TriggeringLayout",
    "UnknownTriggeringLayout",
    "ReactionLayout",
    "StateTransitionLayout",
    "KnownTransitionOmittedLayout",
    "UnknownTransitionLayout",
    "TranscriptionLayout",
    "TranslationLayout",
    "TransportLayout",
    "HeterodimerAssociationLayout",
    "DissociationLayout",
    "TruncationLayout",
    "AndGateLayout",
    "OrGateLayout",
    "NotGateLayout",
    "UnknownGateLayout",
    "LogicArcLayout",
]
