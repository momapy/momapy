"""Classification mappings for the SBGN-ML writer.

Maps momapy model/layout classes to SBGN-ML XML class attribute strings
and direction/orientation values.
"""

from momapy.core.elements import Direction
from momapy.core.elements import Orientation
from momapy.sbgn.pd import AndOperatorLayout as PDAndOperatorLayout
from momapy.sbgn.pd import AssociationLayout as PDAssociationLayout
from momapy.sbgn.pd import CatalysisLayout as PDCatalysisLayout
from momapy.sbgn.pd import CompartmentLayout as PDCompartmentLayout
from momapy.sbgn.pd import ComplexLayout as PDComplexLayout
from momapy.sbgn.pd import ComplexMultimerLayout as PDComplexMultimerLayout
from momapy.sbgn.pd import (
    ComplexMultimerSubunitLayout as PDComplexMultimerSubunitLayout,
)
from momapy.sbgn.pd import ComplexSubunitLayout as PDComplexSubunitLayout
from momapy.sbgn.pd import ConsumptionLayout as PDConsumptionLayout
from momapy.sbgn.pd import DissociationLayout as PDDissociationLayout
from momapy.sbgn.pd import EmptySetLayout as PDEmptySetLayout
from momapy.sbgn.pd import EquivalenceArcLayout as PDEquivalenceArcLayout
from momapy.sbgn.pd import EquivalenceOperatorLayout as PDEquivalenceOperatorLayout
from momapy.sbgn.pd import GenericProcessLayout as PDGenericProcessLayout
from momapy.sbgn.pd import InhibitionLayout as PDInhibitionLayout
from momapy.sbgn.pd import LogicArcLayout as PDLogicArcLayout
from momapy.sbgn.pd import MacromoleculeLayout as PDMacromoleculeLayout
from momapy.sbgn.pd import MacromoleculeMultimerLayout as PDMacromoleculeMultimerLayout
from momapy.sbgn.pd import (
    MacromoleculeMultimerSubunitLayout as PDMacromoleculeMultimerSubunitLayout,
)
from momapy.sbgn.pd import MacromoleculeSubunitLayout as PDMacromoleculeSubunitLayout
from momapy.sbgn.pd import ModulationLayout as PDModulationLayout
from momapy.sbgn.pd import NecessaryStimulationLayout as PDNecessaryStimulationLayout
from momapy.sbgn.pd import NotOperatorLayout as PDNotOperatorLayout
from momapy.sbgn.pd import NucleicAcidFeatureLayout as PDNucleicAcidFeatureLayout
from momapy.sbgn.pd import (
    NucleicAcidFeatureMultimerLayout as PDNucleicAcidFeatureMultimerLayout,
)
from momapy.sbgn.pd import (
    NucleicAcidFeatureMultimerSubunitLayout as PDNucleicAcidFeatureMultimerSubunitLayout,
)
from momapy.sbgn.pd import (
    NucleicAcidFeatureSubunitLayout as PDNucleicAcidFeatureSubunitLayout,
)
from momapy.sbgn.pd import OmittedProcessLayout as PDOmittedProcessLayout
from momapy.sbgn.pd import OrOperatorLayout as PDOrOperatorLayout
from momapy.sbgn.pd import PerturbingAgentLayout as PDPerturbingAgentLayout
from momapy.sbgn.pd import PhenotypeLayout as PDPhenotypeLayout
from momapy.sbgn.pd import ProductionLayout as PDProductionLayout
from momapy.sbgn.pd import SBGNPDLayout as PDSBGNPDLayout
from momapy.sbgn.pd import SBGNPDMap as PDSBGNPDMap
from momapy.sbgn.pd import SBGNPDModel as PDSBGNPDModel
from momapy.sbgn.pd import SimpleChemicalLayout as PDSimpleChemicalLayout
from momapy.sbgn.pd import (
    SimpleChemicalMultimerLayout as PDSimpleChemicalMultimerLayout,
)
from momapy.sbgn.pd import (
    SimpleChemicalMultimerSubunitLayout as PDSimpleChemicalMultimerSubunitLayout,
)
from momapy.sbgn.pd import SimpleChemicalSubunitLayout as PDSimpleChemicalSubunitLayout
from momapy.sbgn.pd import StateVariableLayout as PDStateVariableLayout
from momapy.sbgn.pd import StimulationLayout as PDStimulationLayout
from momapy.sbgn.pd import SubmapLayout as PDSubmapLayout
from momapy.sbgn.pd import TagLayout as PDTagLayout
from momapy.sbgn.pd import TerminalLayout as PDTerminalLayout
from momapy.sbgn.pd import UncertainProcessLayout as PDUncertainProcessLayout
from momapy.sbgn.pd import UnitOfInformationLayout as PDUnitOfInformationLayout
from momapy.sbgn.pd import UnspecifiedEntityLayout as PDUnspecifiedEntityLayout
from momapy.sbgn.pd import (
    UnspecifiedEntitySubunitLayout as PDUnspecifiedEntitySubunitLayout,
)
from momapy.sbgn.af import AndOperatorLayout as AFAndOperatorLayout
from momapy.sbgn.af import BiologicalActivityLayout as AFBiologicalActivityLayout
from momapy.sbgn.af import CompartmentLayout as AFCompartmentLayout
from momapy.sbgn.af import (
    ComplexUnitOfInformationLayout as AFComplexUnitOfInformationLayout,
)
from momapy.sbgn.af import DelayOperatorLayout as AFDelayOperatorLayout
from momapy.sbgn.af import EquivalenceArcLayout as AFEquivalenceArcLayout
from momapy.sbgn.af import LogicArcLayout as AFLogicArcLayout
from momapy.sbgn.af import (
    MacromoleculeUnitOfInformationLayout as AFMacromoleculeUnitOfInformationLayout,
)
from momapy.sbgn.af import NecessaryStimulationLayout as AFNecessaryStimulationLayout
from momapy.sbgn.af import NegativeInfluenceLayout as AFNegativeInfluenceLayout
from momapy.sbgn.af import NotOperatorLayout as AFNotOperatorLayout
from momapy.sbgn.af import (
    NucleicAcidFeatureUnitOfInformationLayout as AFNucleicAcidFeatureUnitOfInformationLayout,
)
from momapy.sbgn.af import OrOperatorLayout as AFOrOperatorLayout
from momapy.sbgn.af import (
    PerturbationUnitOfInformationLayout as AFPerturbationUnitOfInformationLayout,
)
from momapy.sbgn.af import PhenotypeLayout as AFPhenotypeLayout
from momapy.sbgn.af import PositiveInfluenceLayout as AFPositiveInfluenceLayout
from momapy.sbgn.af import SBGNAFLayout as AFSBGNAFLayout
from momapy.sbgn.af import SBGNAFMap as AFSBGNAFMap
from momapy.sbgn.af import SBGNAFModel as AFSBGNAFModel
from momapy.sbgn.af import (
    SimpleChemicalUnitOfInformationLayout as AFSimpleChemicalUnitOfInformationLayout,
)
from momapy.sbgn.af import SubmapLayout as AFSubmapLayout
from momapy.sbgn.af import TagLayout as AFTagLayout
from momapy.sbgn.af import TerminalLayout as AFTerminalLayout
from momapy.sbgn.af import UnitOfInformationLayout as AFUnitOfInformationLayout
from momapy.sbgn.af import UnknownInfluenceLayout as AFUnknownInfluenceLayout
from momapy.sbgn.af import (
    UnspecifiedEntityUnitOfInformationLayout as AFUnspecifiedEntityUnitOfInformationLayout,
)

CLASS_TO_SBGNML_CLASS = {
    PDSBGNPDMap: "process description",
    PDSBGNPDModel: "process description",
    PDSBGNPDLayout: "process description",
    AFSBGNAFMap: "activity flow",
    AFSBGNAFModel: "activity flow",
    AFSBGNAFLayout: "activity flow",
    PDStateVariableLayout: "state variable",
    PDUnitOfInformationLayout: "unit of information",
    PDTerminalLayout: "terminal",
    PDUnspecifiedEntitySubunitLayout: "unspecified entity",
    PDMacromoleculeSubunitLayout: "macromolecule",
    PDSimpleChemicalSubunitLayout: "simple chemical",
    PDNucleicAcidFeatureSubunitLayout: "nucleic acid feature",
    PDComplexSubunitLayout: "complex",
    PDMacromoleculeMultimerSubunitLayout: "macromolecule multimer",
    PDSimpleChemicalMultimerSubunitLayout: "simple chemical multimer",
    PDNucleicAcidFeatureMultimerSubunitLayout: "nucleic acid feature multimer",
    PDComplexMultimerSubunitLayout: "complex multimer",
    PDCompartmentLayout: "compartment",
    PDSubmapLayout: "submap",
    PDUnspecifiedEntityLayout: "unspecified entity",
    PDMacromoleculeLayout: "macromolecule",
    PDSimpleChemicalLayout: "simple chemical",
    PDNucleicAcidFeatureLayout: "nucleic acid feature",
    PDComplexLayout: "complex",
    PDMacromoleculeMultimerLayout: "macromolecule multimer",
    PDSimpleChemicalMultimerLayout: "simple chemical multimer",
    PDNucleicAcidFeatureMultimerLayout: "nucleic acid feature multimer",
    PDComplexMultimerLayout: "complex multimer",
    PDPerturbingAgentLayout: "perturbing agent",
    PDEmptySetLayout: "empty set",
    PDTagLayout: "tag",
    PDGenericProcessLayout: "process",
    PDUncertainProcessLayout: "uncertain process",
    PDOmittedProcessLayout: "omitted process",
    PDAssociationLayout: "association",
    PDDissociationLayout: "dissociation",
    PDPhenotypeLayout: "phenotype",
    PDAndOperatorLayout: "and",
    PDOrOperatorLayout: "or",
    PDNotOperatorLayout: "not",
    PDEquivalenceOperatorLayout: "equivalence",
    PDConsumptionLayout: "consumption",
    PDProductionLayout: "production",
    PDModulationLayout: "modulation",
    PDStimulationLayout: "stimulation",
    PDCatalysisLayout: "catalysis",
    PDNecessaryStimulationLayout: "necessary stimulation",
    PDInhibitionLayout: "inhibition",
    PDLogicArcLayout: "logic arc",
    PDEquivalenceArcLayout: "equivalence arc",
    AFCompartmentLayout: "compartment",
    AFSubmapLayout: "submap",
    AFBiologicalActivityLayout: "biological activity",
    AFUnitOfInformationLayout: "unit of information",
    AFUnspecifiedEntityUnitOfInformationLayout: "unit of information",
    AFMacromoleculeUnitOfInformationLayout: "unit of information",
    AFSimpleChemicalUnitOfInformationLayout: "unit of information",
    AFNucleicAcidFeatureUnitOfInformationLayout: "unit of information",
    AFComplexUnitOfInformationLayout: "unit of information",
    AFPerturbationUnitOfInformationLayout: "unit of information",
    AFPhenotypeLayout: "phenotype",
    AFAndOperatorLayout: "and",
    AFOrOperatorLayout: "or",
    AFNotOperatorLayout: "not",
    AFDelayOperatorLayout: "delay",
    AFUnknownInfluenceLayout: "unknown influence",
    AFPositiveInfluenceLayout: "positive influence",
    AFNecessaryStimulationLayout: "necessary stimulation",
    AFNegativeInfluenceLayout: "negative influence",
    AFTerminalLayout: "terminal",
    AFTagLayout: "tag",
    AFLogicArcLayout: "logic arc",
    AFEquivalenceArcLayout: "equivalence arc",
}

# AF units of information are encoded as ``class="unit of information"`` glyphs
# carrying an ``<entity name="..."/>`` child that names the entity type. This maps
# each AF unit-of-information layout class to the entity name the reader expects.
CLASS_TO_SBGNML_ENTITY_NAME = {
    AFUnspecifiedEntityUnitOfInformationLayout: "unspecified entity",
    AFMacromoleculeUnitOfInformationLayout: "macromolecule",
    AFSimpleChemicalUnitOfInformationLayout: "simple chemical",
    AFNucleicAcidFeatureUnitOfInformationLayout: "nucleic acid feature",
    AFComplexUnitOfInformationLayout: "complex",
    AFPerturbationUnitOfInformationLayout: "perturbation",
}

DIRECTION_TO_SBGNML_ORIENTATION = {
    Orientation.HORIZONTAL: "horizontal",
    Orientation.VERTICAL: "vertical",
    Direction.RIGHT: "right",
    Direction.LEFT: "left",
    Direction.DOWN: "down",
    Direction.UP: "up",
}

# Arc types whose direction is reversed in momapy compared to SBGN-ML.
REVERSED_ARC_TYPES = (
    PDConsumptionLayout,
    PDLogicArcLayout,
    AFLogicArcLayout,
    PDEquivalenceArcLayout,
    AFEquivalenceArcLayout,
)
