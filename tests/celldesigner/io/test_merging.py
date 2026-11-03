"""Tests for the merging of equal CellDesigner elements at the end of reading."""

import pytest

import momapy.io.core
from momapy.celldesigner.model import Catalyzer
from momapy.celldesigner.model import NegativeInfluence

_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<sbml xmlns="http://www.sbml.org/sbml/level2/version4" xmlns:celldesigner="http://www.sbml.org/2001/ns/celldesigner" level="2" version="4">
<model metaid="merging" id="merging">
<annotation>
<celldesigner:extension>
<celldesigner:modelVersion>4.0</celldesigner:modelVersion>
<celldesigner:modelDisplay sizeX="800" sizeY="600"/>
"""

_VIEW = (
    '<celldesigner:font size="12"/>'
    '<celldesigner:view state="usual"/>'
    '<celldesigner:usualView><celldesigner:innerPosition x="0.0" y="0.0"/>'
    '<celldesigner:boxSize width="{width}" height="{height}"/>'
    '<celldesigner:singleLine width="1.0"/>'
    '<celldesigner:paint color="ffccffcc" scheme="Color"/></celldesigner:usualView>'
    '<celldesigner:briefView><celldesigner:innerPosition x="0.0" y="0.0"/>'
    '<celldesigner:boxSize width="{width}" height="{height}"/>'
    '<celldesigner:singleLine width="1.0"/>'
    '<celldesigner:paint color="ffccffcc" scheme="Color"/></celldesigner:briefView>'
)

_LINE = (
    '<celldesigner:connectScheme connectPolicy="direct">'
    '<celldesigner:listOfLineDirection><celldesigner:lineDirection index="0" value="unknown"/>'
    "</celldesigner:listOfLineDirection></celldesigner:connectScheme>"
    '<celldesigner:line width="1.0" color="ff000000" type="Straight"/>'
)


def make_species_alias(alias_id, species_id, x, y, complex_alias_id=None):
    if complex_alias_id is None:
        complex_attribute = ""
    else:
        complex_attribute = f' complexSpeciesAlias="{complex_alias_id}"'
    return (
        f'<celldesigner:speciesAlias id="{alias_id}" species="{species_id}"{complex_attribute}>'
        "<celldesigner:activity>inactive</celldesigner:activity>"
        f'<celldesigner:bounds x="{x}" y="{y}" w="60.0" h="30.0"/>'
        + _VIEW.format(width=60.0, height=30.0)
        + "</celldesigner:speciesAlias>\n"
    )


def make_complex_alias(alias_id, species_id, x, y):
    return (
        f'<celldesigner:complexSpeciesAlias id="{alias_id}" species="{species_id}">'
        "<celldesigner:activity>inactive</celldesigner:activity>"
        f'<celldesigner:bounds x="{x}" y="{y}" w="100.0" h="120.0"/>'
        + _VIEW.format(width=100.0, height=120.0)
        + "</celldesigner:complexSpeciesAlias>\n"
    )


def make_included_species(species_id, name, complex_species_id):
    return (
        f'<celldesigner:species id="{species_id}" name="{name}"><celldesigner:annotation>'
        f"<celldesigner:complexSpecies>{complex_species_id}</celldesigner:complexSpecies>"
        "<celldesigner:speciesIdentity><celldesigner:class>SIMPLE_MOLECULE</celldesigner:class>"
        f"<celldesigner:name>{name}</celldesigner:name></celldesigner:speciesIdentity>"
        "</celldesigner:annotation></celldesigner:species>\n"
    )


def make_species(species_id, name, species_class):
    return (
        f'<species name="{name}" id="{species_id}" metaid="{species_id}" '
        'initialAmount="0.0" hasOnlySubstanceUnits="false" constant="false" '
        'boundaryCondition="false" compartment="default"><annotation><celldesigner:extension>'
        "<celldesigner:positionToCompartment>inside</celldesigner:positionToCompartment>"
        f"<celldesigner:speciesIdentity><celldesigner:class>{species_class}</celldesigner:class>"
        f"<celldesigner:name>{name}</celldesigner:name></celldesigner:speciesIdentity>"
        "</celldesigner:extension></annotation></species>\n"
    )


def make_species_reference(tag, metaid, species_id, alias_id):
    if metaid is None:
        metaid_attribute = ""
    else:
        metaid_attribute = f' metaid="{metaid}"'
    return (
        f'<{tag}{metaid_attribute} species="{species_id}"><annotation><celldesigner:extension>'
        f"<celldesigner:alias>{alias_id}</celldesigner:alias>"
        f"</celldesigner:extension></annotation></{tag}>"
    )


def make_map_file(
    tmp_path,
    complex_2_name="C",
    base_reactant=("b", "sa3"),
    reactant_links=(),
    catalyzer_aliases=(),
    modulation_source_aliases=(),
    gate_modulation_targets=(),
):
    """Write a CellDesigner file and return its path.

    The file has two complexes `c1` (alias `csa1`) and `c2` (alias `csa2`)
    holding the subunits `p1` (alias `sa1`) and `p2` (alias `sa2`), both
    named `P`, a third subunit `p0` of `c1` named `P` (alias `sa0`), and the
    top-level species `b` (alias `sa3`), `d` (alias `sa4`), `e` (alias
    `sa5`) and `f` (alias `sa6`). Reaction `re1` goes from `base_reactant`
    to `sa4`. `p0` and `p1` are equal, so `p0` replaces `p1`, and the two
    complexes are equal when `complex_2_name` is `"C"`.
    """
    included_species = (
        make_included_species("p1", "P", "c1")
        + make_included_species("p0", "P", "c1")
        + make_included_species("p2", "P", "c2")
    )
    complex_aliases = make_complex_alias("csa1", "c1", 50.0, 50.0) + make_complex_alias(
        "csa2", "c2", 250.0, 50.0
    )
    species_aliases = (
        make_species_alias("sa1", "p1", 70.0, 70.0, "csa1")
        + make_species_alias("sa0", "p0", 70.0, 120.0, "csa1")
        + make_species_alias("sa2", "p2", 270.0, 70.0, "csa2")
        + make_species_alias("sa3", "b", 100.0, 400.0)
        + make_species_alias("sa4", "d", 500.0, 400.0)
        + make_species_alias("sa5", "e", 600.0, 100.0)
        + make_species_alias("sa6", "f", 600.0, 250.0)
    )
    species = (
        make_species("c1", "C", "COMPLEX")
        + make_species("c2", complex_2_name, "COMPLEX")
        + make_species("b", "B", "SIMPLE_MOLECULE")
        + make_species("d", "D", "SIMPLE_MOLECULE")
        + make_species("e", "E", "SIMPLE_MOLECULE")
        + make_species("f", "F", "SIMPLE_MOLECULE")
    )
    reactant_link_elements = "".join(
        f'<celldesigner:reactantLink reactant="{species_id}" alias="{alias_id}">'
        '<celldesigner:linkAnchor position="S"/>'
        + _LINE
        + "</celldesigner:reactantLink>"
        for species_id, alias_id in reactant_links
    )
    modification_elements = "".join(
        f'<celldesigner:modification type="CATALYSIS" modifiers="{species_id}" '
        f'aliases="{alias_id}" targetLineIndex="-1,2">'
        + _LINE
        + "</celldesigner:modification>"
        for species_id, alias_id in catalyzer_aliases
    )
    base_species_id, base_alias_id = base_reactant
    reactant_references = make_species_reference(
        "speciesReference", "re1_reactant", base_species_id, base_alias_id
    ) + "".join(
        make_species_reference(
            "speciesReference", f"re1_link_{alias_id}", species_id, alias_id
        )
        for species_id, alias_id in reactant_links
    )
    modifier_references = "".join(
        make_species_reference(
            "modifierSpeciesReference", f"re1_modifier_{alias_id}", species_id, alias_id
        )
        for species_id, alias_id in catalyzer_aliases
    )
    if modifier_references:
        modifier_references = (
            f"<listOfModifiers>{modifier_references}</listOfModifiers>"
        )
    reactions = (
        '<reaction metaid="re1" id="re1" reversible="false"><annotation><celldesigner:extension>'
        "<celldesigner:reactionType>STATE_TRANSITION</celldesigner:reactionType>"
        "<celldesigner:baseReactants>"
        f'<celldesigner:baseReactant species="{base_species_id}" alias="{base_alias_id}">'
        '<celldesigner:linkAnchor position="E"/></celldesigner:baseReactant></celldesigner:baseReactants>'
        '<celldesigner:baseProducts><celldesigner:baseProduct species="d" alias="sa4">'
        '<celldesigner:linkAnchor position="W"/></celldesigner:baseProduct></celldesigner:baseProducts>'
        f"<celldesigner:listOfReactantLinks>{reactant_link_elements}</celldesigner:listOfReactantLinks>"
        "<celldesigner:listOfProductLinks/>"
        '<celldesigner:connectScheme connectPolicy="direct" rectangleIndex="0">'
        '<celldesigner:listOfLineDirection><celldesigner:lineDirection index="0" value="unknown"/>'
        "</celldesigner:listOfLineDirection></celldesigner:connectScheme>"
        f"<celldesigner:listOfModification>{modification_elements}</celldesigner:listOfModification>"
        '<celldesigner:line width="1.0" color="ff000000" type="Straight"/>'
        "</celldesigner:extension></annotation>"
        f"<listOfReactants>{reactant_references}</listOfReactants>"
        "<listOfProducts>"
        + make_species_reference("speciesReference", "re1_product", "d", "sa4")
        + f"</listOfProducts>{modifier_references}</reaction>\n"
    )
    for index, (species_id, alias_id) in enumerate(modulation_source_aliases):
        reactions += (
            f'<reaction metaid="mod{index}" id="mod{index}" reversible="false">'
            "<annotation><celldesigner:extension>"
            "<celldesigner:reactionType>NEGATIVE_INFLUENCE</celldesigner:reactionType>"
            f'<celldesigner:baseReactants><celldesigner:baseReactant species="{species_id}" alias="{alias_id}"/>'
            "</celldesigner:baseReactants>"
            '<celldesigner:baseProducts><celldesigner:baseProduct species="e" alias="sa5"/>'
            "</celldesigner:baseProducts>"
            "<celldesigner:listOfReactantLinks/><celldesigner:listOfProductLinks/>"
            '<celldesigner:connectScheme connectPolicy="direct" rectangleIndex="0">'
            '<celldesigner:listOfLineDirection><celldesigner:lineDirection index="0" value="unknown"/>'
            "</celldesigner:listOfLineDirection></celldesigner:connectScheme>"
            '<celldesigner:line width="1.0" color="ff000000" type="Straight"/>'
            "</celldesigner:extension></annotation>"
            "<listOfReactants>"
            + make_species_reference("speciesReference", None, species_id, alias_id)
            + "</listOfReactants><listOfProducts>"
            + make_species_reference("speciesReference", None, "e", "sa5")
            + "</listOfProducts></reaction>\n"
        )
    for index, (species_id, alias_id) in enumerate(gate_modulation_targets):
        reactions += (
            f'<reaction metaid="gate_mod{index}" id="gate_mod{index}" reversible="false">'
            "<annotation><celldesigner:extension>"
            "<celldesigner:reactionType>BOOLEAN_LOGIC_GATE</celldesigner:reactionType>"
            '<celldesigner:baseReactants><celldesigner:baseReactant species="b" alias="sa3"/>'
            '<celldesigner:baseReactant species="d" alias="sa4"/></celldesigner:baseReactants>'
            f'<celldesigner:baseProducts><celldesigner:baseProduct species="{species_id}" alias="{alias_id}"/>'
            "</celldesigner:baseProducts>"
            "<celldesigner:listOfReactantLinks/><celldesigner:listOfProductLinks/>"
            '<celldesigner:connectScheme connectPolicy="direct" rectangleIndex="1">'
            "<celldesigner:listOfLineDirection>"
            '<celldesigner:lineDirection index="0" value="unknown"/>'
            '<celldesigner:lineDirection index="1" value="unknown"/>'
            '<celldesigner:lineDirection index="2" value="unknown"/>'
            '<celldesigner:lineDirection index="3" value="unknown"/>'
            "</celldesigner:listOfLineDirection></celldesigner:connectScheme>"
            f"<celldesigner:editPoints>{300.0 + 100.0 * index},300.0</celldesigner:editPoints>"
            "<celldesigner:listOfModification/><celldesigner:listOfGateMember>"
            '<celldesigner:GateMember type="BOOLEAN_LOGIC_GATE_AND" aliases="sa3,sa4" '
            f'modificationType="NEGATIVE_INFLUENCE" editPoints="{300.0 + 100.0 * index},300.0">'
            + _LINE
            + "</celldesigner:GateMember>"
            '<celldesigner:GateMember type="NEGATIVE_INFLUENCE" aliases="sa3">'
            + _LINE
            + "</celldesigner:GateMember>"
            '<celldesigner:GateMember type="NEGATIVE_INFLUENCE" aliases="sa4">'
            + _LINE
            + "</celldesigner:GateMember>"
            "</celldesigner:listOfGateMember>"
            '<celldesigner:line width="1.0" color="ff000000" type="Straight"/>'
            "</celldesigner:extension></annotation>"
            "<listOfReactants>"
            + make_species_reference("speciesReference", None, "b", "sa3")
            + make_species_reference("speciesReference", None, "d", "sa4")
            + "</listOfReactants><listOfProducts>"
            + make_species_reference("speciesReference", None, species_id, alias_id)
            + "</listOfProducts></reaction>\n"
        )
    text = (
        _HEADER
        + f"<celldesigner:listOfIncludedSpecies>{included_species}</celldesigner:listOfIncludedSpecies>\n"
        + "<celldesigner:listOfCompartmentAliases/>\n"
        + f"<celldesigner:listOfComplexSpeciesAliases>{complex_aliases}</celldesigner:listOfComplexSpeciesAliases>\n"
        + f"<celldesigner:listOfSpeciesAliases>{species_aliases}</celldesigner:listOfSpeciesAliases>\n"
        + "<celldesigner:listOfProteins/><celldesigner:listOfGenes/><celldesigner:listOfRNAs/>"
        + "<celldesigner:listOfAntisenseRNAs/><celldesigner:listOfLayers/>\n"
        + "</celldesigner:extension></annotation>\n"
        + '<listOfCompartments><compartment id="default" size="1" units="volume"/></listOfCompartments>\n'
        + f"<listOfSpecies>{species}</listOfSpecies>\n"
        + f"<listOfReactions>{reactions}</listOfReactions>\n"
        + "</model>\n</sbml>\n"
    )
    file_path = tmp_path / "merging.xml"
    file_path.write_text(text)
    return file_path


def get_reaction(map_):
    return next(reaction for reaction in map_.model.reactions if reaction.id_ == "re1")


def get_species(map_, species_id):
    return next(species for species in map_.model.species if species.id_ == species_id)


def get_subunit(complex_, subunit_id):
    return next(subunit for subunit in complex_.subunits if subunit.id_ == subunit_id)


class TestParticipantGroups:
    def test_base_and_link_on_subunits_of_equal_complexes(self, tmp_path):
        file_path = make_map_file(
            tmp_path, base_reactant=("p1", "sa1"), reactant_links=[("p2", "sa2")]
        )
        map_ = momapy.io.core.read(file_path).obj
        reactants = get_reaction(map_).reactants
        assert len(reactants) == 1
        reactant = next(iter(reactants))
        assert reactant.base is True
        assert reactant.stoichiometry == 2.0
        complex_ = get_species(map_, "c1")
        assert reactant.referred_element is get_subunit(complex_, "p0")

    def test_base_and_link_on_subunits_of_unequal_complexes(self, tmp_path):
        file_path = make_map_file(
            tmp_path,
            complex_2_name="D",
            base_reactant=("p1", "sa1"),
            reactant_links=[("p2", "sa2")],
        )
        map_ = momapy.io.core.read(file_path).obj
        reactants = get_reaction(map_).reactants
        assert {(reactant.base, reactant.stoichiometry) for reactant in reactants} == {
            (True, None),
            (False, None),
        }

    def test_two_links_on_subunits_of_unequal_complexes_raise(self, tmp_path):
        file_path = make_map_file(
            tmp_path,
            complex_2_name="D",
            reactant_links=[("p1", "sa1"), ("p2", "sa2")],
        )
        with pytest.raises(ValueError):
            momapy.io.core.read(file_path)


class TestLostReferences:
    def test_modulations_from_subunits_of_unequal_complexes_raise(self, tmp_path):
        file_path = make_map_file(
            tmp_path,
            complex_2_name="D",
            modulation_source_aliases=[("p1", "sa1"), ("p2", "sa2")],
        )
        with pytest.raises(ValueError):
            momapy.io.core.read(file_path)

    def test_modulations_from_subunits_of_equal_complexes_merge(self, tmp_path):
        file_path = make_map_file(
            tmp_path, modulation_source_aliases=[("p1", "sa1"), ("p2", "sa2")]
        )
        map_ = momapy.io.core.read(file_path).obj
        assert len(map_.model.modulations) == 1
        modulation = next(iter(map_.model.modulations))
        assert isinstance(modulation, NegativeInfluence)
        complex_ = get_species(map_, "c1")
        assert modulation.source is get_subunit(complex_, "p0")

    def test_catalyzers_from_subunits_of_unequal_complexes_raise(self, tmp_path):
        file_path = make_map_file(
            tmp_path,
            complex_2_name="D",
            catalyzer_aliases=[("p1", "sa1"), ("p2", "sa2")],
        )
        with pytest.raises(ValueError):
            momapy.io.core.read(file_path)

    def test_modulation_from_one_subunit(self, tmp_path):
        file_path = make_map_file(
            tmp_path, complex_2_name="D", modulation_source_aliases=[("p2", "sa2")]
        )
        map_ = momapy.io.core.read(file_path).obj
        modulation = next(iter(map_.model.modulations))
        complex_ = get_species(map_, "c2")
        assert modulation.source is get_subunit(complex_, "p2")

    def test_catalyzer_from_dropped_subunit(self, tmp_path):
        file_path = make_map_file(
            tmp_path, complex_2_name="D", catalyzer_aliases=[("p1", "sa1")]
        )
        map_ = momapy.io.core.read(file_path).obj
        complex_ = get_species(map_, "c1")
        assert len(complex_.subunits) == 1
        modifier = next(iter(get_reaction(map_).modifiers))
        assert isinstance(modifier, Catalyzer)
        assert modifier.referred_element is get_subunit(complex_, "p0")


def test_equal_gates_are_merged(tmp_path):
    file_path = make_map_file(
        tmp_path, gate_modulation_targets=[("e", "sa5"), ("f", "sa6")]
    )
    map_ = momapy.io.core.read(file_path).obj
    assert len(map_.model.boolean_logic_gates) == 1
    gate = next(iter(map_.model.boolean_logic_gates))
    assert len(map_.model.modulations) == 2
    for modulation in map_.model.modulations:
        assert modulation.source is gate
