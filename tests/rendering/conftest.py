"""Shared fixtures for rendering tests."""

import pytest
import tempfile
import os
import momapy.io.core


# Get the directory containing this conftest file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SBGN_MAPS_DIR = os.path.join(TEST_DIR, "..", "sbgn", "maps", "pd")


def get_sbgn_files():
    """Get all SBGN files from the maps directory."""
    if not os.path.exists(SBGN_MAPS_DIR):
        return []
    return [f for f in os.listdir(SBGN_MAPS_DIR) if f.endswith(".sbgn")]


SBGN_FILES = get_sbgn_files()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_map():
    """Load a sample SBGN map for rendering tests."""
    if not SBGN_FILES:
        pytest.skip("No SBGN files found for testing")
    # Use the first available SBGN file
    input_file = os.path.join(SBGN_MAPS_DIR, SBGN_FILES[0])
    result = momapy.io.core.read(input_file)
    return result.obj


@pytest.fixture
def gradient_rectangles():
    """Rectangles filled with each kind of gradient."""
    import momapy.coloring
    import momapy.drawing
    import momapy.geometry

    stops = (
        momapy.drawing.GradientStop(offset=0.0, stop_color=momapy.coloring.red),
        momapy.drawing.GradientStop(offset=1.0, stop_color=momapy.coloring.blue),
    )
    gradients = [
        momapy.drawing.LinearGradient(stops=stops),
        momapy.drawing.LinearGradient(
            gradient_units=momapy.drawing.GradientUnits.USER_SPACE_ON_USE,
            x2=10.0,
            spread_method=momapy.drawing.SpreadMethod.REPEAT,
            gradient_transform=(momapy.geometry.Rotation(0.5),),
            stops=stops,
        ),
        momapy.drawing.RadialGradient(
            fx=0.3, spread_method=momapy.drawing.SpreadMethod.REFLECT, stops=stops
        ),
    ]
    return [
        momapy.drawing.Rectangle(
            point=momapy.geometry.Point(10.0, 10.0),
            width=80.0,
            height=40.0,
            rx=0.0,
            ry=0.0,
            fill=gradient,
            stroke=gradient,
        )
        for gradient in gradients
    ]


@pytest.fixture
def line_join_and_cap_paths():
    """Open paths with each line join and line cap."""
    import momapy.coloring
    import momapy.drawing
    import momapy.geometry

    actions = (
        momapy.drawing.MoveTo(momapy.geometry.Point(10.0, 90.0)),
        momapy.drawing.LineTo(momapy.geometry.Point(50.0, 10.0)),
        momapy.drawing.LineTo(momapy.geometry.Point(90.0, 90.0)),
    )
    return [
        momapy.drawing.Path(
            actions=actions,
            stroke=momapy.coloring.black,
            stroke_width=8.0,
            fill=momapy.drawing.NoneValue,
            stroke_linejoin=line_join,
            stroke_linecap=line_cap,
        )
        for line_join, line_cap in zip(momapy.drawing.LineJoin, momapy.drawing.LineCap)
    ]
