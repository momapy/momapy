"""SBGN Activity Flow (AF) subpackage facade.

Layout-model mapping catalogue
------------------------------

This section lists, for each model-element category in SBGN-AF, the shape
of the corresponding key in [LayoutModelMapping][momapy.core.LayoutModelMapping].
See [LayoutModelMapping][momapy.core.LayoutModelMapping] for the general concepts
(singleton keys, frozenset keys, representatives).
The keys can be computed from a plain ``{layout_element: model_element}``
dict by ``momapy.sbgn.utils.make_af_map_from_map_elements``.

Singleton keys (one layout element represents the model element):

| Model element | Layout element used as the key |
|---|---|
| [Compartment][momapy.sbgn.af.Compartment] | [CompartmentLayout][momapy.sbgn.af.CompartmentLayout] |
| [BiologicalActivity][momapy.sbgn.af.BiologicalActivity] | [BiologicalActivityLayout][momapy.sbgn.af.BiologicalActivityLayout] |
| [Phenotype][momapy.sbgn.af.Phenotype] | [PhenotypeLayout][momapy.sbgn.af.PhenotypeLayout] |
| [UnitOfInformation][momapy.sbgn.af.UnitOfInformation] and subclasses (e.g. [MacromoleculeUnitOfInformation][momapy.sbgn.af.MacromoleculeUnitOfInformation], [NucleicAcidFeatureUnitOfInformation][momapy.sbgn.af.NucleicAcidFeatureUnitOfInformation], [SimpleChemicalUnitOfInformation][momapy.sbgn.af.SimpleChemicalUnitOfInformation], [ComplexUnitOfInformation][momapy.sbgn.af.ComplexUnitOfInformation], [UnspecifiedEntityUnitOfInformation][momapy.sbgn.af.UnspecifiedEntityUnitOfInformation], [PerturbationUnitOfInformation][momapy.sbgn.af.PerturbationUnitOfInformation]) | The corresponding `*UnitOfInformationLayout` (e.g. [MacromoleculeUnitOfInformationLayout][momapy.sbgn.af.MacromoleculeUnitOfInformationLayout], [PerturbationUnitOfInformationLayout][momapy.sbgn.af.PerturbationUnitOfInformationLayout]) |
| [Submap][momapy.sbgn.af.Submap] | [SubmapLayout][momapy.sbgn.af.SubmapLayout] |
| [LogicalOperatorInput][momapy.sbgn.af.LogicalOperatorInput] | [LogicArcLayout][momapy.sbgn.af.LogicArcLayout] |
| [TagReference][momapy.sbgn.af.TagReference], [TerminalReference][momapy.sbgn.af.TerminalReference] | [EquivalenceArcLayout][momapy.sbgn.af.EquivalenceArcLayout] |

Frozenset keys (a cluster of layout elements jointly represents the
model element; the **representative** is the layout that stands for the cluster
on its own and must be passed as ``representative=`` when calling
[add_mapping][momapy.core.LayoutModelMappingBuilder.add_mapping]):

| Model element | Members of the frozenset key | Representative |
|---|---|---|
| [LogicalOperator][momapy.sbgn.af.LogicalOperator] and subclasses (e.g. [AndOperator][momapy.sbgn.af.AndOperator], [OrOperator][momapy.sbgn.af.OrOperator], [NotOperator][momapy.sbgn.af.NotOperator], [DelayOperator][momapy.sbgn.af.DelayOperator]) | The operator `*Layout` (e.g. [AndOperatorLayout][momapy.sbgn.af.AndOperatorLayout], [DelayOperatorLayout][momapy.sbgn.af.DelayOperatorLayout]) + every [LogicArcLayout][momapy.sbgn.af.LogicArcLayout] input + every target layout those logic arcs point to | The operator `*Layout` |
| [Influence][momapy.sbgn.af.Influence] and subclasses (e.g. [UnknownInfluence][momapy.sbgn.af.UnknownInfluence], [PositiveInfluence][momapy.sbgn.af.PositiveInfluence], [NegativeInfluence][momapy.sbgn.af.NegativeInfluence], [NecessaryStimulation][momapy.sbgn.af.NecessaryStimulation]) | The influence arc layout (e.g. [UnknownInfluenceLayout][momapy.sbgn.af.UnknownInfluenceLayout], [PositiveInfluenceLayout][momapy.sbgn.af.PositiveInfluenceLayout], [NecessaryStimulationLayout][momapy.sbgn.af.NecessaryStimulationLayout]) + all layouts in the source cluster (resolved via the source's own frozenset key if it has one, else the source layout itself) + all layouts in the target cluster (resolved the same way) | The influence arc layout |
| [Tag][momapy.sbgn.af.Tag] or [Terminal][momapy.sbgn.af.Terminal] carrying [TagReference][momapy.sbgn.af.TagReference] or [TerminalReference][momapy.sbgn.af.TerminalReference] arcs | The [TagLayout][momapy.sbgn.af.TagLayout] or [TerminalLayout][momapy.sbgn.af.TerminalLayout] + every [EquivalenceArcLayout][momapy.sbgn.af.EquivalenceArcLayout] reference arc + every referenced activity layout | The [TagLayout][momapy.sbgn.af.TagLayout] or [TerminalLayout][momapy.sbgn.af.TerminalLayout] |

Standalone [Tag][momapy.sbgn.af.Tag] and [Terminal][momapy.sbgn.af.Terminal] instances (with no
reference arcs) use a singleton key: [TagLayout][momapy.sbgn.af.TagLayout] or
[TerminalLayout][momapy.sbgn.af.TerminalLayout].
"""

from momapy.sbgn.layout import (
    DEFAULT_AUXILIARY_UNIT_FONT_SIZE as DEFAULT_AUXILIARY_UNIT_FONT_SIZE,
)
from momapy.sbgn.layout import DEFAULT_FONT_SIZE as DEFAULT_FONT_SIZE
from momapy.sbgn.af.model import UnitOfInformation as UnitOfInformation
from momapy.sbgn.af.model import Compartment as Compartment
from momapy.sbgn.af.model import (
    MacromoleculeUnitOfInformation as MacromoleculeUnitOfInformation,
)
from momapy.sbgn.af.model import (
    NucleicAcidFeatureUnitOfInformation as NucleicAcidFeatureUnitOfInformation,
)
from momapy.sbgn.af.model import ComplexUnitOfInformation as ComplexUnitOfInformation
from momapy.sbgn.af.model import (
    SimpleChemicalUnitOfInformation as SimpleChemicalUnitOfInformation,
)
from momapy.sbgn.af.model import (
    UnspecifiedEntityUnitOfInformation as UnspecifiedEntityUnitOfInformation,
)
from momapy.sbgn.af.model import (
    PerturbationUnitOfInformation as PerturbationUnitOfInformation,
)
from momapy.sbgn.af.model import Activity as Activity
from momapy.sbgn.af.model import BiologicalActivity as BiologicalActivity
from momapy.sbgn.af.model import Phenotype as Phenotype
from momapy.sbgn.af.model import LogicalOperatorInput as LogicalOperatorInput
from momapy.sbgn.af.model import LogicalOperator as LogicalOperator
from momapy.sbgn.af.model import OrOperator as OrOperator
from momapy.sbgn.af.model import AndOperator as AndOperator
from momapy.sbgn.af.model import NotOperator as NotOperator
from momapy.sbgn.af.model import DelayOperator as DelayOperator
from momapy.sbgn.af.model import Influence as Influence
from momapy.sbgn.af.model import UnknownInfluence as UnknownInfluence
from momapy.sbgn.af.model import PositiveInfluence as PositiveInfluence
from momapy.sbgn.af.model import NegativeInfluence as NegativeInfluence
from momapy.sbgn.af.model import NecessaryStimulation as NecessaryStimulation
from momapy.sbgn.af.model import TerminalReference as TerminalReference
from momapy.sbgn.af.model import TagReference as TagReference
from momapy.sbgn.af.model import Terminal as Terminal
from momapy.sbgn.af.model import Tag as Tag
from momapy.sbgn.af.model import Submap as Submap
from momapy.sbgn.af.model import SBGNAFModel as SBGNAFModel

from momapy.sbgn.af.layout import SBGNAFLayout as SBGNAFLayout
from momapy.sbgn.af.layout import UnitOfInformationLayout as UnitOfInformationLayout
from momapy.sbgn.af.layout import (
    UnspecifiedEntityUnitOfInformationLayout as UnspecifiedEntityUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import (
    SimpleChemicalUnitOfInformationLayout as SimpleChemicalUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import (
    MacromoleculeUnitOfInformationLayout as MacromoleculeUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import (
    NucleicAcidFeatureUnitOfInformationLayout as NucleicAcidFeatureUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import (
    ComplexUnitOfInformationLayout as ComplexUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import (
    PerturbationUnitOfInformationLayout as PerturbationUnitOfInformationLayout,
)
from momapy.sbgn.af.layout import TerminalLayout as TerminalLayout
from momapy.sbgn.af.layout import CompartmentLayout as CompartmentLayout
from momapy.sbgn.af.layout import SubmapLayout as SubmapLayout
from momapy.sbgn.af.layout import BiologicalActivityLayout as BiologicalActivityLayout
from momapy.sbgn.af.layout import PhenotypeLayout as PhenotypeLayout
from momapy.sbgn.af.layout import AndOperatorLayout as AndOperatorLayout
from momapy.sbgn.af.layout import OrOperatorLayout as OrOperatorLayout
from momapy.sbgn.af.layout import NotOperatorLayout as NotOperatorLayout
from momapy.sbgn.af.layout import DelayOperatorLayout as DelayOperatorLayout
from momapy.sbgn.af.layout import TagLayout as TagLayout
from momapy.sbgn.af.layout import UnknownInfluenceLayout as UnknownInfluenceLayout
from momapy.sbgn.af.layout import PositiveInfluenceLayout as PositiveInfluenceLayout
from momapy.sbgn.af.layout import (
    NecessaryStimulationLayout as NecessaryStimulationLayout,
)
from momapy.sbgn.af.layout import NegativeInfluenceLayout as NegativeInfluenceLayout
from momapy.sbgn.af.layout import LogicArcLayout as LogicArcLayout
from momapy.sbgn.af.layout import EquivalenceArcLayout as EquivalenceArcLayout

from momapy.sbgn.af.map import SBGNAFMap as SBGNAFMap

__all__ = [
    "DEFAULT_AUXILIARY_UNIT_FONT_SIZE",
    "DEFAULT_FONT_SIZE",
    "UnitOfInformation",
    "Compartment",
    "MacromoleculeUnitOfInformation",
    "NucleicAcidFeatureUnitOfInformation",
    "ComplexUnitOfInformation",
    "SimpleChemicalUnitOfInformation",
    "UnspecifiedEntityUnitOfInformation",
    "PerturbationUnitOfInformation",
    "Activity",
    "BiologicalActivity",
    "Phenotype",
    "LogicalOperatorInput",
    "LogicalOperator",
    "OrOperator",
    "AndOperator",
    "NotOperator",
    "DelayOperator",
    "Influence",
    "UnknownInfluence",
    "PositiveInfluence",
    "NegativeInfluence",
    "NecessaryStimulation",
    "TerminalReference",
    "TagReference",
    "Terminal",
    "Tag",
    "Submap",
    "SBGNAFModel",
    "SBGNAFLayout",
    "UnitOfInformationLayout",
    "UnspecifiedEntityUnitOfInformationLayout",
    "SimpleChemicalUnitOfInformationLayout",
    "MacromoleculeUnitOfInformationLayout",
    "NucleicAcidFeatureUnitOfInformationLayout",
    "ComplexUnitOfInformationLayout",
    "PerturbationUnitOfInformationLayout",
    "TerminalLayout",
    "CompartmentLayout",
    "SubmapLayout",
    "BiologicalActivityLayout",
    "PhenotypeLayout",
    "AndOperatorLayout",
    "OrOperatorLayout",
    "NotOperatorLayout",
    "DelayOperatorLayout",
    "TagLayout",
    "UnknownInfluenceLayout",
    "PositiveInfluenceLayout",
    "NecessaryStimulationLayout",
    "NegativeInfluenceLayout",
    "LogicArcLayout",
    "EquivalenceArcLayout",
    "SBGNAFMap",
]
