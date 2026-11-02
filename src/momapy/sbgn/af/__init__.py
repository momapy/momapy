"""Classes for SBGN Activity Flow (AF) maps.

Layout-model mapping catalogue
------------------------------

The table below lists, for each model element category in SBGN-AF, the
layout elements of its key in
[LayoutModelMapping][momapy.core.LayoutModelMapping].

| Model element | Key | Representative |
|---|---|---|
| [Compartment][momapy.sbgn.af.Compartment] | The [CompartmentLayout][momapy.sbgn.af.CompartmentLayout] | The [CompartmentLayout][momapy.sbgn.af.CompartmentLayout] |
| [Activity][momapy.sbgn.af.Activity] and subclasses | The `*Layout` (e.g. [BiologicalActivityLayout][momapy.sbgn.af.BiologicalActivityLayout]) + the key of its container, if it draws the compartment of the activity | The `*Layout` |
| [UnitOfInformation][momapy.sbgn.af.UnitOfInformation] and subclasses | The `*Layout` (e.g. [MacromoleculeUnitOfInformationLayout][momapy.sbgn.af.MacromoleculeUnitOfInformationLayout]) | The `*Layout` |
| [Submap][momapy.sbgn.af.Submap] | The [SubmapLayout][momapy.sbgn.af.SubmapLayout] | The [SubmapLayout][momapy.sbgn.af.SubmapLayout] |
| [LogicalOperator][momapy.sbgn.af.LogicalOperator] and subclasses | The `*Layout` (e.g. [AndOperatorLayout][momapy.sbgn.af.AndOperatorLayout]) + the keys of every [LogicArcLayout][momapy.sbgn.af.LogicArcLayout] whose source is the `*Layout` | The `*Layout` |
| [Influence][momapy.sbgn.af.Influence] and subclasses | The `*Layout` (e.g. [PositiveInfluenceLayout][momapy.sbgn.af.PositiveInfluenceLayout]) + the key of its source layout element + the key of its target layout element | The `*Layout` |
| [Tag][momapy.sbgn.af.Tag], [Terminal][momapy.sbgn.af.Terminal] | The [TagLayout][momapy.sbgn.af.TagLayout] or [TerminalLayout][momapy.sbgn.af.TerminalLayout] + the keys of every [EquivalenceArcLayout][momapy.sbgn.af.EquivalenceArcLayout] whose source is the [TagLayout][momapy.sbgn.af.TagLayout] or [TerminalLayout][momapy.sbgn.af.TerminalLayout] | The [TagLayout][momapy.sbgn.af.TagLayout] or [TerminalLayout][momapy.sbgn.af.TerminalLayout] |
| [LogicalOperatorInput][momapy.sbgn.af.LogicalOperatorInput] | The [LogicArcLayout][momapy.sbgn.af.LogicArcLayout] + the key of its target layout element | The [LogicArcLayout][momapy.sbgn.af.LogicArcLayout] |
| [TagReference][momapy.sbgn.af.TagReference], [TerminalReference][momapy.sbgn.af.TerminalReference] | The [EquivalenceArcLayout][momapy.sbgn.af.EquivalenceArcLayout] + the key of its target layout element | The [EquivalenceArcLayout][momapy.sbgn.af.EquivalenceArcLayout] |
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
