"""Tests for momapy.rendering.core module."""

import pytest

import momapy.rendering
import momapy.rendering.core


def test_renderer_registry_exists():
    """Test that renderer registry exists."""
    assert hasattr(momapy.rendering, "renderer_registry")


def test_register_renderer():
    """Test register_renderer function."""

    class DummyRenderer(momapy.rendering.core.Renderer):
        pass

    try:
        momapy.rendering.register_renderer("test_renderer", DummyRenderer)
        assert momapy.rendering.renderer_registry.is_available("test_renderer")
        assert momapy.rendering.renderer_registry.get("test_renderer") == DummyRenderer
    finally:
        # Restore original state - remove test renderer
        if "test_renderer" in momapy.rendering.renderer_registry.list_loaded():
            del momapy.rendering.renderer_registry._loaded_plugins["test_renderer"]


def test_render_layout_element_exists():
    """Test that render_layout_element function exists."""
    assert hasattr(momapy.rendering.core, "render_layout_element")
    assert callable(momapy.rendering.core.render_layout_element)


def test_render_layout_elements_exists():
    """Test that render_layout_elements function exists."""
    assert hasattr(momapy.rendering.core, "render_layout_elements")
    assert callable(momapy.rendering.core.render_layout_elements)


def test_renderer_base_has_no_file_capability():
    """File output is not part of the base Renderer contract."""
    assert not hasattr(momapy.rendering.core.Renderer, "supported_formats")
    assert not hasattr(momapy.rendering.core.Renderer, "from_file")


def test_supports_file_output_mixin_for_svg_native():
    """The svg-native backend mixes in SupportsFileOutput with declared formats."""
    renderer_cls = momapy.rendering.core.get_renderer("svg-native")
    assert issubclass(renderer_cls, momapy.rendering.core.SupportsFileOutput)
    assert issubclass(renderer_cls, momapy.rendering.core.Renderer)
    assert renderer_cls.supported_formats


def test_render_map_rejects_layout_less_map(temp_dir):
    """A map with layout=None raises a clear ValueError instead of AttributeError."""
    import os

    import momapy.builder
    import momapy.core

    builder = momapy.builder.builder_from_object(momapy.core.Map())
    builder.layout = None
    layout_less_map = builder.build()

    output_file = os.path.join(temp_dir, "out.svg")
    with pytest.raises(ValueError, match="no layout"):
        momapy.rendering.core.render_map(layout_less_map, output_file)
    with pytest.raises(ValueError, match="no layout"):
        momapy.rendering.core.render_maps([layout_less_map], output_file)


def test_renderer_render_map_rejects_layout_less_map():
    """Renderer.render_map raises a clear ValueError, like the module-level one.

    Regression (finding 15): the convenience method previously called
    render_layout_element(None) and raised a raw AttributeError.
    """
    import momapy.builder
    import momapy.core

    class DummyRenderer(momapy.rendering.core.Renderer):
        supported_formats = ["svg"]

        def begin_session(self):
            pass

        def end_session(self):
            pass

        def new_page(self, width, height):
            pass

        def render_layout_element(self, layout_element):
            pass

        def render_drawing_element(self, drawing_element):
            pass

        @classmethod
        def from_file(cls, file_path, width, height, format_):
            pass

        def self_save(self):
            pass

        def self_restore(self):
            pass

    builder = momapy.builder.builder_from_object(momapy.core.Map())
    builder.layout = None
    layout_less_map = builder.build()

    renderer = DummyRenderer()
    with pytest.raises(ValueError, match="no layout"):
        renderer.render_map(layout_less_map)


def test_render_layout_elements_rejects_empty_input(temp_dir):
    """Empty input raises a clear ValueError for both multi_pages branches.

    Regression (finding 16): multi_pages=False previously leaked the low-level
    fit([]) message and multi_pages=True silently wrote an empty file.
    """
    import os

    output_file = os.path.join(temp_dir, "out.svg")
    for multi_pages in (False, True):
        with pytest.raises(ValueError, match="no layout elements to render"):
            momapy.rendering.core.render_layout_elements(
                [], output_file, multi_pages=multi_pages
            )


def test_render_maps_rejects_empty_input(temp_dir):
    """render_maps([]) raises its own clear ValueError (finding 16)."""
    import os

    output_file = os.path.join(temp_dir, "out.svg")
    with pytest.raises(ValueError, match="no maps to render"):
        momapy.rendering.core.render_maps([], output_file)


def test_render_layout_elements_rejects_non_file_renderer(sample_map, temp_dir):
    """A renderer without from_file raises a clear error on file output."""
    import os

    class NonFileRenderer(momapy.rendering.core.Renderer):
        supported_formats = ["svg"]

        def begin_session(self):
            pass

        def end_session(self):
            pass

        def new_page(self, width, height):
            pass

        def render_map(self, map_):
            pass

        def render_layout_element(self, layout_element):
            pass

        def render_drawing_element(self, drawing_element):
            pass

    momapy.rendering.register_renderer("test_non_file_renderer", NonFileRenderer)
    try:
        output_file = os.path.join(temp_dir, "out.svg")
        with pytest.raises(ValueError, match="from_file"):
            momapy.rendering.core.render_layout_element(
                sample_map.layout,
                output_file,
                format_="svg",
                renderer="test_non_file_renderer",
            )
    finally:
        loaded = momapy.rendering.renderer_registry._loaded_plugins
        loaded.pop("test_non_file_renderer", None)


def test_make_gradient_matrix_object_bounding_box():
    """Box units map the unit square onto the box, then apply the transform."""
    import numpy
    import momapy.drawing
    import momapy.geometry

    bbox = momapy.geometry.Bbox(momapy.geometry.Point(20.0, 10.0), 20.0, 10.0)
    gradient = momapy.drawing.LinearGradient(
        gradient_transform=(momapy.geometry.Translation(0.5, 0.0),)
    )
    matrix = momapy.rendering.core.make_gradient_matrix(gradient, bbox)
    point = numpy.matmul(matrix, numpy.array([0.5, 1.0, 1.0]))
    assert point[0] == pytest.approx(30.0)
    assert point[1] == pytest.approx(15.0)


def test_make_gradient_matrix_user_space_on_use():
    """User space units ignore the box."""
    import numpy
    import momapy.drawing
    import momapy.geometry

    bbox = momapy.geometry.Bbox(momapy.geometry.Point(20.0, 10.0), 20.0, 10.0)
    gradient = momapy.drawing.LinearGradient(
        gradient_units=momapy.drawing.GradientUnits.USER_SPACE_ON_USE
    )
    matrix = momapy.rendering.core.make_gradient_matrix(gradient, bbox)
    assert numpy.allclose(matrix, numpy.identity(3))
