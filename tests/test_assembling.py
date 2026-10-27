"""Tests for momapy.core._assembling."""

import dataclasses
import inspect
import typing

import pytest

from momapy.core._assembling import is_reference_field
from momapy.core.elements import ModelElement
from momapy.sbgn.elements import SBGNRole
import momapy.celldesigner.model
import momapy.sbgn.af.model
import momapy.sbgn.elements
import momapy.sbgn.pd.model
import momapy.sbml.model

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
