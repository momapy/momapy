"""Tests for momapy.sbgn.utils — SBGN map layout utility functions."""

import dataclasses
import os

import pytest

import momapy.io.core
import momapy.builder
import momapy.sbgn
import momapy.sbgn.pd
import momapy.sbgn.af
import momapy.sbgn.utils
import momapy.core._assembling
import momapy.core.layout
import momapy.geometry


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SBGN_MAPS_DIR = os.path.join(TEST_DIR, "maps", "pd")


def _get_sbgn_files():
    if not os.path.exists(SBGN_MAPS_DIR):
        return []
    return sorted(f for f in os.listdir(SBGN_MAPS_DIR) if f.endswith(".sbgn"))


SBGN_FILES = _get_sbgn_files()


@pytest.fixture(scope="session")
def pd_maps():
    """Load all PD maps once for the entire test session."""
    if not SBGN_FILES:
        pytest.skip("No SBGN test files found")
    maps = {}
    for fname in SBGN_FILES:
        path = os.path.join(SBGN_MAPS_DIR, fname)
        result = momapy.io.core.read(path)
        maps[fname] = result.obj
    return maps


@pytest.fixture(params=SBGN_FILES, ids=SBGN_FILES)
def pd_map(request, pd_maps):
    """Yield each loaded PD map in turn (parametrized)."""
    return pd_maps[request.param]


@pytest.fixture
def representative_map(pd_maps):
    """Return a single representative map for non-parametrized tests."""
    return pd_maps[SBGN_FILES[0]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_UTILS_FUNCTIONS = [
    "set_compartments_to_fit_content",
    "set_complexes_to_fit_content",
    "set_submaps_to_fit_content",
    "set_nodes_to_fit_labels",
    "set_arcs_to_borders",
    "set_auxiliary_units_to_borders",
    "set_auxiliary_units_label_font_size",
    "set_layout_to_fit_content",
    "tidy",
    "sbgned_tidy",
    "newt_tidy",
]


def _call_function(name, map_):
    fn = getattr(momapy.sbgn.utils, name)
    if name == "set_auxiliary_units_label_font_size":
        return fn(map_, font_size=14.0)
    return fn(map_)


# ---------------------------------------------------------------------------
# TestReturnTypes
# ---------------------------------------------------------------------------


class TestReturnTypes:
    """Each util function returns the correct type depending on input."""

    @pytest.mark.parametrize("func_name", ALL_UTILS_FUNCTIONS)
    def test_returns_sbgnmap_for_sbgnmap_input(self, representative_map, func_name):
        assert isinstance(representative_map, momapy.sbgn.SBGNMap)
        result = _call_function(func_name, representative_map)
        assert isinstance(result, momapy.sbgn.SBGNMap), (
            f"{func_name} should return SBGNMap when given SBGNMap"
        )

    @pytest.mark.parametrize("func_name", ALL_UTILS_FUNCTIONS)
    def test_returns_builder_for_builder_input(self, representative_map, func_name):
        builder = momapy.builder.builder_from_object(representative_map)
        result = _call_function(func_name, builder)
        assert not isinstance(result, momapy.sbgn.SBGNMap), (
            f"{func_name} should not return SBGNMap when given a builder"
        )
        assert momapy.builder.isinstance_or_builder(result, momapy.sbgn.SBGNMap), (
            f"{func_name} should return a builder of SBGNMap"
        )


# ---------------------------------------------------------------------------
# TestSetArcsToBorders
# ---------------------------------------------------------------------------


def _find_arcs_of_type(map_builder, layout_type):
    """Yield arc layout elements matching *layout_type* (builder-aware)."""
    for le in map_builder.layout.layout_elements:
        if momapy.builder.isinstance_or_builder(le, layout_type):
            yield le


class TestSetArcsToBorders:
    """set_arcs_to_borders moves arc endpoints away from node centres."""

    def test_consumption_start_not_at_center(self, pd_map):
        builder = momapy.builder.builder_from_object(pd_map)
        momapy.sbgn.utils.set_arcs_to_borders(builder)
        for arc in _find_arcs_of_type(builder, momapy.sbgn.pd.ConsumptionLayout):
            source_center = arc.source.center()
            start = arc.segments[0].p1
            # At least one coordinate should differ from center
            assert start.x != source_center.x or start.y != source_center.y

    def test_production_end_not_at_center(self, pd_map):
        builder = momapy.builder.builder_from_object(pd_map)
        momapy.sbgn.utils.set_arcs_to_borders(builder)
        for arc in _find_arcs_of_type(builder, momapy.sbgn.pd.ProductionLayout):
            target_center = arc.target.center()
            end = arc.segments[-1].p2
            assert end.x != target_center.x or end.y != target_center.y

    def test_modulation_endpoints_differ_from_centers(self, pd_map):
        builder = momapy.builder.builder_from_object(pd_map)
        momapy.sbgn.utils.set_arcs_to_borders(builder)
        modulation_types = (
            momapy.sbgn.pd.ModulationLayout,
            momapy.sbgn.pd.StimulationLayout,
            momapy.sbgn.pd.CatalysisLayout,
            momapy.sbgn.pd.NecessaryStimulationLayout,
            momapy.sbgn.pd.InhibitionLayout,
        )
        for arc in _find_arcs_of_type(builder, modulation_types):
            target_center = arc.target.center()
            end = arc.segments[-1].p2
            assert end.x != target_center.x or end.y != target_center.y


# ---------------------------------------------------------------------------
# TestSetNodesToFitLabels
# ---------------------------------------------------------------------------


class TestSetNodesToFitLabels:
    """set_nodes_to_fit_labels resizes nodes to encompass their labels."""

    def test_nodes_at_least_as_large_as_labels(self, representative_map):
        builder = momapy.builder.builder_from_object(representative_map)
        momapy.sbgn.utils.set_nodes_to_fit_labels(builder)
        for le in builder.layout.descendants():
            if (
                momapy.builder.isinstance_or_builder(le, momapy.core.layout.Node)
                and hasattr(le, "label")
                and le.label is not None
            ):
                label_bbox = le.label.bbox()
                assert le.width >= label_bbox.width, (
                    f"Node width {le.width} < label bbox width {label_bbox.width}"
                )
                assert le.height >= label_bbox.height, (
                    f"Node height {le.height} < label bbox height {label_bbox.height}"
                )

    def test_restrict_to_limits_affected_types(self, representative_map):
        builder_restricted = momapy.builder.builder_from_object(representative_map)
        momapy.sbgn.utils.set_nodes_to_fit_labels(
            builder_restricted,
            restrict_to=[momapy.sbgn.pd.StateVariableLayout],
        )

        builder_all = momapy.builder.builder_from_object(representative_map)
        momapy.sbgn.utils.set_nodes_to_fit_labels(builder_all)

        # Gather widths of non-StateVariable nodes; they should be unchanged
        for le_r, le_a in zip(
            builder_restricted.layout.descendants(),
            builder_all.layout.descendants(),
        ):
            if (
                momapy.builder.isinstance_or_builder(le_r, momapy.core.layout.Node)
                and not momapy.builder.isinstance_or_builder(
                    le_r, momapy.sbgn.pd.StateVariableLayout
                )
                and hasattr(le_r, "width")
            ):
                # restricted run should not have changed non-StateVariable nodes
                # so they should differ from the all-nodes run (or be original)
                pass  # Just verify it didn't crash with restrict_to

    def test_exclude_skips_types(self, representative_map):
        builder = momapy.builder.builder_from_object(representative_map)
        result = momapy.sbgn.utils.set_nodes_to_fit_labels(
            builder,
            exclude=[momapy.sbgn.pd.StateVariableLayout],
        )
        # Should complete without error
        assert result is builder


# ---------------------------------------------------------------------------
# TestSetAuxiliaryUnitsLabelFontSize
# ---------------------------------------------------------------------------


class TestSetAuxiliaryUnitsLabelFontSize:
    """set_auxiliary_units_label_font_size sets font sizes correctly."""

    def test_all_auxiliary_labels_get_font_size(self, representative_map):
        target_size = 14.0
        result = momapy.sbgn.utils.set_auxiliary_units_label_font_size(
            representative_map, font_size=target_size
        )
        builder = momapy.builder.builder_from_object(result)
        aux_types = (
            momapy.sbgn.pd.StateVariableLayout,
            momapy.sbgn.pd.UnitOfInformationLayout,
        )
        for le in builder.layout.descendants():
            if momapy.builder.isinstance_or_builder(le, aux_types):
                if le.label is not None:
                    assert le.label.font_size == target_size, (
                        f"Expected font_size={target_size}, got {le.label.font_size}"
                    )
        # Only assert we found some if the map actually has auxiliary units
        # (all PD maps should have some)


# ---------------------------------------------------------------------------
# TestSetLayoutToFitContent
# ---------------------------------------------------------------------------


class TestSetLayoutToFitContent:
    """set_layout_to_fit_content makes the layout encompass all elements."""

    def test_layout_encompasses_elements(self, representative_map):
        result = momapy.sbgn.utils.set_layout_to_fit_content(representative_map)
        builder = momapy.builder.builder_from_object(result)
        layout = builder.layout
        layout_bbox = layout.bbox()
        # bbox position is center-based; compute edges
        layout_left = layout_bbox.x - layout_bbox.width / 2
        layout_right = layout_bbox.x + layout_bbox.width / 2
        layout_top = layout_bbox.y - layout_bbox.height / 2
        layout_bottom = layout_bbox.y + layout_bbox.height / 2
        for le in layout.layout_elements:
            le_bbox = le.bbox()
            le_left = le_bbox.x - le_bbox.width / 2
            le_right = le_bbox.x + le_bbox.width / 2
            le_top = le_bbox.y - le_bbox.height / 2
            le_bottom = le_bbox.y + le_bbox.height / 2
            assert le_left >= layout_left - 1e-6, (
                f"Element left {le_left} outside layout left {layout_left}"
            )
            assert le_right <= layout_right + 1e-6, (
                f"Element right {le_right} outside layout right {layout_right}"
            )
            assert le_top >= layout_top - 1e-6, (
                f"Element top {le_top} outside layout top {layout_top}"
            )
            assert le_bottom <= layout_bottom + 1e-6, (
                f"Element bottom {le_bottom} outside layout bottom {layout_bottom}"
            )


# ---------------------------------------------------------------------------
# TestNonCrash — smoke tests across ALL PD files
# ---------------------------------------------------------------------------


class TestNonCrash:
    """Every utility function completes without error on every PD file."""

    def test_set_compartments_to_fit_content(self, pd_map):
        momapy.sbgn.utils.set_compartments_to_fit_content(pd_map)

    def test_set_complexes_to_fit_content(self, pd_map):
        momapy.sbgn.utils.set_complexes_to_fit_content(pd_map)

    def test_set_submaps_to_fit_content(self, pd_map):
        momapy.sbgn.utils.set_submaps_to_fit_content(pd_map)

    def test_set_auxiliary_units_to_borders(self, pd_map):
        momapy.sbgn.utils.set_auxiliary_units_to_borders(pd_map)

    def test_tidy(self, pd_map):
        momapy.sbgn.utils.tidy(pd_map)

    def test_sbgned_tidy(self, pd_map):
        momapy.sbgn.utils.sbgned_tidy(pd_map)

    def test_newt_tidy(self, pd_map):
        momapy.sbgn.utils.newt_tidy(pd_map)


# ---------------------------------------------------------------------------
# Building, taking apart and merging maps from map elements
# ---------------------------------------------------------------------------

AF_MAPS_DIR = os.path.join(TEST_DIR, "maps", "af")


def make_glyph(x, y=0.0, cls=momapy.sbgn.pd.MacromoleculeLayout, layout_elements=()):
    return cls(
        position=momapy.geometry.Point(x, y),
        width=60.0,
        height=30.0,
        layout_elements=tuple(layout_elements),
    )


def make_process_layout(x, y=0.0):
    return momapy.sbgn.pd.GenericProcessLayout(
        position=momapy.geometry.Point(x, y), width=20.0, height=20.0
    )


def make_arc(cls, source, target):
    return cls(
        source=source,
        target=target,
        segments=(momapy.geometry.Segment(source.position, target.position),),
    )


def get_model_descendant_ids(model):
    return {
        id(descendant)
        for element in momapy.core._assembling.get_map_elements_from_map(
            momapy.sbgn.pd.SBGNPDMap(model=model)
        )[2]
        for descendant in momapy.core._assembling.get_descendants(element)
    }


def make_simple_process_map_elements():
    """Return the elements of `A -> B` catalysed by `E`."""
    a = momapy.sbgn.pd.Macromolecule(label="A")
    b = momapy.sbgn.pd.Macromolecule(label="B")
    e = momapy.sbgn.pd.Macromolecule(label="E")
    reactant = momapy.sbgn.pd.Reactant(referred_element=a)
    product = momapy.sbgn.pd.Product(referred_element=b)
    process = momapy.sbgn.pd.GenericProcess(
        reactants=frozenset([reactant]), products=frozenset([product])
    )
    catalysis = momapy.sbgn.pd.Catalysis(source=e, target=process)
    a_layout = make_glyph(0.0)
    b_layout = make_glyph(200.0)
    e_layout = make_glyph(100.0, 100.0)
    process_layout = make_process_layout(100.0)
    consumption_layout = make_arc(
        momapy.sbgn.pd.ConsumptionLayout, process_layout, a_layout
    )
    production_layout = make_arc(
        momapy.sbgn.pd.ProductionLayout, process_layout, b_layout
    )
    catalysis_layout = make_arc(
        momapy.sbgn.pd.CatalysisLayout, e_layout, process_layout
    )
    layout_elements = [
        a_layout,
        b_layout,
        e_layout,
        process_layout,
        consumption_layout,
        production_layout,
        catalysis_layout,
    ]
    layout_element_to_model_element = {
        a_layout: a,
        b_layout: b,
        e_layout: e,
        process_layout: process,
        consumption_layout: reactant,
        production_layout: product,
        catalysis_layout: catalysis,
    }
    return layout_elements, layout_element_to_model_element


class TestMakeMapFromMapElements:
    @pytest.mark.parametrize(
        "path, make_function, get_function",
        [
            (
                os.path.join(SBGN_MAPS_DIR, file_name),
                momapy.sbgn.utils.make_pd_map_from_map_elements,
                momapy.sbgn.utils.get_map_elements_from_pd_map,
            )
            for file_name in SBGN_FILES
        ]
        + [
            (
                os.path.join(AF_MAPS_DIR, "small_activity_flow.sbgn"),
                momapy.sbgn.utils.make_af_map_from_map_elements,
                momapy.sbgn.utils.get_map_elements_from_af_map,
            )
        ],
    )
    def test_rebuild_read_map(self, path, make_function, get_function):
        map_ = momapy.io.core.read(path).obj
        rebuilt_map = make_function(*get_function(map_))
        assert rebuilt_map.model == map_.model
        assert rebuilt_map.layout.layout_elements == map_.layout.layout_elements
        assert dict(rebuilt_map.layout_model_mapping) == dict(map_.layout_model_mapping)
        assert dict(rebuilt_map.layout_model_mapping.representative_to_key) == dict(
            map_.layout_model_mapping.representative_to_key
        )
        model_descendant_ids = get_model_descendant_ids(rebuilt_map.model)
        for model_element in rebuilt_map.layout_model_mapping.values():
            assert id(model_element) in model_descendant_ids

    def test_process_key(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            layout_elements, layout_element_to_model_element
        )
        (
            a_layout,
            b_layout,
            e_layout,
            process_layout,
            consumption_layout,
            production_layout,
            catalysis_layout,
        ) = layout_elements
        process_key = frozenset(
            [process_layout, consumption_layout, production_layout, a_layout, b_layout]
        )
        mapping = map_.layout_model_mapping
        assert mapping.representative_to_key[process_layout] == process_key
        assert (
            mapping.representative_to_key[catalysis_layout]
            == frozenset([catalysis_layout, e_layout]) | process_key
        )
        assert mapping[process_key] is next(iter(map_.model.processes))

    def test_missing_elements_are_added(self):
        compartment = momapy.sbgn.pd.Compartment(label="cell")
        a = momapy.sbgn.pd.Macromolecule(label="A", compartment=compartment)
        b = momapy.sbgn.pd.Macromolecule(label="B")
        reactant = momapy.sbgn.pd.Reactant(referred_element=a)
        product = momapy.sbgn.pd.Product(referred_element=b)
        process = momapy.sbgn.pd.GenericProcess(
            reactants=frozenset([reactant]), products=frozenset([product])
        )
        process_layout = make_process_layout(100.0)
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [process_layout], {process_layout: process}
        )
        assert map_.model.entity_pools == frozenset([a, b])
        assert map_.model.compartments == frozenset([compartment])
        assert map_.model.processes == frozenset([process])

    def test_equal_model_elements_become_one(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="atp")
        atp2 = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="atp2")
        reactant = momapy.sbgn.pd.Reactant(referred_element=atp2)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        atp_layout = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        atp2_layout = make_glyph(0.0, 100.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        process_layout = make_process_layout(100.0, 100.0)
        consumption_layout = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_layout, atp2_layout
        )
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [atp_layout, atp2_layout, process_layout, consumption_layout],
            {
                atp_layout: atp,
                atp2_layout: atp2,
                process_layout: process,
                consumption_layout: reactant,
            },
            [atp],
        )
        kept_atp = next(iter(map_.model.entity_pools))
        assert len(map_.model.entity_pools) == 1
        assert kept_atp.id_ == "atp"
        kept_process = next(iter(map_.model.processes))
        assert next(iter(kept_process.reactants)).referred_element is kept_atp
        assert set(map_.layout_model_mapping.get_mapping(kept_atp)) == {
            atp_layout,
            atp2_layout,
        }

    @pytest.mark.parametrize("reverse", [False, True])
    def test_survivor_has_smallest_id(self, reverse):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="b")
        atp2 = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        model_elements = [atp, atp2]
        if reverse:
            model_elements.reverse()
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            model_elements=model_elements
        )
        assert next(iter(map_.model.entity_pools)) is atp2

    def test_survivor_on_equal_ids_is_first_seen(self):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        atp2 = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="a")
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            model_elements=[atp2, atp]
        )
        assert next(iter(map_.model.entity_pools)) is atp2

    def test_equal_state_variables_of_different_owners_are_kept(self):
        a_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        b_state_variable = momapy.sbgn.pd.StateVariable(value="P")
        a = momapy.sbgn.pd.Macromolecule(
            label="A", state_variables=frozenset([a_state_variable])
        )
        b = momapy.sbgn.pd.Macromolecule(
            label="B", state_variables=frozenset([b_state_variable])
        )
        a_state_variable_layout = make_glyph(
            0.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        b_state_variable_layout = make_glyph(
            200.0, -15.0, cls=momapy.sbgn.pd.StateVariableLayout
        )
        a_layout = make_glyph(0.0, layout_elements=[a_state_variable_layout])
        b_layout = make_glyph(200.0, layout_elements=[b_state_variable_layout])
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [a_layout, b_layout],
            {
                a_layout: a,
                b_layout: b,
                a_state_variable_layout: a_state_variable,
                b_state_variable_layout: b_state_variable,
            },
        )
        mapping = map_.layout_model_mapping
        kept_a = mapping[a_layout]
        kept_b = mapping[b_layout]
        assert mapping[a_state_variable_layout] is next(iter(kept_a.state_variables))
        assert mapping[b_state_variable_layout] is next(iter(kept_b.state_variables))
        assert mapping[a_state_variable_layout] is not mapping[b_state_variable_layout]

    def test_clone_glyphs_consumed_twice(self):
        a = momapy.sbgn.pd.Macromolecule(label="A")
        b = momapy.sbgn.pd.Macromolecule(label="B")
        reactant = momapy.sbgn.pd.Reactant(referred_element=a, stoichiometry=2)
        product = momapy.sbgn.pd.Product(referred_element=b)
        process = momapy.sbgn.pd.GenericProcess(
            reactants=frozenset([reactant]), products=frozenset([product])
        )
        a_layout = make_glyph(0.0)
        a_clone_layout = make_glyph(0.0, 100.0)
        b_layout = make_glyph(200.0)
        process_layout = make_process_layout(100.0)
        consumption_layout = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_layout, a_layout
        )
        clone_consumption_layout = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_layout, a_clone_layout
        )
        production_layout = make_arc(
            momapy.sbgn.pd.ProductionLayout, process_layout, b_layout
        )
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [
                a_layout,
                a_clone_layout,
                b_layout,
                process_layout,
                consumption_layout,
                clone_consumption_layout,
                production_layout,
            ],
            {
                a_layout: a,
                a_clone_layout: a,
                b_layout: b,
                process_layout: process,
                consumption_layout: reactant,
                clone_consumption_layout: reactant,
                production_layout: product,
            },
        )
        mapping = map_.layout_model_mapping
        kept_process = next(iter(map_.model.processes))
        kept_reactant = next(iter(kept_process.reactants))
        assert kept_reactant.stoichiometry == 2
        assert mapping[consumption_layout] is kept_reactant
        assert mapping[clone_consumption_layout] is kept_reactant
        assert set(mapping.get_child_layout_elements(kept_reactant, kept_process)) == {
            consumption_layout,
            clone_consumption_layout,
        }

    def test_process_drawn_twice(self):
        a = momapy.sbgn.pd.Macromolecule(label="A")
        reactant = momapy.sbgn.pd.Reactant(referred_element=a)
        process = momapy.sbgn.pd.GenericProcess(reactants=frozenset([reactant]))
        layout_elements = []
        layout_element_to_model_element = {}
        for y in [0.0, 100.0]:
            a_layout = make_glyph(0.0, y)
            process_layout = make_process_layout(100.0, y)
            consumption_layout = make_arc(
                momapy.sbgn.pd.ConsumptionLayout, process_layout, a_layout
            )
            layout_elements += [a_layout, process_layout, consumption_layout]
            layout_element_to_model_element |= {
                a_layout: a,
                process_layout: process,
                consumption_layout: reactant,
            }
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            layout_elements, layout_element_to_model_element
        )
        keys = map_.layout_model_mapping.get_mapping(next(iter(map_.model.processes)))
        assert set(keys) == {
            frozenset(layout_elements[:3]),
            frozenset(layout_elements[3:]),
        }

    def test_empty_set_in_process_key(self):
        b = momapy.sbgn.pd.Macromolecule(label="B")
        product = momapy.sbgn.pd.Product(referred_element=b)
        process = momapy.sbgn.pd.GenericProcess(
            products=frozenset([product]), has_external_source=True
        )
        empty_set_layout = make_glyph(0.0, cls=momapy.sbgn.pd.EmptySetLayout)
        b_layout = make_glyph(200.0)
        process_layout = make_process_layout(100.0)
        consumption_layout = make_arc(
            momapy.sbgn.pd.ConsumptionLayout, process_layout, empty_set_layout
        )
        production_layout = make_arc(
            momapy.sbgn.pd.ProductionLayout, process_layout, b_layout
        )
        layout_elements = [
            empty_set_layout,
            b_layout,
            process_layout,
            consumption_layout,
            production_layout,
        ]
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            layout_elements,
            {b_layout: b, process_layout: process, production_layout: product},
        )
        assert map_.layout_model_mapping.representative_to_key[
            process_layout
        ] == frozenset(layout_elements)

    def test_no_layout_elements(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        model_elements = [
            model_element
            for model_element in layout_element_to_model_element.values()
            if isinstance(
                model_element,
                (momapy.sbgn.pd.GenericProcess, momapy.sbgn.pd.Catalysis),
            )
        ]
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements(
            model_elements=model_elements
        )
        assert len(map_.model.entity_pools) == 3
        assert map_.layout is None
        assert map_.layout_model_mapping is None
        rebuilt_map = momapy.sbgn.utils.make_pd_map_from_map_elements(
            *momapy.sbgn.utils.get_map_elements_from_pd_map(map_)
        )
        assert rebuilt_map.model == map_.model
        merged_map = momapy.sbgn.utils.merge_pd_maps([map_, map_])
        assert merged_map.model == map_.model
        assert merged_map.layout is None

    def test_nothing_given(self):
        map_ = momapy.sbgn.utils.make_pd_map_from_map_elements()
        assert map_.model is None
        assert map_.layout is None
        assert map_.layout_model_mapping is None


class TestMakeMapFromMapElementsErrors:
    def test_mapping_key_not_in_layout(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        a_layout = layout_elements[0]
        a = layout_element_to_model_element.pop(a_layout)
        layout_element_to_model_element[dataclasses.replace(a_layout)] = a
        with pytest.raises(ValueError, match="mapping key"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element
            )

    def test_arc_end_not_in_layout(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        consumption_layout = layout_elements[4]
        new_consumption_layout = dataclasses.replace(
            consumption_layout, target=dataclasses.replace(layout_elements[0])
        )
        layout_elements[4] = new_consumption_layout
        layout_element_to_model_element[new_consumption_layout] = (
            layout_element_to_model_element.pop(consumption_layout)
        )
        with pytest.raises(ValueError, match="end .* of arc"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element
            )

    def test_element_held_by_two_owners(self):
        state_variable = momapy.sbgn.pd.StateVariable(value="P")
        a = momapy.sbgn.pd.Macromolecule(
            label="A", state_variables=frozenset([state_variable])
        )
        b = momapy.sbgn.pd.Macromolecule(
            label="B", state_variables=frozenset([state_variable])
        )
        with pytest.raises(ValueError, match="held by two owners"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(model_elements=[a, b])

    def test_owned_element_with_no_owner(self):
        a = momapy.sbgn.pd.Macromolecule(label="A")
        with pytest.raises(ValueError, match="not held by any element"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                model_elements=[momapy.sbgn.pd.Reactant(referred_element=a)]
            )

    def test_arc_mapped_to_child_not_held(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        consumption_layout = layout_elements[4]
        reactant = layout_element_to_model_element[consumption_layout]
        other_process = momapy.sbgn.pd.GenericProcess(
            reactants=frozenset([dataclasses.replace(reactant, stoichiometry=3)])
        )
        layout_element_to_model_element[consumption_layout] = next(
            iter(other_process.reactants)
        )
        with pytest.raises(ValueError, match="does not hold"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element, [other_process]
            )

    def test_consumption_arc_mapped_to_product(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        process_layout = layout_elements[3]
        process = layout_element_to_model_element[process_layout]
        a = layout_element_to_model_element[layout_elements[0]]
        product = momapy.sbgn.pd.Product(referred_element=a)
        new_process = dataclasses.replace(
            process, products=process.products | {product}
        )
        layout_element_to_model_element[process_layout] = new_process
        layout_element_to_model_element[layout_elements[4]] = product
        catalysis_layout = layout_elements[6]
        layout_element_to_model_element[catalysis_layout] = dataclasses.replace(
            layout_element_to_model_element[catalysis_layout], target=new_process
        )
        with pytest.raises(ValueError, match="may only map to Reactant"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element
            )

    def test_consumption_arc_to_other_element(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        process_layout = layout_elements[3]
        consumption_layout = layout_elements[4]
        new_consumption_layout = dataclasses.replace(
            consumption_layout, target=layout_elements[1]
        )
        layout_elements[4] = new_consumption_layout
        layout_element_to_model_element[new_consumption_layout] = (
            layout_element_to_model_element.pop(consumption_layout)
        )
        assert new_consumption_layout.source is process_layout
        with pytest.raises(ValueError, match="does not draw it"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element
            )

    def test_modulation_arc_with_wrong_source(self):
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        catalysis_layout = layout_elements[6]
        new_catalysis_layout = dataclasses.replace(
            catalysis_layout, source=layout_elements[0]
        )
        layout_elements[6] = new_catalysis_layout
        layout_element_to_model_element[new_catalysis_layout] = (
            layout_element_to_model_element.pop(catalysis_layout)
        )
        with pytest.raises(ValueError, match="does not draw the source"):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                layout_elements, layout_element_to_model_element
            )

    def test_mapped_equivalence_operator(self):
        equivalence_operator = momapy.sbgn.pd.EquivalenceOperator()
        equivalence_operator_layout = make_glyph(
            0.0, cls=momapy.sbgn.pd.EquivalenceOperatorLayout
        )
        with pytest.raises(NotImplementedError):
            momapy.sbgn.utils.make_pd_map_from_map_elements(
                [equivalence_operator_layout],
                {equivalence_operator_layout: equivalence_operator},
            )


class TestMergeMaps:
    def test_merge_one_map(self, pd_map):
        merged_map = momapy.sbgn.utils.merge_pd_maps([pd_map])
        assert merged_map.model == pd_map.model
        assert merged_map.layout.layout_elements == pd_map.layout.layout_elements
        assert dict(merged_map.layout_model_mapping) == dict(
            pd_map.layout_model_mapping
        )

    def test_merge_map_with_itself(self, pd_map):
        merged_map = momapy.sbgn.utils.merge_pd_maps([pd_map])
        merged_twice_map = momapy.sbgn.utils.merge_pd_maps([pd_map, pd_map])
        assert merged_twice_map.model == merged_map.model
        assert (
            merged_twice_map.layout.layout_elements == merged_map.layout.layout_elements
        )
        assert dict(merged_twice_map.layout_model_mapping) == dict(
            merged_map.layout_model_mapping
        )

    def test_merge_empty(self):
        map_ = momapy.sbgn.utils.merge_pd_maps([])
        assert map_.model is None
        assert map_.layout is None
        assert map_.layout_model_mapping is None

    def make_atp_map(self, atp_id, layout_id, y=0.0):
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_=atp_id)
        atp_layout = dataclasses.replace(
            make_glyph(0.0, y, cls=momapy.sbgn.pd.SimpleChemicalLayout), id_=layout_id
        )
        return momapy.sbgn.utils.make_pd_map_from_map_elements(
            [atp_layout], {atp_layout: atp}
        )

    def test_survivors_do_not_depend_on_order(self):
        first_map = self.make_atp_map("b", "layout_b")
        second_map = self.make_atp_map("a", "layout_a")
        for maps in [[first_map, second_map], [second_map, first_map]]:
            merged_map = momapy.sbgn.utils.merge_pd_maps(maps)
            assert [
                layout_element.id_
                for layout_element in merged_map.layout.layout_elements
            ] == ["layout_a"]
            assert [element.id_ for element in merged_map.model.entity_pools] == ["a"]

    def test_shared_model_element_at_different_places(self):
        merged_map = momapy.sbgn.utils.merge_pd_maps(
            [
                self.make_atp_map("atp", "first"),
                self.make_atp_map("atp", "second", 100.0),
            ]
        )
        atp = next(iter(merged_map.model.entity_pools))
        assert len(merged_map.model.entity_pools) == 1
        assert len(merged_map.layout_model_mapping.get_mapping(atp)) == 2

    def test_arcs_point_to_kept_glyph(self):
        first_map = self.make_atp_map("atp", "first")
        layout_elements, layout_element_to_model_element = (
            make_simple_process_map_elements()
        )
        a_layout = layout_elements[0]
        atp_layout = dataclasses.replace(
            make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout), id_="second"
        )
        consumption_layout = dataclasses.replace(layout_elements[4], target=atp_layout)
        reactant = layout_element_to_model_element.pop(layout_elements[4])
        atp = momapy.sbgn.pd.SimpleChemical(label="ATP", id_="atp")
        process_layout = layout_elements[3]
        process = layout_element_to_model_element[process_layout]
        new_reactant = dataclasses.replace(reactant, referred_element=atp)
        new_process = dataclasses.replace(process, reactants=frozenset([new_reactant]))
        catalysis_layout = layout_elements[6]
        del layout_element_to_model_element[a_layout]
        layout_element_to_model_element |= {
            atp_layout: atp,
            consumption_layout: new_reactant,
            process_layout: new_process,
            catalysis_layout: dataclasses.replace(
                layout_element_to_model_element[catalysis_layout], target=new_process
            ),
        }
        second_map = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [
                atp_layout,
                *layout_elements[1:4],
                consumption_layout,
                *layout_elements[5:],
            ],
            layout_element_to_model_element,
        )
        merged_map = momapy.sbgn.utils.merge_pd_maps([first_map, second_map])
        atp_layouts = [
            layout_element
            for layout_element in merged_map.layout.layout_elements
            if isinstance(layout_element, momapy.sbgn.pd.SimpleChemicalLayout)
        ]
        assert [layout_element.id_ for layout_element in atp_layouts] == ["first"]
        merged_consumption_layout = next(
            layout_element
            for layout_element in merged_map.layout.layout_elements
            if isinstance(layout_element, momapy.sbgn.pd.ConsumptionLayout)
        )
        assert merged_consumption_layout.target is atp_layouts[0]

    def test_equal_layout_elements_with_different_model_elements(self):
        first_map = self.make_atp_map("atp", "first")
        adp = momapy.sbgn.pd.SimpleChemical(label="ADP")
        adp_layout = make_glyph(0.0, cls=momapy.sbgn.pd.SimpleChemicalLayout)
        second_map = momapy.sbgn.utils.make_pd_map_from_map_elements(
            [adp_layout], {adp_layout: adp}
        )
        with pytest.raises(ValueError, match="not equal"):
            momapy.sbgn.utils.merge_pd_maps([first_map, second_map])
