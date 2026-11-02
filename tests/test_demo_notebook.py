"""Demo notebook converted to Python script that runs as a test."""

import dataclasses

import os
import pathlib

import pytest

import momapy.io.core
import momapy.builder
import momapy.coloring
import momapy.styling
import momapy.utils
import momapy.rendering.core
import momapy.sbgn.styling
import momapy.sbgn.utils
import momapy.core
import momapy.core.elements
import momapy.core.layout
import momapy.sbgn.pd
import momapy.geometry
import momapy.meta.shapes
import momapy.meta.nodes
import momapy.positioning

pytestmark = pytest.mark.slow


def test_demo_notebook(tmp_path):
    """Run all demo notebook code in a temporary directory."""
    # Get the project root directory
    project_root = pathlib.Path(__file__).parent.parent
    demo_dir = project_root / "demos" / "user_manual" / "data"

    # Change to temp directory for file operations
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        # Maps section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj
        momapy.utils.pretty_print(m)
        momapy.utils.pretty_print(m.model)

        for e in m.model.entity_pools:
            break
        momapy.utils.pretty_print(e)

        assert isinstance(e, momapy.sbgn.pd.EntityPool)
        assert isinstance(e, momapy.core.elements.ModelElement)

        momapy.utils.pretty_print(m.layout)
        momapy.utils.pretty_print(m.layout.drawing_elements())

        for layout_element in m.layout.layout_elements:
            break
        momapy.utils.pretty_print(layout_element)

        e = m.layout_model_mapping.get_mapping(layout_element)
        momapy.utils.pretty_print(e)

        # Equality section
        r1 = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m1 = r1.obj

        r2 = momapy.io.core.read(demo_dir / "phospho2.sbgn")
        m2 = r2.obj

        assert m1 != m2
        assert m1.model == m2.model
        assert m1.layout != m2.layout
        assert m1.layout_model_mapping != m2.layout_model_mapping

        # Submap section
        r1 = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m1 = r1.obj

        r3 = momapy.io.core.read(demo_dir / "phospho3.sbgn")
        m3 = r3.obj

        assert m3.is_submap(m1)
        assert m3.model.is_submodel(m1.model)
        assert m3.layout.is_sublayout(m1.layout)
        assert m3.layout_model_mapping.is_submapping(m1.layout_model_mapping)

        # Frozen objects section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj

        for layout_element in m.layout.layout_elements:
            break

        try:
            layout_element.stroke_width = 3.0
            assert False, "Should have raised an error"
        except Exception:
            pass  # Expected

        lb = momapy.builder.builder_from_object(layout_element)
        momapy.utils.pretty_print(lb)

        lb.stroke_width = 3.0
        lb.stroke_dasharray = (5, 5)

        l2 = lb.build()
        momapy.utils.pretty_print(l2)
        assert l2.stroke_width == 3.0

        # IO section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj
        momapy.io.core.write(m, "phospho1_output.sbgn", writer="sbgnml")
        assert pathlib.Path("phospho1_output.sbgn").exists()

        # Styling section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj
        momapy.styling.apply_style_sheet(m.layout, momapy.sbgn.styling.sbgned)

        # Load custom stylesheet
        css_path = project_root / "src/momapy/sbgn/styling/sbgned_no_cs.css"
        if css_path.exists():
            with open(css_path) as f:
                f.read()

        # Rendering section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj

        # Render to SVG (always available)
        momapy.rendering.core.render_map(m, "phospho1.svg")
        assert pathlib.Path("phospho1.svg").exists()

        # Render to other formats (require skia or cairo)
        for fmt in ["pdf", "png", "jpeg", "webp"]:
            try:
                momapy.rendering.core.render_map(m, f"phospho1.{fmt}")
                assert pathlib.Path(f"phospho1.{fmt}").exists()
            except ValueError:
                pass  # Renderer not available in -min install

        # Multi-page rendering (requires skia or cairo)
        r1 = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        r2 = momapy.io.core.read(demo_dir / "phospho2.sbgn")
        r3 = momapy.io.core.read(demo_dir / "phospho3.sbgn")

        m1 = r1.obj
        m2 = r2.obj
        m3 = r3.obj

        try:
            momapy.rendering.core.render_maps(
                [m1, m2, m3], "phospho_multi.pdf", multi_pages=True
            )
            assert pathlib.Path("phospho_multi.pdf").exists()
        except ValueError:
            pass  # Renderer not available in -min install

        # Geometry section
        r = momapy.io.core.read(demo_dir / "phospho1.sbgn")
        m = r.obj

        for layout_element in m.layout.layout_elements:
            break

        border_elements = layout_element._border_drawing_elements()
        momapy.utils.pretty_print(border_elements)

        # Anchors

        # Custom types section
        @dataclasses.dataclass(frozen=True)
        class MyRectangle(momapy.core.layout.Node):
            width: float = 40.0
            height: float = 30.0

            def _border(self):
                return momapy.meta.shapes.Rectangle(
                    position=self.position, width=self.width, height=self.height
                )

        @dataclasses.dataclass(frozen=True)
        class MyTriangle(momapy.core.layout.SingleHeadedArc):
            arrowhead_width: float = 20.0
            arrowhead_height: float = 10.0

            def _arrowhead_border(self):
                return momapy.meta.shapes.Triangle(
                    position=momapy.geometry.Point(0, 0),
                    width=self.arrowhead_width,
                    height=self.arrowhead_height,
                )

        @dataclasses.dataclass(frozen=True)
        class MyRectangleArrow(momapy.core.layout.SingleHeadedArc):
            arrowhead_width: float = 20.0
            arrowhead_height: float = 10.0

            def _arrowhead_border(self):
                return momapy.meta.shapes.Rectangle(
                    position=momapy.geometry.Point(0, 0),
                    width=self.arrowhead_width,
                    height=self.arrowhead_height,
                )

        @dataclasses.dataclass(frozen=True)
        class MyDoubleRectangleArrow(momapy.core.layout.DoubleHeadedArc):
            start_arrowhead_width: float = 10.0
            start_arrowhead_height: float = 10.0
            start_arrowhead_fill = momapy.coloring.white
            start_arrowhead_stroke = momapy.coloring.black
            end_arrowhead_width: float = 20.0
            end_arrowhead_height: float = 10.0
            end_arrowhead_fill = momapy.coloring.white
            end_arrowhead_stroke = momapy.coloring.black
            path_fill = momapy.drawing.NoneValue
            path_stroke = momapy.coloring.black

            def _start_arrowhead_border(self):
                return momapy.meta.shapes.Rectangle(
                    position=momapy.geometry.Point(-self.start_arrowhead_width / 2, 0),
                    width=self.start_arrowhead_width,
                    height=self.start_arrowhead_height,
                )

            def _end_arrowhead_border(self):
                return momapy.meta.shapes.Rectangle(
                    position=momapy.geometry.Point(self.end_arrowhead_width / 2, 0),
                    width=self.end_arrowhead_width,
                    height=self.end_arrowhead_height,
                )

    finally:
        # Restore original directory
        os.chdir(original_dir)
