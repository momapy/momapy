"""Tests for the reading and writing of CellDesigner structural states with no value."""

import os

import pytest

import momapy.io.core
from momapy.celldesigner.layout import StructuralStateLayout

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(TEST_DIR, "..", "fixtures", "empty_structural_states.xml")
TWO_STATES_FIXTURE = os.path.join(
    TEST_DIR, "..", "fixtures", "two_empty_structural_states.xml"
)


def check_structural_state(map_):
    species = next(iter(map_.model.species))
    assert species.structural_state is not None
    assert species.structural_state.value is None
    species_layout = map_.layout.layout_elements[0]
    structural_state_layouts = [
        layout_element
        for layout_element in species_layout.layout_elements
        if isinstance(layout_element, StructuralStateLayout)
    ]
    assert len(structural_state_layouts) == 1
    assert all(
        structural_state_layout.label is None
        for structural_state_layout in structural_state_layouts
    )


def test_read():
    map_ = momapy.io.core.read(FIXTURE).obj
    check_structural_state(map_)
    structural_state_layout_ids = {
        layout_element.id_
        for layout_element in map_.layout.layout_elements[0].layout_elements
    }
    assert structural_state_layout_ids == {"sa1_structural_state_layout"}


def test_round_trip(tmp_path):
    map_ = momapy.io.core.read(FIXTURE).obj
    output_file = tmp_path / "output.xml"
    momapy.io.core.write(map_, str(output_file), writer="celldesigner")
    check_structural_state(momapy.io.core.read(str(output_file)).obj)


def test_two_structural_states_raise():
    with pytest.raises(ValueError, match="several structural states"):
        momapy.io.core.read(TWO_STATES_FIXTURE)
