"""SBML reader.

Reads an SBML file into an `SBMLMap` (model only; SBML has no layout).
Follows the shared I/O conventions: a `reading_context` first argument, an
`SBMLReadingContext` extending `momapy.io._utils.ReadingContext`, and
module-level `make_*` element builders in `_reading_model`.
"""

import os
import typing
import collections

import frozendict
import lxml.etree
import lxml.objectify

from momapy.builder import new_builder_object
from momapy.builder import object_from_builder
from momapy.io._utils import add_child_model_element
from momapy.io._utils import add_top_level_model_element
from momapy.io._utils import build_id_mappings
from momapy.io._utils import get_xml_root_element
from momapy.io._utils import merge_read_model_elements
from momapy.io.core import Reader
from momapy.io.core import ReaderResult
from momapy.utils import check_file_exists
from momapy.sbml.io.sbml._reading_context import SBMLReadingContext
from momapy.sbml.map import SBMLMap
from momapy.sbml.model import SBMLModel
from momapy.sbml.io.sbml._reading_parsing import get_compartments
from momapy.sbml.io.sbml._reading_parsing import get_modifiers
from momapy.sbml.io.sbml._reading_parsing import get_products
from momapy.sbml.io.sbml._reading_parsing import get_reactants
from momapy.sbml.io.sbml._reading_parsing import get_reactions
from momapy.sbml.io.sbml._reading_parsing import get_species
from momapy.sbml.io.sbml._reading_model import make_and_add_annotations_and_notes
from momapy.sbml.io.sbml._reading_model import make_compartment
from momapy.sbml.io.sbml._reading_model import make_modifier_species_reference
from momapy.sbml.io.sbml._reading_model import make_reaction
from momapy.sbml.io.sbml._reading_model import make_species
from momapy.sbml.io.sbml._reading_model import make_species_reference


class SBMLReader(Reader):
    """Reader for SBML files (model only; no layout)."""

    @classmethod
    def check_file(cls, file_path: str | os.PathLike) -> bool:
        """Return `True` if the file looks like SBML.

        A CellDesigner file is also a valid SBML file and matches here; the
        `read()` dispatcher resolves the ambiguity by trying readers in
        registration order (CellDesigner before SBML).

        Args:
            file_path: Path of the file to check.

        Returns:
            `True` if the root element of the file is an `sbml` element in an
            SBML namespace (with or without a prefix), `False` otherwise.
        """
        root_element = get_xml_root_element(file_path)
        if root_element is None:
            return False
        root_tag = lxml.etree.QName(root_element)
        return root_tag.localname == "sbml" and (root_tag.namespace or "").startswith(
            "http://www.sbml.org/sbml/"
        )

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
        """Read an SBML file and return a reader result object.

        Args:
            file_path: Path of the SBML file to read.
            return_type: Shape of `result.obj`: `"map"` (default) returns an
                `SBMLMap`, `"model"` returns the bare `SBMLModel`. SBML has no
                layout, so `"layout"` raises `NotImplementedError`.
            with_model: Whether to build the model. When `False` and
                `return_type="map"`, the map's `model` is `None`. Defaults to
                `True`.
            with_layout: Accepted for signature parity with the other readers;
                SBML has no layout, so it has no effect. Defaults to `True`.
            with_annotations: Whether to read annotations. Defaults to `True`.
            with_notes: Whether to read notes. Defaults to `True`.
            options: Additional reader-specific options (ignored).

        Returns:
            A `ReaderResult` whose `obj` is an `SBMLMap` or `SBMLModel`.

        Raises:
            NotImplementedError: If `return_type="layout"` (SBML has no layout).
        """
        check_file_exists(file_path)
        sbml_document = lxml.objectify.parse(file_path)
        sbml = sbml_document.getroot()
        (
            obj,
            annotations,
            notes,
            id_to_element,
            source_id_to_model_element,
        ) = cls._make_main_obj(
            sbml_model=sbml.model,
            return_type=return_type,
            with_model=with_model,
            with_layout=with_layout,
            with_annotations=with_annotations,
            with_notes=with_notes,
        )
        result = ReaderResult(
            obj=obj,
            element_to_annotations=annotations,
            element_to_notes=notes,
            id_to_element=id_to_element,
            source_id_to_model_element=source_id_to_model_element,
            source_id_to_layout_element=None,
            source_id_to_annotations=None,
            source_id_to_notes=None,
            file_path=file_path,
        )
        return result

    @classmethod
    def _make_empty_map(cls, sbml_model: typing.Any) -> typing.Any:
        return new_builder_object(SBMLMap)

    @classmethod
    def _make_empty_model(cls, sbml_model: typing.Any) -> typing.Any:
        return new_builder_object(SBMLModel)

    @classmethod
    def _make_main_obj(
        cls,
        sbml_model: typing.Any,
        return_type: typing.Literal["map", "model", "layout"],
        with_model: bool = True,
        with_layout: bool = True,
        with_annotations: bool = True,
        with_notes: bool = True,
    ) -> tuple[typing.Any, typing.Any, typing.Any, typing.Any, typing.Any]:
        if return_type not in ("map", "model", "layout"):
            raise ValueError(
                f"invalid return_type {return_type!r}: expected 'map', "
                "'model' or 'layout'"
            )
        if return_type == "layout":
            raise NotImplementedError(
                "SBML has no layout; return_type='layout' is not supported"
            )
        if return_type == "model" or return_type == "map" and with_model:
            model = cls._make_empty_model(sbml_model)
        else:
            model = None
        reading_context = SBMLReadingContext(
            xml_root=sbml_model,
            model=model,
            sbml_model=sbml_model,
            element_to_annotations=collections.defaultdict(set),
            element_to_notes=collections.defaultdict(set),
            source_id_to_annotations=collections.defaultdict(set),
            source_id_to_notes=collections.defaultdict(set),
            with_annotations=with_annotations,
            with_notes=with_notes,
        )
        if model is not None:
            for sbml_compartment in get_compartments(sbml_model):
                cls._make_and_add_compartment(reading_context, sbml_compartment)
            for sbml_species in get_species(sbml_model):
                cls._make_and_add_species(reading_context, sbml_species)
            for sbml_reaction in get_reactions(sbml_model):
                cls._make_and_add_reaction(reading_context, sbml_reaction)
            merge_read_model_elements(reading_context)
        if return_type == "model":
            obj = object_from_builder(model)
            make_and_add_annotations_and_notes(reading_context, sbml_model, obj)
        elif return_type == "map":
            map_ = cls._make_empty_map(sbml_model)
            map_.model = model
            obj = object_from_builder(map_)
            make_and_add_annotations_and_notes(reading_context, sbml_model, obj)
        element_to_annotations = frozendict.frozendict(
            {
                key: frozenset(value)
                for key, value in reading_context.element_to_annotations.items()
            }
        )
        element_to_notes = frozendict.frozendict(
            {
                key: frozenset(value)
                for key, value in reading_context.element_to_notes.items()
            }
        )
        if model is not None:
            id_to_element, source_id_to_model_element, _ = build_id_mappings(
                reading_context=reading_context,
                obj=obj,
            )
        else:
            id_to_element = frozendict.frozendict()
            source_id_to_model_element = None
        return (
            obj,
            element_to_annotations,
            element_to_notes,
            id_to_element,
            source_id_to_model_element,
        )

    @classmethod
    def _make_and_add_compartment(
        cls,
        reading_context: SBMLReadingContext,
        sbml_compartment: typing.Any,
    ) -> typing.Any:
        model_element = make_compartment(reading_context, sbml_compartment)
        model_element = object_from_builder(model_element)
        model_element = add_top_level_model_element(
            reading_context, model_element, sbml_compartment.get("id")
        )
        reading_context.sbml_id_to_model_element[sbml_compartment.get("id")] = (
            model_element
        )
        make_and_add_annotations_and_notes(
            reading_context, sbml_compartment, model_element
        )
        return model_element

    @classmethod
    def _make_and_add_species(
        cls, reading_context: SBMLReadingContext, sbml_species: typing.Any
    ) -> typing.Any:
        model_element = make_species(reading_context, sbml_species)
        model_element = object_from_builder(model_element)
        model_element = add_top_level_model_element(
            reading_context, model_element, sbml_species.get("id")
        )
        reading_context.sbml_id_to_model_element[sbml_species.get("id")] = model_element
        make_and_add_annotations_and_notes(reading_context, sbml_species, model_element)
        return model_element

    @classmethod
    def _make_and_add_reaction(
        cls, reading_context: SBMLReadingContext, sbml_reaction: typing.Any
    ) -> typing.Any:
        model_element = make_reaction(reading_context, sbml_reaction)
        for sbml_reactant in get_reactants(sbml_reaction):
            cls._make_and_add_reactant(reading_context, sbml_reactant, model_element)
        for sbml_product in get_products(sbml_reaction):
            cls._make_and_add_product(reading_context, sbml_product, model_element)
        for sbml_modifier in get_modifiers(sbml_reaction):
            cls._make_and_add_modifier(reading_context, sbml_modifier, model_element)
        model_element = object_from_builder(model_element)
        model_element = add_top_level_model_element(
            reading_context, model_element, sbml_reaction.get("id")
        )
        reading_context.sbml_id_to_model_element[sbml_reaction.get("id")] = (
            model_element
        )
        make_and_add_annotations_and_notes(
            reading_context, sbml_reaction, model_element
        )
        return model_element

    @classmethod
    def _make_and_add_reactant(
        cls,
        reading_context: SBMLReadingContext,
        sbml_species_reference: typing.Any,
        super_model_element: typing.Any,
    ) -> typing.Any:
        model_element = make_species_reference(
            reading_context, sbml_species_reference, super_model_element.id_
        )
        return add_child_model_element(
            reading_context, model_element, super_model_element.reactants
        )

    @classmethod
    def _make_and_add_product(
        cls,
        reading_context: SBMLReadingContext,
        sbml_species_reference: typing.Any,
        super_model_element: typing.Any,
    ) -> typing.Any:
        model_element = make_species_reference(
            reading_context, sbml_species_reference, super_model_element.id_
        )
        return add_child_model_element(
            reading_context, model_element, super_model_element.products
        )

    @classmethod
    def _make_and_add_modifier(
        cls,
        reading_context: SBMLReadingContext,
        sbml_modifier_species_reference: typing.Any,
        super_model_element: typing.Any,
    ) -> typing.Any:
        model_element = make_modifier_species_reference(
            reading_context, sbml_modifier_species_reference, super_model_element.id_
        )
        return add_child_model_element(
            reading_context, model_element, super_model_element.modifiers
        )
