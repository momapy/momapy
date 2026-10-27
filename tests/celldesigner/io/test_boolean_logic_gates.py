"""Tests for the mapping keys of boolean logic gates."""

import os

import lxml.etree

import momapy.io.core
from momapy.celldesigner.model import AndGate
from momapy.celldesigner.model import OrGate

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(TEST_DIR, "..", "fixtures", "boolean_logic_gates.xml")

_CD_NS = "http://www.sbml.org/2001/ns/celldesigner"
_SBML_NS = "http://www.sbml.org/sbml/level2/version4"


def get_gate_key(map_, gate_class):
    mapping = map_.layout_model_mapping
    gate = next(
        gate for gate in map_.model.boolean_logic_gates if isinstance(gate, gate_class)
    )
    keys = [key for key, value in mapping.items() if value is gate]
    assert len(keys) == 1
    return keys[0], gate


def check_gate_keys(map_):
    mapping = map_.layout_model_mapping
    for gate_class, owner_class_name in (
        (OrGate, "StateTransition"),
        (AndGate, "NegativeInfluence"),
    ):
        key, gate = get_gate_key(map_, gate_class)
        assert isinstance(key, frozenset)
        assert sorted(type(element).__name__ for element in key) == sorted(
            [
                f"{gate_class.__name__}Layout",
                "LogicArcLayout",
                "LogicArcLayout",
                "SimpleMoleculeLayout",
                "SimpleMoleculeLayout",
            ]
        )
        assert {
            element.id_
            for element in key
            if type(element).__name__ == "SimpleMoleculeLayout"
        } == {"sa3", "sa4"}
        gate_layout = next(
            element for element in key if type(element).__name__.endswith("GateLayout")
        )
        assert mapping.representative_to_key[gate_layout] == key
        assert mapping.get_mapping(gate_layout) is gate
        owner_keys = [
            owner_key
            for owner_key, value in mapping.items()
            if type(value).__name__ == owner_class_name
        ]
        assert len(owner_keys) == 1
        assert key <= owner_keys[0]


def test_read():
    check_gate_keys(momapy.io.core.read(FIXTURE).obj)


def test_round_trip(tmp_path):
    map_ = momapy.io.core.read(FIXTURE).obj
    output_file = tmp_path / "output.xml"
    momapy.io.core.write(map_, str(output_file), writer="celldesigner")
    root = lxml.etree.parse(str(output_file)).getroot()
    ns = {"sbml": _SBML_NS, "cd": _CD_NS}
    gate_modifications = [
        modification
        for modification in root.findall(
            ".//sbml:reaction[@id='re1']//cd:modification", ns
        )
        if modification.get("type") == "BOOLEAN_LOGIC_GATE_OR"
    ]
    assert len(gate_modifications) == 1
    assert sorted(gate_modifications[0].get("aliases").split(",")) == ["sa3", "sa4"]
    modifier_aliases = {
        modifier_species_reference.findtext(".//cd:alias", namespaces=ns)
        for modifier_species_reference in root.findall(
            ".//sbml:reaction[@id='re1']/sbml:listOfModifiers"
            "/sbml:modifierSpeciesReference",
            ns,
        )
    }
    assert modifier_aliases == {"sa3", "sa4"}
    gate_members = [
        gate_member
        for gate_member in root.findall(".//cd:GateMember", ns)
        if gate_member.get("type") == "BOOLEAN_LOGIC_GATE_AND"
    ]
    assert len(gate_members) == 1
    assert sorted(gate_members[0].get("aliases").split(",")) == ["sa3", "sa4"]
    written_map = momapy.io.core.read(str(output_file)).obj
    assert written_map.model == map_.model
    check_gate_keys(written_map)
