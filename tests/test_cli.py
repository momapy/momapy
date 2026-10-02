"""Tests for momapy CLI module."""

import json
import os
import pathlib
from unittest import mock

import pytest

import momapy.cli
import momapy.io


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_cli_main_with_help(self):
        """Test CLI main with --help shows help."""
        with mock.patch("sys.argv", ["momapy", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
            # argparse exits with 0 for --help
            assert exc_info.value.code == 0

    def test_cli_render_subcommand_help(self):
        """Test render subcommand shows help."""
        with mock.patch("sys.argv", ["momapy", "render", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
            assert exc_info.value.code == 0


class TestCLIRenderCommand:
    """Tests for CLI render command."""

    SBGN_MAP_PATH = os.path.join(
        os.path.dirname(__file__), "sbgn", "maps", "pd", "glycolysis.sbgn"
    )

    def test_render_with_missing_input_file(self, tmp_path, capsys):
        """A missing input file exits cleanly instead of dumping a traceback."""
        with mock.patch(
            "sys.argv",
            [
                "momapy",
                "render",
                "/nonexistent/file.sbgn",
                "-o",
                str(tmp_path / "output.svg"),
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
        assert exc_info.value.code == 1
        assert "error:" in capsys.readouterr().err

    def test_render_with_unsupported_format(self, tmp_path, capsys):
        """An unresolvable output format exits cleanly instead of a traceback."""
        with mock.patch(
            "sys.argv",
            [
                "momapy",
                "render",
                self.SBGN_MAP_PATH,
                "-o",
                str(tmp_path / "output.unsupported"),
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
        assert exc_info.value.code == 1
        assert "error:" in capsys.readouterr().err

    def test_render_with_unknown_renderer(self, tmp_path, capsys):
        """An unknown --renderer exits cleanly instead of a traceback."""
        with mock.patch(
            "sys.argv",
            [
                "momapy",
                "render",
                self.SBGN_MAP_PATH,
                "-o",
                str(tmp_path / "output.svg"),
                "-r",
                "nosuch",
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
        assert exc_info.value.code == 1
        assert "error:" in capsys.readouterr().err


class TestCLIInfoCommand:
    """Tests for CLI info command."""

    SBGN_MAP_PATH = os.path.join(
        os.path.dirname(__file__),
        "sbgn",
        "maps",
        "pd",
        "glycolysis.sbgn",
    )

    def test_info_subcommand_help(self):
        """Test info subcommand shows help."""
        with mock.patch("sys.argv", ["momapy", "info", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
            assert exc_info.value.code == 0

    def test_info_text_output(self, capsys):
        """Test info command text output."""
        with mock.patch("sys.argv", ["momapy", "info", self.SBGN_MAP_PATH]):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "SBGN PD" in captured.out
        assert "entity pools:" in captured.out
        assert "dimensions:" in captured.out

    def test_info_json_output(self, capsys):
        """Test info command JSON output."""
        with mock.patch(
            "sys.argv",
            ["momapy", "info", self.SBGN_MAP_PATH, "--format", "json"],
        ):
            momapy.cli.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["map_type"] == "SBGN PD"
        assert "model" in data
        assert "layout" in data
        assert "entity_pools" in data["model"]
        assert "width" in data["layout"]

    SBML_MAP_PATH = os.path.join(
        os.path.dirname(__file__),
        "sbml",
        "models",
        "Zake2021_Metformin_Human_multiple_PO_dose.xml",
    )

    def test_info_sbml_text_output(self, capsys):
        """Info on a layout-less SBML map summarizes the model without crashing."""
        with mock.patch("sys.argv", ["momapy", "info", self.SBML_MAP_PATH]):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "SBML" in captured.out
        assert "species:" in captured.out
        assert "reactions:" in captured.out
        # SBML has no layout, so the Layout section is omitted.
        assert "Layout:" not in captured.out

    def test_info_sbml_json_output(self, capsys):
        """Info JSON on an SBML map reports layout as null."""
        with mock.patch(
            "sys.argv",
            ["momapy", "info", self.SBML_MAP_PATH, "--format", "json"],
        ):
            momapy.cli.main()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["map_type"] == "SBML"
        assert data["layout"] is None
        assert "reactions" in data["model"]

    def test_info_output_to_file(self, tmp_path):
        """Test info command writes to file when -o is given."""
        output_file = tmp_path / "info.txt"
        with mock.patch(
            "sys.argv",
            ["momapy", "info", self.SBGN_MAP_PATH, "-o", str(output_file)],
        ):
            momapy.cli.main()
        content = output_file.read_text()
        assert "SBGN PD" in content
        assert "entity pools:" in content


class TestCLIExportCommand:
    """Tests for CLI export command."""

    SBGN_MAP_PATH = os.path.join(
        os.path.dirname(__file__),
        "sbgn",
        "maps",
        "pd",
        "glycolysis.sbgn",
    )

    def test_export_to_stdout(self, capsys):
        """Test export command outputs XML to stdout when stdout is a TTY."""
        with (
            mock.patch("sys.argv", ["momapy", "export", self.SBGN_MAP_PATH]),
            mock.patch("sys.stdout.isatty", return_value=True),
        ):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "<?xml" in captured.out
        assert "<sbgn" in captured.out

    def test_export_to_file(self, tmp_path):
        """Test export command writes to file when -o is given."""
        output_file = tmp_path / "output.sbgn"
        with mock.patch(
            "sys.argv",
            ["momapy", "export", self.SBGN_MAP_PATH, "-o", str(output_file)],
        ):
            momapy.cli.main()
        content = output_file.read_text()
        assert "<?xml" in content
        assert "<sbgn" in content

    ANNOTATED_MAP_PATH = os.path.join(
        os.path.dirname(__file__),
        "sbgn",
        "maps",
        "pd",
        "simple_annotated.sbgn",
    )

    def test_export_to_file_preserves_annotations(self, tmp_path):
        """Annotations must survive an export to a file (B9)."""
        output_file = tmp_path / "output.sbgn"
        with mock.patch(
            "sys.argv",
            ["momapy", "export", self.ANNOTATED_MAP_PATH, "-o", str(output_file)],
        ):
            momapy.cli.main()
        content = output_file.read_text()
        assert "urn:miriam:uniprot:P28482" in content
        assert "urn:miriam:pubmed:12345678" in content


class TestCLIListCommand:
    """Tests for CLI list command."""

    def test_list_subcommand_help(self):
        """Test list subcommand shows help."""
        with mock.patch("sys.argv", ["momapy", "list", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                momapy.cli.main()
            assert exc_info.value.code == 0

    def test_list_readers(self, capsys):
        """Test listing available readers."""
        with mock.patch("sys.argv", ["momapy", "list", "readers"]):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "sbgnml" in captured.out
        assert "celldesigner" in captured.out

    def test_list_writers(self, capsys):
        """Test listing available writers."""
        with mock.patch("sys.argv", ["momapy", "list", "writers"]):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "sbgnml" in captured.out

    def test_list_renderers(self, capsys):
        """Test listing available renderers."""
        with mock.patch("sys.argv", ["momapy", "list", "renderers"]):
            momapy.cli.main()
        captured = capsys.readouterr()
        assert "svg-native" in captured.out

    def test_list_invalid_plugin_type(self):
        """Test list with invalid plugin type."""
        with mock.patch("sys.argv", ["momapy", "list", "invalid"]):
            with pytest.raises(SystemExit):
                momapy.cli.main()


class TestCLIMainEntryPoint:
    """Tests for CLI main entry point."""

    def test_cli_module_has_main_function(self):
        """Test that CLI module has a main function."""
        assert hasattr(momapy.cli, "main")
        assert callable(momapy.cli.main)

    def test_cli_module_has_run_function(self):
        """Test that CLI module has an internal _run function."""
        assert hasattr(momapy.cli, "_run")
        assert callable(momapy.cli._run)


class TestCLIVisualizeCommand:
    """Tests for the visualize command's HTML escaping."""

    SBGN_MAP_PATH = os.path.join(
        os.path.dirname(__file__), "sbgn", "maps", "pd", "glycolysis.sbgn"
    )

    def test_make_script_safe_json_escapes_markup(self):
        """Markup in JSON values cannot close the enclosing script element."""
        text = momapy.cli._make_script_safe_json(
            {"label": "</script><script>alert(1)</script>"}
        )
        assert "<" not in text
        assert ">" not in text
        assert "\\u003c" in text

    def test_visualize_escapes_untrusted_values(self, capsys):
        """A malicious label and filename are escaped in the generated page."""
        result = momapy.io.read(self.SBGN_MAP_PATH)
        malicious_label = "</script><script>alert(1)</script>"
        metadata = {
            "n1": {
                "type": "TextLayout",
                "label": malicious_label,
                "model_id": None,
                "parent_id": None,
            }
        }
        with (
            mock.patch.object(
                momapy.cli, "_extract_element_metadata", return_value=metadata
            ),
            mock.patch.object(momapy.cli.webbrowser, "open") as open_mock,
        ):
            momapy.cli._visualize_map(result.obj, "evil<script>.sbgn")
        open_mock.assert_called_once()
        assert open_mock.call_args[0][0].startswith("file://")
        html_path = capsys.readouterr().out.strip().split(": ", 1)[1]
        content = pathlib.Path(html_path).read_text()
        assert "<script>alert(1)" not in content
        assert "\\u003cscript\\u003ealert(1)" in content
        assert "&lt;script&gt;" in content
        assert "escapeHtml(metadata.label)" in content
        pathlib.Path(html_path).unlink()
