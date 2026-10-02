"""Pickle-based reader and writer.

Pickle is format-agnostic: the class of the pickled `obj` (SBGN map,
CellDesigner map, ...) survives the round-trip unchanged, so one pair
of classes handles all formats. Registered under the single name
`"pickle"` in `momapy.io`.
"""

import collections.abc
import os
import pickle
import typing

from momapy.builder import builder_from_object
from momapy.builder import object_from_builder
from momapy.core.elements import LayoutElement
from momapy.core.elements import ModelElement
from momapy.core.layout import Layout
from momapy.core.map import Map
from momapy.core.model import Model
from momapy.io._utils import build_id_to_element
from momapy.io.core import Reader
from momapy.io.core import ReaderResult
from momapy.io.core import Writer
from momapy.io.core import WriterResult
from momapy.utils import check_parent_dir_exists

_PICKLE_PROTOCOL_HEADER = b"\x80"


def _filter_mapping_by_classes(
    mapping: collections.abc.Mapping,
    include_classes: collections.abc.Iterable[type] | None = None,
    exclude_classes: collections.abc.Iterable[type] | None = None,
) -> collections.abc.Mapping:
    """Return a new mapping of the same type with filtered keys.

    A key is kept unless it is an instance of any class in
    ``exclude_classes`` without also being an instance of any class in
    ``include_classes``. Non-mutating: the original mapping (which may
    be a `frozendict`) is not touched.
    """
    if include_classes is None:
        include_classes = []
    if exclude_classes is None:
        exclude_classes = [object]
    include = tuple(include_classes)
    exclude = tuple(exclude_classes)
    kept = {
        key: value
        for key, value in mapping.items()
        if not (isinstance(key, exclude) and not isinstance(key, include))
    }
    return type(mapping)(kept)


def _filter_annotation_mappings(
    reader_result: ReaderResult,
    include_classes: collections.abc.Iterable[type] | None = None,
    exclude_classes: collections.abc.Iterable[type] | None = None,
) -> None:
    """Rebuild `element_to_annotations` / `element_to_notes` filtered."""
    if reader_result.element_to_annotations is not None:
        reader_result.element_to_annotations = _filter_mapping_by_classes(
            reader_result.element_to_annotations,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
        )
    if reader_result.element_to_notes is not None:
        reader_result.element_to_notes = _filter_mapping_by_classes(
            reader_result.element_to_notes,
            include_classes=include_classes,
            exclude_classes=exclude_classes,
        )


class PickleReader(Reader):
    """Reader for pickled maps."""

    @classmethod
    def check_file(cls, file_path: str | os.PathLike) -> bool:
        r"""Return `True` if the file starts with a pickle protocol header.

        Only the first byte is read and the file is never unpickled, so
        auto-detection cannot execute code from the file. The `PROTO` opcode
        `b"\x80"` is the first byte of every pickle protocol since protocol 2,
        including the Python default protocol used by `PickleWriter`. Protocols
        0 and 1 do not carry it and are therefore not auto-detected; reading
        them still works through an explicit `reader="pickle"`.

        Args:
            file_path: Path of the file to check.

        Returns:
            `True` if the file starts with the pickle protocol header.
        """
        with open(file_path, "rb") as f:
            header = f.read(1)
        return header == _PICKLE_PROTOCOL_HEADER

    @classmethod
    def read(
        cls,
        file_path: str | os.PathLike,
        return_type: typing.Literal["map", "model", "layout"] = "map",
        with_model: bool = True,
        with_layout: bool = True,
        with_annotations: bool = True,
        with_notes: bool = True,
        **options: typing.Any,
    ) -> ReaderResult:
        """Load a pickled `ReaderResult` and project it per the flags.

        Pickle is shape-agnostic: the pickled `obj` may be a `Map`, a bare
        `Model`, or a bare `Layout`. When `obj` is a `Map` it is projected as
        requested; when `obj` is already a bare `Model`/`Layout` it is returned
        as-is if it matches `return_type`. A mismatch (e.g. `return_type="map"`
        on a bare `Model`) raises `ValueError`.

        Args:
            file_path: Path of the pickle file to read.
            return_type: Shape of `result.obj`: `"map"` (default) returns the
                pickled map, `"model"` returns its model, `"layout"` returns
                its layout.
            with_model: Whether to keep the model. When `False` and
                `return_type="map"`, the map's `model` is set to `None`.
                Defaults to `True`.
            with_layout: Whether to keep the layout. When `False` and
                `return_type="map"`, the map's `layout` is set to `None`.
                Defaults to `True`.
            with_annotations: Whether to keep annotations. Defaults to `True`.
            with_notes: Whether to keep notes. Defaults to `True`.
            options: Additional reader-specific options (ignored).

        Returns:
            The unpickled `ReaderResult`, projected per the flags.

        Raises:
            ValueError: If the file does not contain a `ReaderResult`, or if
                `return_type` is incompatible with the pickled object's shape
                (e.g. a bare `Model` requested as a `"map"`).
        """
        with open(file_path, "rb") as f:
            reader_result = pickle.load(f)
        if not isinstance(reader_result, ReaderResult):
            raise ValueError(
                "pickle file does not contain a momapy ReaderResult: "
                f"{type(reader_result).__name__}"
            )
        if not with_annotations:
            reader_result.element_to_annotations = None
        if not with_notes:
            reader_result.element_to_notes = None
        obj = reader_result.obj
        if return_type == "model":
            if isinstance(obj, Map):
                obj = obj.model
            elif not isinstance(obj, Model):
                raise ValueError(
                    f"cannot return a model from a pickled {type(obj).__name__}"
                )
            _filter_annotation_mappings(
                reader_result,
                include_classes=[ModelElement, Model],
            )
        elif return_type == "layout":
            if isinstance(obj, Map):
                obj = obj.layout
            elif not isinstance(obj, Layout):
                raise ValueError(
                    f"cannot return a layout from a pickled {type(obj).__name__}"
                )
            _filter_annotation_mappings(
                reader_result,
                include_classes=[LayoutElement],
            )
        else:
            if not isinstance(obj, Map):
                raise ValueError(
                    f"cannot return a map from a pickled {type(obj).__name__}"
                )
            if not with_model or not with_layout:
                map_builder = builder_from_object(obj)
                if not with_model:
                    map_builder.model = None
                    _filter_annotation_mappings(
                        reader_result,
                        exclude_classes=[ModelElement],
                    )
                if not with_layout:
                    map_builder.layout = None
                    _filter_annotation_mappings(
                        reader_result,
                        exclude_classes=[LayoutElement],
                    )
                map_builder.layout_model_mapping = None
                obj = object_from_builder(map_builder)
        reader_result.obj = obj
        # Match the native readers' ReaderResult contract for the projected obj:
        # null out the source-id table for a side the result no longer carries,
        # and rebuild id_to_element from the projected obj (findings 27, 28).
        if isinstance(obj, Map):
            has_model = obj.model is not None
            has_layout = obj.layout is not None
        else:
            has_model = isinstance(obj, Model)
            has_layout = isinstance(obj, Layout)
        if not has_model:
            reader_result.source_id_to_model_element = None
        if not has_layout:
            reader_result.source_id_to_layout_element = None
        reader_result.id_to_element = build_id_to_element(obj)
        return reader_result


class PickleWriter(Writer):
    """Writer for pickled maps."""

    @classmethod
    def write(
        cls,
        obj: typing.Any,
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
        """Pickle a `ReaderResult` holding `obj` and its side-tables.

        Args:
            obj: The object to pickle. Pickle is format-agnostic, so this may
                be a `Map` or a bare `Model`/`Layout` (matching the reader's
                shape-agnostic contract).
            file_path: Destination file path.
            element_to_annotations: Optional per-element annotation dict.
            element_to_notes: Optional per-element notes dict.
            source_id_to_model_element: Optional source id to model
                element mapping from a `ReaderResult`.
            source_id_to_layout_element: Optional source id to layout
                element mapping from a `ReaderResult`.
            source_id_to_annotations: Optional per-source-id annotations
                from a `ReaderResult`.
            source_id_to_notes: Optional per-source-id notes from a
                `ReaderResult`.
            with_annotations: Whether to persist annotations. When False,
                the annotation tables are dropped before pickling.
            with_notes: Whether to persist notes. When False, the notes
                tables are dropped before pickling.
            options: Additional options (accepted and ignored).

        Returns:
            WriterResult containing the written object and file path.
        """
        check_parent_dir_exists(file_path)
        if not with_annotations:
            element_to_annotations = None
            source_id_to_annotations = None
        if not with_notes:
            element_to_notes = None
            source_id_to_notes = None
        reader_result = ReaderResult(
            obj=obj,
            element_to_annotations=element_to_annotations,
            element_to_notes=element_to_notes,
            source_id_to_model_element=source_id_to_model_element,
            source_id_to_layout_element=source_id_to_layout_element,
            source_id_to_annotations=source_id_to_annotations,
            source_id_to_notes=source_id_to_notes,
            file_path=file_path,
        )
        with open(file_path, "wb") as f:
            pickle.dump(reader_result, f)
        return WriterResult(obj=obj, file_path=file_path)
