"""CellDesigner reader class.

ID Assignment
-------------

CellDesigner uses different XML ID namespaces for model and layout
elements. The general rules are:

- When an element has a natural XML ID (``compartment/@id``,
  ``species/@id``, ``reaction/@id``), the model element uses it
  directly.
- When a separate alias element exists (``speciesAlias/@id``,
  ``compartmentAlias/@id``), the layout element uses the alias ID.
- When model and layout share the same XML ID source (reactions,
  modulations), the layout element gets a ``_layout`` suffix:
  ``f"{reaction/@id}_layout"``.

The map, model and layout IDs are derived from the SBML ``model/@id``:
``map_.id_`` = ``model/@id``, ``model.id_`` = ``f"{model/@id}_model"``,
``layout.id_`` = ``f"{model/@id}_layout"``.

Element-specific patterns:

- **Compartment**: model ``id_`` = ``compartment/@id``,
  layout ``id_`` = ``compartmentAlias/@id``.
- **Species**: model ``id_`` = ``species/@id`` (or
  ``f"{species/@id}_active"`` for active species),
  layout ``id_`` = ``speciesAlias/@id``.
- **Species Template**: model ``id_`` = ``proteinReference/@id``
  (etc.), no layout.
- **ModificationResidue / Region**: model ``id_`` =
  ``f"{template/@id}_{child/@id}"``, no layout.
- **Modification**: model ``id_`` =
  ``f"{species/@id}_{modification/@residue}"``,
  layout ``id_`` =
  ``f"{speciesAlias/@id}_{modification/@residue}_layout"``.
  The layout id is keyed on the alias, not the species, so it stays
  unique when one species appears under several aliases.
- **StructuralState**: model ``id_`` =
  ``f"{species/@id}_{structuralState/@structuralState}"``,
  layout ``id_`` =
  ``f"{speciesAlias/@id}_{structuralState/@structuralState}_layout"``.
  Keyed on the alias for the same reason as Modification.
  Spaces in the value are replaced with ``_``.
  When the value is missing, ``structural_state_{order}`` is used in place
  of the value in both ids.
- **Reactant / Product**: model ``id_`` = ``speciesReference/@metaid`` of
  the first entry of the group of entries of one reaction side referring to
  the same species (or ``f"{reaction/@id}_{speciesReference/@species}"``
  fallback), layout ``id_`` = ``f"{metaid}_layout"`` with the ``metaid`` of
  the ``speciesReference`` matched by ``celldesigner:alias`` (or
  ``f"{reaction/@id}_{alias/@id}_layout"`` fallback), when present.
- **Modulator**: model ``id_`` = ``modifierSpeciesReference/@metaid`` of
  the first ``modifierSpeciesReference`` read for the modifier, layout
  ``id_`` = ``f"{metaid}_layout"`` with the ``metaid`` of the
  ``modifierSpeciesReference`` matched by ``celldesigner:alias``.
- **Reaction**: model ``id_`` = ``reaction/@id``,
  layout ``id_`` = ``f"{reaction/@id}_layout"``.
- **Modulation**: model ``id_`` = ``reaction/@id``,
  layout ``id_`` = ``f"{reaction/@id}_layout"``.
- **BooleanGate**: model ``id_`` =
  ``f"{reaction/@id}_gate_{sorted_aliases}"``,
  layout ``id_`` =
  ``f"{reaction/@id}_gate_{sorted_aliases}_layout"``.
- **BooleanGateInput / LogicArcLayout**: model ``id_`` =
  ``f"{gate_id}_input_{speciesAlias/@id}"``,
  layout ``id_`` = ``f"{gate_id}_arc_{speciesAlias/@id}"``.
"""

import os
import collections
import typing
import warnings

import frozendict
import lxml.etree
import lxml.objectify

from momapy.core.mapping import LayoutModelMappingBuilder
from momapy.io.core import Reader, ReaderResult
from momapy.io._utils import (
    apply_remap_to_layout_model_mapping,
    build_id_mappings,
    get_xml_root_element,
    register_model_element,
)
from momapy.builder import new_builder_object
from momapy.builder import object_from_builder
from momapy.celldesigner.map import CellDesignerMap
from momapy.utils import (
    IdentityMultiDict,
    add_or_replace_element_in_set,
    check_file_exists,
)

from momapy.celldesigner.io.celldesigner._reading_parsing import (
    get_activity,
    get_base_products,
    get_base_reactants,
    get_compartments,
    get_complex_species_aliases,
    get_gate_members,
    get_height,
    get_homodimer,
    get_hypothetical,
    get_included_complex_species_aliases,
    get_included_species,
    get_included_species_aliases,
    get_key_from_gate_member,
    get_key_from_reaction,
    get_key_from_reaction_modification,
    get_key_from_region,
    get_key_from_species,
    get_key_from_species_template,
    get_modification_residues,
    get_modifier_metaid,
    get_notes,
    get_product_id,
    get_ordered_compartment_aliases,
    get_product_links,
    get_products,
    get_reactant_id,
    get_reactant_links,
    get_reactants,
    get_reaction_modifications,
    get_reactions,
    get_regions,
    get_species,
    get_species_aliases,
    get_species_modifications,
    get_species_structural_states,
    get_species_templates,
    get_template_from_species_alias,
    get_width,
    has_boolean_input_from_modification,
    has_boolean_input_from_reaction,
    get_complex_alias_to_included_ids_mapping,
    get_id_to_element_mapping,
    get_name,
)
from momapy.celldesigner.io.celldesigner._constants import (
    CD_MODIFICATION_STATE_TO_MODIFICATION_STATE,
)
from momapy.celldesigner.io.celldesigner import _reading_model
from momapy.celldesigner.io.celldesigner import _reading_layout
from momapy.celldesigner.io.celldesigner._reading_classification import KEY_TO_CLASS
from momapy.celldesigner.io.celldesigner._reading_classification import (
    normalize_modulation_class,
)
from momapy.celldesigner.io.celldesigner._reading_context import (
    CellDesignerReadingContext,
)
from momapy.celldesigner.model import (
    CellDesignerModel,
    Product,
    Reactant,
    Reaction,
)
from momapy.celldesigner.layout import (
    CellDesignerLayout,
)


class CellDesignerReader(Reader):
    """Class for CellDesigner reader objects."""

    @classmethod
    def _parse_cd_model(cls, reading_context: CellDesignerReadingContext) -> None:
        """Pre-scan the CellDesigner model into categorized element lists.

        Populates reading_context with ID mappings and categorized
        elements, avoiding repeated XML traversals during the main read.

        Args:
            reading_context: The reading context to populate.
        """
        cd_model = reading_context.xml_root
        reading_context.xml_id_to_xml_element = get_id_to_element_mapping(cd_model)
        reading_context.cd_complex_alias_id_to_cd_included_species_ids = (
            get_complex_alias_to_included_ids_mapping(cd_model)
        )
        reading_context.cd_compartment_aliases = get_ordered_compartment_aliases(
            cd_model, reading_context.xml_id_to_xml_element
        )
        reading_context.canvas_width = float(get_width(cd_model))
        reading_context.canvas_height = float(get_height(cd_model))
        reading_context.cd_compartments = get_compartments(cd_model)
        reading_context.cd_species_templates = get_species_templates(cd_model)
        reading_context.cd_species_aliases = get_species_aliases(
            cd_model
        ) + get_complex_species_aliases(cd_model)
        reading_context.cd_reactions = []
        reading_context.cd_modulations = []
        for cd_reaction in get_reactions(cd_model):
            key = get_key_from_reaction(cd_reaction)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            if issubclass(model_element_cls, Reaction):
                reading_context.cd_reactions.append(cd_reaction)
            else:
                reading_context.cd_modulations.append(cd_reaction)
        # Collect real source IDs (XML attributes that exist verbatim in
        # the file), split by which side they name.  SBML-level ids
        # (species, compartments, templates, reactions, metaids) name
        # model entities; CellDesigner alias ids name layout entities.
        # Reaction ids name both a model reaction and its sole layout
        # arc.  Composite/synthetic IDs are excluded.
        real_model_ids = reading_context.real_model_source_ids
        real_layout_ids = reading_context.real_layout_source_ids
        for cd_compartment in reading_context.cd_compartments:
            real_model_ids.add(cd_compartment.get("id"))
        for cd_compartment_alias in reading_context.cd_compartment_aliases:
            real_layout_ids.add(cd_compartment_alias.get("id"))
        for cd_species_template in reading_context.cd_species_templates:
            real_model_ids.add(cd_species_template.get("id"))
        for cd_species in get_species(cd_model):
            real_model_ids.add(cd_species.get("id"))
        for cd_included_species in get_included_species(cd_model):
            real_model_ids.add(cd_included_species.get("id"))
        for cd_species_alias in reading_context.cd_species_aliases:
            real_layout_ids.add(cd_species_alias.get("id"))
        for cd_included_alias in get_included_species_aliases(cd_model):
            real_layout_ids.add(cd_included_alias.get("id"))
        for cd_included_complex_alias in get_included_complex_species_aliases(cd_model):
            real_layout_ids.add(cd_included_complex_alias.get("id"))
        for cd_reaction in (
            reading_context.cd_reactions + reading_context.cd_modulations
        ):
            reaction_id = cd_reaction.get("id")
            real_model_ids.add(reaction_id)
            real_layout_ids.add(reaction_id)
            # Metaids on speciesReferences and modifierSpeciesReferences
            # name SBML-level model entities; the matching layout ids
            # are synthetic (metaid + "_layout") and excluded.
            for cd_reactant in get_reactants(cd_reaction):
                metaid = cd_reactant.get("metaid")
                if metaid is not None:
                    real_model_ids.add(metaid)
            for cd_product in get_products(cd_reaction):
                metaid = cd_product.get("metaid")
                if metaid is not None:
                    real_model_ids.add(metaid)
            for cd_modifier in get_reaction_modifications(cd_reaction):
                metaid = get_modifier_metaid(cd_modifier, cd_reaction)
                if metaid is not None:
                    real_model_ids.add(metaid)

    @classmethod
    def check_file(cls, file_path: str | os.PathLike) -> bool:
        """Return `True` if the file is a CellDesigner file.

        Args:
            file_path: Path of the file to check.

        Returns:
            `True` if the root element of the file is an SBML `sbml` element
            declaring the CellDesigner namespace, `False` otherwise.
        """
        root_element = get_xml_root_element(file_path)
        if root_element is None:
            return False
        root_tag = lxml.etree.QName(root_element)
        return (
            root_tag.localname == "sbml"
            and (root_tag.namespace or "").startswith("http://www.sbml.org/sbml/")
            and "http://www.sbml.org/2001/ns/celldesigner"
            in root_element.nsmap.values()
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
        """Read a CellDesigner file and return a reader result object.

        Args:
            file_path: Path of the CellDesigner file to read.
            return_type: Shape of `result.obj`: `"map"` (default) returns a
                CellDesigner map, `"model"` returns the bare model, `"layout"`
                returns the bare layout.
            with_model: Whether to build the model. When `False` and
                `return_type="map"`, the map's `model` is `None`. Defaults to
                `True`.
            with_layout: Whether to build the layout. When `False` and
                `return_type="map"`, the map's `layout` is `None`. Defaults to
                `True`.
            with_annotations: Whether to read annotations. Defaults to `True`.
            with_notes: Whether to read notes. Defaults to `True`.
            options: Additional reader-specific options (ignored).

        Returns:
            A `ReaderResult` whose `obj` is a map, model, or layout depending
            on `return_type`.
        """
        check_file_exists(file_path)
        cd_document = lxml.objectify.parse(file_path)
        cd_sbml = cd_document.getroot()
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
            cd_model=cd_sbml.model,
            return_type=return_type,
            with_model=with_model,
            with_layout=with_layout,
            with_annotations=with_annotations,
            with_notes=with_notes,
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
    def _make_empty_model(cls, cd_model: typing.Any) -> typing.Any:
        return new_builder_object(CellDesignerModel)

    @classmethod
    def _make_empty_map(cls, cd_model: typing.Any) -> typing.Any:
        map_ = new_builder_object(CellDesignerMap)
        cd_map_id = cd_model.get("id")
        if cd_map_id is not None:
            map_.id_ = cd_map_id
        return map_

    @classmethod
    def _make_empty_layout(cls, cd_model: typing.Any) -> typing.Any:
        return new_builder_object(CellDesignerLayout)

    @classmethod
    def _make_main_obj(
        cls,
        cd_model: lxml.objectify.ObjectifiedElement,
        return_type: typing.Literal["map", "model", "layout"] = "map",
        with_model: bool = True,
        with_layout: bool = True,
        with_annotations: bool = True,
        with_notes: bool = True,
    ) -> tuple[typing.Any, ...]:
        if return_type not in ("map", "model", "layout"):
            raise ValueError(
                f"invalid return_type {return_type!r}: expected 'map', "
                "'model' or 'layout'"
            )
        if return_type == "model" or return_type == "map" and with_model:
            model = cls._make_empty_model(cd_model)
        else:
            model = None
        if return_type == "layout" or return_type == "map" and with_layout:
            layout = cls._make_empty_layout(cd_model)
        else:
            layout = None
        element_to_annotations = collections.defaultdict(set)
        element_to_notes = collections.defaultdict(set)
        source_id_to_annotations = collections.defaultdict(set)
        source_id_to_notes = collections.defaultdict(set)
        # Bound even when neither a model nor a layout is requested (both flags
        # False), so the map branch below yields an all-None map instead of
        # crashing with UnboundLocalError.
        layout_model_mapping = None
        if model is not None or layout is not None:
            if model is not None and layout is not None:
                layout_model_mapping = LayoutModelMappingBuilder()
            reading_context = CellDesignerReadingContext(
                xml_root=cd_model,
                model=model,
                layout=layout,
                xml_id_to_model_element=IdentityMultiDict(),
                element_to_annotations=element_to_annotations,
                element_to_notes=element_to_notes,
                source_id_to_annotations=source_id_to_annotations,
                source_id_to_notes=source_id_to_notes,
                layout_model_mapping=layout_model_mapping,
                with_annotations=with_annotations,
                with_notes=with_notes,
            )
            cls._parse_cd_model(reading_context)
            for cd_compartment_alias in reading_context.cd_compartment_aliases:
                cls._make_and_add_compartment_from_alias(
                    reading_context,
                    cd_compartment_alias=cd_compartment_alias,
                )
            for cd_compartment in reading_context.cd_compartments:
                if (
                    cd_compartment.get("id")
                    not in reading_context.xml_id_to_model_element
                ):
                    cls._make_and_add_compartment(
                        reading_context,
                        cd_compartment=cd_compartment,
                    )
            for cd_species_template in reading_context.cd_species_templates:
                cls._make_and_add_species_template(
                    reading_context,
                    cd_species_template=cd_species_template,
                )
            for cd_species_alias in reading_context.cd_species_aliases:
                cls._make_and_add_species(
                    reading_context,
                    cd_species_alias=cd_species_alias,
                )
            for cd_reaction in reading_context.cd_reactions:
                cls._make_and_add_reaction(
                    reading_context,
                    cd_reaction=cd_reaction,
                )
            for cd_modulation in reading_context.cd_modulations:
                cls._make_and_add_modulation(
                    reading_context,
                    cd_reaction=cd_modulation,
                )
            # Fix stale references in layout_model_mapping from
            # local variables captured before dedup events.
            if (
                reading_context.model_element_remap
                and reading_context.layout_model_mapping is not None
            ):
                apply_remap_to_layout_model_mapping(reading_context)
            if layout is not None:
                _reading_layout.set_layout_size_and_position(reading_context, cd_model)
        cd_model_id = cd_model.get("id")
        if cd_model_id is not None:
            if model is not None:
                model.id_ = f"{cd_model_id}_model"
            if layout is not None:
                layout.id_ = f"{cd_model_id}_layout"
        if return_type == "model":
            obj = object_from_builder(model)
            if with_annotations:
                annotations = _reading_model.make_annotations_from_element(cd_model)
                element_to_annotations[obj].update(annotations)
            if with_notes:
                notes = _reading_model.make_notes_from_element(cd_model)
                element_to_notes[obj].update(notes)
        elif return_type == "layout":
            obj = object_from_builder(layout)
        elif return_type == "map":
            map_ = cls._make_empty_map(cd_model)
            map_.model = model
            map_.layout = layout
            map_.layout_model_mapping = layout_model_mapping
            obj = object_from_builder(map_)
            if with_annotations:
                annotations = _reading_model.make_annotations_from_element(cd_model)
                element_to_annotations[obj].update(annotations)
            if with_notes:
                notes = _reading_model.make_notes_from_element(cd_model)
                element_to_notes[obj].update(notes)
        annotations = frozendict.frozendict(
            {key: frozenset(val) for key, val in element_to_annotations.items()}
        )
        notes = frozendict.frozendict(
            {key: frozenset(val) for key, val in element_to_notes.items()}
        )
        frozen_source_id_to_annotations = frozendict.frozendict(
            {key: frozenset(val) for key, val in source_id_to_annotations.items()}
        )
        frozen_source_id_to_notes = frozendict.frozendict(
            {key: frozenset(val) for key, val in source_id_to_notes.items()}
        )
        if model is not None or layout is not None:
            id_to_element, source_id_to_model_element, source_id_to_layout_element = (
                build_id_mappings(
                    reading_context=reading_context,
                    obj=obj,
                    real_model_source_ids=reading_context.real_model_source_ids,
                    real_layout_source_ids=reading_context.real_layout_source_ids,
                )
            )
        else:
            id_to_element = None
            source_id_to_model_element = None
            source_id_to_layout_element = None
        return (
            obj,
            annotations,
            notes,
            id_to_element,
            source_id_to_model_element,
            source_id_to_layout_element,
            frozen_source_id_to_annotations,
            frozen_source_id_to_notes,
        )

    @classmethod
    def _make_and_add_compartment_from_alias(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_compartment_alias: lxml.objectify.ObjectifiedElement,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            cd_compartment = reading_context.xml_id_to_xml_element[
                cd_compartment_alias.get("compartment")
            ]
            if reading_context.model is not None:
                # we make and add the model element from the cd compartment
                # the cd element is an alias of, if it has not already been made
                # while being outside another one
                model_element = next(
                    iter(
                        reading_context.xml_id_to_model_element.get(
                            cd_compartment.get("id"), ()
                        )
                    ),
                    None,
                )
                if model_element is None:
                    model_element, _ = cls._make_and_add_compartment(
                        reading_context,
                        cd_compartment=cd_compartment,
                    )
            else:
                model_element = None
            if reading_context.layout is not None:
                layout_element = _reading_layout.make_compartment_from_alias(
                    reading_context, cd_compartment, cd_compartment_alias
                )
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[
                    cd_compartment_alias.get("id")
                ] = layout_element
            else:
                layout_element = None
            if reading_context.model is not None and reading_context.layout is not None:
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        return model_element, layout_element

    @classmethod
    def _make_and_add_compartment(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_compartment: lxml.objectify.ObjectifiedElement,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None:
            model_element = _reading_model.make_compartment(
                reading_context, cd_compartment
            )
            if cd_compartment.get("outside") is not None:
                outside_model_element = next(
                    iter(
                        reading_context.xml_id_to_model_element.get(
                            cd_compartment.get("outside"), ()
                        )
                    ),
                    None,
                )
                # if outside is not already made, we make it
                if outside_model_element is None:
                    cd_outside = reading_context.xml_id_to_xml_element[
                        cd_compartment.get("outside")
                    ]
                    outside_model_element, _ = cls._make_and_add_compartment(
                        reading_context,
                        cd_compartment=cd_outside,
                    )
                model_element.outside = outside_model_element
            model_element = object_from_builder(model_element)
            model_element = register_model_element(
                reading_context,
                model_element,
                reading_context.model.compartments,
                cd_compartment.get("id"),
            )
            _reading_model.make_and_add_annotations(
                reading_context,
                cd_compartment,
                model_element,
                source_id=cd_compartment.get("id"),
            )
            _reading_model.make_and_add_notes(
                reading_context,
                cd_compartment,
                model_element,
                source_id=cd_compartment.get("id"),
            )
        else:
            model_element = None
        layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_species_template(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_species_template: lxml.objectify.ObjectifiedElement,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None:
            key = get_key_from_species_template(cd_species_template)
            model_element_cls = KEY_TO_CLASS[key]
            model_element = _reading_model.make_species_template(
                reading_context, cd_species_template, model_element_cls
            )
            n_undefined_modification_residue_names = 0
            cd_modification_residues = get_modification_residues(cd_species_template)
            cd_modification_residues.sort(
                key=lambda cd_modification_residue: cd_modification_residue.get("angle")
            )
            for cd_modification_residue in get_modification_residues(
                cd_species_template
            ):
                if cd_modification_residue.get("name") is None:
                    n_undefined_modification_residue_names += 1
                    order = n_undefined_modification_residue_names
                else:
                    order = None
                modification_residue_model_element, _ = (
                    cls._make_and_add_modification_residue(
                        reading_context,
                        cd_modification_residue=cd_modification_residue,
                        super_cd_element=cd_species_template,
                        super_model_element=model_element,
                        order=order,
                    )
                )
            n_undefined_region_names = 0
            cd_regions = get_regions(cd_species_template)
            cd_regions.sort(key=lambda cd_region: cd_region.get("pos"))
            for cd_region in cd_regions:
                if cd_region.get("name") is None:
                    n_undefined_region_names += 1
                    order = n_undefined_region_names
                else:
                    order = None
                region_model_element, _ = cls._make_and_add_region(
                    reading_context,
                    cd_region=cd_region,
                    super_cd_element=cd_species_template,
                    super_model_element=model_element,
                    order=order,
                )
            model_element = object_from_builder(model_element)
            model_element = register_model_element(
                reading_context,
                model_element,
                reading_context.model.species_templates,
                cd_species_template.get("id"),
            )
        else:
            model_element = None
        layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_modification_residue(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_modification_residue: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        order: int | None,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None:
            model_element = _reading_model.make_modification_residue(
                reading_context, cd_modification_residue, super_cd_element, order
            )
            cd_modification_residue_id = model_element.id_
            model_element = object_from_builder(model_element)
            super_model_element.modification_residues.add(model_element)
            # we use the model element's id (a composite of the parent and
            # child cd ids) rather than the cd element's own id
            reading_context.xml_id_to_model_element.add(
                cd_modification_residue_id, model_element
            )
        else:
            model_element = None
        layout_element = None  # purely a model element
        return model_element, layout_element

    @classmethod
    def _make_and_add_region(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_region: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        order: int | None,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None:
            key = get_key_from_region(cd_region)
            model_element_cls = KEY_TO_CLASS[key]
            model_element = _reading_model.make_region(
                reading_context,
                cd_region,
                model_element_cls,
                super_cd_element,
                order,
            )
            model_element = object_from_builder(model_element)
            super_model_element.regions.add(model_element)
            # we use the model element's id (a composite of the parent and
            # child cd ids) rather than the cd element's own id
            reading_context.xml_id_to_model_element.add(
                model_element.id_, model_element
            )
        else:
            model_element = None
        layout_element = None  # purely a model element
        return model_element, layout_element

    @classmethod
    def _make_and_add_species(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_species_alias: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement | None = None,
        super_model_element: typing.Any = None,
        super_layout_element: typing.Any = None,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            cd_species = reading_context.xml_id_to_xml_element[
                cd_species_alias.get("species")
            ]
            key = get_key_from_species(
                cd_species, reading_context.xml_id_to_xml_element
            )
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            name = get_name(cd_species.get("name"))
            cd_species_homodimer = get_homodimer(cd_species)
            if cd_species_homodimer is not None:
                homomultimer = int(cd_species_homodimer)
            else:
                homomultimer = 1
            cd_species_hypothetical = get_hypothetical(cd_species)
            if cd_species_hypothetical is not None:
                hypothetical = cd_species_hypothetical.text == "true"
            else:
                hypothetical = False
            cd_species_activity = get_activity(cd_species_alias)
            active = (
                cd_species_activity is not None and cd_species_activity.text == "active"
            )
            if model_element_cls is None:
                # Degraded species — no model peer; track ids so reactant /
                # product / modifier creation can detect references to them.
                reading_context.cd_degraded_alias_ids.add(cd_species_alias.get("id"))
                reading_context.cd_degraded_species_ids.add(cd_species.get("id"))
            if reading_context.model is not None:
                model_element = _reading_model.make_species(
                    reading_context,
                    cd_species,
                    model_element_cls,
                    name,
                    homomultimer,
                    hypothetical,
                    active,
                )
            else:
                model_element = None
            if reading_context.layout is not None:
                layout_element = _reading_layout.make_species(
                    reading_context,
                    cd_species_alias,
                    layout_element_cls,
                    name,
                    homomultimer,
                    hypothetical,
                    active,
                )
            else:
                layout_element = None
            auxiliary_map_elements = []
            covered_cd_residue_ids = set()
            for cd_species_modification in get_species_modifications(cd_species):
                covered_cd_residue_ids.add(cd_species_modification.get("residue"))
                modification_model_element, modification_layout_element = (
                    cls._make_and_add_species_modification(
                        reading_context,
                        cd_species_modification=cd_species_modification,
                        super_cd_element=cd_species_alias,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    modification_model_element is not None
                    and modification_layout_element is not None
                ):
                    auxiliary_map_elements.append(
                        (modification_model_element, modification_layout_element)
                    )
            cd_species_template = get_template_from_species_alias(
                cd_species_alias, reading_context.xml_id_to_xml_element
            )
            for cd_modification_residue in get_modification_residues(
                cd_species_template
            ):
                residue_xml_id = cd_modification_residue.get("id")
                if residue_xml_id not in covered_cd_residue_ids:
                    (
                        empty_modification_model_element,
                        empty_modification_layout_element,
                    ) = cls._make_and_add_species_modification(
                        reading_context,
                        cd_species_modification={
                            "state": "empty",
                            "residue": residue_xml_id,
                        },
                        super_cd_element=cd_species_alias,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                    if (
                        empty_modification_model_element is not None
                        and empty_modification_layout_element is not None
                    ):
                        auxiliary_map_elements.append(
                            (
                                empty_modification_model_element,
                                empty_modification_layout_element,
                            )
                        )
            number_of_structural_states_without_value = 0
            for cd_species_structural_state in get_species_structural_states(
                cd_species
            ):
                if cd_species_structural_state.get("structuralState") is None:
                    number_of_structural_states_without_value += 1
                    order = number_of_structural_states_without_value
                else:
                    order = None
                (
                    structural_state_model_element,
                    structural_state_layout_element,
                ) = cls._make_and_add_species_structural_state(
                    reading_context,
                    cd_species_structural_state=cd_species_structural_state,
                    super_cd_element=cd_species_alias,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                    order=order,
                )
                if (
                    structural_state_model_element is not None
                    and structural_state_layout_element is not None
                ):
                    auxiliary_map_elements.append(
                        (
                            structural_state_model_element,
                            structural_state_layout_element,
                        )
                    )
            cd_subunits = [
                reading_context.xml_id_to_xml_element[cd_subunit_id]
                for cd_subunit_id in reading_context.cd_complex_alias_id_to_cd_included_species_ids[
                    cd_species_alias.get("id")
                ]
            ]
            for cd_subunit in cd_subunits:
                cls._make_and_add_species(
                    reading_context,
                    cd_species_alias=cd_subunit,
                    super_cd_element=cd_species_alias,
                    super_model_element=model_element,
                    super_layout_element=layout_element,
                )
            if reading_context.model is not None and model_element is not None:
                model_element = object_from_builder(model_element)
                if super_model_element is None:  # species case
                    model_element = register_model_element(
                        reading_context,
                        model_element,
                        reading_context.model.species,
                        cd_species.get("id"),
                    )
                    _reading_model.make_and_add_annotations(
                        reading_context,
                        cd_species,
                        model_element,
                        source_id=cd_species.get("id"),
                    )
                    _reading_model.make_and_add_notes(
                        reading_context,
                        cd_species,
                        model_element,
                        source_id=cd_species.get("id"),
                    )
                else:  # included species case
                    model_element = add_or_replace_element_in_set(
                        model_element,
                        super_model_element.subunits,
                        func=lambda new, old: new.id_ < old.id_,
                    )
                    _reading_model.make_and_add_annotations_from_notes(
                        reading_context,
                        get_notes(cd_species),
                        model_element,
                        source_id=cd_species.get("id"),
                    )
                    _reading_model.make_and_add_notes(
                        reading_context,
                        cd_species,
                        model_element,
                        source_id=cd_species.get("id"),
                    )
                reading_context.xml_id_to_model_element.add(
                    cd_species.get("id"), model_element
                )
                reading_context.xml_id_to_model_element.add(
                    cd_species_alias.get("id"), model_element
                )
            if reading_context.layout is not None:
                layout_element = object_from_builder(layout_element)
                if super_layout_element is None:  # species case
                    reading_context.layout.layout_elements.append(layout_element)
                else:  # included species case
                    super_layout_element.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[cd_species_alias.get("id")] = (
                    layout_element
                )
            if (
                reading_context.model is not None
                and reading_context.layout is not None
                and model_element is not None
            ):
                for (
                    auxiliary_model_element,
                    auxiliary_layout_element,
                ) in auxiliary_map_elements:
                    reading_context.layout_model_mapping.add_mapping(
                        auxiliary_layout_element,
                        auxiliary_model_element,
                    )
                reading_context.layout_model_mapping.add_mapping(
                    layout_element, model_element
                )
        return model_element, layout_element

    @classmethod
    def _make_and_add_species_modification(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_species_modification: typing.Any,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            cd_species_modification_state = cd_species_modification.get("state")
            modification_state = CD_MODIFICATION_STATE_TO_MODIFICATION_STATE[
                cd_species_modification_state
            ]
            cd_species_template = get_template_from_species_alias(
                super_cd_element,
                reading_context.xml_id_to_xml_element,
            )
            cd_modification_residue_id = f"{cd_species_template.get('id')}_{cd_species_modification.get('residue')}"
            cd_species_id = super_cd_element.get("species")
            cd_residue_id = cd_species_modification.get("residue")
            cd_species_modification_id = f"{cd_species_id}_{cd_residue_id}"
            if reading_context.model is not None:
                model_element = _reading_model.make_species_modification(
                    reading_context,
                    modification_state,
                    cd_modification_residue_id,
                )
                model_element.id_ = cd_species_modification_id
                model_element = object_from_builder(model_element)
                super_model_element.modifications.add(model_element)
            else:
                model_element = None
            if reading_context.layout is not None:
                cd_modification_residue = reading_context.xml_id_to_xml_element[
                    cd_modification_residue_id
                ]  # can also be of type ModificationSite for Genes, RNAs, etc.
                layout_element = _reading_layout.make_species_modification(
                    reading_context,
                    cd_modification_residue,
                    modification_state,
                    super_layout_element,
                )
                # Key the layout id on the alias (the layout element), not
                # the model species id: the same species can appear under
                # several aliases, so a species-id-based prefix would collide
                # across those aliases.  This mirrors the parent species
                # layout, whose id_ is the alias id.
                layout_element.id_ = (
                    f"{super_layout_element.id_}_{cd_residue_id}_layout"
                )
                layout_element = object_from_builder(layout_element)
                super_layout_element.layout_elements.append(layout_element)
            else:
                layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_species_structural_state(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_species_structural_state: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
        order: int | None = None,
    ) -> tuple[typing.Any, typing.Any]:
        cd_species_id = super_cd_element.get("species")
        cd_structural_state_value = cd_species_structural_state.get("structuralState")
        if cd_structural_state_value is None:
            id_part = f"structural_state_{order}"
        else:
            id_part = cd_structural_state_value.replace(" ", "_")
        cd_structural_state_id = f"{cd_species_id}_{id_part}"
        if reading_context.model is not None:
            model_element = _reading_model.make_species_structural_state(
                reading_context, cd_species_structural_state, order=order
            )
            model_element.id_ = cd_structural_state_id
            model_element = object_from_builder(model_element)
            super_model_element.structural_states.add(model_element)
        else:
            model_element = None
        if reading_context.layout is not None:
            layout_element = _reading_layout.make_species_structural_state(
                reading_context, cd_species_structural_state, super_layout_element
            )
            # Key the layout id on the alias (the layout element), not the
            # model species id, so it stays unique when one species appears
            # under several aliases — consistent with the parent species
            # layout and the modification layout above.
            layout_element.id_ = f"{super_layout_element.id_}_{id_part}_layout"
            layout_element = object_from_builder(layout_element)
            super_layout_element.layout_elements.append(layout_element)
        else:
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_reaction(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_reaction: lxml.objectify.ObjectifiedElement,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_key_from_reaction(cd_reaction)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            cd_base_reactants = get_base_reactants(cd_reaction)
            cd_base_products = get_base_products(cd_reaction)
            if reading_context.model is not None:
                model_element = _reading_model.make_reaction(
                    reading_context, cd_reaction, model_element_cls
                )
                # Flag external source/sink before reactant/product creation:
                # a Degraded alias on either side of the reaction means the
                # reaction has unspecified external flux on that side.
                for cd_base in cd_base_reactants:
                    if cd_base.get("alias") in reading_context.cd_degraded_alias_ids:
                        model_element.has_external_source = True
                        break
                else:
                    for cd_link in get_reactant_links(cd_reaction):
                        if (
                            cd_link.get("alias")
                            in reading_context.cd_degraded_alias_ids
                        ):
                            model_element.has_external_source = True
                            break
                for cd_base in cd_base_products:
                    if cd_base.get("alias") in reading_context.cd_degraded_alias_ids:
                        model_element.has_external_sink = True
                        break
                else:
                    for cd_link in get_product_links(cd_reaction):
                        if (
                            cd_link.get("alias")
                            in reading_context.cd_degraded_alias_ids
                        ):
                            model_element.has_external_sink = True
                            break
            else:
                model_element = None
            if reading_context.layout is not None:
                (
                    layout_element,
                    make_base_reactant_layouts,
                    make_base_product_layouts,
                ) = _reading_layout.make_reaction(
                    reading_context,
                    cd_reaction,
                    layout_element_cls,
                    cd_base_reactants,
                    cd_base_products,
                )
            else:
                layout_element = None
                make_base_reactant_layouts = False
                make_base_product_layouts = False
            if reading_context.layout is not None:
                layout_element = object_from_builder(layout_element)
            participant_map_elements = []
            layout_elements_for_mapping = []
            for n_cd_base_reactant, cd_base_reactant in enumerate(cd_base_reactants):
                reactant_model_element, reactant_layout_element = (
                    cls._make_and_add_reactant_from_base(
                        reading_context,
                        cd_base_reactant=cd_base_reactant,
                        n_cd_base_reactant=n_cd_base_reactant,
                        make_layout=make_base_reactant_layouts,
                        super_cd_element=cd_reaction,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    reading_context.model is not None
                    and reading_context.layout is not None
                ):
                    if reactant_layout_element is not None:
                        participant_map_elements.append(
                            (reactant_model_element, reactant_layout_element)
                        )
                        layout_elements_for_mapping.append(reactant_layout_element)
                    layout_elements_for_mapping.append(
                        reading_context.xml_id_to_layout_element[
                            cd_base_reactant.get("alias")
                        ]
                    )
            for cd_reactant_link in get_reactant_links(cd_reaction):
                reactant_model_element, reactant_layout_element = (
                    cls._make_and_add_reactant_from_link(
                        reading_context,
                        cd_reactant_link=cd_reactant_link,
                        super_cd_element=cd_reaction,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    reading_context.model is not None
                    and reading_context.layout is not None
                ):
                    participant_map_elements.append(
                        (reactant_model_element, reactant_layout_element)
                    )
                    layout_elements_for_mapping.append(reactant_layout_element)
                    layout_elements_for_mapping.append(
                        reading_context.xml_id_to_layout_element[
                            cd_reactant_link.get("alias")
                        ]
                    )
            for n_cd_base_product, cd_base_product in enumerate(cd_base_products):
                product_model_element, product_layout_element = (
                    cls._make_and_add_product_from_base(
                        reading_context,
                        cd_base_product=cd_base_product,
                        n_cd_base_product=n_cd_base_product,
                        make_layout=make_base_product_layouts,
                        super_cd_element=cd_reaction,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    reading_context.model is not None
                    and reading_context.layout is not None
                ):
                    if product_layout_element is not None:
                        participant_map_elements.append(
                            (product_model_element, product_layout_element)
                        )
                        layout_elements_for_mapping.append(product_layout_element)
                    layout_elements_for_mapping.append(
                        reading_context.xml_id_to_layout_element[
                            cd_base_product.get("alias")
                        ]
                    )
            for cd_product_link in get_product_links(cd_reaction):
                product_model_element, product_layout_element = (
                    cls._make_and_add_product_from_link(
                        reading_context,
                        cd_product_link=cd_product_link,
                        super_cd_element=cd_reaction,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    reading_context.model is not None
                    and reading_context.layout is not None
                ):
                    participant_map_elements.append(
                        (product_model_element, product_layout_element)
                    )
                    layout_elements_for_mapping.append(product_layout_element)
                    layout_elements_for_mapping.append(
                        reading_context.xml_id_to_layout_element[
                            cd_product_link.get("alias")
                        ]
                    )
            for cd_reaction_modification in get_reaction_modifications(cd_reaction):
                modifier_model_element, modifier_layout_element = (
                    cls._make_and_add_modifier(
                        reading_context,
                        cd_reaction_modification=cd_reaction_modification,
                        super_cd_element=cd_reaction,
                        super_model_element=model_element,
                        super_layout_element=layout_element,
                    )
                )
                if (
                    reading_context.model is not None
                    and reading_context.layout is not None
                ):
                    participant_map_elements.append(
                        (modifier_model_element, modifier_layout_element)
                    )
                    layout_elements_for_mapping.append(modifier_layout_element)
                    layout_elements_for_mapping.append(modifier_layout_element.source)
            if reading_context.model is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.reactions,
                    cd_reaction.get("id"),
                )
                _reading_model.make_and_add_annotations(
                    reading_context,
                    cd_reaction,
                    model_element,
                    source_id=cd_reaction.get("id"),
                )
                _reading_model.make_and_add_notes(
                    reading_context,
                    cd_reaction,
                    model_element,
                    source_id=cd_reaction.get("id"),
                )
            if reading_context.layout is not None:
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[layout_element.id_] = (
                    layout_element
                )
                layout_elements_for_mapping.append(layout_element)
            if reading_context.model is not None and reading_context.layout is not None:
                expanded = set()
                for layout_element_for_mapping in layout_elements_for_mapping:
                    existing_key = (
                        reading_context.layout_model_mapping.representative_to_key.get(
                            layout_element_for_mapping
                        )
                    )
                    if existing_key is not None:
                        expanded |= existing_key
                    else:
                        expanded.add(layout_element_for_mapping)
                reading_context.layout_model_mapping.add_mapping(
                    frozenset(expanded),
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
        return model_element, layout_element

    @classmethod
    def _make_and_add_reactant_from_base(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_base_reactant: lxml.objectify.ObjectifiedElement,
        n_cd_base_reactant: int,
        make_layout: bool,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        cd_reactant_id = get_reactant_id(cd_base_reactant, super_cd_element)
        if reading_context.model is not None:
            model_element = _reading_model.make_participant(
                reading_context,
                Reactant,
                cd_base_reactant,
                super_cd_element,
            )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = add_or_replace_element_in_set(
                    model_element,
                    super_model_element.reactants,
                    func=lambda new, old: new.id_ < old.id_,
                )
                reading_context.xml_id_to_model_element.add(
                    model_element.id_, model_element
                )
        else:
            model_element = None
        if reading_context.layout is not None and make_layout:
            layout_element = _reading_layout.make_reactant_from_base(
                reading_context,
                cd_base_reactant,
                n_cd_base_reactant,
                super_cd_element,
                super_layout_element,
            )
            layout_element.id_ = f"{cd_reactant_id}_layout"
            layout_element = object_from_builder(layout_element)
            reading_context.layout.layout_elements.append(layout_element)
        else:
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_reactant_from_link(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_reactant_link: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        cd_reactant_id = get_reactant_id(cd_reactant_link, super_cd_element)
        if reading_context.model is not None:
            model_element = _reading_model.make_participant(
                reading_context,
                Reactant,
                cd_reactant_link,
                super_cd_element,
            )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = add_or_replace_element_in_set(
                    model_element,
                    super_model_element.reactants,
                    func=lambda new, old: new.id_ < old.id_,
                )
                reading_context.xml_id_to_model_element.add(
                    model_element.id_, model_element
                )
        else:
            model_element = None
        if reading_context.layout is not None:
            layout_element = _reading_layout.make_reactant_from_link(
                reading_context,
                cd_reactant_link,
                super_layout_element,
            )
            layout_element.id_ = f"{cd_reactant_id}_layout"
            layout_element = object_from_builder(layout_element)
            reading_context.layout.layout_elements.append(layout_element)
        else:
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_product_from_base(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_base_product: lxml.objectify.ObjectifiedElement,
        n_cd_base_product: int,
        make_layout: bool,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        cd_product_id = get_product_id(cd_base_product, super_cd_element)
        if reading_context.model is not None:
            model_element = _reading_model.make_participant(
                reading_context,
                Product,
                cd_base_product,
                super_cd_element,
            )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = add_or_replace_element_in_set(
                    model_element,
                    super_model_element.products,
                    func=lambda new, old: new.id_ < old.id_,
                )
                reading_context.xml_id_to_model_element.add(
                    model_element.id_, model_element
                )
        else:
            model_element = None
        if reading_context.layout is not None and make_layout:
            layout_element = _reading_layout.make_product_from_base(
                reading_context,
                cd_base_product,
                n_cd_base_product,
                super_cd_element,
                super_layout_element,
            )
            layout_element.id_ = f"{cd_product_id}_layout"
            layout_element = object_from_builder(layout_element)
            reading_context.layout.layout_elements.append(layout_element)
        else:
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_product_from_link(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_product_link: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        cd_product_id = get_product_id(cd_product_link, super_cd_element)
        if reading_context.model is not None:
            model_element = _reading_model.make_participant(
                reading_context,
                Product,
                cd_product_link,
                super_cd_element,
            )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = add_or_replace_element_in_set(
                    model_element,
                    super_model_element.products,
                    func=lambda new, old: new.id_ < old.id_,
                )
                reading_context.xml_id_to_model_element.add(
                    model_element.id_, model_element
                )
        else:
            model_element = None
        if reading_context.layout is not None:
            layout_element = _reading_layout.make_product_from_link(
                reading_context,
                cd_product_link,
                super_layout_element,
            )
            layout_element.id_ = f"{cd_product_id}_layout"
            layout_element = object_from_builder(layout_element)
            reading_context.layout.layout_elements.append(layout_element)
        else:
            layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_modifier(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_reaction_modification: lxml.objectify.ObjectifiedElement,
        super_cd_element: lxml.objectify.ObjectifiedElement,
        super_model_element: typing.Any,
        super_layout_element: typing.Any,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_key_from_reaction_modification(cd_reaction_modification)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            has_boolean_input = has_boolean_input_from_modification(
                cd_reaction_modification
            )
            if has_boolean_input:
                source_model_element, source_layout_element = (
                    cls._make_and_add_logic_gate(
                        reading_context,
                        cd_reaction_modification_or_cd_gate_member=cd_reaction_modification,
                        cd_reaction_id=super_cd_element.get("id"),
                    )
                )
            modifier_metaid = get_modifier_metaid(
                cd_reaction_modification, super_cd_element
            )
            if reading_context.model is not None:
                if not has_boolean_input:
                    source_model_element = next(
                        iter(
                            reading_context.xml_id_to_model_element.get(
                                cd_reaction_modification.get("aliases"), ()
                            )
                        ),
                        None,
                    )
                model_element = _reading_model.make_modifier(
                    reading_context,
                    model_element_cls,
                    source_model_element,
                    metaid=modifier_metaid,
                )
                model_element = object_from_builder(model_element)
                model_element = add_or_replace_element_in_set(
                    model_element,
                    super_model_element.modifiers,
                )
                reading_context.xml_id_to_model_element.add(
                    modifier_metaid, model_element
                )
            else:
                model_element = None
            if reading_context.layout is not None:
                if not has_boolean_input:
                    source_layout_element = reading_context.xml_id_to_layout_element[
                        cd_reaction_modification.get("aliases")
                    ]
                layout_element = _reading_layout.make_modifier(
                    reading_context,
                    cd_reaction_modification,
                    layout_element_cls,
                    source_layout_element,
                    super_layout_element,
                    has_boolean_input,
                )
                layout_element.id_ = f"{modifier_metaid}_layout"
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[layout_element.id_] = (
                    layout_element
                )
            else:
                layout_element = None
        return model_element, layout_element

    @classmethod
    def _make_and_add_logic_gate(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_reaction_modification_or_cd_gate_member: lxml.objectify.ObjectifiedElement,
        cd_reaction_id: str,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_key_from_gate_member(cd_reaction_modification_or_cd_gate_member)
            cd_modifiers = cd_reaction_modification_or_cd_gate_member.get("aliases")
            cd_input_ids = cd_modifiers.split(",")
            sorted_aliases = "_".join(sorted(cd_input_ids))
            cd_gate_id = f"{cd_reaction_id}_gate_{sorted_aliases}"
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            if reading_context.model is not None:
                model_element = _reading_model.make_logic_gate(
                    reading_context,
                    model_element_cls,
                )
                model_element.id_ = cd_gate_id
            else:
                model_element = None
            if reading_context.layout is not None:
                layout_element = _reading_layout.make_logic_gate(
                    reading_context,
                    cd_reaction_modification_or_cd_gate_member,
                    layout_element_cls,
                )
                layout_element.id_ = f"{cd_gate_id}_layout"
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                gate_layout_elements = [layout_element]
            else:
                layout_element = None
            for cd_input_id in cd_input_ids:
                input_model_element = None
                logic_arc = None
                if reading_context.model is not None:
                    source_model_element = next(
                        iter(
                            reading_context.xml_id_to_model_element.get(cd_input_id, ())
                        ),
                        None,
                    )
                    input_model_element = _reading_model.make_logic_gate_input(
                        reading_context, source_model_element
                    )
                    input_model_element.id_ = f"{cd_gate_id}_input_{cd_input_id}"
                    input_model_element = object_from_builder(input_model_element)
                    model_element.inputs.add(input_model_element)
                if reading_context.layout is not None:
                    input_layout_element = reading_context.xml_id_to_layout_element[
                        cd_input_id
                    ]
                    logic_arc = _reading_layout.make_logic_arc(
                        reading_context,
                        layout_element,
                        input_layout_element,
                    )
                    logic_arc.id_ = f"{cd_gate_id}_arc_{cd_input_id}"
                    logic_arc = object_from_builder(logic_arc)
                    reading_context.layout.layout_elements.append(logic_arc)
                    gate_layout_elements.append(logic_arc)
                    gate_layout_elements.append(input_layout_element)
                if input_model_element is not None and logic_arc is not None:
                    reading_context.layout_model_mapping.add_mapping(
                        logic_arc,
                        input_model_element,
                    )
            if model_element is not None:
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.boolean_logic_gates,
                    cd_gate_id,
                )
            if model_element is not None and layout_element is not None:
                reading_context.layout_model_mapping.add_mapping(
                    frozenset(gate_layout_elements),
                    model_element,
                    representative=layout_element,
                )
        return model_element, layout_element

    @classmethod
    def _make_and_add_modulation(
        cls,
        reading_context: CellDesignerReadingContext,
        cd_reaction: lxml.objectify.ObjectifiedElement,
    ) -> tuple[typing.Any, typing.Any]:
        if reading_context.model is not None or reading_context.layout is not None:
            key = get_key_from_reaction(cd_reaction)
            model_element_cls, layout_element_cls = KEY_TO_CLASS[key]
            has_boolean_input = has_boolean_input_from_reaction(cd_reaction)
            cd_base_reactant = get_base_reactants(cd_reaction)[0]
            cd_base_product = get_base_products(cd_reaction)[0]
            # TODO: remove once a proper reader warning/error mechanism exists.
            # A modulation pointing at (or originating from) a Degraded
            # species cannot be represented in the model — Degraded has no
            # model peer in the new design. Such modulations are malformed
            # input (e.g. Iron_metabolism.xml: ir3e6 -> ir15b); skip them
            # entirely with a warning so the user notices.
            source_alias_is_degraded = (
                not has_boolean_input
                and cd_base_reactant.get("alias")
                in reading_context.cd_degraded_alias_ids
            )
            target_alias_is_degraded = (
                cd_base_product.get("alias") in reading_context.cd_degraded_alias_ids
            )
            if source_alias_is_degraded or target_alias_is_degraded:
                warnings.warn(
                    f"skipping modulation '{cd_reaction.get('id')}': "
                    f"references a Degraded species "
                    f"(source alias='{cd_base_reactant.get('alias')}', "
                    f"target alias='{cd_base_product.get('alias')}'); "
                    "Degraded species have no model peer.",
                    stacklevel=2,
                )
                return None, None
            if has_boolean_input:
                cd_gate_members = get_gate_members(cd_reaction)
                cd_gate_member = cd_gate_members[0]
                source_model_element, source_layout_element = (
                    cls._make_and_add_logic_gate(
                        reading_context,
                        cd_reaction_modification_or_cd_gate_member=cd_gate_member,
                        cd_reaction_id=cd_reaction.get("id"),
                    )
                )
            if reading_context.model is not None:
                if not has_boolean_input:
                    source_model_element = next(
                        iter(
                            reading_context.xml_id_to_model_element.get(
                                cd_base_reactant.get("alias"), ()
                            )
                        ),
                        None,
                    )
                target_model_element = next(
                    iter(
                        reading_context.xml_id_to_model_element.get(
                            cd_base_product.get("alias"), ()
                        )
                    ),
                    None,
                )
                # CellDesigner rewrites a phenotype-targeting INHIBITION to
                # NEGATIVE_INFLUENCE on its next save, so the reaction type
                # alone does not identify the class; the target decides.
                model_element_cls = normalize_modulation_class(
                    model_element_cls, target_model_element
                )
                model_element = _reading_model.make_modulation(
                    reading_context,
                    cd_reaction,
                    model_element_cls,
                    source_model_element,
                    target_model_element,
                )
                model_element = object_from_builder(model_element)
                model_element = register_model_element(
                    reading_context,
                    model_element,
                    reading_context.model.modulations,
                    cd_reaction.get("id"),
                )
                _reading_model.make_and_add_annotations(
                    reading_context,
                    cd_reaction,
                    model_element,
                    source_id=cd_reaction.get("id"),
                )
                _reading_model.make_and_add_notes(
                    reading_context,
                    cd_reaction,
                    model_element,
                    source_id=cd_reaction.get("id"),
                )
            else:
                model_element = None
            if reading_context.layout is not None:
                if not has_boolean_input:
                    source_layout_element = reading_context.xml_id_to_layout_element[
                        cd_base_reactant.get("alias")
                    ]
                target_layout_element = reading_context.xml_id_to_layout_element[
                    cd_base_product.get("alias")
                ]
                layout_element = _reading_layout.make_modulation(
                    reading_context,
                    cd_reaction,
                    layout_element_cls,
                    source_layout_element,
                    target_layout_element,
                    has_boolean_input,
                    cd_base_reactant,
                    cd_base_product,
                )
                layout_element = object_from_builder(layout_element)
                reading_context.layout.layout_elements.append(layout_element)
                reading_context.xml_id_to_layout_element[layout_element.id_] = (
                    layout_element
                )
            else:
                layout_element = None
            if reading_context.model is not None and reading_context.layout is not None:
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
        return model_element, layout_element
