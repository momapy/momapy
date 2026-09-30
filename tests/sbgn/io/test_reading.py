"""Tests for SBGN reading functionality."""

import pytest
import os
import momapy.io.core
import momapy.sbgn
import momapy.sbgn.pd
import momapy.sbml.model
import momapy.core.layout
import frozendict


# Get the directory containing this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SBGN_MAPS_DIR = os.path.join(TEST_DIR, "..", "maps", "pd")


# Discover all .sbgn files in the maps directory
def get_sbgn_files():
    """Get all SBGN files from the maps directory."""
    if not os.path.exists(SBGN_MAPS_DIR):
        return []
    return [f for f in os.listdir(SBGN_MAPS_DIR) if f.endswith(".sbgn")]


SBGN_FILES = get_sbgn_files()


class TestSBGNReading:
    """Tests for reading SBGN files."""

    @pytest.mark.parametrize("filename", SBGN_FILES)
    @pytest.mark.parametrize("return_type", ["map", "model", "layout"])
    def test_read_sbgn_file(self, filename, return_type):
        """Test reading SBGN files with all return types."""
        input_file = os.path.join(SBGN_MAPS_DIR, filename)
        if not os.path.exists(input_file):
            pytest.skip(f"SBGN file {filename} not found")
        result = momapy.io.core.read(input_file, return_type=return_type)
        assert result is not None
        assert result.obj is not None


class TestSBGNReadOptionalParameters:
    """Tests for SBGN read function optional parameters."""

    @pytest.fixture
    def test_file(self):
        """Return path to a test SBGN file."""
        if not SBGN_FILES:
            pytest.skip("No SBGN test files found")
        return os.path.join(SBGN_MAPS_DIR, SBGN_FILES[0])

    @pytest.mark.parametrize(
        "return_type,expected_type",
        [
            ("map", momapy.sbgn.SBGNMap),
            ("model", momapy.sbgn.SBGNModel),
            ("layout", momapy.core.layout.Layout),
        ],
    )
    def test_return_type_parameter(self, test_file, return_type, expected_type):
        """Test return_type parameter returns correct object type."""
        result = momapy.io.core.read(test_file, return_type=return_type)
        assert isinstance(result.obj, expected_type)

    def test_id_to_element_includes_model_and_layout_containers(self, test_file):
        """The container model and layout ids both appear in id_to_element.

        Regression: the model container id was previously omitted (only its
        descendants were inserted), despite id_to_element being documented as
        holding all model and layout elements.
        """
        result = momapy.io.core.read(test_file, return_type="map")
        map_ = result.obj
        assert map_.model.id_ in result.id_to_element
        assert result.id_to_element[map_.model.id_] is map_.model
        assert map_.layout.id_ in result.id_to_element
        assert result.id_to_element[map_.layout.id_] is map_.layout

    def test_with_model_true(self, test_file):
        """Test with_model=True includes model in result."""
        result = momapy.io.core.read(test_file, return_type="map", with_model=True)
        assert result.obj is not None
        assert isinstance(result.obj, momapy.sbgn.SBGNMap)
        # Verify the map has a model
        assert hasattr(result.obj, "model")
        assert result.obj.model is not None

    def test_with_model_false(self, test_file):
        """Test with_model=False excludes model from result."""
        result = momapy.io.core.read(test_file, return_type="map", with_model=False)
        assert result.obj is not None
        assert isinstance(result.obj, momapy.sbgn.SBGNMap)
        # Verify the map has no model (or model is None)
        assert hasattr(result.obj, "model")
        assert result.obj.model is None

    def test_with_layout_true(self, test_file):
        """Test with_layout=True includes layout in result."""
        result = momapy.io.core.read(test_file, return_type="map", with_layout=True)
        assert result.obj is not None
        assert isinstance(result.obj, momapy.sbgn.SBGNMap)
        # Verify the map has a layout
        assert hasattr(result.obj, "layout")
        assert result.obj.layout is not None

    def test_with_layout_false(self, test_file):
        """Test with_layout=False excludes layout from result."""
        result = momapy.io.core.read(test_file, return_type="map", with_layout=False)
        assert result.obj is not None
        assert isinstance(result.obj, momapy.sbgn.SBGNMap)
        # Verify the map has no layout (or layout is None)
        assert hasattr(result.obj, "layout")
        assert result.obj.layout is None

    def test_with_model_and_layout_false(self, test_file):
        """Test with_model=False and with_layout=False yields an all-None map.

        Regression: this combination previously raised UnboundLocalError.
        """
        result = momapy.io.core.read(
            test_file,
            return_type="map",
            with_model=False,
            with_layout=False,
        )
        assert isinstance(result.obj, momapy.sbgn.SBGNMap)
        assert result.obj.model is None
        assert result.obj.layout is None
        assert result.obj.layout_model_mapping is None

    def test_with_annotations_true(self, test_file):
        """Test with_annotations=True includes annotations in result."""
        result = momapy.io.core.read(test_file, with_annotations=True)
        assert hasattr(result, "element_to_annotations")
        assert isinstance(result.element_to_annotations, frozendict.frozendict)
        # Annotations may be empty if file has none, but should be a frozendict

    def test_with_annotations_false(self, test_file):
        """Test with_annotations=False excludes annotations from result."""
        result = momapy.io.core.read(test_file, with_annotations=False)
        assert hasattr(result, "element_to_annotations")
        # Should be empty frozendict when with_annotations=False
        assert result.element_to_annotations == frozendict.frozendict()

    def test_with_notes_true(self, test_file):
        """Test with_notes=True includes notes in result."""
        result = momapy.io.core.read(test_file, with_notes=True)
        assert hasattr(result, "element_to_notes")
        assert isinstance(result.element_to_notes, frozendict.frozendict)
        # Notes may be empty if file has none, but should be a frozendict

    def test_with_notes_false(self, test_file):
        """Test with_notes=False excludes notes from result."""
        result = momapy.io.core.read(test_file, with_notes=False)
        assert hasattr(result, "element_to_notes")
        # Should be empty frozendict when with_notes=False
        assert result.element_to_notes == frozendict.frozendict()


ANNOTATED_FILE = os.path.join(SBGN_MAPS_DIR, "simple_annotated.sbgn")


class TestSBGNAnnotationsContent:
    """Tests that annotations are correctly parsed from SBGN-ML files.

    Uses simple_annotated.sbgn which has RDF annotations on two
    macromolecule glyphs (ERK and MEK).
    """

    @pytest.fixture(scope="class")
    def result(self):
        if not os.path.exists(ANNOTATED_FILE):
            pytest.skip("simple_annotated.sbgn not found")
        return momapy.io.core.read(
            ANNOTATED_FILE, with_annotations=True, with_notes=True
        )

    def _get_element_by_id(self, result, id_):
        """Find an annotated element by its id_."""
        for elem in result.element_to_annotations:
            if getattr(elem, "id_", None) == id_:
                return elem
        return None

    def _get_annotations_by_id(self, result, id_):
        """Get the frozenset of annotations for an element by its id_."""
        elem = self._get_element_by_id(result, id_)
        if elem is not None:
            return result.element_to_annotations.get(elem, frozenset())
        return frozenset()

    def test_annotations_are_non_empty(self, result):
        """Test that the file produces a non-empty annotations dict."""
        non_empty = {
            elem: annots
            for elem, annots in result.element_to_annotations.items()
            if annots
        }
        assert len(non_empty) > 0

    def test_annotation_values_are_frozensets_of_rdf_annotations(self, result):
        """Test that each value is a frozenset of RDFAnnotation objects."""
        for elem, annots in result.element_to_annotations.items():
            assert isinstance(annots, frozenset)
            for a in annots:
                assert isinstance(a, momapy.sbml.model.RDFAnnotation)

    def test_erk_annotations(self, result):
        """Test annotations on glyph1 (ERK macromolecule)."""
        annots = self._get_annotations_by_id(result, "glyph1_model")
        assert len(annots) == 2
        qualifiers = {a.qualifier for a in annots}
        assert qualifiers == {
            momapy.sbml.model.BQBiol.IS,
            momapy.sbml.model.BQBiol.IS_DESCRIBED_BY,
        }
        resources = {r for a in annots for r in a.resources}
        assert "urn:miriam:uniprot:P28482" in resources
        assert "urn:miriam:pubmed:12345678" in resources

    def test_mek_annotation(self, result):
        """Test annotation on glyph2 (MEK macromolecule)."""
        annots = self._get_annotations_by_id(result, "glyph2_model")
        assert len(annots) == 1
        annotation = next(iter(annots))
        assert annotation.qualifier == momapy.sbml.model.BQBiol.IS
        assert annotation.resources == frozenset({"urn:miriam:uniprot:Q02750"})

    def test_annotated_elements_are_macromolecules(self, result):
        """Test that annotated elements are Macromolecule instances."""
        for elem, annots in result.element_to_annotations.items():
            if annots:
                assert isinstance(elem, momapy.sbgn.pd.Macromolecule)

    def test_with_annotations_false_produces_empty(self):
        """Test that with_annotations=False produces no annotations."""
        if not os.path.exists(ANNOTATED_FILE):
            pytest.skip("simple_annotated.sbgn not found")
        result = momapy.io.core.read(ANNOTATED_FILE, with_annotations=False)
        assert result.element_to_annotations == frozendict.frozendict()


class TestSBGNNotesContent:
    """Tests that notes are correctly parsed from SBGN-ML files.

    Uses simple_annotated.sbgn which has notes on the ERK glyph.
    """

    @pytest.fixture(scope="class")
    def result(self):
        if not os.path.exists(ANNOTATED_FILE):
            pytest.skip("simple_annotated.sbgn not found")
        return momapy.io.core.read(
            ANNOTATED_FILE, with_annotations=True, with_notes=True
        )

    def test_notes_are_non_empty(self, result):
        """Test that the file produces a non-empty notes dict."""
        non_empty = {
            elem: notes for elem, notes in result.element_to_notes.items() if notes
        }
        assert len(non_empty) > 0

    def test_notes_values_are_frozensets_of_strings(self, result):
        """Test that each value is a frozenset of str."""
        for elem, notes in result.element_to_notes.items():
            assert isinstance(notes, frozenset)
            for n in notes:
                assert isinstance(n, str)

    def test_erk_notes_content(self, result):
        """Test that glyph1 (ERK) has notes with expected content."""
        for elem, notes in result.element_to_notes.items():
            if getattr(elem, "id_", None) == "glyph1_model" and notes:
                assert len(notes) == 1
                note = next(iter(notes))
                assert "ERK is a MAP kinase" in note
                assert "<html" in note
                return
        pytest.fail("No notes found for glyph1 (ERK)")

    def test_mek_has_no_notes(self, result):
        """Test that glyph2 (MEK) has no notes."""
        for elem, notes in result.element_to_notes.items():
            if getattr(elem, "id_", None) == "glyph2_model":
                assert len(notes) == 0
                return

    def test_with_notes_false_produces_empty(self):
        """Test that with_notes=False produces no notes."""
        if not os.path.exists(ANNOTATED_FILE):
            pytest.skip("simple_annotated.sbgn not found")
        result = momapy.io.core.read(ANNOTATED_FILE, with_notes=False)
        assert result.element_to_notes == frozendict.frozendict()


DEDUP_ANNOTATED_FILE = os.path.join(SBGN_MAPS_DIR, "dedup_annotated.sbgn")


class TestSBGNSourceIdAnnotationsAndNotes:
    """Tests per-source-id annotations/notes on ReaderResult for SBGN-ML.

    Uses dedup_annotated.sbgn which has two macromolecule glyphs with the
    same label (``ERK``) — they deduplicate to a single model element —
    but carry divergent RDF annotations and divergent notes.
    """

    @pytest.fixture(scope="class")
    def result(self):
        if not os.path.exists(DEDUP_ANNOTATED_FILE):
            pytest.skip("dedup_annotated.sbgn not found")
        return momapy.io.core.read(
            DEDUP_ANNOTATED_FILE, with_annotations=True, with_notes=True
        )

    def test_elements_are_deduplicated(self, result):
        """The two ERK glyphs collapse to a single entity pool."""
        assert len(result.obj.model.entity_pools) == 1

    def test_source_id_to_annotations_is_frozendict(self, result):
        assert isinstance(result.source_id_to_annotations, frozendict.frozendict)

    def test_source_id_to_notes_is_frozendict(self, result):
        assert isinstance(result.source_id_to_notes, frozendict.frozendict)

    def test_per_source_annotations_granularity(self, result):
        """Each source glyph keeps its own annotation set."""
        a_annots = result.source_id_to_annotations["glyphA"]
        b_annots = result.source_id_to_annotations["glyphB"]
        a_resources = {r for annot in a_annots for r in annot.resources}
        b_resources = {r for annot in b_annots for r in annot.resources}
        assert "urn:miriam:uniprot:P28482" in a_resources
        assert "urn:miriam:uniprot:P28482" not in b_resources
        assert "urn:miriam:taxonomy:9606" in b_resources
        assert "urn:miriam:taxonomy:9606" not in a_resources

    def test_per_source_notes_granularity(self, result):
        """Each source glyph keeps its own notes set."""
        a_notes = " ".join(result.source_id_to_notes["glyphA"])
        b_notes = " ".join(result.source_id_to_notes["glyphB"])
        assert "glyphA" in a_notes and "glyphB" not in a_notes
        assert "glyphB" in b_notes and "glyphA" not in b_notes

    def test_merged_view_is_union_of_per_source(self, result):
        """For the deduplicated ERK, merged annotations/notes equal the
        union of per-source annotations/notes across source ids that
        bind to it."""
        (erk,) = tuple(result.obj.model.entity_pools)
        source_ids = result.source_id_to_model_element.inverse[id(erk)]
        assert set(source_ids) == {"glyphA", "glyphB"}
        union_annots = set()
        union_notes = set()
        for source_id in source_ids:
            union_annots |= result.source_id_to_annotations.get(source_id, frozenset())
            union_notes |= result.source_id_to_notes.get(source_id, frozenset())
        assert result.element_to_annotations[erk] == frozenset(union_annots)
        assert result.element_to_notes[erk] == frozenset(union_notes)

    def test_with_annotations_false_empties_source_id(self):
        if not os.path.exists(DEDUP_ANNOTATED_FILE):
            pytest.skip("dedup_annotated.sbgn not found")
        result = momapy.io.core.read(DEDUP_ANNOTATED_FILE, with_annotations=False)
        assert result.source_id_to_annotations == frozendict.frozendict()

    def test_with_notes_false_empties_source_id(self):
        if not os.path.exists(DEDUP_ANNOTATED_FILE):
            pytest.skip("dedup_annotated.sbgn not found")
        result = momapy.io.core.read(DEDUP_ANNOTATED_FILE, with_notes=False)
        assert result.source_id_to_notes == frozendict.frozendict()


class TestIsProcessLeftToRight:
    """Unit tests for is_process_left_to_right parsing helper."""

    class _StubProcess:
        """Minimal stand-in for a parsed sbgnml process element."""

        def __init__(self, id_):
            self._id = id_

        def get(self, key):
            if key == "id":
                return self._id
            return None

    def test_no_arcs_defaults_to_left_to_right(self):
        """A process with neither production nor consumption arcs returns True.

        Regression: this both-empty case previously fell off the end and
        implicitly returned None, violating the -> bool contract.
        """
        import momapy.sbgn.io.sbgnml._reading_parsing as parsing

        process = self._StubProcess("p")
        result = parsing.is_process_left_to_right(process, {"p": []})
        assert result is True


_MODULATION_TARGETS_PORT_SBGN = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
    <map language="process description" id="map_port_target">
        <glyph id="glyph1" class="macromolecule">
            <label text="A"/>
            <bbox y="100.0" x="100.0" h="60.0" w="120.0"/>
        </glyph>
        <glyph id="glyph2" class="macromolecule">
            <label text="B"/>
            <bbox y="100.0" x="300.0" h="60.0" w="120.0"/>
        </glyph>
        <glyph id="glyph3" class="process">
            <bbox y="120.0" x="250.0" h="20.0" w="20.0"/>
            <port id="glyph3.1" y="130.0" x="240.0"/>
            <port id="glyph3.2" y="130.0" x="280.0"/>
        </glyph>
        <glyph id="glyph4" class="macromolecule">
            <label text="Cat"/>
            <bbox y="300.0" x="240.0" h="60.0" w="120.0"/>
        </glyph>
        <arc id="arc1" target="glyph3.1" source="glyph1" class="consumption">
            <start y="130.0" x="220.0"/>
            <end y="130.0" x="240.0"/>
        </arc>
        <arc id="arc2" target="glyph2" source="glyph3.2" class="production">
            <start y="130.0" x="280.0"/>
            <end y="130.0" x="300.0"/>
        </arc>
        <arc id="arc3" target="glyph3.1" source="glyph4" class="catalysis">
            <start y="300.0" x="260.0"/>
            <end y="145.0" x="260.0"/>
        </arc>
    </map>
</sbgn>
"""


_LABELLESS_STOICHIOMETRY_SBGN = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
    <map language="process description" id="map_stoich">
        <glyph id="glyph1" class="macromolecule">
            <label text="A"/>
            <bbox y="100.0" x="100.0" h="60.0" w="120.0"/>
        </glyph>
        <glyph id="glyph2" class="macromolecule">
            <label text="B"/>
            <bbox y="100.0" x="300.0" h="60.0" w="120.0"/>
        </glyph>
        <glyph id="glyph3" class="process">
            <bbox y="120.0" x="250.0" h="20.0" w="20.0"/>
            <port id="glyph3.1" y="130.0" x="240.0"/>
            <port id="glyph3.2" y="130.0" x="280.0"/>
        </glyph>
        <arc id="arc1" target="glyph3.1" source="glyph1" class="consumption">
            <start y="130.0" x="220.0"/>
            <end y="130.0" x="240.0"/>
            <glyph id="stoich1" class="stoichiometry">
                <bbox y="118.0" x="222.0" h="16.0" w="16.0"/>
            </glyph>
        </arc>
        <arc id="arc2" target="glyph2" source="glyph3.2" class="production">
            <start y="130.0" x="280.0"/>
            <end y="130.0" x="300.0"/>
        </arc>
    </map>
</sbgn>
"""


class TestLabellessStoichiometry:
    """Regression (finding 14): a label-less stoichiometry glyph is kept.

    The ``layout_elements.append`` was nested in the label guard, so a
    ``<glyph class="stoichiometry">`` with no ``<label>`` was positioned then
    silently discarded from the layout.
    """

    @pytest.fixture
    def sbgn_file(self, tmp_path):
        path = tmp_path / "labelless_stoichiometry.sbgn"
        path.write_text(_LABELLESS_STOICHIOMETRY_SBGN)
        return str(path)

    def test_labelless_stoichiometry_is_attached(self, sbgn_file):
        import momapy.sbgn.pd

        layout = momapy.io.core.read(sbgn_file, return_type="layout").obj
        cardinalities = [
            descendant
            for descendant in layout.descendants()
            if isinstance(descendant, momapy.sbgn.pd.CardinalityLayout)
        ]
        assert len(cardinalities) == 1
        assert cardinalities[0].label is None


class TestModulationTargetsPort:
    """Regression: a modulation arc whose target is a process port.

    Previously the reader port-resolved the arc source but not the target,
    so ``return_type="map"``/``"layout"`` raised ``KeyError`` at the layout
    lookup and ``return_type="model"`` silently produced ``target=None``.
    """

    @pytest.fixture
    def sbgn_file(self, tmp_path):
        path = tmp_path / "modulation_targets_port.sbgn"
        path.write_text(_MODULATION_TARGETS_PORT_SBGN)
        return str(path)

    @pytest.mark.parametrize("return_type", ["map", "model", "layout"])
    def test_read_does_not_crash(self, sbgn_file, return_type):
        result = momapy.io.core.read(sbgn_file, return_type=return_type)
        assert result.obj is not None

    def test_model_target_resolves_to_process(self, sbgn_file):
        model = momapy.io.core.read(sbgn_file, return_type="model").obj
        (modulation,) = tuple(model.modulations)
        assert modulation.target is not None
        assert modulation.target in model.processes


_COMPARTMENT_LABEL_BBOX_SBGN = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sbgn xmlns="http://sbgn.org/libsbgn/0.3">
    <map language="process description" id="map_label_bbox">
        <glyph id="glyph1" class="compartment">
            <label text="cytosol">
                <bbox y="20.0" x="300.0" h="20.0" w="80.0"/>
            </label>
            <bbox y="0.0" x="0.0" h="200.0" w="400.0"/>
        </glyph>
        <glyph id="glyph2" class="compartment">
            <label text="nucleus"/>
            <bbox y="300.0" x="0.0" h="200.0" w="400.0"/>
        </glyph>
    </map>
</sbgn>
"""


class TestLabelBbox:
    """A label with a bbox is placed at the center of that bbox."""

    @pytest.fixture
    def sbgn_file(self, tmp_path):
        path = tmp_path / "compartment_label_bbox.sbgn"
        path.write_text(_COMPARTMENT_LABEL_BBOX_SBGN)
        return str(path)

    def test_label_position(self, sbgn_file):
        from momapy.geometry import Point

        layout = momapy.io.core.read(sbgn_file, return_type="layout").obj
        labels = {
            layout_element.id_: layout_element.label.position
            for layout_element in layout.layout_elements
        }
        assert labels["glyph1"] == Point(340.0, 30.0)
        assert labels["glyph2"] == Point(200.0, 400.0)
