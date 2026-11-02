"""Tests for building, taking apart and merging maps from map elements."""

import dataclasses
import glob
import inspect
import os
import subprocess
import sys
import typing

import pytest

from momapy.core import get_layout_model_pairs
from momapy.core import make_map
from momapy.core import merge_maps
from momapy.core._assembling import check_equal_layout_elements
from momapy.core.elements import is_reference_field
from momapy.core.elements import ModelElement
from momapy.io._utils import ReadingContext
from momapy.io._utils import add_child_model_element
from momapy.io._utils import add_top_level_model_element
from momapy.io._utils import merge_read_model_elements
from momapy.sbgn.elements import SBGNRole
import momapy.celldesigner.model
import momapy.sbgn.af.model
import momapy.sbgn.elements
import momapy.sbgn.pd.model
import momapy.sbml.model
import momapy.builder
import momapy.geometry
import momapy.io.core
import momapy.sbgn.af
import momapy.sbgn.pd
import momapy.sbgn.utils
import momapy.sbml.map

MODEL_MODULES = [
    momapy.sbml.model,
    momapy.sbgn.elements,
    momapy.sbgn.pd.model,
    momapy.sbgn.af.model,
    momapy.celldesigner.model,
]

EXPECTED_MODEL_ELEMENT_FIELDS = {
    "momapy.sbml.model.Compartment": {"outside": True},
    "momapy.sbml.model.Species": {"compartment": True},
    "momapy.sbml.model.SimpleSpeciesReference": {"referred_element": True},
    "momapy.sbml.model.ModifierSpeciesReference": {"referred_element": True},
    "momapy.sbml.model.SpeciesReference": {"referred_element": True},
    "momapy.sbml.model.Reaction": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.sbgn.elements.SBGNRole": {"referred_element": True},
    "momapy.sbgn.pd.model.MacromoleculeSubunit": {
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.NucleicAcidFeatureSubunit": {
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.SimpleChemicalSubunit": {
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.ComplexSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.MultimerSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.MacromoleculeMultimerSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.NucleicAcidFeatureMultimerSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.SimpleChemicalMultimerSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.ComplexMultimerSubunit": {
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.Compartment": {"units_of_information": False},
    "momapy.sbgn.pd.model.EntityPool": {"compartment": True},
    "momapy.sbgn.pd.model.PerturbingAgent": {"compartment": True},
    "momapy.sbgn.pd.model.UnspecifiedEntity": {"compartment": True},
    "momapy.sbgn.pd.model.Macromolecule": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.NucleicAcidFeature": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.SimpleChemical": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
    },
    "momapy.sbgn.pd.model.Complex": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.Multimer": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.MacromoleculeMultimer": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.NucleicAcidFeatureMultimer": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.SimpleChemicalMultimer": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.ComplexMultimer": {
        "compartment": True,
        "state_variables": False,
        "units_of_information": False,
        "subunits": False,
    },
    "momapy.sbgn.pd.model.FluxRole": {"referred_element": True},
    "momapy.sbgn.pd.model.Reactant": {"referred_element": True},
    "momapy.sbgn.pd.model.Product": {"referred_element": True},
    "momapy.sbgn.pd.model.LogicalOperatorInput": {"referred_element": True},
    "momapy.sbgn.pd.model.EquivalenceOperatorInput": {"referred_element": True},
    "momapy.sbgn.pd.model.EquivalenceOperatorOutput": {"referred_element": True},
    "momapy.sbgn.pd.model.StoichiometricProcess": {
        "reactants": False,
        "products": False,
    },
    "momapy.sbgn.pd.model.GenericProcess": {"reactants": False, "products": False},
    "momapy.sbgn.pd.model.UncertainProcess": {"reactants": False, "products": False},
    "momapy.sbgn.pd.model.Association": {"reactants": False, "products": False},
    "momapy.sbgn.pd.model.Dissociation": {"reactants": False, "products": False},
    "momapy.sbgn.pd.model.OmittedProcess": {"reactants": False, "products": False},
    "momapy.sbgn.pd.model.LogicalOperator": {"inputs": False},
    "momapy.sbgn.pd.model.OrOperator": {"inputs": False},
    "momapy.sbgn.pd.model.AndOperator": {"inputs": False},
    "momapy.sbgn.pd.model.NotOperator": {"inputs": False},
    "momapy.sbgn.pd.model.EquivalenceOperator": {"inputs": False, "output": False},
    "momapy.sbgn.pd.model.Modulation": {"source": True, "target": True},
    "momapy.sbgn.pd.model.Inhibition": {"source": True, "target": True},
    "momapy.sbgn.pd.model.Stimulation": {"source": True, "target": True},
    "momapy.sbgn.pd.model.Catalysis": {"source": True, "target": True},
    "momapy.sbgn.pd.model.NecessaryStimulation": {"source": True, "target": True},
    "momapy.sbgn.pd.model.TagReference": {"referred_element": True},
    "momapy.sbgn.pd.model.Tag": {"referred_element": False},
    "momapy.sbgn.pd.model.TerminalReference": {"referred_element": True},
    "momapy.sbgn.pd.model.Terminal": {"referred_element": False},
    "momapy.sbgn.pd.model.Submap": {"terminals": False},
    "momapy.sbgn.af.model.Compartment": {"units_of_information": False},
    "momapy.sbgn.af.model.Activity": {"compartment": True},
    "momapy.sbgn.af.model.BiologicalActivity": {
        "compartment": True,
        "units_of_information": False,
    },
    "momapy.sbgn.af.model.Phenotype": {"compartment": True},
    "momapy.sbgn.af.model.LogicalOperatorInput": {"referred_element": True},
    "momapy.sbgn.af.model.LogicalOperator": {"inputs": False},
    "momapy.sbgn.af.model.OrOperator": {"inputs": False},
    "momapy.sbgn.af.model.AndOperator": {"inputs": False},
    "momapy.sbgn.af.model.NotOperator": {"inputs": False},
    "momapy.sbgn.af.model.DelayOperator": {"inputs": False},
    "momapy.sbgn.af.model.Influence": {"source": True, "target": True},
    "momapy.sbgn.af.model.UnknownInfluence": {"source": True, "target": True},
    "momapy.sbgn.af.model.PositiveInfluence": {"source": True, "target": True},
    "momapy.sbgn.af.model.NegativeInfluence": {"source": True, "target": True},
    "momapy.sbgn.af.model.NecessaryStimulation": {"source": True, "target": True},
    "momapy.sbgn.af.model.TerminalReference": {"referred_element": True},
    "momapy.sbgn.af.model.TagReference": {"referred_element": True},
    "momapy.sbgn.af.model.Terminal": {"referred_element": False},
    "momapy.sbgn.af.model.Tag": {"referred_element": False},
    "momapy.sbgn.af.model.Submap": {"terminals": False},
    "momapy.celldesigner.model.ProteinTemplate": {"modification_residues": False},
    "momapy.celldesigner.model.GenericProteinTemplate": {
        "modification_residues": False
    },
    "momapy.celldesigner.model.TruncatedProteinTemplate": {
        "modification_residues": False
    },
    "momapy.celldesigner.model.ReceptorTemplate": {"modification_residues": False},
    "momapy.celldesigner.model.IonChannelTemplate": {"modification_residues": False},
    "momapy.celldesigner.model.GeneTemplate": {"regions": False},
    "momapy.celldesigner.model.RNATemplate": {"regions": False},
    "momapy.celldesigner.model.AntisenseRNATemplate": {"regions": False},
    "momapy.celldesigner.model.Modification": {"residue": True},
    "momapy.celldesigner.model.Compartment": {"outside": True},
    "momapy.celldesigner.model.Species": {"compartment": True},
    "momapy.celldesigner.model.Protein": {
        "compartment": True,
        "template": True,
        "modifications": False,
        "structural_states": False,
    },
    "momapy.celldesigner.model.GenericProtein": {
        "compartment": True,
        "template": True,
        "modifications": False,
        "structural_states": False,
    },
    "momapy.celldesigner.model.TruncatedProtein": {
        "compartment": True,
        "template": True,
        "modifications": False,
        "structural_states": False,
    },
    "momapy.celldesigner.model.Receptor": {
        "compartment": True,
        "template": True,
        "modifications": False,
        "structural_states": False,
    },
    "momapy.celldesigner.model.IonChannel": {
        "compartment": True,
        "template": True,
        "modifications": False,
        "structural_states": False,
    },
    "momapy.celldesigner.model.Gene": {
        "compartment": True,
        "template": True,
        "modifications": False,
    },
    "momapy.celldesigner.model.RNA": {
        "compartment": True,
        "template": True,
        "modifications": False,
    },
    "momapy.celldesigner.model.AntisenseRNA": {
        "compartment": True,
        "template": True,
        "modifications": False,
    },
    "momapy.celldesigner.model.Phenotype": {"compartment": True},
    "momapy.celldesigner.model.Ion": {"compartment": True},
    "momapy.celldesigner.model.SimpleMolecule": {"compartment": True},
    "momapy.celldesigner.model.Drug": {"compartment": True},
    "momapy.celldesigner.model.Unknown": {"compartment": True},
    "momapy.celldesigner.model.Complex": {
        "compartment": True,
        "structural_states": False,
        "subunits": False,
    },
    "momapy.celldesigner.model.Reactant": {"referred_element": True},
    "momapy.celldesigner.model.Product": {"referred_element": True},
    "momapy.celldesigner.model.BooleanLogicGateInput": {"referred_element": True},
    "momapy.celldesigner.model.BooleanLogicGate": {"inputs": False},
    "momapy.celldesigner.model.AndGate": {"inputs": False},
    "momapy.celldesigner.model.OrGate": {"inputs": False},
    "momapy.celldesigner.model.NotGate": {"inputs": False},
    "momapy.celldesigner.model.UnknownGate": {"inputs": False},
    "momapy.celldesigner.model.KnownOrUnknownModulator": {"referred_element": True},
    "momapy.celldesigner.model.Modulator": {"referred_element": True},
    "momapy.celldesigner.model.UnknownModulator": {"referred_element": True},
    "momapy.celldesigner.model.Inhibitor": {"referred_element": True},
    "momapy.celldesigner.model.PhysicalStimulator": {"referred_element": True},
    "momapy.celldesigner.model.Catalyzer": {"referred_element": True},
    "momapy.celldesigner.model.Trigger": {"referred_element": True},
    "momapy.celldesigner.model.UnknownCatalyzer": {"referred_element": True},
    "momapy.celldesigner.model.UnknownInhibitor": {"referred_element": True},
    "momapy.celldesigner.model.Reaction": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.StateTransition": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.KnownTransitionOmitted": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.UnknownTransition": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.Transcription": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.Translation": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.Transport": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.HeterodimerAssociation": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.Dissociation": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.Truncation": {
        "compartment": True,
        "reactants": False,
        "products": False,
        "modifiers": False,
    },
    "momapy.celldesigner.model.KnownOrUnknownModulation": {
        "source": True,
        "target": True,
    },
    "momapy.celldesigner.model.Modulation": {"source": True, "target": True},
    "momapy.celldesigner.model.Inhibition": {"source": True, "target": True},
    "momapy.celldesigner.model.PhysicalStimulation": {"source": True, "target": True},
    "momapy.celldesigner.model.Catalysis": {"source": True, "target": True},
    "momapy.celldesigner.model.Triggering": {"source": True, "target": True},
    "momapy.celldesigner.model.PositiveInfluence": {"source": True, "target": True},
    "momapy.celldesigner.model.NegativeInfluence": {"source": True, "target": True},
    "momapy.celldesigner.model.UnknownModulation": {"source": True, "target": True},
    "momapy.celldesigner.model.UnknownInhibition": {"source": True, "target": True},
    "momapy.celldesigner.model.UnknownPositiveInfluence": {
        "source": True,
        "target": True,
    },
    "momapy.celldesigner.model.UnknownNegativeInfluence": {
        "source": True,
        "target": True,
    },
    "momapy.celldesigner.model.UnknownPhysicalStimulation": {
        "source": True,
        "target": True,
    },
    "momapy.celldesigner.model.UnknownCatalysis": {"source": True, "target": True},
    "momapy.celldesigner.model.UnknownTriggering": {"source": True, "target": True},
}


def holds_model_elements(type_hint: typing.Any) -> bool:
    if inspect.isclass(type_hint) and issubclass(type_hint, ModelElement):
        return True
    return any(
        holds_model_elements(argument) for argument in typing.get_args(type_hint)
    )


def get_model_element_fields() -> dict[str, dict[str, bool]]:
    model_element_fields = {}
    for module in MODEL_MODULES:
        for class_name, cls in vars(module).items():
            if not inspect.isclass(cls) or not issubclass(cls, ModelElement):
                continue
            if cls.__module__ != module.__name__:
                continue
            type_hints = typing.get_type_hints(cls)
            fields = {
                field.name: is_reference_field(cls, field.name)
                for field in dataclasses.fields(cls)
                if holds_model_elements(type_hints[field.name])
            }
            if fields:
                model_element_fields[f"{module.__name__}.{class_name}"] = fields
    return model_element_fields


class TestIsReferenceField:
    def test_model_element_fields(self):
        assert get_model_element_fields() == EXPECTED_MODEL_ELEMENT_FIELDS

    def test_redeclared_field_in_user_subclass(self):
        @dataclasses.dataclass(frozen=True, kw_only=True)
        class MyRole(SBGNRole):
            referred_element: momapy.sbgn.pd.model.EntityPool = dataclasses.field()

        assert is_reference_field(MyRole, "referred_element")

    @pytest.mark.parametrize(
        "cls, field_name",
        [
            (momapy.sbgn.pd.model.Macromolecule, "state_variables"),
            (momapy.sbgn.pd.model.Tag, "referred_element"),
            (momapy.sbgn.pd.model.EquivalenceOperator, "output"),
            (momapy.sbgn.pd.model.Macromolecule, "label"),
            (momapy.sbgn.pd.model.Macromolecule, "not_a_field"),
        ],
    )
    def test_not_reference_field(self, cls, field_name):
        assert not is_reference_field(cls, field_name)


# ---------------------------------------------------------------------------
# Building, taking apart and merging maps from map elements
# ---------------------------------------------------------------------------

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SBGN_MAP_PATHS = sorted(
    glob.glob(os.path.join(TEST_DIR, "sbgn", "maps", "*", "*.sbgn"))
)
CELLDESIGNER_MAP_PATHS = sorted(
    glob.glob(os.path.join(TEST_DIR, "celldesigner", "maps", "*.xml"))
    + glob.glob(os.path.join(TEST_DIR, "celldesigner", "fixtures", "*.xml"))
)


def make_glyph(x, y=0.0, cls=momapy.sbgn.pd.MacromoleculeLayout, layout_elements=()):
    return cls(
        position=momapy.geometry.Point(x, y),
        width=60.0,
        height=30.0,
        layout_elements=tuple(layout_elements),
    )


def make_process_glyph(x, y=0.0):
    return momapy.sbgn.pd.GenericProcessLayout(
        position=momapy.geometry.Point(x, y), width=20.0, height=20.0
    )


def make_arc(cls, source, target):
    return cls(
        source=source,
        target=target,
        segments=(momapy.geometry.Segment(source.position, target.position),),
    )


def make_process_map_elements():
    """Return the elements of `a -> b` catalysed by `enzyme`."""
    a = momapy.sbgn.pd.Macromolecule(label="A")
    b = momapy.sbgn.pd.Macromolecule(label="B")
    enzyme = momapy.sbgn.pd.Macromolecule(label="E")
    reactant = momapy.sbgn.pd.Reactant(referred_element=a)
    product = momapy.sbgn.pd.Product(referred_element=b)
    process = momapy.sbgn.pd.GenericProcess(
        reactants=frozenset([reactant]), products=frozenset([product])
    )
    catalysis = momapy.sbgn.pd.Catalysis(source=enzyme, target=process)
    a_glyph = make_glyph(0.0)
    b_glyph = make_glyph(200.0)
    enzyme_glyph = make_glyph(100.0, 100.0)
    process_glyph = make_process_glyph(100.0)
    consumption_arc = make_arc(momapy.sbgn.pd.ConsumptionLayout, process_glyph, a_glyph)
    production_arc = make_arc(momapy.sbgn.pd.ProductionLayout, process_glyph, b_glyph)
    catalysis_arc = make_arc(
        momapy.sbgn.pd.CatalysisLayout, enzyme_glyph, process_glyph
    )
    return {
        "model_elements": [a, b, enzyme, process, catalysis],
        "layout_elements": [
            a_glyph,
            b_glyph,
            enzyme_glyph,
            process_glyph,
            consumption_arc,
            production_arc,
            catalysis_arc,
        ],
        "layout_model_pairs": [
            (a_glyph, a),
            (b_glyph, b),
            (enzyme_glyph, enzyme),
            (process_glyph, process),
            (consumption_arc, reactant),
            (production_arc, product),
            (catalysis_arc, catalysis),
        ],
    }


def make_complex(label, subunit_label):
    subunit = momapy.sbgn.pd.MacromoleculeSubunit(label=subunit_label)
    return momapy.sbgn.pd.Complex(label=label, subunits=frozenset([subunit])), subunit


class TestMapElementMethods:
    def test_model_element(self):
        state_variable = momapy.sbgn.pd.StateVariable(value="P")
        compartment = momapy.sbgn.pd.Compartment(label="cell")
        a = momapy.sbgn.pd.Macromolecule(
            label="A",
            state_variables=frozenset([state_variable]),
            compartment=compartment,
        )
        reactant = momapy.sbgn.pd.Reactant(referred_element=a)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        assert a.children() == [state_variable]
        assert a.descendants() == [state_variable]
        assert a.references() == [compartment]
        assert process.children() == [reactant]
        assert process.descendants() == [reactant]
        assert process.references() == []
        assert reactant.references() == [a]

    def test_model(self):
        a = momapy.sbgn.pd.Macromolecule(label="A")
        reactant = momapy.sbgn.pd.Reactant(referred_element=a)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        model = momapy.sbgn.pd.SBGNPDModel(
            entity_pools=frozenset([a]), processes=frozenset([process])
        )
        assert set(map(id, model.children())) == {id(a), id(process)}
        assert set(map(id, model.descendants())) == {id(a), id(process), id(reactant)}

    def test_arc_references(self):
        map_elements = make_process_map_elements()
        a_glyph = map_elements["layout_elements"][0]
        process_glyph = map_elements["layout_elements"][3]
        consumption_arc = map_elements["layout_elements"][4]
        assert consumption_arc.references() == [process_glyph, a_glyph]
        assert a_glyph.references() == []
        compartment_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.CompartmentLayout)
        contained_glyph = dataclasses.replace(a_glyph, container=compartment_glyph)
        assert contained_glyph.references() == [compartment_glyph]


class TestMakeMap:
    @pytest.mark.parametrize("path", SBGN_MAP_PATHS, ids=os.path.basename)
    def test_rebuild_read_map(self, path):
        map_ = momapy.io.core.read(path).obj
        rebuilt_map = make_map(
            type(map_),
            map_.model.children(),
            map_.layout.children(),
            get_layout_model_pairs(map_.layout_model_mapping),
        )
        assert rebuilt_map.model == map_.model
        assert rebuilt_map.layout.layout_elements == map_.layout.layout_elements
        assert dict(rebuilt_map.layout_model_mapping) == dict(map_.layout_model_mapping)
        assert dict(rebuilt_map.layout_model_mapping.representative_to_key) == dict(
            map_.layout_model_mapping.representative_to_key
        )
        model_element_ids = {id(element) for element in rebuilt_map.model.descendants()}
        for model_element in rebuilt_map.layout_model_mapping.values():
            assert id(model_element) in model_element_ids
        layout_element_ids = {
            id(element) for element in rebuilt_map.layout.descendants()
        }
        for layout_element in rebuilt_map.layout.descendants():
            for reference in layout_element.references():
                assert id(reference) in layout_element_ids

    @pytest.mark.parametrize("path", CELLDESIGNER_MAP_PATHS, ids=os.path.basename)
    def test_rebuild_read_celldesigner_map(self, path):
        map_ = momapy.io.core.read(path).obj
        rebuilt_map = make_map(
            type(map_),
            map_.model.children(),
            map_.layout.children(),
            get_layout_model_pairs(map_.layout_model_mapping),
        )
        assert rebuilt_map.model == map_.model
        assert rebuilt_map.layout.layout_elements == map_.layout.layout_elements
        mapping = map_.layout_model_mapping
        rebuilt_mapping = rebuilt_map.layout_model_mapping
        assert len(rebuilt_mapping) == len(mapping)
        for key, model_element in mapping.items():
            if key in rebuilt_mapping:
                assert rebuilt_mapping[key] == model_element
            else:
                # The reader gives an arc that draws a child a single key.
                rebuilt_key = rebuilt_mapping.representative_to_key[key]
                assert key in rebuilt_key
                assert rebuilt_mapping[rebuilt_key] == model_element
        model_element_ids = {id(element) for element in rebuilt_map.model.descendants()}
        for model_element in rebuilt_mapping.values():
            assert id(model_element) in model_element_ids
        layout_element_ids = {
            id(element) for element in rebuilt_map.layout.descendants()
        }
        for layout_element in rebuilt_map.layout.descendants():
            for reference in layout_element.references():
                assert id(reference) in layout_element_ids

    def test_keys(self):
        map_elements = make_process_map_elements()
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, **map_elements)
        (
            a_glyph,
            b_glyph,
            enzyme_glyph,
            process_glyph,
            consumption_arc,
            production_arc,
            catalysis_arc,
        ) = map_elements["layout_elements"]
        mapping = map_.layout_model_mapping
        process_key = frozenset(
            [process_glyph, consumption_arc, production_arc, a_glyph, b_glyph]
        )
        assert mapping.representative_to_key[process_glyph] == process_key
        assert mapping.representative_to_key[catalysis_arc] == process_key | {
            catalysis_arc,
            enzyme_glyph,
        }
        assert mapping.representative_to_key[consumption_arc] == frozenset(
            [consumption_arc, a_glyph]
        )
        assert mapping[a_glyph] is next(
            model_element
            for model_element in map_.model.entity_pools
            if model_element.label == "A"
        )
        assert mapping.get_representative_layout_elements(
            mapping[mapping.representative_to_key[catalysis_arc]]
        ) == [catalysis_arc]

    def test_empty_set_in_process_key(self):
        b = momapy.sbgn.pd.Macromolecule(label="B")
        product = momapy.sbgn.pd.Product(referred_element=b)
        process = momapy.sbgn.pd.GenericProcess(
            products=frozenset([product]), has_external_source=True
        )
        empty_set_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.EmptySetLayout)
        b_glyph = make_glyph(200.0)
        process_glyph = make_process_glyph(100.0)
        empty_set_arc = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_glyph, empty_set_glyph
        )
        production_arc = make_arc(
            momapy.sbgn.pd.ProductionLayout, process_glyph, b_glyph
        )
        layout_elements = [
            empty_set_glyph,
            b_glyph,
            process_glyph,
            empty_set_arc,
            production_arc,
        ]
        map_ = make_map(
            momapy.sbgn.pd.SBGNPDMap,
            [b, process],
            layout_elements,
            [(b_glyph, b), (process_glyph, process), (production_arc, product)],
        )
        mapping = map_.layout_model_mapping
        assert mapping.representative_to_key[process_glyph] == frozenset(
            layout_elements
        )
        assert empty_set_glyph not in mapping
        assert empty_set_arc not in mapping

    @pytest.mark.parametrize("reverse", [False, True])
    def test_kept_element_has_smallest_id(self, reverse):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="b")
        atp_copy = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        model_elements = [atp, atp_copy]
        if reverse:
            model_elements.reverse()
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, model_elements)
        assert list(map_.model.entity_pools) == [atp_copy]
        assert next(iter(map_.model.entity_pools)) is atp_copy

    def test_kept_element_on_equal_ids_is_first(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        atp_copy = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, [atp_copy, atp])
        assert next(iter(map_.model.entity_pools)) is atp_copy

    def test_references_point_to_kept_element(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        atp_copy = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="b")
        reactant = momapy.sbgn.pd.Reactant(referred_element=atp_copy)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        process_glyph = make_process_glyph(100.0)
        atp_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        consumption_arc = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_glyph, atp_glyph
        )
        map_ = make_map(
            momapy.sbgn.pd.SBGNPDMap,
            [atp, atp_copy, process],
            [atp_glyph, process_glyph, consumption_arc],
            [
                (atp_glyph, atp_copy),
                (process_glyph, process),
                (consumption_arc, reactant),
            ],
        )
        kept_process = next(iter(map_.model.processes))
        kept_reactant = next(iter(kept_process.reactants))
        assert map_.model.entity_pools == frozenset([atp])
        assert kept_reactant.referred_element is atp
        assert map_.layout_model_mapping[atp_glyph] is atp
        assert map_.layout_model_mapping.get_mapping(consumption_arc) is kept_reactant

    def test_reference_to_equal_element_not_given(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP")
        reactant = momapy.sbgn.pd.Reactant(
            referred_element=dataclasses.replace(atp, id_="copy")
        )
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, [atp, process])
        kept_process = next(iter(map_.model.processes))
        assert next(iter(kept_process.reactants)).referred_element is atp

    def test_equal_descendants_of_different_owners_stay_two(self):
        a_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        b_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        a = momapy.sbgn.pd.Macromolecule(
            label="A", state_variables=frozenset([a_state_variable])
        )
        b = momapy.sbgn.pd.Macromolecule(
            label="B", state_variables=frozenset([b_state_variable])
        )
        a_state_variable_glyph = make_glyph(
            0.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        b_state_variable_glyph = make_glyph(
            200.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        a_glyph = make_glyph(0.0, layout_elements=[a_state_variable_glyph])
        b_glyph = make_glyph(200.0, layout_elements=[b_state_variable_glyph])
        map_ = make_map(
            momapy.sbgn.pd.SBGNPDMap,
            [a, b],
            [a_glyph, b_glyph],
            [
                (a_glyph, a),
                (b_glyph, b),
                (a_state_variable_glyph, a_state_variable),
                (b_state_variable_glyph, b_state_variable),
            ],
        )
        mapping = map_.layout_model_mapping
        assert mapping[a_state_variable_glyph] is a_state_variable
        assert mapping[b_state_variable_glyph] is b_state_variable

    def test_equal_glyphs_become_one(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP")
        atp_glyph = dataclasses.replace(
            make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout), id_="b"
        )
        atp_glyph_copy = dataclasses.replace(atp_glyph, id_="a")
        map_ = make_map(
            momapy.sbgn.pd.SBGNPDMap,
            [atp],
            [atp_glyph, atp_glyph_copy],
            [(atp_glyph, atp), (atp_glyph_copy, atp)],
        )
        assert map_.layout.layout_elements == (atp_glyph_copy,)
        assert map_.layout.layout_elements[0] is atp_glyph_copy
        assert map_.layout_model_mapping.get_representative_layout_elements(atp) == [
            atp_glyph_copy
        ]

    def test_arc_to_equal_glyph_is_rebuilt(self):
        map_elements = make_process_map_elements()
        a_glyph = map_elements["layout_elements"][0]
        consumption_arc = map_elements["layout_elements"][4]
        a_glyph_copy = dataclasses.replace(a_glyph, id_="copy")
        new_consumption_arc = dataclasses.replace(consumption_arc, target=a_glyph_copy)
        map_elements["layout_elements"][4] = new_consumption_arc
        map_elements["layout_model_pairs"][4] = (
            new_consumption_arc,
            map_elements["layout_model_pairs"][4][1],
        )
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, **map_elements)
        kept_consumption_arc = map_.layout.layout_elements[4]
        assert kept_consumption_arc == new_consumption_arc
        assert kept_consumption_arc.target is map_.layout.layout_elements[0]

    def test_complex_with_container(self):
        compartment = momapy.sbgn.pd.Compartment(label="cell")
        complex_, _ = make_complex("C", "S")
        complex_ = dataclasses.replace(complex_, compartment=compartment)
        subunit = next(iter(complex_.subunits))
        compartment_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.CompartmentLayout)
        subunit_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.MacromoleculeSubunitLayout)
        complex_glyph = make_glyph(
            0.0, cls=momapy.sbgn.pd.ComplexLayout, layout_elements=[subunit_glyph]
        )
        complex_glyph = dataclasses.replace(complex_glyph, container=compartment_glyph)
        map_ = make_map(
            momapy.sbgn.pd.SBGNPDMap,
            [compartment, complex_],
            [compartment_glyph, complex_glyph],
            [
                (compartment_glyph, compartment),
                (complex_glyph, complex_),
                (subunit_glyph, subunit),
            ],
        )
        mapping = map_.layout_model_mapping
        assert mapping.representative_to_key[complex_glyph] == frozenset(
            [complex_glyph, compartment_glyph]
        )
        assert compartment_glyph in mapping
        assert mapping.get_child_layout_elements(subunit, complex_) == [subunit_glyph]
        map_builder = momapy.builder.builder_from_object(map_)
        mapping_builder = map_builder.layout_model_mapping
        complex_builder = next(iter(map_builder.model.entity_pools))
        subunit_builder = next(iter(complex_builder.subunits))
        assert (
            len(
                mapping_builder.get_child_layout_elements(
                    subunit_builder, complex_builder
                )
            )
            == 1
        )

    def test_no_layout(self):
        map_elements = make_process_map_elements()
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, map_elements["model_elements"])
        assert len(map_.model.entity_pools) == 3
        assert map_.layout is None
        assert map_.layout_model_mapping is None

    def test_sbml_map(self):
        compartment = momapy.sbml.model.Compartment(id_="c")
        species = momapy.sbml.model.Species(id_="s", compartment=compartment)
        map_ = make_map(momapy.sbml.map.SBMLMap, [compartment, species])
        assert map_.model.species == frozenset([species])
        assert map_.layout is None
        assert map_.layout_model_mapping is None

    def test_nothing_given(self):
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap)
        assert map_.model is None
        assert map_.layout is None
        assert map_.layout_model_mapping is None

    def test_set_arcs_to_borders_with_frozenset_production_key(self):
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, **make_process_map_elements())
        production_arc = map_.layout.layout_elements[5]
        assert production_arc not in map_.layout_model_mapping
        map_builder = momapy.builder.builder_from_object(map_)
        momapy.sbgn.utils.set_arcs_to_borders(map_builder)
        production_arc_builder = map_builder.layout.layout_elements[5]
        process_glyph = map_.layout.layout_elements[3]
        if process_glyph.left_to_right:
            expected_point = process_glyph.right_connector_tip()
        else:
            expected_point = process_glyph.left_connector_tip()
        assert (
            momapy.builder.object_from_builder(production_arc_builder.segments[0].p1)
            == expected_point
        )


class TestMakeMapErrors:
    def test_reference_not_given(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP")
        reactant = momapy.sbgn.pd.Reactant(referred_element=atp)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        with pytest.raises(ValueError, match="is referred to"):
            make_map(momapy.sbgn.pd.SBGNPDMap, [process])

    def test_pair_descendant_not_held(self):
        state_variable = momapy.sbgn.pd.StateVariable(value="P")
        a = momapy.sbgn.pd.Macromolecule(
            label="A", state_variables=frozenset([state_variable])
        )
        state_variable_glyph = make_glyph(
            0.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        a_glyph = make_glyph(0.0, layout_elements=[state_variable_glyph])
        with pytest.raises(ValueError, match="is not one of the given elements"):
            make_map(
                momapy.sbgn.pd.SBGNPDMap,
                [a],
                [a_glyph],
                [
                    (a_glyph, a),
                    (state_variable_glyph, dataclasses.replace(state_variable)),
                ],
            )

    def test_pair_model_element_equal_but_not_given(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP")
        atp_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        with pytest.raises(ValueError, match="is not one of the given elements"):
            make_map(
                momapy.sbgn.pd.SBGNPDMap,
                [atp],
                [atp_glyph],
                [(atp_glyph, dataclasses.replace(atp))],
            )

    def test_pair_layout_element_not_in_layout(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP")
        atp_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        with pytest.raises(ValueError, match="is not one of the given elements"):
            make_map(
                momapy.sbgn.pd.SBGNPDMap,
                [atp],
                [atp_glyph],
                [(dataclasses.replace(atp_glyph), atp)],
            )

    def test_equal_glyphs_of_equal_children_of_different_owners(self):
        a_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        b_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        a = momapy.sbgn.pd.Macromolecule(
            label="A", state_variables=frozenset([a_state_variable])
        )
        b = momapy.sbgn.pd.Macromolecule(
            label="B", state_variables=frozenset([b_state_variable])
        )
        a_state_variable_glyph = make_glyph(
            0.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        b_state_variable_glyph = dataclasses.replace(a_state_variable_glyph)
        a_glyph = make_glyph(0.0, layout_elements=[a_state_variable_glyph])
        b_glyph = make_glyph(
            0.0,
            cls=momapy.sbgn.pd.SimpleChemicalLayout,
            layout_elements=[b_state_variable_glyph],
        )
        with pytest.raises(ValueError, match="are equal but are two objects"):
            make_map(
                momapy.sbgn.pd.SBGNPDMap,
                [a, b],
                [a_glyph, b_glyph],
                [
                    (a_glyph, a),
                    (b_glyph, b),
                    (a_state_variable_glyph, a_state_variable),
                    (b_state_variable_glyph, b_state_variable),
                ],
            )


class TestLostReferences:
    def make_modulations(self, equal_complexes):
        complex_1, subunit_1 = make_complex("C", "IL4R")
        complex_2, subunit_2 = make_complex("C" if equal_complexes else "D", "IL4R")
        complex_1 = dataclasses.replace(complex_1, id_="complex_1")
        complex_2 = dataclasses.replace(complex_2, id_="complex_2")
        subunit_1 = next(iter(complex_1.subunits))
        subunit_2 = next(iter(complex_2.subunits))
        target = momapy.sbgn.pd.Macromolecule(label="T")
        modulation_1 = momapy.sbgn.pd.Stimulation(
            source=subunit_1, target=target, id_="modulation_1"
        )
        modulation_2 = momapy.sbgn.pd.Stimulation(
            source=subunit_2, target=target, id_="modulation_2"
        )
        return [complex_1, complex_2, target, modulation_1, modulation_2]

    def test_modulations_from_subunits_of_different_complexes(self):
        with pytest.raises(ValueError, match="would lose a reference"):
            make_map(momapy.sbgn.pd.SBGNPDMap, self.make_modulations(False))

    def test_modulations_from_subunits_of_equal_complexes(self):
        model_elements = self.make_modulations(True)
        complex_1 = model_elements[0]
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, model_elements)
        assert len(map_.model.modulations) == 1
        kept_complex = next(
            element for element in map_.model.entity_pools if element.label == "C"
        )
        assert kept_complex.id_ == "complex_1"
        modulation = next(iter(map_.model.modulations))
        assert modulation.source is next(iter(kept_complex.subunits))
        assert kept_complex is complex_1

    def make_gate_copy_model_elements(self, with_subunits):
        if with_subunits:
            complex_1, input_element = make_complex("C", "IL4R")
            complex_2, input_element_copy = make_complex("D", "IL4R")
            other_model_elements = [complex_1, complex_2]
        else:
            input_element = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="atp")
            input_element_copy = dataclasses.replace(input_element, id_="atp_copy")
            other_model_elements = [input_element]
        gate = momapy.sbgn.pd.AndOperator(
            inputs=frozenset(
                [momapy.sbgn.pd.LogicalOperatorInput(referred_element=input_element)]
            ),
            id_="gate",
        )
        gate_copy = momapy.sbgn.pd.AndOperator(
            inputs=frozenset(
                [
                    momapy.sbgn.pd.LogicalOperatorInput(
                        referred_element=input_element_copy
                    )
                ]
            ),
            id_="gate_copy",
        )
        process = momapy.sbgn.pd.GenericProcess()
        catalysis = momapy.sbgn.pd.Catalysis(source=gate_copy, target=process)
        return other_model_elements + [gate, process, catalysis], gate, input_element

    def test_gate_copy_with_subunits_of_different_complexes(self):
        model_elements, _, _ = self.make_gate_copy_model_elements(True)
        with pytest.raises(ValueError, match="would lose a reference"):
            make_map(momapy.sbgn.pd.SBGNPDMap, model_elements)

    def test_gate_copy_with_equal_inputs(self):
        model_elements, gate, atp = self.make_gate_copy_model_elements(False)
        map_ = make_map(momapy.sbgn.pd.SBGNPDMap, model_elements)
        catalysis = next(iter(map_.model.modulations))
        assert catalysis.source is gate
        assert next(iter(gate.inputs)).referred_element is atp


class TestMergeMaps:
    @pytest.mark.parametrize("path", SBGN_MAP_PATHS, ids=os.path.basename)
    def test_merge_map_with_itself(self, path):
        map_ = momapy.io.core.read(path).obj
        merged_map = merge_maps([map_, map_])
        assert merged_map.model == map_.model
        assert merged_map.layout.layout_elements == map_.layout.layout_elements
        assert dict(merged_map.layout_model_mapping) == dict(map_.layout_model_mapping)

    def test_no_map(self):
        with pytest.raises(ValueError, match="no map"):
            merge_maps([])

    def test_maps_of_different_classes(self):
        with pytest.raises(ValueError, match="cannot merge"):
            merge_maps([momapy.sbgn.pd.SBGNPDMap(), momapy.sbgn.af.SBGNAFMap()])

    def make_atp_map(self, atp_id, glyph_id, y=0.0):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_=atp_id)
        atp_glyph = dataclasses.replace(
            make_glyph(0.0, y, cls=momapy.sbgn.pd.SimpleChemicalLayout), id_=glyph_id
        )
        return make_map(
            momapy.sbgn.pd.SBGNPDMap, [atp], [atp_glyph], [(atp_glyph, atp)]
        )

    def test_kept_elements_do_not_depend_on_order(self):
        first_map = self.make_atp_map("b", "glyph_b")
        second_map = self.make_atp_map("a", "glyph_a")
        for maps in [[first_map, second_map], [second_map, first_map]]:
            merged_map = merge_maps(maps)
            assert [
                layout_element.id_
                for layout_element in merged_map.layout.layout_elements
            ] == ["glyph_a"]
            assert [element.id_ for element in merged_map.model.entity_pools] == ["a"]

    def test_model_element_drawn_in_both_maps(self):
        merged_map = merge_maps(
            [
                self.make_atp_map("atp", "first"),
                self.make_atp_map("atp", "second", 100.0),
            ]
        )
        atp = next(iter(merged_map.model.entity_pools))
        assert len(merged_map.model.entity_pools) == 1
        assert (
            len(merged_map.layout_model_mapping.get_representative_layout_elements(atp))
            == 2
        )

    def test_equal_processes_share_their_reactants(self):
        map_elements = make_process_map_elements()
        first_map = make_map(momapy.sbgn.pd.SBGNPDMap, **map_elements)
        model_elements = [
            dataclasses.replace(model_element, id_=f"{model_element.id_}_2")
            if isinstance(model_element, momapy.sbgn.pd.GenericProcess)
            else model_element
            for model_element in map_elements["model_elements"]
        ]
        second_map = make_map(momapy.sbgn.pd.SBGNPDMap, model_elements)
        merged_map = merge_maps([first_map, second_map])
        assert len(merged_map.model.processes) == 1
        kept_process = next(iter(merged_map.model.processes))
        assert len(kept_process.reactants) == 1
        reactant = next(iter(kept_process.reactants))
        consumption_arc = map_elements["layout_elements"][4]
        assert merged_map.layout_model_mapping.get_mapping(consumption_arc) is reactant

    def test_equal_glyphs_of_different_model_elements(self):
        first_map = self.make_atp_map("atp", "first")
        adp = momapy.sbgn.pd.SimpleChemical(label="ADP")
        adp_glyph = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        second_map = make_map(
            momapy.sbgn.pd.SBGNPDMap, [adp], [adp_glyph], [(adp_glyph, adp)]
        )
        merged_map = merge_maps([first_map, second_map])
        assert len(merged_map.layout.layout_elements) == 1
        assert len(merged_map.model.entity_pools) == 2


class TestReadingHelpers:
    def test_equal_children_end_at_smallest_id(self):
        reading_context = ReadingContext(
            model=momapy.builder.builder_from_object(momapy.sbgn.pd.SBGNPDModel())
        )
        complex_builder = momapy.builder.builder_from_object(
            momapy.sbgn.pd.Complex(label="C")
        )
        subunits = []
        for subunit_id in ["c", "b", "a"]:
            state_variable = momapy.sbgn.pd.StateVariable(
                value="P", id_=f"{subunit_id}_state_variable"
            )
            subunit = momapy.sbgn.pd.MacromoleculeSubunit(
                label="S",
                id_=subunit_id,
                state_variables=frozenset([state_variable]),
            )
            subunit_glyph = make_glyph(
                float(len(subunits)), cls=momapy.sbgn.pd.MacromoleculeSubunitLayout
            )
            held_subunit = add_child_model_element(
                reading_context, subunit, complex_builder.subunits
            )
            reading_context.xml_id_to_model_element.add(subunit_id, held_subunit)
            reading_context.xml_id_to_model_element.add(
                state_variable.id_, next(iter(held_subunit.state_variables))
            )
            reading_context.layout_model_pairs.append((subunit_glyph, held_subunit))
            subunits.append(subunit)
        complex_ = momapy.builder.object_from_builder(complex_builder)
        add_top_level_model_element(reading_context, complex_, "complex")
        target = momapy.sbgn.pd.Macromolecule(label="T")
        add_top_level_model_element(reading_context, target, "target")
        modulation = momapy.sbgn.pd.Stimulation(
            source=next(iter(reading_context.xml_id_to_model_element["c"])),
            target=target,
        )
        add_top_level_model_element(reading_context, modulation, "modulation")
        merge_read_model_elements(reading_context)
        model = momapy.builder.object_from_builder(reading_context.model)
        kept_complex = next(
            element for element in model.entity_pools if element.label == "C"
        )
        kept_subunit = next(iter(kept_complex.subunits))
        assert kept_subunit.id_ == "a"
        for subunit_id in ["a", "b", "c"]:
            assert reading_context.xml_id_to_model_element[subunit_id] == frozenset(
                [kept_subunit]
            )
            assert (
                next(iter(reading_context.xml_id_to_model_element[subunit_id]))
                is kept_subunit
            )
            assert next(
                iter(
                    reading_context.xml_id_to_model_element[
                        f"{subunit_id}_state_variable"
                    ]
                )
            ) is next(iter(kept_subunit.state_variables))
        for _, model_element in reading_context.layout_model_pairs:
            assert model_element is kept_subunit
        assert next(iter(model.modulations)).source is kept_subunit

    def test_lost_reference_of_dropped_child(self):
        reading_context = ReadingContext(
            model=momapy.builder.builder_from_object(momapy.sbgn.pd.SBGNPDModel())
        )
        complex_1, subunit_1 = make_complex("C", "SYK")
        complex_2, subunit_2 = make_complex("D", "SYK")
        add_top_level_model_element(reading_context, complex_1, "complex_1")
        add_top_level_model_element(reading_context, complex_2, "complex_2")
        gate_builder = momapy.builder.builder_from_object(momapy.sbgn.pd.AndOperator())
        for subunit in [subunit_1, subunit_2]:
            add_child_model_element(
                reading_context,
                momapy.sbgn.pd.LogicalOperatorInput(referred_element=subunit),
                gate_builder.inputs,
            )
        add_top_level_model_element(
            reading_context, momapy.builder.object_from_builder(gate_builder), "gate"
        )
        with pytest.raises(ValueError, match="would lose a reference"):
            merge_read_model_elements(reading_context)


def test_check_equal_layout_elements():
    glyph = make_glyph(0.0)
    check_equal_layout_elements([glyph, make_glyph(100.0)])
    with pytest.raises(ValueError, match="are equal"):
        check_equal_layout_elements([glyph, dataclasses.replace(glyph, id_="copy")])


@pytest.mark.parametrize("module_name", ["momapy.positioning", "momapy.sbgn.utils"])
def test_import_alone(module_name):
    subprocess.run([sys.executable, "-c", f"import {module_name}"], check=True)
