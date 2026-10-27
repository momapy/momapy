"""SBGN Process Description (PD) subpackage facade.

Layout-model mapping catalogue
------------------------------

This section lists, for each model-element category in SBGN-PD, the shape
of the corresponding key in [LayoutModelMapping][momapy.core.LayoutModelMapping].
See [LayoutModelMapping][momapy.core.LayoutModelMapping] for the general concepts
(singleton keys, frozenset keys, representatives).
The keys can be computed from a plain ``{layout_element: model_element}``
dict by ``momapy.sbgn.utils.make_pd_map_from_map_elements``.

Singleton keys (one layout element represents the model element):

| Model element | Layout element used as the key |
|---|---|
| [Compartment][momapy.sbgn.pd.Compartment] | [CompartmentLayout][momapy.sbgn.pd.CompartmentLayout] |
| [EntityPool][momapy.sbgn.pd.EntityPool] and subclasses (e.g. [Macromolecule][momapy.sbgn.pd.Macromolecule], [NucleicAcidFeature][momapy.sbgn.pd.NucleicAcidFeature], [SimpleChemical][momapy.sbgn.pd.SimpleChemical], [Complex][momapy.sbgn.pd.Complex], [UnspecifiedEntity][momapy.sbgn.pd.UnspecifiedEntity], [PerturbingAgent][momapy.sbgn.pd.PerturbingAgent], and every [Multimer][momapy.sbgn.pd.Multimer] variant) | The corresponding `*Layout` (e.g. [MacromoleculeLayout][momapy.sbgn.pd.MacromoleculeLayout], [ComplexLayout][momapy.sbgn.pd.ComplexLayout], [PerturbingAgentLayout][momapy.sbgn.pd.PerturbingAgentLayout]) |
| [Subunit][momapy.sbgn.pd.Subunit] and subclasses | The corresponding `*SubunitLayout` |
| [StateVariable][momapy.sbgn.pd.StateVariable] | [StateVariableLayout][momapy.sbgn.pd.StateVariableLayout] |
| [UnitOfInformation][momapy.sbgn.pd.UnitOfInformation] | [UnitOfInformationLayout][momapy.sbgn.pd.UnitOfInformationLayout] |
| [Submap][momapy.sbgn.pd.Submap] | [SubmapLayout][momapy.sbgn.pd.SubmapLayout] |
| [Reactant][momapy.sbgn.pd.Reactant] | [ConsumptionLayout][momapy.sbgn.pd.ConsumptionLayout] |
| [Product][momapy.sbgn.pd.Product] | [ProductionLayout][momapy.sbgn.pd.ProductionLayout] |
| [LogicalOperatorInput][momapy.sbgn.pd.LogicalOperatorInput] | [LogicArcLayout][momapy.sbgn.pd.LogicArcLayout] |
| [TagReference][momapy.sbgn.pd.TagReference], [TerminalReference][momapy.sbgn.pd.TerminalReference] | [EquivalenceArcLayout][momapy.sbgn.pd.EquivalenceArcLayout] |
| [Phenotype][momapy.sbgn.pd.Phenotype] | [PhenotypeLayout][momapy.sbgn.pd.PhenotypeLayout] |

Frozenset keys (a cluster of layout elements jointly represents the
model element; the **representative** is the layout that stands for the cluster
on its own and must be passed as ``representative=`` when calling
[add_mapping][momapy.core.LayoutModelMappingBuilder.add_mapping]):

| Model element | Members of the frozenset key | Representative |
|---|---|---|
| [Process][momapy.sbgn.pd.Process] and subclasses (e.g. [StoichiometricProcess][momapy.sbgn.pd.StoichiometricProcess], [GenericProcess][momapy.sbgn.pd.GenericProcess], [UncertainProcess][momapy.sbgn.pd.UncertainProcess], [Association][momapy.sbgn.pd.Association], [Dissociation][momapy.sbgn.pd.Dissociation], [OmittedProcess][momapy.sbgn.pd.OmittedProcess]) | The process `*Layout` (e.g. [GenericProcessLayout][momapy.sbgn.pd.GenericProcessLayout], [AssociationLayout][momapy.sbgn.pd.AssociationLayout], [DissociationLayout][momapy.sbgn.pd.DissociationLayout]) + every [ConsumptionLayout][momapy.sbgn.pd.ConsumptionLayout] and [ProductionLayout][momapy.sbgn.pd.ProductionLayout] attached to the process + every target layout (the entity-pool layouts those arcs point to) | The process `*Layout` |
| [LogicalOperator][momapy.sbgn.pd.LogicalOperator] and subclasses (e.g. [AndOperator][momapy.sbgn.pd.AndOperator], [OrOperator][momapy.sbgn.pd.OrOperator], [NotOperator][momapy.sbgn.pd.NotOperator]) | The operator `*Layout` (e.g. [AndOperatorLayout][momapy.sbgn.pd.AndOperatorLayout], [OrOperatorLayout][momapy.sbgn.pd.OrOperatorLayout]) + every [LogicArcLayout][momapy.sbgn.pd.LogicArcLayout] input + every target layout those logic arcs point to | The operator `*Layout` |
| [Modulation][momapy.sbgn.pd.Modulation] and subclasses (e.g. [Stimulation][momapy.sbgn.pd.Stimulation], [Inhibition][momapy.sbgn.pd.Inhibition], [Catalysis][momapy.sbgn.pd.Catalysis], [NecessaryStimulation][momapy.sbgn.pd.NecessaryStimulation]) | The modulation arc layout (e.g. [ModulationLayout][momapy.sbgn.pd.ModulationLayout], [StimulationLayout][momapy.sbgn.pd.StimulationLayout], [InhibitionLayout][momapy.sbgn.pd.InhibitionLayout]) + all layouts in the source cluster (resolved via the source's own frozenset key if it has one, else the source layout itself) + all layouts in the target cluster (resolved the same way) | The modulation arc layout |
| [Tag][momapy.sbgn.pd.Tag] or [Terminal][momapy.sbgn.pd.Terminal] carrying [TagReference][momapy.sbgn.pd.TagReference] or [TerminalReference][momapy.sbgn.pd.TerminalReference] arcs | The [TagLayout][momapy.sbgn.pd.TagLayout] or [TerminalLayout][momapy.sbgn.pd.TerminalLayout] + every [EquivalenceArcLayout][momapy.sbgn.pd.EquivalenceArcLayout] reference arc + every referenced entity layout | The [TagLayout][momapy.sbgn.pd.TagLayout] or [TerminalLayout][momapy.sbgn.pd.TerminalLayout] |

Standalone [Tag][momapy.sbgn.pd.Tag] and [Terminal][momapy.sbgn.pd.Terminal] instances (with no
reference arcs) use a singleton key: [TagLayout][momapy.sbgn.pd.TagLayout] or
[TerminalLayout][momapy.sbgn.pd.TerminalLayout].

Empty-set glyphs ([EmptySetLayout][momapy.sbgn.pd.EmptySetLayout]) have no
model singleton. They are members of the frozenset key of the process they
attach to, and the two boolean flags ``has_external_source`` and
``has_external_sink`` on the [StoichiometricProcess][momapy.sbgn.pd.StoichiometricProcess]
record which side of the process the empty set represents.
"""

from momapy.sbgn.layout import (
    DEFAULT_AUXILIARY_UNIT_FONT_SIZE as DEFAULT_AUXILIARY_UNIT_FONT_SIZE,
)
from momapy.sbgn.layout import DEFAULT_FONT_SIZE as DEFAULT_FONT_SIZE
from momapy.sbgn.pd.model import StateVariable as StateVariable
from momapy.sbgn.pd.model import UnitOfInformation as UnitOfInformation
from momapy.sbgn.pd.model import Subunit as Subunit
from momapy.sbgn.pd.model import UnspecifiedEntitySubunit as UnspecifiedEntitySubunit
from momapy.sbgn.pd.model import MacromoleculeSubunit as MacromoleculeSubunit
from momapy.sbgn.pd.model import NucleicAcidFeatureSubunit as NucleicAcidFeatureSubunit
from momapy.sbgn.pd.model import SimpleChemicalSubunit as SimpleChemicalSubunit
from momapy.sbgn.pd.model import ComplexSubunit as ComplexSubunit
from momapy.sbgn.pd.model import MultimerSubunit as MultimerSubunit
from momapy.sbgn.pd.model import (
    MacromoleculeMultimerSubunit as MacromoleculeMultimerSubunit,
)
from momapy.sbgn.pd.model import (
    NucleicAcidFeatureMultimerSubunit as NucleicAcidFeatureMultimerSubunit,
)
from momapy.sbgn.pd.model import (
    SimpleChemicalMultimerSubunit as SimpleChemicalMultimerSubunit,
)
from momapy.sbgn.pd.model import ComplexMultimerSubunit as ComplexMultimerSubunit
from momapy.sbgn.pd.model import Compartment as Compartment
from momapy.sbgn.pd.model import EntityPool as EntityPool
from momapy.sbgn.pd.model import PerturbingAgent as PerturbingAgent
from momapy.sbgn.pd.model import UnspecifiedEntity as UnspecifiedEntity
from momapy.sbgn.pd.model import Macromolecule as Macromolecule
from momapy.sbgn.pd.model import NucleicAcidFeature as NucleicAcidFeature
from momapy.sbgn.pd.model import SimpleChemical as SimpleChemical
from momapy.sbgn.pd.model import Complex as Complex
from momapy.sbgn.pd.model import Multimer as Multimer
from momapy.sbgn.pd.model import MacromoleculeMultimer as MacromoleculeMultimer
from momapy.sbgn.pd.model import (
    NucleicAcidFeatureMultimer as NucleicAcidFeatureMultimer,
)
from momapy.sbgn.pd.model import SimpleChemicalMultimer as SimpleChemicalMultimer
from momapy.sbgn.pd.model import ComplexMultimer as ComplexMultimer
from momapy.sbgn.pd.model import FluxRole as FluxRole
from momapy.sbgn.pd.model import Reactant as Reactant
from momapy.sbgn.pd.model import Product as Product
from momapy.sbgn.pd.model import LogicalOperatorInput as LogicalOperatorInput
from momapy.sbgn.pd.model import EquivalenceOperatorInput as EquivalenceOperatorInput
from momapy.sbgn.pd.model import EquivalenceOperatorOutput as EquivalenceOperatorOutput
from momapy.sbgn.pd.model import Process as Process
from momapy.sbgn.pd.model import StoichiometricProcess as StoichiometricProcess
from momapy.sbgn.pd.model import GenericProcess as GenericProcess
from momapy.sbgn.pd.model import UncertainProcess as UncertainProcess
from momapy.sbgn.pd.model import Association as Association
from momapy.sbgn.pd.model import Dissociation as Dissociation
from momapy.sbgn.pd.model import OmittedProcess as OmittedProcess
from momapy.sbgn.pd.model import Phenotype as Phenotype
from momapy.sbgn.pd.model import LogicalOperator as LogicalOperator
from momapy.sbgn.pd.model import OrOperator as OrOperator
from momapy.sbgn.pd.model import AndOperator as AndOperator
from momapy.sbgn.pd.model import NotOperator as NotOperator
from momapy.sbgn.pd.model import EquivalenceOperator as EquivalenceOperator
from momapy.sbgn.pd.model import Modulation as Modulation
from momapy.sbgn.pd.model import Inhibition as Inhibition
from momapy.sbgn.pd.model import Stimulation as Stimulation
from momapy.sbgn.pd.model import Catalysis as Catalysis
from momapy.sbgn.pd.model import NecessaryStimulation as NecessaryStimulation
from momapy.sbgn.pd.model import TagReference as TagReference
from momapy.sbgn.pd.model import Tag as Tag
from momapy.sbgn.pd.model import TerminalReference as TerminalReference
from momapy.sbgn.pd.model import Terminal as Terminal
from momapy.sbgn.pd.model import Submap as Submap
from momapy.sbgn.pd.model import SBGNPDModel as SBGNPDModel

from momapy.sbgn.pd.layout import SBGNPDLayout as SBGNPDLayout
from momapy.sbgn.pd.layout import StateVariableLayout as StateVariableLayout
from momapy.sbgn.pd.layout import UnitOfInformationLayout as UnitOfInformationLayout
from momapy.sbgn.pd.layout import TerminalLayout as TerminalLayout
from momapy.sbgn.pd.layout import CardinalityLayout as CardinalityLayout
from momapy.sbgn.pd.layout import (
    UnspecifiedEntitySubunitLayout as UnspecifiedEntitySubunitLayout,
)
from momapy.sbgn.pd.layout import (
    SimpleChemicalSubunitLayout as SimpleChemicalSubunitLayout,
)
from momapy.sbgn.pd.layout import (
    MacromoleculeSubunitLayout as MacromoleculeSubunitLayout,
)
from momapy.sbgn.pd.layout import (
    NucleicAcidFeatureSubunitLayout as NucleicAcidFeatureSubunitLayout,
)
from momapy.sbgn.pd.layout import ComplexSubunitLayout as ComplexSubunitLayout
from momapy.sbgn.pd.layout import (
    SimpleChemicalMultimerSubunitLayout as SimpleChemicalMultimerSubunitLayout,
)
from momapy.sbgn.pd.layout import (
    MacromoleculeMultimerSubunitLayout as MacromoleculeMultimerSubunitLayout,
)
from momapy.sbgn.pd.layout import (
    NucleicAcidFeatureMultimerSubunitLayout as NucleicAcidFeatureMultimerSubunitLayout,
)
from momapy.sbgn.pd.layout import (
    ComplexMultimerSubunitLayout as ComplexMultimerSubunitLayout,
)
from momapy.sbgn.pd.layout import CompartmentLayout as CompartmentLayout
from momapy.sbgn.pd.layout import SubmapLayout as SubmapLayout
from momapy.sbgn.pd.layout import UnspecifiedEntityLayout as UnspecifiedEntityLayout
from momapy.sbgn.pd.layout import SimpleChemicalLayout as SimpleChemicalLayout
from momapy.sbgn.pd.layout import MacromoleculeLayout as MacromoleculeLayout
from momapy.sbgn.pd.layout import NucleicAcidFeatureLayout as NucleicAcidFeatureLayout
from momapy.sbgn.pd.layout import ComplexLayout as ComplexLayout
from momapy.sbgn.pd.layout import (
    SimpleChemicalMultimerLayout as SimpleChemicalMultimerLayout,
)
from momapy.sbgn.pd.layout import (
    MacromoleculeMultimerLayout as MacromoleculeMultimerLayout,
)
from momapy.sbgn.pd.layout import (
    NucleicAcidFeatureMultimerLayout as NucleicAcidFeatureMultimerLayout,
)
from momapy.sbgn.pd.layout import ComplexMultimerLayout as ComplexMultimerLayout
from momapy.sbgn.pd.layout import EmptySetLayout as EmptySetLayout
from momapy.sbgn.pd.layout import PerturbingAgentLayout as PerturbingAgentLayout
from momapy.sbgn.pd.layout import AndOperatorLayout as AndOperatorLayout
from momapy.sbgn.pd.layout import OrOperatorLayout as OrOperatorLayout
from momapy.sbgn.pd.layout import NotOperatorLayout as NotOperatorLayout
from momapy.sbgn.pd.layout import EquivalenceOperatorLayout as EquivalenceOperatorLayout
from momapy.sbgn.pd.layout import GenericProcessLayout as GenericProcessLayout
from momapy.sbgn.pd.layout import OmittedProcessLayout as OmittedProcessLayout
from momapy.sbgn.pd.layout import UncertainProcessLayout as UncertainProcessLayout
from momapy.sbgn.pd.layout import AssociationLayout as AssociationLayout
from momapy.sbgn.pd.layout import DissociationLayout as DissociationLayout
from momapy.sbgn.pd.layout import PhenotypeLayout as PhenotypeLayout
from momapy.sbgn.pd.layout import TagLayout as TagLayout
from momapy.sbgn.pd.layout import ConsumptionLayout as ConsumptionLayout
from momapy.sbgn.pd.layout import ProductionLayout as ProductionLayout
from momapy.sbgn.pd.layout import ModulationLayout as ModulationLayout
from momapy.sbgn.pd.layout import StimulationLayout as StimulationLayout
from momapy.sbgn.pd.layout import (
    NecessaryStimulationLayout as NecessaryStimulationLayout,
)
from momapy.sbgn.pd.layout import CatalysisLayout as CatalysisLayout
from momapy.sbgn.pd.layout import InhibitionLayout as InhibitionLayout
from momapy.sbgn.pd.layout import LogicArcLayout as LogicArcLayout
from momapy.sbgn.pd.layout import EquivalenceArcLayout as EquivalenceArcLayout

from momapy.sbgn.pd.map import SBGNPDMap as SBGNPDMap

__all__ = [
    "DEFAULT_AUXILIARY_UNIT_FONT_SIZE",
    "DEFAULT_FONT_SIZE",
    "StateVariable",
    "UnitOfInformation",
    "Subunit",
    "UnspecifiedEntitySubunit",
    "MacromoleculeSubunit",
    "NucleicAcidFeatureSubunit",
    "SimpleChemicalSubunit",
    "ComplexSubunit",
    "MultimerSubunit",
    "MacromoleculeMultimerSubunit",
    "NucleicAcidFeatureMultimerSubunit",
    "SimpleChemicalMultimerSubunit",
    "ComplexMultimerSubunit",
    "Compartment",
    "EntityPool",
    "PerturbingAgent",
    "UnspecifiedEntity",
    "Macromolecule",
    "NucleicAcidFeature",
    "SimpleChemical",
    "Complex",
    "Multimer",
    "MacromoleculeMultimer",
    "NucleicAcidFeatureMultimer",
    "SimpleChemicalMultimer",
    "ComplexMultimer",
    "FluxRole",
    "Reactant",
    "Product",
    "LogicalOperatorInput",
    "EquivalenceOperatorInput",
    "EquivalenceOperatorOutput",
    "Process",
    "StoichiometricProcess",
    "GenericProcess",
    "UncertainProcess",
    "Association",
    "Dissociation",
    "OmittedProcess",
    "Phenotype",
    "LogicalOperator",
    "OrOperator",
    "AndOperator",
    "NotOperator",
    "EquivalenceOperator",
    "Modulation",
    "Inhibition",
    "Stimulation",
    "Catalysis",
    "NecessaryStimulation",
    "TagReference",
    "Tag",
    "TerminalReference",
    "Terminal",
    "Submap",
    "SBGNPDModel",
    "SBGNPDLayout",
    "StateVariableLayout",
    "UnitOfInformationLayout",
    "TerminalLayout",
    "CardinalityLayout",
    "UnspecifiedEntitySubunitLayout",
    "SimpleChemicalSubunitLayout",
    "MacromoleculeSubunitLayout",
    "NucleicAcidFeatureSubunitLayout",
    "ComplexSubunitLayout",
    "SimpleChemicalMultimerSubunitLayout",
    "MacromoleculeMultimerSubunitLayout",
    "NucleicAcidFeatureMultimerSubunitLayout",
    "ComplexMultimerSubunitLayout",
    "CompartmentLayout",
    "SubmapLayout",
    "UnspecifiedEntityLayout",
    "SimpleChemicalLayout",
    "MacromoleculeLayout",
    "NucleicAcidFeatureLayout",
    "ComplexLayout",
    "SimpleChemicalMultimerLayout",
    "MacromoleculeMultimerLayout",
    "NucleicAcidFeatureMultimerLayout",
    "ComplexMultimerLayout",
    "EmptySetLayout",
    "PerturbingAgentLayout",
    "AndOperatorLayout",
    "OrOperatorLayout",
    "NotOperatorLayout",
    "EquivalenceOperatorLayout",
    "GenericProcessLayout",
    "OmittedProcessLayout",
    "UncertainProcessLayout",
    "AssociationLayout",
    "DissociationLayout",
    "PhenotypeLayout",
    "TagLayout",
    "ConsumptionLayout",
    "ProductionLayout",
    "ModulationLayout",
    "StimulationLayout",
    "NecessaryStimulationLayout",
    "CatalysisLayout",
    "InhibitionLayout",
    "LogicArcLayout",
    "EquivalenceArcLayout",
    "SBGNPDMap",
]
