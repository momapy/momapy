"""SBGN-ML writer classes.

Model-first approach: iterates model collections in dependency order,
looking up layout elements via layout_model_mapping.
"""

import os
import typing

import lxml.etree

from momapy.io.core import Writer
from momapy.io.core import WriterResult
from momapy.io._utils import WritingContext
from momapy.utils import check_parent_dir_exists
from momapy.sbgn import SBGNMap
from momapy.sbgn.io.sbgnml._writing import NSMAP
from momapy.sbgn.io.sbgnml._writing import make_lxml_element
from momapy.sbgn.io.sbgnml._writing import make_sbgnml_map


# ---------------------------------------------------------------------------
# Writer classes
# ---------------------------------------------------------------------------


class SBGNML0_3Writer(Writer):
    """Class for SBGN-ML 0.3 writer objects.

    The single SBGN-ML writer (registered under both ``sbgnml`` and
    ``sbgnml-0.3``). All serialization logic lives in module-level functions;
    this class only provides the ``write`` entry point.
    """

    @classmethod
    def write(
        cls,
        obj: SBGNMap,
        file_path: str | os.PathLike,
        element_to_annotations: dict | None = None,
        element_to_notes: dict | None = None,
        source_id_to_model_element: dict | None = None,
        source_id_to_layout_element: dict | None = None,
        source_id_to_annotations: dict | None = None,
        source_id_to_notes: dict | None = None,
        with_annotations: bool = True,
        with_notes: bool = True,
        **options: typing.Any,
    ) -> WriterResult:
        """Write an SBGN map to an SBGN-ML file.

        Args:
            obj: The SBGN map to serialize.
            file_path: Destination file path.
            element_to_annotations: Optional per-element annotation dict.
            element_to_notes: Optional per-element notes dict.
            source_id_to_model_element: Optional source ID to model
                element mapping from ReaderResult.
            source_id_to_layout_element: Optional source ID to layout
                element mapping from ReaderResult.
            source_id_to_annotations: Optional per-source-id annotations
                from ReaderResult.
            source_id_to_notes: Optional per-source-id notes from
                ReaderResult.
            with_annotations: Whether to write annotations.
            with_notes: Whether to write notes.
            options: Additional options (accepted and ignored).

        Returns:
            WriterResult containing the written object and file path.

        Raises:
            ValueError: If the map has no model or no layout.
            NotImplementedError: If the model has equivalence operators.
        """
        if obj.model is None or obj.layout is None:
            raise ValueError("cannot write a map without both a model and a layout")
        if getattr(obj.model, "equivalence_operators", ()):
            raise NotImplementedError(
                "the SBGN-ML writer does not write equivalence operators"
            )
        check_parent_dir_exists(file_path)
        if element_to_annotations is None:
            element_to_annotations = {}
        if element_to_notes is None:
            element_to_notes = {}
        writing_context = WritingContext(
            map_=obj,
            element_to_annotations=element_to_annotations,
            element_to_notes=element_to_notes,
            source_id_to_model_element=source_id_to_model_element,
            source_id_to_layout_element=source_id_to_layout_element,
            source_id_to_annotations=source_id_to_annotations,
            source_id_to_notes=source_id_to_notes,
            with_annotations=with_annotations,
            with_notes=with_notes,
        )
        sbgnml_sbgn = make_lxml_element("sbgn", nsmap=NSMAP)
        sbgnml_map = make_sbgnml_map(writing_context)
        sbgnml_sbgn.append(sbgnml_map)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                lxml.etree.tostring(
                    sbgnml_sbgn, pretty_print=True, xml_declaration=True
                ).decode()
            )
        return WriterResult(obj=obj, file_path=file_path)
