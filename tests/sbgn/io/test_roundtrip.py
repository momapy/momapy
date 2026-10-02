"""Round-trip tests for SBGN import/export."""

import pytest
import tempfile
import os
import momapy.io.core
import momapy.sbml.model

pytestmark = pytest.mark.slow


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


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestSBGNRoundTrip:
    """Tests for SBGN round-trip import/export."""

    @pytest.mark.parametrize("filename", SBGN_FILES)
    def test_roundtrip_sbgn_file(self, filename, temp_dir):
        """Test round-trip: import -> export -> import and check equality."""
        input_file = os.path.join(SBGN_MAPS_DIR, filename)
        if not os.path.exists(input_file):
            pytest.skip(f"SBGN file {filename} not found")
        result1 = momapy.io.core.read(input_file)
        map1 = result1.obj
        output_file = os.path.join(temp_dir, f"output_{filename}")
        momapy.io.core.write(map1, output_file, writer="sbgnml-0.3")
        result2 = momapy.io.core.read(output_file)
        map2 = result2.obj
        assert map1 == map2

    @pytest.mark.parametrize("filename", SBGN_FILES[:1])
    def test_write_returns_writer_result(self, filename, temp_dir):
        """The SBGN-ML writer returns a WriterResult with the file path."""
        input_file = os.path.join(SBGN_MAPS_DIR, filename)
        if not os.path.exists(input_file):
            pytest.skip(f"SBGN file {filename} not found")
        map_ = momapy.io.core.read(input_file).obj
        output_file = os.path.join(temp_dir, f"output_{filename}")
        result = momapy.io.core.write(map_, output_file, writer="sbgnml-0.3")
        assert isinstance(result, momapy.io.core.WriterResult)
        assert result.file_path == output_file
        assert result.obj is map_


# One biological activity per AF unit-of-information entity type. Each unit of
# information is encoded the spec-correct way: class="unit of information" with
# an <entity name="..."/> child naming the entity type.
_AF_UOI_ENTITY_NAMES = [
    "unspecified entity",
    "macromolecule",
    "simple chemical",
    "nucleic acid feature",
    "complex",
    "perturbation",
]

_AF_UOI_EXPECTED_MODEL_CLASSES = {
    "unspecified entity": "UnspecifiedEntityUnitOfInformation",
    "macromolecule": "MacromoleculeUnitOfInformation",
    "simple chemical": "SimpleChemicalUnitOfInformation",
    "nucleic acid feature": "NucleicAcidFeatureUnitOfInformation",
    "complex": "ComplexUnitOfInformation",
    "perturbation": "PerturbationUnitOfInformation",
}


def _make_af_uoi_sbgnml():
    """Build a minimal AF map with one biological activity per UoI type."""
    glyphs = []
    for i, name in enumerate(_AF_UOI_ENTITY_NAMES):
        glyphs.append(
            f'  <glyph id="a{i}" class="biological activity">\n'
            f'    <label text="A{i}"/>\n'
            f'    <bbox x="{100 + i * 200}" y="100" w="120" h="60"/>\n'
            f'    <glyph id="u{i}" class="unit of information">\n'
            f'      <entity name="{name}"/>\n'
            f'      <bbox x="{110 + i * 200}" y="94" w="24" h="12"/>\n'
            f"    </glyph>\n"
            f"  </glyph>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbgn xmlns="http://sbgn.org/libsbgn/0.3">\n'
        '  <map language="activity flow">\n'
        + "\n".join(glyphs)
        + "\n  </map>\n</sbgn>\n"
    )


class TestSBGNAFUnitOfInformationRoundTrip:
    """Regression tests for AF unit-of-information serialization.

    AF units of information were silently lost on write because the writer
    emitted a bare entity class (e.g. ``class="macromolecule"``) instead of
    ``class="unit of information"`` with an ``<entity name="..."/>`` child,
    which the reader could not classify.
    """

    def test_af_unit_of_information_roundtrip(self, temp_dir):
        input_file = os.path.join(temp_dir, "af_uoi.sbgn")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(_make_af_uoi_sbgnml())

        map1 = momapy.io.core.read(input_file, reader="sbgnml").obj
        read_model = {
            activity.label: [
                type(uoi).__name__ for uoi in activity.units_of_information
            ]
            for activity in map1.model.activities
        }
        expected = {
            f"A{i}": [_AF_UOI_EXPECTED_MODEL_CLASSES[name]]
            for i, name in enumerate(_AF_UOI_ENTITY_NAMES)
        }
        assert read_model == expected

        output_file = os.path.join(temp_dir, "af_uoi_out.sbgn")
        momapy.io.core.write(map1, output_file, writer="sbgnml-0.3")
        map2 = momapy.io.core.read(output_file, reader="sbgnml").obj

        # Model: every unit of information survives the round-trip unchanged.
        roundtrip_model = {
            activity.label: [
                type(uoi).__name__ for uoi in activity.units_of_information
            ]
            for activity in map2.model.activities
        }
        assert roundtrip_model == expected

        # Layout: every biological activity keeps its UoI sub-layout.
        roundtrip_layout = {
            le.label.text: [type(child).__name__ for child in le.layout_elements]
            for le in map2.layout.layout_elements
            if type(le).__name__ == "BiologicalActivityLayout"
        }
        expected_layout = {
            f"A{i}": [f"{_AF_UOI_EXPECTED_MODEL_CLASSES[name]}Layout"]
            for i, name in enumerate(_AF_UOI_ENTITY_NAMES)
        }
        assert roundtrip_layout == expected_layout

        # Full structural equality is the strongest guarantee.
        assert map1 == map2


_MAP_ANNOTATION_ID = "map_maplevel"
_MAP_ANNOTATION_RESOURCE = "urn:miriam:reactome:R-HSA-109581"


def _make_map_annotated_sbgnml():
    """Build a minimal PD map carrying a ``<map>``-level RDF annotation."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbgn xmlns="http://sbgn.org/libsbgn/0.3">\n'
        f'  <map language="process description" id="{_MAP_ANNOTATION_ID}">\n'
        "    <extension>\n"
        "      <annotation>\n"
        '        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
        '                 xmlns:bqbiol="http://biomodels.net/biology-qualifiers/">\n'
        f'          <rdf:Description rdf:about="#{_MAP_ANNOTATION_ID}">\n'
        "            <bqbiol:is>\n"
        "              <rdf:Bag>\n"
        f'                <rdf:li rdf:resource="{_MAP_ANNOTATION_RESOURCE}"/>\n'
        "              </rdf:Bag>\n"
        "            </bqbiol:is>\n"
        "          </rdf:Description>\n"
        "        </rdf:RDF>\n"
        "      </annotation>\n"
        "    </extension>\n"
        '    <glyph id="glyph1" class="macromolecule">\n'
        '      <label text="ERK"/>\n'
        '      <bbox x="100" y="100" w="120" h="60"/>\n'
        "    </glyph>\n"
        "  </map>\n"
        "</sbgn>\n"
    )


class TestSBGNMapAnnotationRoundTrip:
    """Regression test for map-level annotation serialization.

    Map-level RDF annotations were silently dropped on write: the reader
    stored them on the ``Map`` object, but ``make_sbgnml_map`` never emitted
    them onto the ``<map>`` element (unlike every glyph and arc).
    """

    def test_map_level_annotation_roundtrip(self, temp_dir):
        input_file = os.path.join(temp_dir, "map_annotated.sbgn")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(_make_map_annotated_sbgnml())

        expected = momapy.sbml.model.RDFAnnotation(
            qualifier=momapy.sbml.model.BQBiol.IS,
            resources=frozenset({_MAP_ANNOTATION_RESOURCE}),
        )

        # The reader attaches the map-level annotation to the Map object.
        result1 = momapy.io.core.read(
            input_file, reader="sbgnml", with_annotations=True
        )
        map1 = result1.obj
        assert map1 in result1.element_to_annotations
        assert expected in result1.element_to_annotations[map1]

        # The writer must emit it again so a re-read recovers it.
        output_file = os.path.join(temp_dir, "map_annotated_out.sbgn")
        momapy.io.core.write(
            map1,
            output_file,
            writer="sbgnml-0.3",
            element_to_annotations=result1.element_to_annotations,
        )
        result2 = momapy.io.core.read(
            output_file, reader="sbgnml", with_annotations=True
        )
        map2 = result2.obj
        assert map2 in result2.element_to_annotations
        assert expected in result2.element_to_annotations[map2]


def _make_stoichiometry_sbgnml():
    """Build a minimal PD map with cardinality on both process arcs."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sbgn xmlns="http://sbgn.org/libsbgn/0.3">\n'
        '  <map language="process description">\n'
        '    <glyph id="m1" class="macromolecule">\n'
        '      <label text="M1"/>\n'
        '      <bbox x="100" y="100" w="80" h="40"/>\n'
        "    </glyph>\n"
        '    <glyph id="m2" class="macromolecule">\n'
        '      <label text="M2"/>\n'
        '      <bbox x="300" y="100" w="80" h="40"/>\n'
        "    </glyph>\n"
        '    <glyph id="p1" class="process">\n'
        '      <bbox x="190" y="80" w="20" h="20"/>\n'
        "    </glyph>\n"
        '    <arc id="c1" class="consumption" source="m1" target="p1">\n'
        '      <start x="140" y="120"/>\n'
        '      <end x="190" y="90"/>\n'
        '      <glyph id="s1" class="stoichiometry">\n'
        '        <label text="2"/>\n'
        '        <bbox x="150" y="90" w="16" h="16"/>\n'
        "      </glyph>\n"
        "    </arc>\n"
        '    <arc id="pr1" class="production" source="p1" target="m2">\n'
        '      <start x="210" y="90"/>\n'
        '      <end x="260" y="120"/>\n'
        '      <glyph id="s2" class="stoichiometry">\n'
        '        <label text="3"/>\n'
        '        <bbox x="220" y="90" w="16" h="16"/>\n'
        "      </glyph>\n"
        "    </arc>\n"
        "  </map>\n"
        "</sbgn>\n"
    )


class TestSBGNStoichiometryRoundTrip:
    """Regression test for cardinality serialization.

    The reader stored stoichiometry as a ``CardinalityLayout`` child of the
    process arc, but the writer emitted no ``<glyph class="stoichiometry">``,
    so every cardinality glyph was silently dropped on write.
    """

    def test_stoichiometry_roundtrip(self, temp_dir):
        input_file = os.path.join(temp_dir, "stoichiometry.sbgn")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(_make_stoichiometry_sbgnml())

        map1 = momapy.io.core.read(input_file, reader="sbgnml").obj

        def cardinality_texts(map_):
            texts = []
            for layout_element in map_.layout.layout_elements:
                for child in getattr(layout_element, "layout_elements", []):
                    if type(child).__name__ == "CardinalityLayout":
                        texts.append(child.label.text)
            return sorted(texts)

        assert cardinality_texts(map1) == ["2", "3"]

        output_file = os.path.join(temp_dir, "stoichiometry_out.sbgn")
        momapy.io.core.write(map1, output_file, writer="sbgnml-0.3")
        with open(output_file, encoding="utf-8") as f:
            output_text = f.read()
        assert output_text.count('class="stoichiometry"') == 2

        map2 = momapy.io.core.read(output_file, reader="sbgnml").obj
        assert cardinality_texts(map2) == ["2", "3"]
        assert map1 == map2
