"""Tests for a modifier drawn from two aliases of the same species."""

import os

import lxml.etree

import momapy.io.core
from momapy.celldesigner.model import Trigger

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(TEST_DIR, "..", "fixtures", "modifier_drawn_twice.xml")

_CD_NS = "http://www.sbml.org/2001/ns/celldesigner"
_SBML_NS = "http://www.sbml.org/sbml/level2/version4"


def check_modifier_drawn_twice(map_):
    reaction = next(iter(map_.model.reactions))
    assert len(reaction.modifiers) == 1
    modifier = next(iter(reaction.modifiers))
    assert isinstance(modifier, Trigger)
    assert modifier.id_ == "MSR1"
    arcs = map_.layout_model_mapping.get_child_layout_elements(modifier, reaction)
    assert {arc.id_ for arc in arcs} == {"MSR1_layout", "MSR2_layout"}
    assert {arc.source.id_ for arc in arcs} == {"sa3", "sa4"}
    for arc in arcs:
        assert map_.layout_model_mapping.get_mapping(arc) is modifier
    return modifier


def test_read():
    result = momapy.io.core.read(FIXTURE)
    modifier = check_modifier_drawn_twice(result.obj)
    assert modifier in result.source_id_to_model_element["MSR2"]


def test_round_trip(tmp_path):
    result = momapy.io.core.read(FIXTURE)
    output_file = tmp_path / "output.xml"
    momapy.io.core.write(
        result.obj,
        str(output_file),
        writer="celldesigner",
        source_id_to_model_element=result.source_id_to_model_element,
        source_id_to_layout_element=result.source_id_to_layout_element,
    )
    root = lxml.etree.parse(str(output_file)).getroot()
    ns = {"sbml": _SBML_NS, "cd": _CD_NS}
    modifications = root.findall(".//sbml:reaction[@id='re1']//cd:modification", ns)
    assert {modification.get("aliases") for modification in modifications} == {
        "sa3",
        "sa4",
    }
    modifier_species_references = root.findall(
        ".//sbml:reaction[@id='re1']/sbml:listOfModifiers"
        "/sbml:modifierSpeciesReference",
        ns,
    )
    assert {
        (
            modifier_species_reference.get("metaid"),
            modifier_species_reference.findtext(".//cd:alias", namespaces=ns),
        )
        for modifier_species_reference in modifier_species_references
    } == {("MSR1", "sa3"), ("MSR2", "sa4")}
    check_modifier_drawn_twice(momapy.io.core.read(str(output_file)).obj)


def test_smaller_metaid_kept(tmp_path):
    with open(FIXTURE) as file:
        text = file.read()
    text = text.replace('metaid="MSR1"', 'metaid="MSR_SWAP"')
    text = text.replace('metaid="MSR2"', 'metaid="MSR1"')
    text = text.replace('metaid="MSR_SWAP"', 'metaid="MSR2"')
    swapped_file = tmp_path / "swapped.xml"
    swapped_file.write_text(text)
    check_modifier_drawn_twice(momapy.io.core.read(str(swapped_file)).obj)
