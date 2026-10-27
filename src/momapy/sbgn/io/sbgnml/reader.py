"""SBGN-ML reader classes.

ID Assignment
-------------

Each SBGN-ML element produces a model element and a layout element
with distinct IDs derived from the same XML ID:

- **Model elements**: ``id_`` = ``f"{glyph/@id}_model"``
  (or ``f"{arc/@id}_model"`` for arcs).
- **Layout elements**: ``id_`` = ``glyph/@id``
  (or ``arc/@id`` for arcs).

When the ``<map>`` element has an ``id`` attribute (SBGN-ML 0.3 only):
``map_.id_`` = ``map/@id``, ``model.id_`` = ``f"{map/@id}_model"``,
``layout.id_`` = ``f"{map/@id}_layout"``.

All elements follow this pattern consistently, including frozen child
elements (state variables, units of information, reactants, products,
logic inputs, terminal/tag references).
"""

import os
import abc
import collections
import typing

import frozendict
import lxml.objectify
import lxml.etree

import momapy.sbgn.pd

from momapy.utils import IdentityMultiDict
from momapy.core.mapping import LayoutModelMappingBuilder
from momapy.core.elements import Orientation
from momapy.io.core import Reader
from momapy.io.core import ReaderResult
from momapy.utils import check_file_exists
from momapy.io._utils import apply_remap_to_layout_model_mapping
from momapy.io._utils import build_id_mappings
from momapy.io._utils import get_xml_root_element
from momapy.io._utils import register_model_element
from momapy.sbgn.io.sbgnml._reading_context import SBGNMLReadingContext
from momapy.positioning import set_fit
from momapy.builder import get_or_make_builder_cls
from momapy.builder import object_from_builder
from momapy.sbgn.pd import EntityPool
from momapy.sbgn.pd import Modulation
from momapy.sbgn.pd import Phenotype
from momapy.sbgn.pd import StoichiometricProcess
from momapy.sbgn.af import Activity
from momapy.sbgn.af import Influence
from momapy.sbgn.io.sbgnml._reading_classification import KEY_TO_CLASS
from momapy.sbgn.io.sbgnml._reading_classification import get_arc_key
from momapy.sbgn.io.sbgnml._reading_classification import get_glyph_key
from momapy.sbgn.io.sbgnml._reading_classification import get_module
from momapy.sbgn.io.sbgnml._reading_classification import get_subglyph_key
from momapy.sbgn.io.sbgnml._reading_parsing import get_arcs
from momapy.sbgn.io.sbgnml._reading_parsing import get_consumption_and_production_arcs
from momapy.sbgn.io.sbgnml._reading_parsing import get_equivalence_arcs
from momapy.sbgn.io.sbgnml._reading_parsing import get_glyphs
from momapy.sbgn.io.sbgnml._reading_parsing import get_glyphs_recursively
from momapy.sbgn.io.sbgnml._reading_parsing import get_logic_arcs
from momapy.sbgn.io.sbgnml._reading_parsing import get_ports
from momapy.sbgn.io.sbgnml._reading_parsing import get_process_orientation
from momapy.sbgn.io.sbgnml._reading_parsing import get_state_variables
from momapy.sbgn.io.sbgnml._reading_parsing import get_subunits
from momapy.sbgn.io.sbgnml._reading_parsing import get_terminals
from momapy.sbgn.io.sbgnml._reading_parsing import get_units_of_information
from momapy.sbgn.io.sbgnml._reading_parsing import has_undefined_variable
from momapy.sbgn.io.sbgnml._reading_parsing import transform_class
from momapy.sbgn.io.sbgnml._reading_model import make_activity as model_make_activity
from momapy.sbgn.io.sbgnml._reading_model import (
    make_and_add_annotations_and_notes as model_make_and_add_annotations_and_notes,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_compartment as model_make_compartment,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_entity_pool_or_subunit as model_make_entity_pool_or_subunit,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_logical_operator as model_make_logical_operator,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_logical_operator_input as model_make_logical_operator_input,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_modulation as model_make_modulation,
)
from momapy.sbgn.io.sbgnml._reading_model import make_product as model_make_product
from momapy.sbgn.io.sbgnml._reading_model import make_reactant as model_make_reactant
from momapy.sbgn.io.sbgnml._reading_model import make_reference as model_make_reference
from momapy.sbgn.io.sbgnml._reading_model import (
    make_state_variable as model_make_state_variable,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_stoichiometric_process as model_make_stoichiometric_process,
)
from momapy.sbgn.io.sbgnml._reading_model import make_submap as model_make_submap
from momapy.sbgn.io.sbgnml._reading_model import (
    make_terminal_or_tag as model_make_terminal_or_tag,
)
from momapy.sbgn.io.sbgnml._reading_model import (
    make_unit_of_information as model_make_unit_of_information,
)
from momapy.sbgn.io.sbgnml._reading_layout import make_activity as layout_make_activity
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_compartment as layout_make_compartment,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_entity_pool_or_subunit as layout_make_entity_pool_or_subunit,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_logical_operator as layout_make_logical_operator,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_logical_operator_input as layout_make_logical_operator_input,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_modulation as layout_make_modulation,
)
from momapy.sbgn.io.sbgnml._reading_layout import make_product as layout_make_product
from momapy.sbgn.io.sbgnml._reading_layout import make_reactant as layout_make_reactant
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_reference as layout_make_reference,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_state_variable as layout_make_state_variable,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_stoichiometric_process as layout_make_stoichiometric_process,
)
from momapy.sbgn.io.sbgnml._reading_layout import make_submap as layout_make_submap
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_terminal_or_tag as layout_make_terminal_or_tag,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    make_unit_of_information as layout_make_unit_of_information,
)
from momapy.sbgn.io.sbgnml._reading_layout import (
    set_position_and_size as layout_set_position_and_size,
)


class _SBGNMLReader(Reader):
    @classmethod
    def read(
        cls,
        file_path: str | os.PathLike,
        return_type: typing.Literal["map", "model", "layout"] = "map",
        with_model: bool = True,
        with_layout: bool = True,
        with_annotations: bool = True,
        with_notes: bool = True,
        xsep: float = 0.0,
        ysep: float = 0.0,
        **options: typing.Any,
    ) -> ReaderResult:
        """Read an SBGN-ML file and return a reader result object.

        Args:
            file_path: Path of the SBGN-ML file to read.
            return_type: Shape of `result.obj`: `"map"` (default) returns an
                SBGN map, `"model"` returns the bare model, `"layout"` returns
                the bare layout.
            with_model: Whether to build the model. When `False` and
                `return_type="map"`, the map's `model` is `None`. Defaults to
                `True`.
            with_layout: Whether to build the layout. When `False` and
                `return_type="map"`, the map's `layout` is `None`. Defaults to
                `True`.
            with_annotations: Whether to read annotations. Defaults to `True`.
            with_notes: Whether to read notes. Defaults to `True`.
            xsep: Horizontal padding added around the fitted layout elements
                when the map has no explicit bounding box (passed to
                `set_fit`). Defaults to `0.0`.
            ysep: Vertical padding added around the fitted layout elements
                when the map has no explicit bounding box (passed to
                `set_fit`). Defaults to `0.0`.
            options: Additional reader-specific options (ignored).

        Returns:
            A `ReaderResult` whose `obj` is a map, model, or layout depending
            on `return_type`.
        """
        check_file_exists(file_path)
        sbgnml_document = lxml.objectify.parse(file_path)
        sbgnml_sbgn = sbgnml_document.getroot()
        (
            obj,
            annotations,
            notes,
            id_to_element,
            source_id_to_model_element,
            source_id_to_layout_element,
            source_id_to_annotations,
            source_id_to_notes,
        ) = cls._make_main_obj(
            sbgnml_map=sbgnml_sbgn.map,
            return_type=return_type,
            with_model=with_model,
            with_layout=with_layout,
            with_annotations=with_annotations,
            with_notes=with_notes,
            xsep=xsep,
            ysep=ysep,
        )
        result = ReaderResult(
            obj=obj,
            element_to_notes=notes,
            element_to_annotations=annotations,
            id_to_element=id_to_element,
            source_id_to_model_element=source_id_to_model_element,
            source_id_to_layout_element=source_id_to_layout_element,
            source_id_to_annotations=source_id_to_annotations,
            source_id_to_notes=source_id_to_notes,
            file_path=file_path,
        )
        return result

    @classmethod
    @abc.abstractmethod
    def _get_map_key(cls, sbgnml_map: lxml.etree._Element) -> str:
        pass

    @classmethod
    def _parse_sbgnml_map(cls, reading_context: SBGNMLReadingContext) -> None:
        """Classify glyphs and arcs from the XML root into the reading context."""
        sbgnml_map = reading_context.xml_root
        map_key = reading_context.map_key
        reading_context.sbgnml_glyph_id_to_sbgnml_arcs = collections.defaultdict(list)
        module = get_module(map_key)
        for sbgnml_glyph in get_glyphs(sbgnml_map):
            reading_context.xml_id_to_xml_element[sbgnml_glyph.get("id")] = sbgnml_glyph
            key = get_glyph_key(sbgnml_glyph, map_key)
            model_element_cls, _ = KEY_TO_CLASS[key]
            if model_element_cls is None:
                # Empty-set / source-and-sink glyphs have no model peer
                # but live in the entity-pool slot of the XML layout.
                reading_context.sbgnml_entity_pools.append(sbgnml_glyph)
            elif issubclass(model_element_cls, EntityPool):
                reading_context.sbgnml_entity_pools.append(sbgnml_glyph)
            elif issubclass(
                model_element_cls,
                module.Compartment,
            ):
                reading_context.sbgnml_compartments.append(sbgnml_glyph)
            elif issubclass(
                model_element_cls,
                module.LogicalOperator,
            ):
                reading_context.sbgnml_logical_operators.append(sbgnml_glyph)
            elif issubclass(
                model_element_cls,
                module.Submap,
            ):
                reading_context.sbgnml_submaps.append(sbgnml_glyph)
            elif issubclass(model_element_cls, StoichiometricProcess):
                reading_context.sbgnml_stoichiometric_processes.append(sbgnml_glyph)
            elif issubclass(model_element_cls, Phenotype):
                reading_context.sbgnml_phenotypes.append(sbgnml_glyph)
            elif issubclass(model_element_cls, Activity):
                reading_context.sbgnml_activities.append(sbgnml_glyph)
            elif issubclass(model_element_cls, module.Tag):
                reading_context.sbgnml_tags.append(sbgnml_glyph)
            for sbgnml_subglyph in get_glyphs_recursively(sbgnml_glyph):
                reading_context.xml_id_to_xml_element[sbgnml_subglyph.get("id")] = (
                    sbgnml_subglyph
                )
            for sbgnml_port in get_ports(sbgnml_glyph):
                reading_context.xml_id_to_xml_element[sbgnml_port.get("id")] = (
                    sbgnml_glyph
                )
        for sbgnml_arc in get_arcs(sbgnml_map):
            reading_context.xml_id_to_xml_element[sbgnml_arc.get("id")] = sbgnml_arc
            sbgnml_source = reading_context.xml_id_to_xml_element[
                sbgnml_arc.get("source")
            ]
            sbgnml_target = reading_context.xml_id_to_xml_element[
                sbgnml_arc.get("target")
            ]
            reading_context.sbgnml_glyph_id_to_sbgnml_arcs[
                sbgnml_source.get("id")
            ].append(sbgnml_arc)
            reading_context.sbgnml_glyph_id_to_sbgnml_arcs[
                sbgnml_target.get("id")
            ].append(sbgnml_arc)
            key = get_arc_key(sbgnml_arc, map_key)
            model_element_cls, _ = KEY_TO_CLASS[key]
            if issubclass(
                model_element_cls,
                (Modulation, Influence),
            ):
                reading_context.sbgnml_modulations.append(sbgnml_arc)
            for sbgnml_subglyph in get_glyphs(sbgnml_arc):
                reading_context.xml_id_to_xml_element[sbgnml_subglyph.get("id")] = (
                    sbgnml_subglyph
                )

    @classmethod
    def _get_map_classes(
        cls, sbgnml_map: lxml.etree._Element
    ) -> tuple[type, type, type]:
        key = cls._get_map_key(sbgnml_map)
        classes = KEY_TO_CLASS.get(key)
        if classes is None:
            if key == "ENTITY_RELATIONSHIP":
                raise NotImplementedError(
                    "entity relationship maps are not yet supported"
                )
            raise ValueError(f"unrecognized SBGN map type {key!r}")
        return classes

    @classmethod
    def _make_empty_map(cls, sbgnml_map: lxml.etree._Element) -> typing.Any:
        map_cls, _, _ = cls._get_map_classes(sbgnml_map)
        builder_cls = get_or_make_builder_cls(map_cls)
        return builder_cls()

    @classmethod
    def _make_empty_model(cls, sbgnml_map: lxml.etree._Element) -> typing.Any:
        _, model_cls, _ = cls._get_map_classes(sbgnml_map)
        builder_cls = get_or_make_builder_cls(model_cls)
        return builder_cls()

    @classmethod
    def _make_empty_layout(cls, sbgnml_map: lxml.etree._Element) -> typing.Any:
        _, _, layout_cls = cls._get_map_classes(sbgnml_map)
        builder_cls = get_or_make_builder_cls(layout_cls)
        return builder_cls()

    @classmethod
    def _make_main_obj(
        cls,
        sbgnml_map: lxml.etree._Element,
        return_type: typing.Literal["map", "model", "layout"],
        with_model: bool = True,
        with_layout: bool = True,
        with_annotations: bool = True,
        with_notes: bool = True,
        xsep: float = 0.0,
        ysep: float = 0.0,
    ) -> tuple[typing.Any, ...]:
        if return_type not in ("map", "model", "layout"):
            raise ValueError(
                f"invalid return_type {return_type!r}: expected 'map', "
                "'model' or 'layout'"
            )
        if return_type == "model" or return_type == "map" and with_model:
            model = cls._make_empty_model(sbgnml_map)
        else:
            model = None
        if return_type == "layout" or return_type == "map" and with_layout:
            layout = cls._make_empty_layout(sbgnml_map)
        else:
            layout = None
        if model is not None and layout is not None:
            layout_model_mapping = LayoutModelMappingBuilder()
        else:
            layout_model_mapping = None
        # The reading context is always created so that it is bound even when
        # neither a model nor a layout is requested (both flags False); in that
        # case the classification and element-making passes below are skipped and
        # only map-level annotations/notes are attached.
        reading_context = SBGNMLReadingContext(
            xml_root=sbgnml_map,
            map_key=cls._get_map_key(sbgnml_map),
            model=model,
            layout=layout,
            xml_id_to_model_element=IdentityMultiDict(),
            xml_id_to_layout_element={},
            element_to_annotations=collections.defaultdict(set),
            element_to_notes=collections.defaultdict(set),
            source_id_to_annotations=collections.defaultdict(set),
            source_id_to_notes=collections.defaultdict(set),
            layout_model_mapping=layout_model_mapping,
            with_annotations=with_annotations,
            with_notes=with_notes,
        )
        if model is not None or layout is not None:
            # Classify glyphs and arcs into the reading context in one pass.
            cls._parse_sbgnml_map(reading_context)
            # We make model and layout elements from glyphs and arcs; when an arc or
            # a glyph references another sbgnml element, we make the model and
            # layout elements corresponding to that sbgnml element in most cases,
            # and add them to their super model or super layout element accordingly.
            # We make glyphs compartments first as they have to be in the background
            for sbgnml_compartment in reading_context.sbgnml_compartments:
                cls._make_and_add_compartment(
                    reading_context=reading_context,
                    sbgnml_compartment=sbgnml_compartment,
                )
            for sbgnml_entity_pool in reading_context.sbgnml_entity_pools:
                cls._make_and_add_entity_pool(
                    reading_context=reading_context,
                    sbgnml_entity_pool=sbgnml_entity_pool,
                )
            for sbgnml_activity in reading_context.sbgnml_activities:
                cls._make_and_add_activity(
                    reading_context=reading_context,
                    sbgnml_activity=sbgnml_activity,
                )
            for sbgnml_logical_operator in reading_context.sbgnml_logical_operators:
                cls._make_and_add_logical_operator(
                    reading_context=reading_context,
                    sbgnml_logical_operator=sbgnml_logical_operator,
                )
            for sbgnml_submap in reading_context.sbgnml_submaps:
                cls._make_and_add_submap(
                    reading_context=reading_context,
                    sbgnml_submap=sbgnml_submap,
                )
            for sbgnml_phenotype in reading_context.sbgnml_phenotypes:
                cls._make_and_add_phenotype(
                    reading_context=reading_context,
                    sbgnml_phenotype=sbgnml_phenotype,
                )
            for sbgnml_tag in reading_context.sbgnml_tags:
                cls._make_and_add_tag(
                    reading_context=reading_context,
                    sbgnml_tag=sbgnml_tag,
                )
            for sbgnml_process in reading_context.sbgnml_stoichiometric_processes:
                cls._make_and_add_stoichiometric_process(
                    reading_context=reading_context,
                    sbgnml_process=sbgnml_process,
                )
            for sbgnml_modulation in reading_context.sbgnml_modulations:
                cls._make_and_add_modulation(
                    reading_context=reading_context,
                    sbgnml_modulation=sbgnml_modulation,
                )
            # Fix stale references in layout_model_mapping from
            # local variables captured before dedup events.
            if (
                reading_context.model_element_remap
                and reading_context.layout_model_mapping is not None
            ):
                apply_remap_to_layout_model_mapping(reading_context)
            if layout is not None:
                sbgnml_bbox = getattr(sbgnml_map, "bbox", None)
                if sbgnml_bbox is not None:
                    layout_set_position_and_size(layout, sbgnml_map)
                else:
                    set_fit(layout, layout.layout_elements, xsep=xsep, ysep=ysep)
        sbgnml_map_id = sbgnml_map.get("id")
        if sbgnml_map_id is not None:
            if model is not None:
                model.id_ = f"{sbgnml_map_id}_model"
            if layout is not None:
                layout.id_ = f"{sbgnml_map_id}_layout"
        if return_type == "model":
            obj = object_from_builder(model)
            # we add the annotations and notes from the map to the model
            model_make_and_add_annotations_and_notes(
                reading_context,
                sbgnml_map,
                obj,
                source_id=sbgnml_map_id,
            )
        elif return_type == "layout":
            obj = object_from_builder(layout)
        elif return_type == "map":
            map_ = cls._make_empty_map(sbgnml_map)
            if sbgnml_map_id is not None:
                map_.id_ = sbgnml_map_id
            map_.model = model
            map_.layout = layout
            map_.layout_model_mapping = reading_context.layout_model_mapping
            obj = object_from_builder(map_)
            model_make_and_add_annotations_and_notes(
                reading_context,
                sbgnml_map,
                obj,
                source_id=sbgnml_map_id,
            )
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
        source_id_to_annotations = frozendict.frozendict(
            {
                key: frozenset(value)
                for key, value in reading_context.source_id_to_annotations.items()
            }
        )
        source_id_to_notes = frozendict.frozendict(
            {
                key: frozenset(value)
                for key, value in reading_context.source_id_to_notes.items()
            }
        )
        if model is not None or layout is not None:
            id_to_element, source_id_to_model_element, source_id_to_layout_element = (
                build_id_mappings(
                    reading_context=reading_context,
                    obj=obj,
                )
            )
        else:
            id_to_element = None
            source_id_to_model_element = None
            source_id_to_layout_element = None
        return (
            obj,
            element_to_annotations,
            element_to_notes,
            id_to_element,
            source_id_to_model_element,
            source_id_to_layout_element,
            source_id_to_annotations,
            source_id_to_notes,
        )

    @classmethod
    def _make_and_add_compartment(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_compartment: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            model_element = model_make_compartment(reading_context, sbgnml_compartment)
            layout_element = layout_make_compartment(
                reading_context, sbgnml_compartment
            )
            auxiliary_units_map_elements = []
            for sbgnml_unit_of_information in get_units_of_information(
                sbgnml_compartment
            ):
                (
                    unit_of_information_model_element,
                    unit_of_information_layout_element,
                ) = cls._make_unit_of_information(
                    reading_context=reading_context,
                    sbgnml_unit_of_information=sbgnml_unit_of_information,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                )
                if model_element is not None:
                    model_element.units_of_information.add(
                        unit_of_information_model_element
                    )
                if layout_element is not None:
                    layout_element.layout_elements.append(
                        unit_of_information_layout_element
                    )
                if model_element is not None and layout_element is not None:
                    auxiliary_units_map_elements.append(
                        (
                            unit_of_information_model_element,
                            unit_of_information_layout_element,
                        )
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.compartments,
                    sbgnml_compartment.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_compartment,
                    model_element,
                    source_id=sbgnml_compartment.get("id"),
                )
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[
                    sbgnml_compartment.get("id")
                ] = layout_element
            if model_element is not None and layout_element is not None:
                for (
                    auxiliary_unit_model_element,
                    auxiliary_unit_layout_element,
                ) in auxiliary_units_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        auxiliary_unit_layout_element,
                        auxiliary_unit_model_element,
                    )
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_entity_pool(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_entity_pool: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_glyph_key(sbgnml_entity_pool, reading_context.map_key)
            model_element_cls, _ = KEY_TO_CLASS[key]
            if model_element_cls is None:
                reading_context.empty_set_xml_ids.add(sbgnml_entity_pool.get("id"))
            model_element, layout_element = cls._make_entity_pool_or_subunit(
                reading_context=reading_context,
                sbgnml_entity_pool_or_subunit=sbgnml_entity_pool,
                super_model_element=None,
                super_layout_element=None,
            )
            if model_element is not None:
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.entity_pools,
                    sbgnml_entity_pool.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_entity_pool,
                    model_element,
                    source_id=sbgnml_entity_pool.get("id"),
                )
            if layout_element is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[
                    sbgnml_entity_pool.get("id")
                ] = layout_element
            if model_element is not None and layout_element is not None:
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_entity_pool_or_subunit(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_entity_pool_or_subunit: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            is_subunit = (
                super_model_element is not None or super_layout_element is not None
            )
            if is_subunit:
                key = get_subglyph_key(
                    sbgnml_entity_pool_or_subunit, reading_context.map_key
                )
            else:
                key = get_glyph_key(
                    sbgnml_entity_pool_or_subunit, reading_context.map_key
                )
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_entity_pool_or_subunit(
                reading_context, sbgnml_entity_pool_or_subunit, model_element_cls
            )
            layout_element = layout_make_entity_pool_or_subunit(
                reading_context, sbgnml_entity_pool_or_subunit, layout_element_cls
            )
            auxiliary_units_map_elements = []
            n_undefined_state_variables = 0
            for sbgnml_state_variable in get_state_variables(
                sbgnml_entity_pool_or_subunit
            ):
                if has_undefined_variable(sbgnml_state_variable):
                    n_undefined_state_variables += 1
                    order = n_undefined_state_variables
                else:
                    order = None
                state_variable_model_element, state_variable_layout_element = (
                    cls._make_state_variable(
                        reading_context=reading_context,
                        sbgnml_state_variable=sbgnml_state_variable,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                        order=order,
                    )
                )
                sbgnml_state_variable_id = sbgnml_state_variable.get("id")
                if model_element is not None:
                    model_element.state_variables.add(state_variable_model_element)
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_state_variable_id,
                        state_variable_model_element,
                    )
                if layout_element is not None:
                    layout_element.layout_elements.append(state_variable_layout_element)
                    reading_context.xml_id_to_layout_element[
                        sbgnml_state_variable_id
                    ] = state_variable_layout_element
                if model_element is not None and layout_element is not None:
                    auxiliary_units_map_elements.append(
                        (
                            state_variable_model_element,
                            state_variable_layout_element,
                        )
                    )
            for sbgnml_unit_of_information in get_units_of_information(
                sbgnml_entity_pool_or_subunit
            ):
                (
                    unit_of_information_model_element,
                    unit_of_information_layout_element,
                ) = cls._make_unit_of_information(
                    reading_context=reading_context,
                    sbgnml_unit_of_information=sbgnml_unit_of_information,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                )
                sbgnml_unit_of_information_id = sbgnml_unit_of_information.get("id")
                if model_element is not None:
                    model_element.units_of_information.add(
                        unit_of_information_model_element
                    )
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_unit_of_information_id,
                        unit_of_information_model_element,
                    )
                if layout_element is not None:
                    layout_element.layout_elements.append(
                        unit_of_information_layout_element
                    )
                    reading_context.xml_id_to_layout_element[
                        sbgnml_unit_of_information_id
                    ] = unit_of_information_layout_element
                if model_element is not None and layout_element is not None:
                    auxiliary_units_map_elements.append(
                        (
                            unit_of_information_model_element,
                            unit_of_information_layout_element,
                        )
                    )
            for sbgnml_subunit in get_subunits(sbgnml_entity_pool_or_subunit):
                (
                    subunit_model_element,
                    subunit_layout_element,
                ) = cls._make_entity_pool_or_subunit(
                    reading_context=reading_context,
                    sbgnml_entity_pool_or_subunit=sbgnml_subunit,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                )
                if model_element is not None:
                    model_element.subunits.add(subunit_model_element)
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_subunit.get("id"),
                        subunit_model_element,
                    )
                    model_make_and_add_annotations_and_notes(
                        reading_context,
                        sbgnml_subunit,
                        subunit_model_element,
                        source_id=sbgnml_subunit.get("id"),
                    )
                if layout_element is not None:
                    layout_element.layout_elements.append(subunit_layout_element)
                    reading_context.xml_id_to_layout_element[
                        sbgnml_subunit.get("id")
                    ] = subunit_layout_element
                if model_element is not None and layout_element is not None:
                    auxiliary_units_map_elements.append(
                        (
                            subunit_model_element,
                            subunit_layout_element,
                        )
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
            if model_element is not None and layout_element is not None:
                for (
                    auxiliary_unit_model_element,
                    auxiliary_unit_layout_element,
                ) in auxiliary_units_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        auxiliary_unit_layout_element,
                        auxiliary_unit_model_element,
                    )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_activity(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_activity: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_glyph_key(sbgnml_activity, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_activity(
                reading_context, sbgnml_activity, model_element_cls
            )
            layout_element = layout_make_activity(
                reading_context, sbgnml_activity, layout_element_cls
            )
            auxiliary_units_map_elements = []
            for sbgnml_unit_of_information in get_units_of_information(sbgnml_activity):
                (
                    unit_of_information_model_element,
                    unit_of_information_layout_element,
                ) = cls._make_unit_of_information(
                    reading_context=reading_context,
                    sbgnml_unit_of_information=sbgnml_unit_of_information,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                )
                sbgnml_unit_of_information_id = sbgnml_unit_of_information.get("id")
                if model_element is not None:
                    model_element.units_of_information.add(
                        unit_of_information_model_element
                    )
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_unit_of_information_id,
                        unit_of_information_model_element,
                    )
                if layout_element is not None:
                    layout_element.layout_elements.append(
                        unit_of_information_layout_element
                    )
                    reading_context.xml_id_to_layout_element[
                        sbgnml_unit_of_information_id
                    ] = unit_of_information_layout_element
                if model_element is not None and layout_element is not None:
                    auxiliary_units_map_elements.append(
                        (
                            unit_of_information_model_element,
                            unit_of_information_layout_element,
                        )
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.activities,
                    sbgnml_activity.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_activity,
                    model_element,
                    source_id=sbgnml_activity.get("id"),
                )
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_activity.get("id")] = (
                    layout_element
                )
            if model_element is not None and layout_element is not None:
                for (
                    auxiliary_unit_model_element,
                    auxiliary_unit_layout_element,
                ) in auxiliary_units_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        auxiliary_unit_layout_element,
                        auxiliary_unit_model_element,
                    )
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_state_variable(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_state_variable: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
        order: int | None = None,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            model_element = model_make_state_variable(
                reading_context, sbgnml_state_variable, order=order
            )
            sbgnml_state = getattr(sbgnml_state_variable, "state", None)
            if sbgnml_state is None:
                text = ""
            else:
                sbgnml_value = sbgnml_state.get("value")
                text = sbgnml_value if sbgnml_value is not None else ""
                sbgnml_variable = sbgnml_state.get("variable")
                if sbgnml_variable is not None:
                    text += f"@{sbgnml_variable}"
            layout_element = layout_make_state_variable(
                reading_context, sbgnml_state_variable, text=text
            )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_unit_of_information(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_unit_of_information: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_subglyph_key(sbgnml_unit_of_information, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_unit_of_information(
                reading_context, sbgnml_unit_of_information, model_element_cls
            )
            layout_element = layout_make_unit_of_information(
                reading_context, sbgnml_unit_of_information, layout_element_cls
            )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_submap(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_submap: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_glyph_key(sbgnml_submap, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_submap(
                reading_context, sbgnml_submap, model_element_cls
            )
            layout_element = layout_make_submap(
                reading_context, sbgnml_submap, layout_element_cls
            )
            terminal_map_elements = []
            reference_map_elements = []
            for sbgnml_terminal in get_terminals(sbgnml_submap):
                terminal_model = model_make_terminal_or_tag(
                    reading_context, sbgnml_terminal, is_terminal=True
                )
                terminal_layout = layout_make_terminal_or_tag(
                    reading_context, sbgnml_terminal, is_terminal=True
                )
                # Freeze terminal layout before creating references
                # (references need it as source)
                if terminal_layout is not None:
                    terminal_layout = object_from_builder(terminal_layout)
                for sbgnml_equivalence_arc in get_equivalence_arcs(
                    sbgnml_terminal,
                    reading_context.xml_id_to_xml_element,
                    reading_context.sbgnml_glyph_id_to_sbgnml_arcs,
                ):
                    reference_model = model_make_reference(
                        reading_context, sbgnml_equivalence_arc, is_terminal=True
                    )
                    reference_layout = layout_make_reference(
                        reading_context, sbgnml_equivalence_arc, terminal_layout
                    )
                    sbgnml_equivalence_arc_id = sbgnml_equivalence_arc.get("id")
                    if terminal_model is not None:
                        terminal_model.referred_element = reference_model
                    if reference_model is not None:
                        reading_context.xml_id_to_model_element.add(
                            sbgnml_equivalence_arc_id,
                            reference_model,
                        )
                    if reference_layout is not None:
                        reading_context.layout.layout_elements.append(reference_layout)
                        reading_context.xml_id_to_layout_element[
                            sbgnml_equivalence_arc_id
                        ] = reference_layout
                    if reference_model is not None and reference_layout is not None:
                        reference_map_elements.append(
                            (
                                reference_model,
                                reference_layout,
                                sbgnml_terminal.get("id"),
                            )
                        )
                sbgnml_terminal_id = sbgnml_terminal.get("id")
                if terminal_model is not None:
                    terminal_model = object_from_builder(terminal_model)
                    model_element.terminals.add(terminal_model)
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_terminal_id,
                        terminal_model,
                    )
                if terminal_layout is not None:
                    layout_element.layout_elements.append(terminal_layout)
                    reading_context.xml_id_to_layout_element[sbgnml_terminal_id] = (
                        terminal_layout
                    )
                if terminal_model is not None and terminal_layout is not None:
                    terminal_map_elements.append(
                        (
                            terminal_model,
                            terminal_layout,
                            sbgnml_terminal.get("id"),
                        )
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.submaps,
                    sbgnml_submap.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_submap,
                    model_element,
                    source_id=sbgnml_submap.get("id"),
                )
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_submap.get("id")] = (
                    layout_element
                )
            if model_element is not None and layout_element is not None:
                for (
                    ref_model,
                    ref_layout,
                    _,
                ) in reference_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        ref_layout,
                        ref_model,
                    )
                for (
                    terminal_model_el,
                    terminal_layout_el,
                    terminal_xml_id,
                ) in terminal_map_elements:
                    references_for_terminal = [
                        (ref_model, ref_layout)
                        for ref_model, ref_layout, xml_id in reference_map_elements
                        if xml_id == terminal_xml_id
                    ]
                    if not references_for_terminal:
                        reading_context.layout_model_mapping.add_mapping(
                            terminal_layout_el,
                            terminal_model_el,
                        )
                        continue
                    frozenset_elements = {terminal_layout_el}
                    for _, ref_layout in references_for_terminal:
                        frozenset_elements.add(ref_layout)
                        referenced_entity_layout = ref_layout.target
                        if referenced_entity_layout is not None:
                            existing_key = reading_context.layout_model_mapping.representative_to_key.get(
                                referenced_entity_layout
                            )
                            if existing_key is not None:
                                frozenset_elements |= existing_key
                            else:
                                frozenset_elements.add(referenced_entity_layout)
                    reading_context.layout_model_mapping.add_mapping(
                        frozenset(frozenset_elements),
                        terminal_model_el,
                        representative=terminal_layout_el,
                    )
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_tag(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_tag: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            tag_model = model_make_terminal_or_tag(
                reading_context, sbgnml_tag, is_terminal=False
            )
            tag_layout = layout_make_terminal_or_tag(
                reading_context, sbgnml_tag, is_terminal=False
            )
            # Freeze tag layout before creating references
            # (references need it as source)
            if tag_layout is not None:
                tag_layout = object_from_builder(tag_layout)
            reference_map_elements = []
            for sbgnml_equivalence_arc in get_equivalence_arcs(
                sbgnml_tag,
                reading_context.xml_id_to_xml_element,
                reading_context.sbgnml_glyph_id_to_sbgnml_arcs,
            ):
                reference_model = model_make_reference(
                    reading_context, sbgnml_equivalence_arc, is_terminal=False
                )
                reference_layout = layout_make_reference(
                    reading_context, sbgnml_equivalence_arc, tag_layout
                )
                sbgnml_equivalence_arc_id = sbgnml_equivalence_arc.get("id")
                if tag_model is not None:
                    tag_model.referred_element = reference_model
                if reference_model is not None:
                    reading_context.xml_id_to_model_element.add(
                        sbgnml_equivalence_arc_id,
                        reference_model,
                    )
                if reference_layout is not None:
                    reading_context.layout.layout_elements.append(reference_layout)
                    reading_context.xml_id_to_layout_element[
                        sbgnml_equivalence_arc_id
                    ] = reference_layout
                if reference_model is not None and reference_layout is not None:
                    reference_map_elements.append((reference_model, reference_layout))
            if tag_model is not None:
                tag_model = object_from_builder(tag_model)
                tag_model = register_model_element(
                    reading_context,
                    tag_model,
                    reading_context.model.tags,
                    sbgnml_tag.get("id"),
                )
            if tag_layout is not None:
                reading_context.layout.layout_elements.append(tag_layout)
                reading_context.xml_id_to_layout_element[sbgnml_tag.get("id")] = (
                    tag_layout
                )
            if tag_model is not None and tag_layout is not None:
                for (
                    reference_model_element,
                    reference_layout_element,
                ) in reference_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        reference_layout_element,
                        reference_model_element,
                    )
                if not reference_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        tag_layout, tag_model
                    )
                else:
                    frozenset_elements = {tag_layout}
                    for _, reference_layout_element in reference_map_elements:
                        frozenset_elements.add(reference_layout_element)
                        referenced_entity_layout = reference_layout_element.target
                        if referenced_entity_layout is not None:
                            existing_key = reading_context.layout_model_mapping.representative_to_key.get(
                                referenced_entity_layout
                            )
                            if existing_key is not None:
                                frozenset_elements |= existing_key
                            else:
                                frozenset_elements.add(referenced_entity_layout)
                    reading_context.layout_model_mapping.add_mapping(
                        frozenset(frozenset_elements),
                        tag_model,
                        representative=tag_layout,
                    )
        else:
            tag_model = None
            tag_layout = None
        return tag_model, tag_layout

    @classmethod
    def _make_and_add_phenotype(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_phenotype: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            model_element, layout_element = cls._make_entity_pool_or_subunit(
                reading_context=reading_context,
                sbgnml_entity_pool_or_subunit=sbgnml_phenotype,
                super_model_element=None,
                super_layout_element=None,
            )
            if model_element is not None:
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.processes,
                    sbgnml_phenotype.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_phenotype,
                    model_element,
                    source_id=sbgnml_phenotype.get("id"),
                )
            if layout_element is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_phenotype.get("id")] = (
                    layout_element
                )
            if model_element is not None and layout_element is not None:
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_stoichiometric_process(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_process: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_glyph_key(sbgnml_process, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_stoichiometric_process(
                reading_context, sbgnml_process, model_element_cls
            )
            layout_element = layout_make_stoichiometric_process(
                reading_context, sbgnml_process, layout_element_cls
            )
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_process.get("id")] = (
                    layout_element
                )
            participant_map_elements = []
            sbgnml_consumption_arcs, sbgnml_production_arcs = (
                get_consumption_and_production_arcs(
                    sbgnml_process, reading_context.sbgnml_glyph_id_to_sbgnml_arcs
                )
            )
            for sbgnml_consumption_arc in sbgnml_consumption_arcs:
                reactant_model_element, reactant_layout_element = (
                    cls._make_and_add_reactant(
                        reading_context=reading_context,
                        sbgnml_consumption_arc=sbgnml_consumption_arc,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if layout_element is not None and reactant_layout_element is not None:
                    participant_map_elements.append(
                        (reactant_model_element, reactant_layout_element)
                    )
            for sbgnml_production_arc in sbgnml_production_arcs:
                product_model_element, product_layout_element = (
                    cls._make_and_add_product(
                        reading_context=reading_context,
                        sbgnml_production_arc=sbgnml_production_arc,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                        super_sbgnml_element=sbgnml_process,
                    )
                )
                if layout_element is not None and product_layout_element is not None:
                    participant_map_elements.append(
                        (product_model_element, product_layout_element)
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.processes,
                    sbgnml_process.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_process,
                    model_element,
                    source_id=sbgnml_process.get("id"),
                )
            if model_element is not None and layout_element is not None:
                reading_context.layout_model_mapping.add_mapping(
                    frozenset(
                        [layout_element]
                        + [
                            participant_map_element[1]
                            for participant_map_element in participant_map_elements
                        ]
                        + [
                            participant_map_element[1].target
                            for participant_map_element in participant_map_elements
                        ]
                    ),
                    model_element,
                    representative=layout_element,
                )
                for (
                    participant_model_element,
                    participant_layout_element,
                ) in participant_map_elements:
                    if participant_model_element is None:
                        continue
                    reading_context.layout_model_mapping.add_mapping(
                        participant_layout_element,
                        participant_model_element,
                    )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_reactant(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_consumption_arc: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            model_element = model_make_reactant(reading_context, sbgnml_consumption_arc)
            layout_element = layout_make_reactant(
                reading_context, sbgnml_consumption_arc, super_layout_element
            )
            sbgnml_consumption_arc_id = sbgnml_consumption_arc.get("id")
            if model_element is not None:
                super_model_element.reactants.add(model_element)
                reading_context.xml_id_to_model_element.add(
                    sbgnml_consumption_arc_id,
                    model_element,
                )
            elif (
                super_model_element is not None
                and sbgnml_consumption_arc.get("source")
                in reading_context.empty_set_xml_ids
            ):
                super_model_element.has_external_source = True
            if layout_element is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_consumption_arc_id] = (
                    layout_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_product(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_production_arc: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
        super_sbgnml_element: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            process_orientation = get_process_orientation(
                super_sbgnml_element, reading_context.sbgnml_glyph_id_to_sbgnml_arcs
            )
            model_element = model_make_product(
                reading_context,
                sbgnml_production_arc,
                super_model_element,
                super_sbgnml_element,
                process_orientation,
            )
            layout_element = layout_make_product(
                reading_context, sbgnml_production_arc, super_layout_element
            )
            sbgnml_production_arc_id = sbgnml_production_arc.get("id")
            if model_element is not None:
                super_model_element.products.add(model_element)
                reading_context.xml_id_to_model_element.add(
                    sbgnml_production_arc_id,
                    model_element,
                )
            elif (
                super_model_element is not None
                and sbgnml_production_arc.get("target")
                in reading_context.empty_set_xml_ids
            ):
                cls._set_empty_set_flag_from_production_arc(
                    super_model_element,
                    sbgnml_production_arc,
                    super_sbgnml_element,
                    process_orientation,
                )
            if layout_element is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_production_arc_id] = (
                    layout_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @staticmethod
    def _set_empty_set_flag_from_production_arc(
        super_model_element: typing.Any,
        sbgnml_production_arc: lxml.etree._Element,
        super_sbgnml_element: lxml.etree._Element,
        process_orientation: Orientation,
    ) -> None:
        """Set has_external_source / has_external_sink on the parent process.

        Production arcs to an empty-set glyph mean external sink, except
        on a reversible process where the arc may originate from the
        reactant side — geometrically determined by comparing the arc
        start to the process bbox center.
        """
        if not super_model_element.reversible:
            super_model_element.has_external_sink = True
            return
        if process_orientation == Orientation.HORIZONTAL:
            on_product_side = float(sbgnml_production_arc.start.get("x")) > float(
                super_sbgnml_element.bbox.get("x")
            )
        else:
            on_product_side = float(sbgnml_production_arc.start.get("y")) > float(
                super_sbgnml_element.bbox.get("y")
            )
        if on_product_side:
            super_model_element.has_external_sink = True
        else:
            super_model_element.has_external_source = True

    @classmethod
    def _make_and_add_logical_operator(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_logical_operator: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_glyph_key(sbgnml_logical_operator, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            model_element = model_make_logical_operator(
                reading_context, sbgnml_logical_operator, model_element_cls
            )
            layout_element = layout_make_logical_operator(
                reading_context, sbgnml_logical_operator, layout_element_cls
            )
            if layout_element is not None:
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[
                    sbgnml_logical_operator.get("id")
                ] = layout_element
            input_map_elements = []
            sbgnml_logic_arcs = get_logic_arcs(
                sbgnml_operator=sbgnml_logical_operator,
                sbgnml_id_to_sbgnml_element=reading_context.xml_id_to_xml_element,
                sbgnml_glyph_id_to_sbgnml_arcs=reading_context.sbgnml_glyph_id_to_sbgnml_arcs,
            )
            for sbgnml_logic_arc in sbgnml_logic_arcs:
                input_model_element, input_layout_element = (
                    cls._make_and_add_logical_operator_input(
                        reading_context=reading_context,
                        sbgnml_logic_arc=sbgnml_logic_arc,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if model_element is not None and layout_element is not None:
                    input_map_elements.append(
                        (input_model_element, input_layout_element)
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.logical_operators,
                    sbgnml_logical_operator.get("id"),
                )
            if model_element is not None and layout_element is not None:
                reading_context.layout_model_mapping.add_mapping(
                    frozenset(
                        [layout_element]
                        + [
                            input_map_element[1]
                            for input_map_element in input_map_elements
                        ]
                        + [
                            input_map_element[1].target
                            for input_map_element in input_map_elements
                        ]
                    ),  # TODO: add whole logical function tree?
                    model_element,
                    representative=layout_element,
                )
                for (
                    input_model_element,
                    input_layout_element,
                ) in input_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        input_layout_element,
                        input_model_element,
                    )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_logical_operator_input(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_logic_arc: lxml.etree._Element,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            sbgnml_source_id = sbgnml_logic_arc.get("source")
            # We consider that the source can be the port of a logical operator.
            # Moreover this logical operator could have not yet been made
            sbgnml_source_element = reading_context.xml_id_to_xml_element[
                sbgnml_source_id
            ]
            sbgnml_source_id = sbgnml_source_element.get("id")
            source_model_element = next(
                iter(reading_context.xml_id_to_model_element.get(sbgnml_source_id, ())),
                None,
            )
            source_layout_element = reading_context.xml_id_to_layout_element.get(
                sbgnml_source_id
            )
            if source_model_element is None and source_layout_element is None:
                source_model_element, source_layout_element = (
                    cls._make_and_add_logical_operator(
                        reading_context=reading_context,
                        sbgnml_logical_operator=sbgnml_source_element,
                    )
                )
            model_element = model_make_logical_operator_input(
                reading_context, sbgnml_logic_arc, source_model_element
            )
            layout_element = layout_make_logical_operator_input(
                reading_context,
                sbgnml_logic_arc,
                source_layout_element,
                super_layout_element,
            )
            sbgnml_logic_arc_id = sbgnml_logic_arc.get("id")
            if model_element is not None:
                super_model_element.inputs.add(model_element)
                reading_context.xml_id_to_model_element.add(
                    sbgnml_logic_arc_id,
                    model_element,
                )
            if layout_element is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[sbgnml_logic_arc_id] = (
                    layout_element
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_modulation(
        cls,
        reading_context: SBGNMLReadingContext,
        sbgnml_modulation: lxml.etree._Element,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_arc_key(sbgnml_modulation, reading_context.map_key)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            sbgnml_source_id = sbgnml_modulation.get("source")
            sbgnml_source_element = reading_context.xml_id_to_xml_element[
                sbgnml_source_id
            ]
            sbgnml_source_id = sbgnml_source_element.get("id")
            sbgnml_target_id = sbgnml_modulation.get("target")
            sbgnml_target_element = reading_context.xml_id_to_xml_element[
                sbgnml_target_id
            ]
            sbgnml_target_id = sbgnml_target_element.get("id")
            if reading_context.model is not None:
                source_model_element = next(
                    iter(
                        reading_context.xml_id_to_model_element.get(
                            sbgnml_source_id, ()
                        )
                    ),
                    None,
                )
                target_model_element = next(
                    iter(
                        reading_context.xml_id_to_model_element.get(
                            sbgnml_target_id, ()
                        )
                    ),
                    None,
                )
                model_element = model_make_modulation(
                    reading_context,
                    sbgnml_modulation,
                    model_element_cls,
                    source_model_element,
                    target_model_element,
                )
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    (
                        reading_context.model.modulations
                        if get_module(reading_context.map_key) == momapy.sbgn.pd
                        else reading_context.model.influences
                    ),
                    sbgnml_modulation.get("id"),
                )
                model_make_and_add_annotations_and_notes(
                    reading_context,
                    sbgnml_modulation,
                    model_element,
                    source_id=sbgnml_modulation.get("id"),
                )
            else:
                model_element = None
            if reading_context.layout is not None:
                source_layout_element = reading_context.xml_id_to_layout_element[
                    sbgnml_source_id
                ]
                target_layout_element = reading_context.xml_id_to_layout_element[
                    sbgnml_target_id
                ]
                layout_element = layout_make_modulation(
                    reading_context,
                    sbgnml_modulation,
                    layout_element_cls,
                    source_layout_element,
                    target_layout_element,
                )
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[
                    sbgnml_modulation.get("id")
                ] = layout_element
            else:
                layout_element = None
            if model_element is not None and layout_element is not None:
                source_mapping_key = (
                    reading_context.layout_model_mapping.representative_to_key.get(
                        source_layout_element
                    )
                )
                if source_mapping_key is not None:
                    source_layout_elements = source_mapping_key
                else:
                    source_layout_elements = frozenset([source_layout_element])
                target_mapping_key = (
                    reading_context.layout_model_mapping.representative_to_key.get(
                        target_layout_element
                    )
                )
                if target_mapping_key is not None:
                    target_layout_elements = target_mapping_key
                else:
                    target_layout_elements = frozenset([target_layout_element])
                reading_context.layout_model_mapping.add_mapping(
                    frozenset([layout_element])
                    | source_layout_elements
                    | target_layout_elements,
                    model_element,
                    representative=layout_element,
                )
        else:
            model_element = None
            layout_element = None
        return model_element, layout_element


class SBGNML0_2Reader(_SBGNMLReader):
    """Class for SBGN-ML 0.2 reader objects."""

    @classmethod
    def _get_map_key(cls, sbgnml_map: lxml.etree._Element) -> str:
        key = transform_class(sbgnml_map.get("language"))
        return key

    @classmethod
    def check_file(cls, file_path: str | os.PathLike) -> bool:
        """Return `True` if the file is an SBGN-ML 0.2 document.

        Args:
            file_path: Path of the file to check.

        Returns:
            `True` if the root element of the file is an `sbgn` element in the
            SBGN-ML 0.2 namespace, `False` otherwise.
        """
        root_element = get_xml_root_element(file_path)
        return (
            root_element is not None
            and root_element.tag == "{http://sbgn.org/libsbgn/0.2}sbgn"
        )


class SBGNML0_3Reader(_SBGNMLReader):
    """Class for SBGN-ML 0.3 reader objects."""

    @classmethod
    def _get_map_key(cls, sbgnml_map: lxml.etree._Element) -> str:
        sbgnml_version = sbgnml_map.get("version")
        if sbgnml_version is not None:
            if "sbgn.pd" in sbgnml_version:
                return "PROCESS_DESCRIPTION"
            elif "sbgn.af" in sbgnml_version:
                return "ACTIVITY_FLOW"
            elif "sbgn.er" in sbgnml_version:
                return "ENTITY_RELATIONSHIP"
            raise ValueError(f"unrecognized SBGN map version {sbgnml_version!r}")
        else:
            return SBGNML0_2Reader._get_map_key(sbgnml_map)

    @classmethod
    def check_file(cls, file_path: str | os.PathLike) -> bool:
        """Return `True` if the file is an SBGN-ML 0.3 document.

        Args:
            file_path: Path of the file to check.

        Returns:
            `True` if the root element of the file is an `sbgn` element in the
            SBGN-ML 0.3 namespace, `False` otherwise.
        """
        root_element = get_xml_root_element(file_path)
        return (
            root_element is not None
            and root_element.tag == "{http://sbgn.org/libsbgn/0.3}sbgn"
        )
