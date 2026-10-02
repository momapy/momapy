"""Tests for Cairo rendering."""

import pytest
import os
import momapy.rendering.core

pytestmark = pytest.mark.slow


# Check if Cairo is available
try:
    # Try to import the momapy cairo renderer module itself
    # This will fail if any of the dependencies are missing
    import momapy.rendering.cairo  # noqa: F401

    CAIRO_AVAILABLE = True
except (ImportError, ValueError, AttributeError, ModuleNotFoundError, Exception):
    CAIRO_AVAILABLE = False


@pytest.mark.skipif(
    not CAIRO_AVAILABLE,
    reason="Cairo dependencies not installed (install with: pip install momapy[cairo])",
)
class TestCairoRendering:
    """Tests for Cairo rendering."""

    def test_render_cairo_png(self, sample_map, temp_dir):
        """Test rendering with cairo renderer to PNG format."""
        import momapy.rendering.cairo

        output_file = os.path.join(temp_dir, "test_output_cairo.png")
        momapy.rendering.core.render_layout_element(
            sample_map.layout, output_file, format_="png", renderer="cairo"
        )
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) > 0

    def test_render_cairo_pdf(self, sample_map, temp_dir):
        """Test rendering with cairo renderer to PDF format."""
        import momapy.rendering.cairo

        output_file = os.path.join(temp_dir, "test_output_cairo.pdf")
        momapy.rendering.core.render_layout_element(
            sample_map.layout, output_file, format_="pdf", renderer="cairo"
        )
        assert os.path.exists(output_file)
        assert os.path.getsize(output_file) > 0

    def test_render_gradients(self, gradient_rectangles, temp_dir):
        """Rendering linear and radial gradient paints does not fail."""
        import momapy.rendering.core

        output_file = os.path.join(temp_dir, "gradients.png")
        renderer_cls = momapy.rendering.core.get_renderer("cairo")
        renderer = renderer_cls.from_file(output_file, 100, 100, "png")
        renderer.begin_session()
        for rectangle in gradient_rectangles:
            renderer.render_drawing_element(rectangle)
        renderer.end_session()
        assert os.path.getsize(output_file) > 0

    def test_render_line_joins_and_caps(self, line_join_and_cap_paths, temp_dir):
        """Rendering each line join and line cap does not fail."""
        import momapy.rendering.core

        output_file = os.path.join(temp_dir, "joins.png")
        renderer_cls = momapy.rendering.core.get_renderer("cairo")
        renderer = renderer_cls.from_file(output_file, 100, 100, "png")
        renderer.begin_session()
        for path in line_join_and_cap_paths:
            renderer.render_drawing_element(path)
        renderer.end_session()
        assert os.path.getsize(output_file) > 0
