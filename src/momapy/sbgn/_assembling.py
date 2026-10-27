"""Internal collection tables and cluster rules to assemble SBGN maps."""

from momapy.core._assembling import ClusterRule
from momapy.sbgn.af.layout import EquivalenceArcLayout as AFEquivalenceArcLayout
from momapy.sbgn.af.layout import LogicArcLayout as AFLogicArcLayout
from momapy.sbgn.af.model import Activity
from momapy.sbgn.af.model import Compartment as AFCompartment
from momapy.sbgn.af.model import Influence
from momapy.sbgn.af.model import LogicalOperator as AFLogicalOperator
from momapy.sbgn.af.model import LogicalOperatorInput as AFLogicalOperatorInput
from momapy.sbgn.af.model import Submap as AFSubmap
from momapy.sbgn.af.model import Tag as AFTag
from momapy.sbgn.af.model import TagReference as AFTagReference
from momapy.sbgn.af.model import Terminal as AFTerminal
from momapy.sbgn.af.model import TerminalReference as AFTerminalReference
from momapy.sbgn.pd.layout import ConsumptionLayout
from momapy.sbgn.pd.layout import EquivalenceArcLayout as PDEquivalenceArcLayout
from momapy.sbgn.pd.layout import LogicArcLayout as PDLogicArcLayout
from momapy.sbgn.pd.layout import ProductionLayout
from momapy.sbgn.pd.model import Compartment as PDCompartment
from momapy.sbgn.pd.model import EntityPool
from momapy.sbgn.pd.model import EquivalenceOperator
from momapy.sbgn.pd.model import LogicalOperator as PDLogicalOperator
from momapy.sbgn.pd.model import LogicalOperatorInput as PDLogicalOperatorInput
from momapy.sbgn.pd.model import Modulation
from momapy.sbgn.pd.model import Process
from momapy.sbgn.pd.model import Product
from momapy.sbgn.pd.model import Reactant
from momapy.sbgn.pd.model import StoichiometricProcess
from momapy.sbgn.pd.model import Submap as PDSubmap
from momapy.sbgn.pd.model import Tag as PDTag
from momapy.sbgn.pd.model import TagReference as PDTagReference
from momapy.sbgn.pd.model import Terminal as PDTerminal
from momapy.sbgn.pd.model import TerminalReference as PDTerminalReference

PD_COLLECTION_TABLE = {
    EntityPool: "entity_pools",
    PDCompartment: "compartments",
    Process: "processes",
    Modulation: "modulations",
    PDLogicalOperator: "logical_operators",
    EquivalenceOperator: "equivalence_operators",
    PDSubmap: "submaps",
    PDTag: "tags",
}

PD_CLUSTER_RULES = (
    ClusterRule(
        model_element_classes=(PDLogicalOperator,),
        arc_classes=((PDLogicArcLayout, (PDLogicalOperatorInput,)),),
    ),
    ClusterRule(
        model_element_classes=(StoichiometricProcess,),
        arc_classes=(
            (ConsumptionLayout, (Reactant,)),
            (ProductionLayout, (Product,)),
        ),
        reversible_arc_classes=((ProductionLayout, (Reactant,)),),
    ),
    ClusterRule(
        model_element_classes=(PDTag, PDTerminal),
        arc_classes=((PDEquivalenceArcLayout, (PDTagReference, PDTerminalReference)),),
        cluster_arc_targets=True,
        single_key_without_arcs=True,
    ),
    ClusterRule(model_element_classes=(Modulation,), with_ends=True),
    ClusterRule(model_element_classes=(EquivalenceOperator,), not_implemented=True),
)

AF_COLLECTION_TABLE = {
    Activity: "activities",
    AFCompartment: "compartments",
    Influence: "influences",
    AFLogicalOperator: "logical_operators",
    AFSubmap: "submaps",
    AFTag: "tags",
}

AF_CLUSTER_RULES = (
    ClusterRule(
        model_element_classes=(AFLogicalOperator,),
        arc_classes=((AFLogicArcLayout, (AFLogicalOperatorInput,)),),
    ),
    ClusterRule(
        model_element_classes=(AFTag, AFTerminal),
        arc_classes=((AFEquivalenceArcLayout, (AFTagReference, AFTerminalReference)),),
        cluster_arc_targets=True,
        single_key_without_arcs=True,
    ),
    ClusterRule(model_element_classes=(Influence,), with_ends=True),
)
