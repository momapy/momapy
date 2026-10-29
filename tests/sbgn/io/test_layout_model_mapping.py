"""Tests for layout_model_mapping integrity in SBGN reader."""

import pytest
import os
import dataclasses

import momapy.io.core
import momapy.sbgn.pd
import momapy.sbgn.af
import momapy.sbgn
import momapy.core.layout
import momapy.core.mapping

pytestmark = pytest.mark.slow

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SBGN_PD_DIR = os.path.join(TEST_DIR, "..", "maps", "pd")


def get_sbgn_files():
    if not os.path.exists(SBGN_PD_DIR):
        return []
    return [f for f in os.listdir(SBGN_PD_DIR) if f.endswith(".sbgn")]


SBGN_FILES = get_sbgn_files()


def _collect_all_model_elements(obj, visited=None):
    """Recursively collect all dataclass objects reachable from a model."""
    if visited is None:
        visited = set()
    if id(obj) in visited:
        return visited
    visited.add(id(obj))
    result = set()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result.add(obj)
        for field in dataclasses.fields(type(obj)):
            value = getattr(obj, field.name)
            if isinstance(value, frozenset):
                for element in value:
                    result.update(_collect_all_model_elements(element, visited))
            elif dataclasses.is_dataclass(value) and not isinstance(value, type):
                result.update(_collect_all_model_elements(value, visited))
    return result


@pytest.fixture(scope="module", params=SBGN_FILES)
def sbgn_map(request):
    path = os.path.join(SBGN_PD_DIR, request.param)
    result = momapy.io.core.read(path)
    return result.obj


class TestLayoutModelMappingIntegrity:
    """Verify layout_model_mapping consistency after reading."""

    def test_mapping_is_not_none(self, sbgn_map):
        assert sbgn_map.layout_model_mapping is not None

    def test_every_node_layout_is_mapped(self, sbgn_map):
        """Every node layout element should appear in the mapping."""
        mapping = sbgn_map.layout_model_mapping
        for layout_element in sbgn_map.layout.layout_elements:
            if isinstance(layout_element, momapy.core.layout.Node):
                found = False
                if layout_element in mapping:
                    found = True
                else:
                    for key in mapping:
                        if isinstance(key, frozenset) and layout_element in key:
                            found = True
                            break
                assert found, (
                    f"{type(layout_element).__name__}({layout_element.id_}) "
                    f"not found in layout_model_mapping"
                )

    def test_mapping_values_reference_live_model_elements(self, sbgn_map):
        """Mapping values should reference elements in the model, not stale copies."""
        mapping = sbgn_map.layout_model_mapping
        all_model_elements = _collect_all_model_elements(sbgn_map.model)
        for layout_key, model_value in mapping.items():
            if isinstance(model_value, tuple):
                for element in model_value:
                    assert element in all_model_elements, (
                        f"Stale reference: {type(element).__name__}({element.id_}) "
                        f"not in model collections"
                    )
            else:
                assert model_value in all_model_elements, (
                    f"Stale reference: {type(model_value).__name__}({model_value.id_}) "
                    f"not in model collections"
                )

    def test_child_mappings_reference_parent(self, sbgn_map):
        """Child mappings (tuples) should have a parent that is itself mapped."""
        mapping = sbgn_map.layout_model_mapping
        all_mapped_model_elements = set()
        for model_value in mapping.values():
            if isinstance(model_value, tuple):
                for element in model_value:
                    all_mapped_model_elements.add(element)
            else:
                all_mapped_model_elements.add(model_value)
        for layout_key, model_value in mapping.items():
            if isinstance(model_value, tuple) and len(model_value) >= 2:
                parent = model_value[-1]
                assert parent in all_mapped_model_elements, (
                    f"Parent {type(parent).__name__}({parent.id_}) "
                    f"referenced in child mapping but not itself mapped"
                )


class TestFrozensetMappings:
    """Verify frozenset mapping keys for processes and modulations."""

    def test_every_process_is_mapped_via_frozenset(self, sbgn_map):
        """Each process should be mapped via a frozenset key containing
        the process layout, participant arcs, and participant targets."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "processes"):
            pytest.skip("No processes attribute on model")
        process_model_elements = {
            p
            for p in sbgn_map.model.processes
            if isinstance(p, momapy.sbgn.pd.StoichiometricProcess)
        }
        for process in process_model_elements:
            found_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is process:
                    found_key = key
                    break
            assert found_key is not None, (
                f"Process {process.id_} not mapped via frozenset key"
            )
            # The frozenset should contain at least the process layout (representative)
            # plus consumption/production arcs and their entity pool targets
            node_count = sum(
                1 for el in found_key if isinstance(el, momapy.core.layout.Node)
            )
            # At least 1 node (the process layout) and some arcs
            assert node_count >= 1, (
                f"Process {process.id_} frozenset has no node layouts"
            )

    def test_process_representative_to_key_has_representative(self, sbgn_map):
        """Each process frozenset should have exactly one representative in
        _representative_to_key that resolves back to it."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "processes"):
            pytest.skip("No processes attribute on model")
        process_model_elements = {
            p
            for p in sbgn_map.model.processes
            if isinstance(p, momapy.sbgn.pd.StoichiometricProcess)
        }
        for process in process_model_elements:
            frozenset_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is process:
                    frozenset_key = key
                    break
            if frozenset_key is None:
                continue
            representatives = [
                el
                for el in frozenset_key
                if mapping._representative_to_key.get(el) == frozenset_key
            ]
            assert len(representatives) == 1, (
                f"Process {process.id_} frozenset should have exactly 1 "
                f"representative in _representative_to_key, found {len(representatives)}"
            )

    def test_process_participants_mapped_as_children(self, sbgn_map):
        """Each consumption/production arc should be mapped to its participant model
        element and be retrievable via ``get_child_layout_elements`` under the process."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "processes"):
            pytest.skip("No processes attribute on model")
        process_model_elements = {
            p
            for p in sbgn_map.model.processes
            if isinstance(p, momapy.sbgn.pd.StoichiometricProcess)
        }
        for process in process_model_elements:
            frozenset_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is process:
                    frozenset_key = key
                    break
            if frozenset_key is None:
                continue
            arcs_in_frozenset = [
                el for el in frozenset_key if isinstance(el, momapy.core.layout.Arc)
            ]
            for arc in arcs_in_frozenset:
                participant_model_element = mapping.get_mapping(arc)
                if participant_model_element is None:
                    continue
                assert not isinstance(participant_model_element, tuple), (
                    f"Participant arc {type(arc).__name__} should map to a plain "
                    f"participant model element, got tuple"
                )
                child_layouts = mapping.get_child_layout_elements(
                    participant_model_element, process
                )
                assert arc in child_layouts, (
                    f"Arc {type(arc).__name__} not found under participant "
                    f"{type(participant_model_element).__name__} of process "
                    f"{process.id_}"
                )

    def test_every_modulation_is_mapped_via_frozenset(self, sbgn_map):
        """Each modulation should be mapped via a frozenset that includes
        the modulation arc layout plus source and target frozensets."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "modulations"):
            pytest.skip("No modulations attribute on model")
        for modulation in sbgn_map.model.modulations:
            found_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is modulation:
                    found_key = key
                    break
            assert found_key is not None, (
                f"Modulation {modulation.id_} not mapped via frozenset key"
            )
            # Should contain the modulation arc layout plus elements
            # from source and target frozensets
            assert len(found_key) > 1, (
                f"Modulation {modulation.id_} frozenset has only "
                f"{len(found_key)} element(s), expected > 1"
            )

    def test_modulation_representative_to_key_has_representative(self, sbgn_map):
        """Each modulation frozenset should have exactly one representative in
        _representative_to_key that resolves back to it."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "modulations"):
            pytest.skip("No modulations attribute on model")
        for modulation in sbgn_map.model.modulations:
            frozenset_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is modulation:
                    frozenset_key = key
                    break
            if frozenset_key is None:
                continue
            representatives = [
                el
                for el in frozenset_key
                if mapping._representative_to_key.get(el) == frozenset_key
            ]
            assert len(representatives) == 1, (
                f"Modulation {modulation.id_} frozenset should have exactly "
                f"1 representative in _representative_to_key, found {len(representatives)}"
            )

    def test_modulation_frozenset_includes_source_and_target(self, sbgn_map):
        """Modulation frozenset should include elements from the source
        entity/process frozenset and target process frozenset."""
        mapping = sbgn_map.layout_model_mapping
        if not hasattr(sbgn_map.model, "modulations"):
            pytest.skip("No modulations attribute on model")
        for modulation in sbgn_map.model.modulations:
            frozenset_key = None
            for key, value in mapping.items():
                if isinstance(key, frozenset) and value is modulation:
                    frozenset_key = key
                    break
            if frozenset_key is None:
                continue
            # The frozenset should contain the modulation arc layout
            # plus layout elements from the source and target mappings.
            # At minimum: 1 modulation arc + at least 1 source element
            # + at least 1 target element = 3+
            assert len(frozenset_key) >= 3, (
                f"Modulation {modulation.id_} frozenset has only "
                f"{len(frozenset_key)} elements, expected >= 3 "
                f"(arc + source + target)"
            )
