"""Tests for CellDesigner writer model-walk invariants.

See ``plans/writer_model_walk_emission.md``. The writer must source
every model-side identifier emitted into XML from a model element in
scope on the model walk, never from a value-keyed lookup into the
layout-model mapping. The mapping is consulted only as a pairing
oracle.
"""

import dataclasses
import os

import lxml.etree
import pytest

import momapy.builder
import momapy.io.core
from momapy.celldesigner.model import Complex


_CD_NS = "http://www.sbml.org/2001/ns/celldesigner"
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_CD_MAPS_DIR = os.path.join(_TEST_DIR, "maps")
_NEUROINFLAMMATION = os.path.join(_CD_MAPS_DIR, "Neuroinflammation.xml")


@pytest.fixture
def neuro_map():
    if not os.path.exists(_NEUROINFLAMMATION):
        pytest.skip("Neuroinflammation fixture not available")
    return momapy.io.core.read(_NEUROINFLAMMATION).obj


def _find_complex_with_non_complex_subunit(map_):
    """Return the first ``(complex, subunit, subunit_layout)`` triple where
    ``subunit`` is a non-Complex Species and a layout is recorded under
    ``complex`` for it."""
    mapping = map_.layout_model_mapping
    for species in map_.model.species:
        if not isinstance(species, Complex):
            continue
        for subunit in species.subunits:
            if isinstance(subunit, Complex):
                continue
            layouts = mapping.get_child_layout_elements(subunit, species)
            if layouts:
                return species, subunit, layouts[0]
    raise RuntimeError("no complex with non-complex subunit and recorded layout found")


def _find_outer_layout(map_, complex_):
    layout_elements = map_.layout_model_mapping.get_representative_layout_elements(
        complex_
    )
    if layout_elements:
        return layout_elements[0]
    raise RuntimeError(f"no layout for complex {complex_.id_}")


def _find_nested_complex_pair(map_):
    """Return ``(outer_complex, outer_layout, inner_complex, inner_layout)``."""
    mapping = map_.layout_model_mapping
    for outer in map_.model.species:
        if not isinstance(outer, Complex):
            continue
        outer_layouts = [
            key
            for key in mapping.inverse.get(id(outer), ())
            if not isinstance(key, frozenset)
        ]
        if not outer_layouts:
            continue
        for inner in outer.subunits:
            if not isinstance(inner, Complex):
                continue
            inner_layouts = mapping.get_child_layout_elements(inner, outer)
            if inner_layouts:
                return outer, outer_layouts[0], inner, inner_layouts[0]
    raise RuntimeError("no nested complex with mapped layouts found")


class TestStaleMappingSurvivesWriting:
    """Identity-keyed mapping is authoritative for layout↔model pairing.

    Replacing a mapping value with a content-equal-but-id-distinct
    sibling no longer aliases the two: the layout pairs to the
    inserted instance by identity, and the original (still in the
    model graph) has no recorded layout. The writer's pairing oracle
    (``get_child_layout_elements``) therefore returns no layout for
    the in-scope subunit, and no alias is emitted. The pairing is
    consistent — model and mapping disagree only by identity, which
    Tier 2 surfaces precisely.
    """

    def test_writer_drops_alias_for_id_distinct_mapping_value(
        self, neuro_map, tmp_path
    ):
        target_complex, target_subunit, target_layout = (
            _find_complex_with_non_complex_subunit(neuro_map)
        )
        stale_subunit = dataclasses.replace(target_subunit, id_="STALE_ALTERNATE_ID")
        assert stale_subunit == target_subunit
        assert stale_subunit is not target_subunit
        cache: dict = {}
        map_builder = momapy.builder.builder_from_object(
            neuro_map, object_to_builder=cache
        )
        target_layout_builder = cache[id(target_layout)]
        stale_subunit_builder = momapy.builder.builder_from_object(stale_subunit)
        map_builder.layout_model_mapping[target_layout_builder] = stale_subunit_builder
        new_map = momapy.builder.object_from_builder(map_builder)
        # Forward-dict lookup: ``==``-keyed by layout, value is the
        # inserted stale instance.
        assert (
            new_map.layout_model_mapping.get_mapping(target_layout).id_
            == "STALE_ALTERNATE_ID"
        )
        # Identity-keyed inverse: target_subunit's identity is not in
        # the mapping; only stale_subunit's is.
        mapping = new_map.layout_model_mapping
        assert mapping.inverse.get(id(target_subunit)) is None
        out_file = tmp_path / "stale.xml"
        momapy.io.core.write(new_map, out_file, writer="celldesigner")
        tree = lxml.etree.parse(str(out_file))
        aliases = tree.getroot().findall(
            f".//{{{_CD_NS}}}speciesAlias[@id='{target_layout.id_}']"
        )
        assert aliases == [], (
            "mapping is identity-keyed: target_layout pairs to the inserted "
            "stale instance, so target_subunit (still in the model) has no "
            "paired layout and no alias should be emitted"
        )

    def test_round_trip_succeeds_with_stale_mapping(self, neuro_map, tmp_path):
        target_complex, target_subunit, target_layout = (
            _find_complex_with_non_complex_subunit(neuro_map)
        )
        stale_subunit = dataclasses.replace(target_subunit, id_="STALE_ALTERNATE_ID_2")
        cache: dict = {}
        map_builder = momapy.builder.builder_from_object(
            neuro_map, object_to_builder=cache
        )
        target_layout_builder = cache[id(target_layout)]
        stale_subunit_builder = momapy.builder.builder_from_object(stale_subunit)
        map_builder.layout_model_mapping[target_layout_builder] = stale_subunit_builder
        new_map = momapy.builder.object_from_builder(map_builder)
        out_file = tmp_path / "stale_roundtrip.xml"
        momapy.io.core.write(new_map, out_file, writer="celldesigner")
        result = momapy.io.core.read(str(out_file), reader="celldesigner")
        assert result.obj is not None


class TestNestedComplexAliasChaining:
    """Nested ``<complexSpeciesAlias>`` entries reference the outer
    complex's emitted alias id via ``complexSpeciesAlias``."""

    def test_inner_alias_references_outer(self, neuro_map, tmp_path):
        outer_complex, outer_layout, inner_complex, inner_layout = (
            _find_nested_complex_pair(neuro_map)
        )
        out_file = tmp_path / "nested.xml"
        momapy.io.core.write(neuro_map, out_file, writer="celldesigner")
        tree = lxml.etree.parse(str(out_file))
        nested_aliases = tree.getroot().findall(
            f".//{{{_CD_NS}}}complexSpeciesAlias[@id='{inner_layout.id_}']"
        )
        assert len(nested_aliases) == 1
        assert nested_aliases[0].get("complexSpeciesAlias") == outer_layout.id_


class TestComplexMemberAliasLink:
    """A complex member references the written id of its complex alias."""

    def test_member_references_written_complex_alias(self, neuro_map, tmp_path):
        target_complex, _, _ = _find_complex_with_non_complex_subunit(neuro_map)
        target_layout = _find_outer_layout(neuro_map, target_complex)
        cache: dict = {}
        map_builder = momapy.builder.builder_from_object(
            neuro_map, object_to_builder=cache
        )
        cache[id(target_layout)].id_ = "complex-1"
        new_map = momapy.builder.object_from_builder(map_builder)
        out_file = tmp_path / "member_link.xml"
        momapy.io.core.write(new_map, out_file, writer="celldesigner")
        root = lxml.etree.parse(str(out_file)).getroot()
        complex_alias_ids = {
            element.get("id")
            for element in root.iter(f"{{{_CD_NS}}}complexSpeciesAlias")
        }
        member_links = [
            element.get("complexSpeciesAlias")
            for element in root.iter(f"{{{_CD_NS}}}speciesAlias")
            if element.get("complexSpeciesAlias") is not None
        ]
        assert "complex_1" in member_links
        assert set(member_links) <= complex_alias_ids


class TestModificationStateString:
    """Regression tests for ``modification_state_string``."""

    def test_every_member_serializes_without_silent_data_loss(self):
        from momapy.celldesigner.io.celldesigner._writing import (
            modification_state_string,
        )
        from momapy.celldesigner.model import ModificationState

        for member in ModificationState:
            assert modification_state_string(member) != "empty", (
                f"{member.name} must not serialize to 'empty' (silent data loss)"
            )

    def test_sulfated_round_trips_through_the_reader(self):
        from momapy.celldesigner.io.celldesigner._writing import (
            modification_state_string,
        )
        from momapy.celldesigner.model import ModificationState

        cd_string = modification_state_string(ModificationState.SULFATED)
        assert cd_string == "sulfated"
        recovered = ModificationState[
            cd_string.upper().replace(" ", "_").replace("'", "_")
        ]
        assert recovered is ModificationState.SULFATED


class TestParticipantsWrittenFromModel:
    """A drawn reaction writes the participants of the model reaction only."""

    def test_participant_removed_from_model_is_not_written(self, tmp_path):
        map_builder = momapy.builder.builder_from_object(
            momapy.io.core.read(os.path.join(_CD_MAPS_DIR, "Apoptosis_pathway.xml")).obj
        )
        reaction_builder = next(
            reaction
            for reaction in map_builder.model.reactions
            if reaction.id_ == "re30"
        )
        for reactant in list(reaction_builder.reactants):
            if reactant.id_ == "re30_s_id_sa47":
                reaction_builder.reactants.remove(reactant)
        output_file = tmp_path / "output.xml"
        momapy.io.core.write(
            map_builder.build(), str(output_file), writer="celldesigner"
        )
        root = lxml.etree.parse(str(output_file)).getroot()
        sbml_namespace = root.nsmap[None]
        reaction = root.find(f".//{{{sbml_namespace}}}reaction[@id='re30']")
        species_references = reaction.iterfind(
            f"{{{sbml_namespace}}}listOfReactants/{{{sbml_namespace}}}speciesReference"
        )
        reactant_links = reaction.iter(f"{{{_CD_NS}}}reactantLink")
        written_species_ids = [
            species_reference.get("species") for species_reference in species_references
        ]
        linked_species_ids = [
            reactant_link.get("reactant") for reactant_link in reactant_links
        ]
        assert "s_id_sa47" not in written_species_ids
        assert "s_id_sa47" not in linked_species_ids
        assert "s_id_sa27" in written_species_ids
        assert "s_id_sa27" in linked_species_ids


class TestDrawnCopiesOfOneReaction:
    """Each drawn copy of a reaction is written with its own identifiers."""

    def test_each_copy_gets_its_own_participant_metaids(self, neuro_map, tmp_path):
        output_file = tmp_path / "output.xml"
        momapy.io.core.write(neuro_map, str(output_file), writer="celldesigner")
        root = lxml.etree.parse(str(output_file)).getroot()
        sbml_namespace = root.nsmap[None]
        for reaction_id in ["ne6db", "ne67d"]:
            reaction = root.find(
                f".//{{{sbml_namespace}}}reaction[@id='{reaction_id}']"
            )
            metaids = [
                species_reference.get("metaid")
                for species_reference in reaction.iter(
                    f"{{{sbml_namespace}}}speciesReference"
                )
            ]
            assert metaids
            assert all(metaid.startswith(f"{reaction_id}_") for metaid in metaids)
        all_metaids = [
            element.get("metaid") for element in root.iter() if element.get("metaid")
        ]
        assert len(all_metaids) == len(set(all_metaids))


def _replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def _get_reaction_block(text, reaction_id):
    start = text.index(f'<reaction metaid="{reaction_id}"')
    end = text.index("</reaction>", start) + len("</reaction>")
    return text[start:end]


class TestDrawnCopiesOfOneReactionModifier:
    """Each drawn copy of a reaction keeps the metaid of its own modifier."""

    def test_each_copy_keeps_its_own_modifier_metaid(self, tmp_path):
        if not os.path.exists(_NEUROINFLAMMATION):
            pytest.skip("Neuroinflammation fixture not available")
        with open(_NEUROINFLAMMATION) as file:
            text = file.read()
        modification = (
            '<celldesigner:modification type="CATALYSIS" modifiers="s_id_ne193"'
            ' aliases="ne193" targetLineIndex="0,6">'
            '<celldesigner:connectScheme connectPolicy="direct">'
            "<celldesigner:listOfLineDirection>"
            '<celldesigner:lineDirection index="0" value="unknown"/>'
            "</celldesigner:listOfLineDirection></celldesigner:connectScheme>"
            '<celldesigner:linkTarget species="s_id_ne193" alias="ne193"/>'
            '<celldesigner:line width="1.0" color="FF000000" type="Straight"/>'
            "</celldesigner:modification>"
        )
        for reaction_id, metaid in [("ne6db", "MSRB"), ("ne67d", "MSRA")]:
            block = _get_reaction_block(text, reaction_id)
            new_block = _replace_once(
                block,
                "<celldesigner:listOfModification>\n",
                f"<celldesigner:listOfModification>\n{modification}\n",
            )
            new_block = _replace_once(
                new_block,
                "</listOfProducts>",
                "</listOfProducts><listOfModifiers>"
                f'<modifierSpeciesReference metaid="{metaid}" species="s_id_ne193">'
                "<annotation><celldesigner:extension>"
                "<celldesigner:alias>ne193</celldesigner:alias>"
                "</celldesigner:extension></annotation>"
                "</modifierSpeciesReference></listOfModifiers>",
            )
            text = _replace_once(text, block, new_block)
        input_file = tmp_path / "input.xml"
        input_file.write_text(text)
        result = momapy.io.core.read(str(input_file))
        for index, options in enumerate(
            [
                {},
                {
                    "source_id_to_model_element": result.source_id_to_model_element,
                    "source_id_to_layout_element": result.source_id_to_layout_element,
                },
            ]
        ):
            output_file = tmp_path / f"output_{index}.xml"
            momapy.io.core.write(
                result.obj, str(output_file), writer="celldesigner", **options
            )
            root = lxml.etree.parse(str(output_file)).getroot()
            sbml_namespace = root.nsmap[None]
            for reaction_id, metaid in [("ne6db", "MSRB"), ("ne67d", "MSRA")]:
                reaction = root.find(
                    f".//{{{sbml_namespace}}}reaction[@id='{reaction_id}']"
                )
                modifier_metaids = [
                    modifier_species_reference.get("metaid")
                    for modifier_species_reference in reaction.iter(
                        f"{{{sbml_namespace}}}modifierSpeciesReference"
                    )
                ]
                assert modifier_metaids == [metaid]
            all_metaids = [
                element.get("metaid")
                for element in root.iter()
                if element.get("metaid")
            ]
            assert len(all_metaids) == len(set(all_metaids))


class TestCompartmentAliasFromContainer:
    """`compartmentAlias` is read into and written from the container."""

    def test_compartment_alias_from_container(self, tmp_path):
        with open(os.path.join(_CD_MAPS_DIR, "Apoptosis_pathway.xml")) as file:
            text = file.read()
        text = _replace_once(
            text,
            '<celldesigner:speciesAlias id="sa30" species="s_id_sa30"'
            ' compartmentAlias="ca6"',
            '<celldesigner:speciesAlias id="sa30" species="s_id_sa30"'
            ' compartmentAlias="ca5"',
        )
        input_file = tmp_path / "input.xml"
        input_file.write_text(text)
        map_ = momapy.io.core.read(str(input_file)).obj
        species_layout = next(
            layout_element
            for layout_element in map_.layout.layout_elements
            if layout_element.id_ == "sa30"
        )
        assert species_layout.container.id_ == "ca5"
        output_file = tmp_path / "output.xml"
        momapy.io.core.write(map_, str(output_file), writer="celldesigner")
        root = lxml.etree.parse(str(output_file)).getroot()
        sbml_namespace = root.nsmap[None]
        species_alias = root.find(f".//{{{_CD_NS}}}speciesAlias[@id='sa30']")
        species = root.find(f".//{{{sbml_namespace}}}species[@id='s_id_sa30']")
        assert species_alias.get("compartmentAlias") == "ca5"
        assert species.get("compartment") == "s_id_ca6"


class TestGateModulationDrawnTwice:
    """Each drawn copy of a gate modulation is written from its own key."""

    def test_gate_modulation_drawn_twice(self, tmp_path):
        with open(
            os.path.join(_TEST_DIR, "fixtures", "boolean_logic_gates.xml")
        ) as file:
            text = file.read()
        block = _get_reaction_block(text, "re2")
        copied_block = block.replace('"re2"', '"re3"').replace(
            "290.0,300.0", "290.0,400.0"
        )
        text = _replace_once(text, block, f"{block}\n{copied_block}")
        input_file = tmp_path / "input.xml"
        input_file.write_text(text)
        map_ = momapy.io.core.read(str(input_file)).obj
        output_file = tmp_path / "output.xml"
        momapy.io.core.write(map_, str(output_file), writer="celldesigner")
        written_map = momapy.io.core.read(str(output_file)).obj
        assert written_map.model == map_.model
        assert written_map.layout == map_.layout
        root = lxml.etree.parse(str(output_file)).getroot()
        sbml_namespace = root.nsmap[None]
        for reaction_id, edit_points in [
            ("re2", "290.0,300.0"),
            ("re3", "290.0,400.0"),
        ]:
            reaction = root.find(
                f".//{{{sbml_namespace}}}reaction[@id='{reaction_id}']"
            )
            gate_member = next(
                gate_member
                for gate_member in reaction.iter(f"{{{_CD_NS}}}GateMember")
                if gate_member.get("type").startswith("BOOLEAN_LOGIC_GATE")
            )
            assert gate_member.get("editPoints") == edit_points
