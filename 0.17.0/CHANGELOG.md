# Changelog

All notable changes to momapy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [0.17.0] - 2026-11-05

### Added

- Build, take apart and merge maps with shared make_map, merge_maps and mapping rules *(core)*
- Build, take apart and merge PD and AF maps from map elements *(sbgn)*
- Mark reference fields of model elements *(core)*

### Changed

- Replace structural_states with a single structural_state *(celldesigner)* **BREAKING**
- Move make_map and merge_maps to core.map, make get_layout_model_pairs a method *(core)*
- Remove the SBGN collection tables and cluster rules *(sbgn)*
- Build the model and mapping with the shared map-element code *(sbgn.io.sbgnml)*

### Documentation

- Rewrite the layout-model mapping catalogues and render the CellDesigner one
- Remove the phospho4 sublayout example broken by containers *(demos)*

### Fixed

- Raise when a map element is a child of two map elements that are not equal *(core)*
- Write containers and drawn copies from the layout-model mapping *(io)*
- Refer to the outermost complex for references drawn to a subunit *(celldesigner.io)*
- Merge equal elements with the shared reading helpers *(celldesigner.io)*
- Merge equal elements with the shared reading helpers *(sbml.io.sbml)*
- Read nested operators once, merge participants by owner and read containers *(sbgn.io.sbgnml)*
- Measure and place skia text with linear metrics and subpixel positioning *(rendering)*
- Reject equal glyphs only when they draw different model elements *(sbgn.io.sbgnml)*
- Read AF tags, terminals, references and logic inputs with AF classes *(sbgn.io.sbgnml)*
- Map boolean logic gates with their frozenset key *(celldesigner.io)*
- Link complex members to the written complex alias id *(celldesigner.io)*

### Other

- Merge branch 'develop' into feat_make_maps

### Testing

- Remove the choose_compartment_layout tests
## [0.16.1] - 2026-10-20

### CI/CD

- Key the tox cache on the exact Python version

### Fixed

- Read and write structural states with no value *(celldesigner.io)*
## [0.16.0] - 2026-10-15

### Added

- Drop the -P short form of --presentation-only *(cli)* **BREAKING**
- Add -W to choose the writer, make -P pickle both ends of the pipe *(cli)*
- Read pickles only on request, write text to stdout by default *(io)* **BREAKING**

### CI/CD

- Run one job per OS and Python version, cache uv and tox *(tests)*

### Documentation

- Update the reactant and product ids in the reader docstring *(celldesigner.io)*

### Fixed

- Write the fill of degraded species instead of a hardcoded green *(celldesigner.io)*
- Read and write palmitoylation with CellDesigner's palmytoylated spelling *(celldesigner.io)*
- Write the cat. reac., gate inp. lines and partic. metaids of each drawn copy *(celldesigner.io)*
- Keep one arc and one metaid per drawing of a modifier *(celldesigner.io)*
- Give a degraded species the compartment of a complex on the other side *(celldesigner.io)*
- Write the participants of a drawn reaction from the model, not the arcs *(celldesigner.io)*
- Read a species used several times on a reaction side as one participant *(celldesigner.io)*
- Take the compartment drawing of a species from the model, not from geometry *(io)*
- Take species compartments from the model instead of writing default *(celldesigner.io)*
- Detect XML formats from the root element, not from a substring search *(io)*

### Testing

- Use a real text stream as stdout in the export pipe tests for Python 3.14 *(cli)*
- Cover SBML detection of newline-split and prefixed root tags *(sbml.io)*
## [0.15.1] - 2026-10-08

### Fixed

- Write unspecified entity subunits and generic AF units of information *(sbgn.io.sbgnml)*
## [0.15.0] - 2026-10-02

### Added

- Added SVG stroke-linejoin and stroke-linecap *(drawing)*
- Added SVG-like linear and radial gradients with CSS gradient functions *(drawing)*

### CI/CD

- Install mkdocs-shadcn in the docs deploy workflows *(docs)*

### Documentation

- Add a how-to-cite section with a BibTeX entry *(about)*
- Move the docs to the shadcn theme with momapy branding and framed code

### Fixed

- Place labels from their label bbox when present *(sbgn.io.sbgnml)*
- Compute TextLayout bbox without intermediate rounding *(core)*
- Serialize stoichiometry on write *(sbgn.io.sbgnml)*
- Escape untrusted values in visualize HTML *(cli)*
- Read only the pickle header during detection *(io)*

### Miscellaneous

- Track issues with Backlog.md in the workbench
- Moved agent instructions to AGENTS.md
- Cleaned the repo
- Add .harness-sandbox

### Other

- Merge branch 'develop'
- Merge pull request #34 from cha-hin/doc/shadcn-theme

Redesign the docs
## [0.14.0] - 2026-09-07

### Changed

- Representative naming, public table, key-shape fixes *(mapping)* **BREAKING**

### Fixed

- Keep model-keyed annotations when returning a model *(io.pickle)*

### Testing

- Cover annotation and notes filtering on projection *(io.pickle)*
## [0.13.0] - 2026-08-06

### Added

- Support Bbox in the directional *_of functions *(positioning)*
- Support pretty_print(max_depth=None) for unlimited depth *(utils)*
- Support info on SBML maps and fail cleanly on unsupported types *(cli)*
- Add -T/--text to emit XML to stdout instead of pickle *(cli)*
- Accept style presets in render/export/visualize *(cli)*
- Add get_color, fast has_color, name-only list_colors *(coloring)*
- Add rgb_range/alpha_range to from_rgb/from_rgba *(coloring)*
- Make rendering bases and IOResult officially public *(api)*
- Auto-detect writer from map type; collapse SBGN-ML writer to one class *(io)*
- Give a clear read-only error when exporting SBML *(cli)*
- Add with_annotations/with_notes and type hints to write *(io.pickle)*
- Thread source_id_to_annotations/notes through writers *(io)*
- Expose map-building default font sizes as public API *(sbgn,celldesigner)*
- Add SBMLMap and uniform read() return contract *(sbml)*
- Expose momapy.__version__

### Changed

- Extract build_subunit_to_complex to _writing *(celldesigner.io)*
- Drop dead code and an unused parameter, add sbml.utils __all__
- Fit delegates bbox merging to Bbox.union *(positioning)*
- Drop the never-read sbml_id_to_sbml_element context state *(sbml.io)*
- Drop redundant __all__ from io/core.py *(io)*
- Rename data-transform make_* helpers to get_* *(celldesigner.io)*
- Rename builtin-shadowing filter field to filter_
- Drop vestigial Compartment.state_variables field *(sbgn.pd)*
- Compose TagLayout from SBGNNode instead of PD TagLayout *(sbgn.af)*
- Make UnitOfInformation extend SBGNAuxiliaryUnit *(sbgn.af)*
- Drop dead tuple handling in _build_layout_to_model_id_mapping *(cli)*
- Drop dead style_sheet param from visualize helpers *(cli)*
- Remove unused get_model_and_layout_classes wrapper *(sbgn.io.sbgnml)*
- Remove dead _make_style_sheet and its unused imports *(sbgn.io.sbgnml)*
- Make renderer output-config fully private *(rendering)*
- Remove unused _FONT_WEIGHT_TO_VALUE constant *(drawing)*
- Use module-qualified dataclasses in the three outlier files
- Use full-word locals in Segment.get_distance_to_point *(geometry)*
- Make to_rgba/to_rgb return floats with opt-in round_to_int *(coloring)*
- Drop duplicated MapInfo TypedDicts from get_info *(sbgn,celldesigner)*
- Make Terminal extend SBGNAuxiliaryUnit like PD *(sbgn.af)*
- Move list-attributes presentation flag to -P *(cli)*
- Extract KEY_TO_CLASS to _reading_classification *(celldesigner.io)*
- Make make_empty_* reader classmethods *(celldesigner.io)*
- Rename build_make_sbml_element to make_sbml_document *(celldesigner.io)*
- Align XML-helper arg names with sbgnml *(celldesigner.io)*
- Move file-existence check to utils.check_file_exists *(io)*
- Share format constants via io _constants module *(celldesigner)*
- Tidy public surface via __all__ conventions
- Harmonize from_file signature and default_format *(rendering)*
- Remove unused SBML root document class *(sbml)*
- Drop find_font from top-level core re-exports *(core)*
- Rename diagonal distance args to distance_y/distance_x *(positioning)*
- Make builder registry private (_builders) *(builder)*
- Make I/O result dataclasses kw_only *(io)*
- Default map model and layout to None *(sbgn)*
- Share SimpleSpeciesReference base across all role classes *(celldesigner)*
- Unify the referenced-element field to referred_element
- Split Direction into Direction (cardinals) + Orientation (axes) *(core)*
- Use public momapy.io read/write imports *(cli)*
- Unify apply_style_sheet call target *(cli)*
- Add TypedDict return type for get_info *(sbgn,celldesigner)*
- Raise RuntimeError on save/restore underflow *(rendering)*
- Drop redundant reversible redeclaration *(celldesigner)*
- Parameterize reading-context collection fields *(io)*
- Add type hints to pretty_print, display, _prepare_layout_elements
- Add TypeVar and signatures to collection generics *(utils)*
- Populate all ReaderResult fields in read *(sbml.io)*
- Annotate **options on abstract Writer.write *(io)*
- Annotate is_submodel other param *(sbgn.pd)*
- Mark register_model_element internal as _register_model_element *(io)*
- Declare public __all__ for nodes, arcs, shapes *(meta)*
- Export Reader/Writer and define module __all__ *(io)*
- Make FilterEffect base kw_only *(drawing)*
- Drop divergent id_to_element write param *(io.pickle)*
- Give filter enums string values *(drawing)*
- Relax SBGNPDMap model/layout to optional *(sbgn.pd)*
- Unify Tag/Terminal field to referred_element *(sbgn)*
- Rename reader modules to convention *(sbml.io)*
- Typed universal reader option set + contract docs *(io)*
- Remove the unused omit_keys parameter *(builder)*
- Drop keyword-only marker from tidy helpers *(sbgn,celldesigner)*
- Make Renderer.render_map a concrete convenience method *(rendering)*
- Add __all__ to flat modules, re-export plugins, document meta
- Drop dead with_render_information, accept-and-ignore **options uniformly *(io)*
- Remove dead monitoring module, fix Builder eq/hash *(builder)*
- Make Model abstract via abc.ABC *(core)*
- Add SupportsFileOutput mixin for file-output capability; unify from_file *(rendering)*

### Documentation

- Fix three stale CellDesigner/SBGN-AF inventory entries *(api-reference)*
- Fix inaccurate and copy-paste field/module docstrings
- Mark conceptually-abstract model/layout base classes as abstract *(model)*
- Fix CellDesigner modulator hierarchy in API_REFERENCE
- Fix sbgnml _writing.py cross-reference and merge duplicate section
- Fix PD Process hierarchy in API_REFERENCE
- Fix DEGRADED classification None slot in API_REFERENCE
- Document NoneValue singleton in API_REFERENCE drawing section
- Document public geometry functions in API_REFERENCE
- Add Cairo backend to api_reference overview
- Capture styled map from apply_style_sheet in examples *(styling)*
- Fix descendant-selector example to use GroupLayout *(styling)*
- Correct unknown-property behavior note *(styling)*
- Remove nonexistent opacity property from properties table *(styling)*
- Remove nonexistent Degraded model class from API_REFERENCE
- List all supported formats in package docstring *(rendering)*
- Drop nonexistent Vector class from geometry.py structure comment
- Bracket optional input/-o in export synopsis *(cli)*
- Document stdin fallback for info and visualize *(cli)*
- Remove unsupported --xsep/--ysep from snap-arcs example *(cli)*
- Drop non-running Examples block from _run *(cli)*
- Use frozenset() in model module docstring example *(sbml)*
- Soften Layout-suffix rule in layout.py docstring *(celldesigner)*
- Fix modifications field descriptions on species *(celldesigner)*
- Fix elements.py module docstring to mark bases public *(celldesigner)*
- Correct xsep/ysep read() docstring *(sbgn.io.sbgnml)*
- Give is_submodel/is_ovav full Google-style docstrings *(sbgn.pd)*
- Drop non-running Examples blocks from base layout/map classes *(sbgn)*
- Fix bare Point() in cairo/skia renderer examples *(rendering)*
- Fix bare Point() in shapes/arcs/nodes examples per import style *(meta)*
- Mark Text.transformed transformation param as unused *(drawing)*
- Fix module docstring example imports *(geometry)*
- Document both lookup directions in Map.get_mapping *(core.map)*
- Fix Node.east_south_east docstring typo *(core.layout)*
- Correct SBGN-ML KEY_TO_CLASS value type to tuple[type | None, type] *(API_REFERENCE)*
- Document Renderer.get_bolder/get_lighter_font_weight *(API_REFERENCE)*
- Remove invented language-concept definitions and homogenize model/layout docstrings
- Qualify Point in Cairo and Skia renderer docstring examples *(rendering)*
- Add required rx/ry to module docstring Rectangle example *(drawing)*
- Replace GLFW-window claim with skia live-rendering note
- Sync cli.md with the current command-line interface *(cli)*
- Fix copy-paste errors in layout/model/tidy docstrings
- Drop nonexistent PD EmptySet, fix LogicalOperatorInput type *(api-reference)*
- Import from public paths in docstring/guide examples
- Fix stylesheet examples so they actually parse *(styling)*
- Note CompositeEffect in_/in2 map to SVG feComposite *(drawing)*
- Enrich top-level CLI description *(cli)*
- Fix tidy example to use a real op *(cli)*
- Document private I/O module layout and privacy convention *(io)*
- Note read-only SBML support and self-contain render example
- Add Cairo renderer API reference page
- Fix lowercase true/false to True/False in predicate docstrings
- Document dataclass fields via field metadata + griffe backfill extension
- Upgrade node, arc, and shape class docstrings to Google-style *(meta)*
- Upgrade model and layout class docstrings to Google-style *(sbgn.pd)*
- Upgrade reader/writer docstrings to Google-style *(io)*
- Note universal read options may be inert per format *(io)*
- Note element base classes/mixins are internal *(sbgn,celldesigner)*
- Mark context dataclasses internal in public-surface notes *(io)*
- Sbml read docs in API_REFERENCE *(sbml)*
- Document top-level momapy package as deliberately re-exporting only __version__
- Annotate get_filter_region as returning Bbox | None *(drawing)*
- Add a loose versioning and deprecation policy
- Note CD writer recomputes link geometry on round-trip *(celldesigner.io)*
- Document the Layout-suffix naming rule for layout classes
- Document the two descendants() semantics (containment vs reachability) *(core)*
- Add type hints and docstrings to public core and Renderer methods
- Refresh project structure, CLI subcommands, mapping wording
- Fix source_id_to_layout_element docstring *(io)*
- Drop stale result.exceptions reference
- Reframe I/O make_* as internal helpers, not public contract

### Fixed

- Detect file format independently of the locale encoding *(io)*
- Pin ruff to the 0.14 line for the lint gate *(ci)*
- Pick the negative-modulation class from the target *(celldesigner.io)*
- Pick the negative-modulation class from the target *(celldesigner.io)*
- Emit map-level annotations and notes on write *(sbgn.io.sbgnml)*
- Guard the info model block against a None model *(cli)*
- Draw Rectangle top-left cut corner explicitly *(meta.shapes)*
- Make StyleSheet.__ior__ merge in place *(styling)*
- StyleSheet.from_files returns an empty StyleSheet on empty input *(styling)*
- Derive get_info map_type from the map class, not the model *(sbgn.utils)*
- Round-trip self-modulations without None endpoints *(celldesigner.io)*
- Widen PickleWriter.write obj type to Any *(io.pickle)*
- Honor the ReaderResult id-table contract on round-trip *(io.pickle)*
- Make SBGN layout bases keyword-only to hide positional style params *(sbgn)*
- Default Point.round() *(geometry)*
- Reject empty input with a clear error, consistently *(rendering)*
- Guard Renderer.render_map against a layout-less map *(rendering)*
- Keep a label-less stoichiometry glyph in the layout *(sbgn.io)*
- Raise a clear error on a segment-less arc *(core)*
- Degrade a zero-radius EllipticalArc to a straight line *(geometry)*
- Round-trip bare Model/Layout pickles by object shape *(io.pickle)*
- Guard is_submap against an incomplete other map *(core)*
- Exit cleanly on read and render errors instead of dumping a traceback *(cli)*
- Guard get_info against a None model like the SBGN/CD siblings *(sbml)*
- Give DoubleHeadedArc its own group a distinct _own id *(core)*
- Key skia blur edge_mode on NoneValue; document NoneValue vs None *(rendering)*
- Parse an empty stylesheet to an empty StyleSheet *(styling)*
- Raise a clear error when styling a map without a layout *(styling)*
- Place complex label at label_center when fitting content *(celldesigner)*
- Port-resolve modulation arc target like the source *(sbgn.io)*
- Serialize ModificationState.SULFATED instead of dropping it *(celldesigner)*
- Handle None model/layout uniformly in get_info *(sbgn,celldesigner)*
- Default root layout background to white like SBGN *(celldesigner)*
- Make apply_style_sheet ancestors param explicitly Optional *(styling)*
- Drop redundant Any | None on ReaderResult/WriterResult.obj *(io.core)*
- Use modern union syntax for SVGElement.value *(rendering)*
- Annotate Point.__iter__ return type *(geometry)*
- Narrow Bezier get_intersection_with_line to list[Point] *(geometry)*
- Widen get_mapping return to include frozenset keys *(core.mapping)*
- Annotate super_or_builder return as super, not typing.Type *(builder)*
- Restore NoneValueType on DoubleHeadedArc arrowhead stroke fields *(core.layout)*
- Add IOResult to io.core __all__ *(io)*
- Nest Catalysis under PhysicalStimulation to match the modifier side *(celldesigner)*
- Correct PALMYTOYLATED to PALMITOYLATED so palmitoylation round-trips *(celldesigner)*
- Reject rendering/visualizing a layout-less map with a clean error *(cli)*
- Return a frozen map from set_nodes_to_fit_labels when both omit flags set *(celldesigner)*
- Make Selector a real abc.ABC to match its docstring and abstractmethod *(styling)*
- Fall back to composite id for species references without metaid *(sbml.io)*
- Implement SBMLModel.is_submodel subset check instead of no-op stub *(sbml)*
- Reject writing a map without both a model and a layout *(io)*
- Give _ReactionNodeMixin a default _font_size_func *(celldesigner)*
- Grey Dissociation/Truncation arrowheads in highlight_layout_elements *(celldesigner)*
- Remove dead branch and add explicit fallback in is_process_left_to_right *(sbgn.io.sbgnml)*
- Rename dead border_stroke_width to stroke_width so AF borders render thick *(sbgn.af)*
- Include the top-level Model in build_id_mappings id_to_element *(io)*
- Raise clear ValueError when rendering a layout-less map *(rendering)*
- Exclude id_ from get_stylable_attributes so listed names round-trip *(styling)*
- Resolve percentage filter regions bbox-relative under USER_SPACE_ON_USE *(drawing)*
- Clamp Segment.shortened so over-shortening yields a zero-length segment *(geometry)*
- Clamp EllipticalArc.shortened and make degenerate arcs well-defined *(geometry)*
- Correct EllipticalArc.transformed minor-axis probe and radians output *(geometry,drawing)*
- Return empty list from Arc.points() for a segment-less arc *(core)*
- Make GroupLayout.own_bbox/own_to_geometry self-only *(core)*
- Return an all-None map when reading with_model=False and with_layout=False *(io)*
- Import Point so pretty_print works without a preloaded momapy.geometry *(utils)*
- Read sweep_flag not seep_flag when building elliptical-arc path action *(core)*
- Default Reaction.reversible to False *(sbml)*
- Surface SBML read-only error cleanly in export/style *(cli)*
- Gate fit-complexes to SBGN-PD and report tidy errors cleanly *(cli)*
- Honor --no-snap-arcs in fit-complexes/compartments/submaps *(cli)*
- List supported formats in unsupported-format error *(rendering)*
- Default multi_pages to False to match the CLI *(rendering)*
- Populate ReaderResult id_to_element via build_id_mappings *(sbml.io)*
- Raise FileNotFoundError up front for missing input files *(io)*
- Raise clear error on invalid return_type *(io)*
- Fill in element types for bare dict/list annotations *(types)*
- Parameterize plugin registries with their element type *(types)*
- Type get_drawing_elements_angle unit as Literal *(types)*
- Type sequence-indexing args as Sequence not Collection *(types)*
- Add | None to nullable return annotations *(types)*
- Annotate variable-length tuple fields as tuple[X, ...] *(types)*
- Annotate Color.__or__ return type as Self *(coloring)*
- Round alpha in to_hexa for exact hex round-trip *(coloring)*
- Make the | alpha operator use the 0.0-1.0 scale *(coloring)*
- Raise clear error for unknown SBGN-ML 0.3 map version *(sbgn.io)*
- Center Bar shape on its position *(meta)*
- Only fit complex to its own subunit layouts when tidying *(celldesigner)*
- Make NoneValue pickle-stable so identity survives round-trips *(drawing)*
- Error-contract cleanups for @import, registry getters, get_initial_value, CLI usage
- Auto-detect readers in registration order so CellDesigner precedes SBML *(io)*
- Export to file preserves annotations and notes *(cli)*
- To_rgb no longer truncates fractional ranges *(coloring)*
- Validate with_alpha range, document __or__ percent scale *(coloring)*
- Writer.write returns WriterResult instead of None *(sbgn.io.sbgnml)*

### Miscellaneous

- Drop leftover momapy.transform references
- Adopt ruff D+ANN quality gate and bring the tree into compliance

### Styling

- Correct inaccurate type annotations and numeric literals
- Normalize int literals to float for float-typed fields/params
- Use from-style absolute imports across the codebase
- Compare NoneValue by identity (is / is not) *(rendering)*
- Del leaked registration loop variables *(io,rendering)*
## [0.12.0] - 2026-06-15

### Added

- Expose display() and print_source() with optional notebook deps *(utils)*

### Changed

- Unify the six mapping classes on one frozendict .inverse contract *(utils)*
- Drop vestigial no-op replace parameter from add_mapping *(core.mapping)*

### Documentation

- Regenerate API_REFERENCE.md and fix stale meta docstrings

### Fixed

- Correct auxiliary unit sizing and rendering defaults *(sbgn)*
- Serialize AF units of information with entity child *(sbgn.io.sbgnml)*
- Enlarge default unit-of-information layout sizes *(sbgn.af)*

### Styling

- Remove unused imports, fix ambiguous names, drop duplicate test
## [0.11.2] - 2026-06-05

### Changed

- Resolve residue angle via mapping, not layout-id parsing *(celldesigner.writer)*

### Fixed

- Pass module name string to LogicalOperator ForwardRef *(sbgn.model)*
- Key modification/structural-state layout ids on alias, not species *(celldesigner.reader)*
- Project writer ids onto valid, unique, consistent XML ids *(io)*
- Key subunit_to_complex by id() to distinguish content-equal species *(celldesigner.writer)*

### Testing

- Added FOXO3_activity map to celldesigner testing
## [0.11.1] - 2026-05-05

### Changed

- Identity-keyed multidict for xml_id/source_id model element mappings *(io)*
- Identity-keyed inverse for LayoutModelMapping *(core.mapping)*

### Fixed

- Source subunit alias ids from model walk, not mapping lookup *(celldesigner.writer)*
## [0.11.0] - 2026-05-04

### Added

- Replace Degraded model class with layout-driven emission for external flux *(celldesigner)*
- Add snap_arcs option to size-changing tidy helpers *(sbgn,celldesigner,cli)*
- Clean up visualize page title and add favicon *(cli)*
- Implement arithmetic feComposite operator and fix ARTIHMETIC typo *(drawing,rendering)*
- Re-export ReaderResult and WriterResult from momapy.io *(io)*

### Changed

- Replace EmptySet/Degraded model elements with process flags *(sbgn,celldesigner)*
- Expose font and text attributes as instance fields *(sbgn,celldesigner)*

### Documentation

- Document external source/sink invariant on Reaction and StoichiometricProcess *(model)*
- Add ID assignment sections to SBGN-ML and CellDesigner I/O pages *(api)*
- Use favicon as header logo
- Add favicon and switch yellow brand color to amber
- Add API reference landing page *(api)*
- Align API reference with public re-export facades *(api)*

### Fixed

- Resolve modulation alias layouts from arc, not model identity *(celldesigner.writer)*
- Exclude compartments from tidy's label-fit step *(celldesigner.utils)*
- Skip modulation referencing degraded species *(celldesigner)*
- Add pickling of _singleton_to_key *(layout model mapping)*
- Mark _MultiMixin._make_subunit_shape as abstractmethod *(sbgn)*
- Resolve relative @import against stylesheet directory; remove os.chdir hack *(styling)*

### Miscellaneous

- Remove speculative # TO DO markers *(builder)*
- Remove resolved TODO comments on Reactant.base and Product.base *(celldesigner)*

### Other

- Merge branch 'develop'

### Styling

- Align species default sizes and colors with CellDesigner conventions *(celldesigner.layout)*
## [0.10.4] - 2026-04-23

### Added

- Expose per-source-id annotations and notes on ReaderResult *(io)*

### Documentation

- Document ReaderResult fields and surjection dicts in SKILL.md *(skills)*
## [0.10.3] - 2026-04-23

### CI/CD

- Use mike for versioned documentation deployment *(docs)*
- Install momapy and its dependencies before building docs *(docs)*

### Documentation

- Fix cross-reference syntax in layout-model mapping docstrings
- Fix table rendering in sbgn pd/af and celldesigner module docstrings
- Fix and expand CLI reference, index, and about pages

### Fixed

- Add missing type annotations to resolve griffe warnings *(typing)*

### Other

- Merge branch 'develop'
## [0.10.2] - 2026-04-22

### Changed

- Updated with new public facing api *(demos)*

### Documentation

- Fix SKILL.md bugs (rendering fence, backend name, visualize, info) *(skill)*
- Clarify import conventions in SKILL.md *(skill)*
- Cross-link layout-model mapping catalogues
- Regenerate after package-split refactor *(API_REFERENCE)*
- Prefer public re-exports in usage examples
- Rename CODEBASE_SPEC.md to API_REFERENCE.md and move under skills/momapy/
- Add installable Claude Code skill for momapy
## [0.10.1] - 2026-04-22

### Changed

- Rename format-specific Reading/WritingContext subclasses *(io)*
## [0.10.0] - 2026-04-22

### Added

- Write RDF annotations in CellDesigner writer *(celldesigner.io)*
- Add package facade with re-exports *(celldesigner)*
- Read/write SQUARE_CLOSEUP_* compartments *(celldesigner.io)*
- Add closeup compartment layouts *(celldesigner)*
- Check parent dir exists before writing / rendering *(utils)*

### Changed

- Migrate utils callers to get_child_layout_elements *(sbgn, celldesigner)*
- Drop tuple values from layout_model_mapping *(celldesigner.io.celldesigner)*
- Drop tuple values from layout_model_mapping *(sbgn.io.sbgnml)*
- Add get_child_layout_elements and make _singleton_to_key a SurjectionDict *(core.mapping)*
- Update type annotations and isinstance checks *(rendering,styling,positioning)*
- Replace new_element with new_builder_object in readers *(io)*
- Drop pre-made map/model/layout builders *(sbgn,celldesigner,sbml)*
- Remove PointBuilder and BboxBuilder module-level names *(geometry)*
- Remove pre-made builder classes and convenience methods *(core)*
- Copy user-defined dunders to generated builders *(builder)*
- Expose readers and writers via format subpackage __init__ facades *(io)*
- Move registry and helpers to core, expose via __init__ facade *(rendering)*
- Move registry and helpers to core, expose via __init__ facade *(io)*
- Move registry logic to core, keep __init__ as facade *(rendering)*
- Move registry logic to core, keep __init__ as facade *(io)*
- Promote styling module to subpackage with facade *(styling)*
- Convert pd/af module bodies to from-imports *(sbgn)*
- Add subpackage facade and update callers after restructur *(sbgn)*
- Split af.py into af/ subpackage (model/layout/map + facade) *(sbgn)*
- Split pd.py into pd/ subpackage (model/layout/map + facade) *(sbgn)*
- Split core.py into elements/model/layout/map *(sbgn)*
- Update callers after sbml/core.py removal *(sbml)*
- Split core.py into elements/model, mirror momapy.core layout *(sbml)*
- Update callers after core.py removal *(celldesigner)*
- Split core.py into elements/map, mirror momapy.core layout *(celldesigner)*
- Split core.py into core/model/layout *(celldesigner)*
- Migrate core submodules and __init__ facade to absolute from-imports *(core)*
- Drop unused IOResult.exceptions field *(io.core)*
- Add type hints to public methods *(rendering.svg_native)*
- Add type hints to public functions *(coloring)*
- Hoist WritingContext base to momapy.io.utils *(io)*
- Normalize type hints to PEP 604 union syntax *(sbgn.af)*
- Annotate file_path on SBGN-ML and CellDesigner writers *(io)*
- Drop dead None checks after get_reader/get_writer *(io.core)*
- Include unsupported type in TypeError messages *(positioning)*
- Remove no-op pass branch in modulation reader *(celldesigner.io)*
- Use isinstance_or_builder helper *(sbgn.utils)*
- Align stroke/fill NoneValue checks with skia *(rendering.cairo)*
- Consolidate format-specific pickle readers into one pickle handler *(io pickle)*

### Documentation

- Describe uniform layout_model_mapping scheme
- Update CODEBASE_SPEC and demos for builder refactor
- Fix misleading __init__ docstring *(meta)*
- Flag sbml subpackage as partial skeleton in package docstring *(sbml)*
- Document subpackage layout and exposed stylesheets *(sbgn.styling)*
- Codify absolute-from-imports policy
- Codify absolute-imports rule with __init__.py re-export carve-out *(claude)*
- Require ruff format after edits *(claude)*
- Expand terse model subclass docstrings *(sbgn.af)*
- Add docstrings to reader helper functions *(celldesigner.io)*
- Add docstrings to anchor methods *(celldesigner.core)*
- Note filter effects are unsupported *(rendering.cairo)*
- Replace commented-out example with runnable one *(plugins.core)*
- Mark CellDesigner as read/write *(readme)*

### Fixed

- Read source files as UTF-8 in super discipline test *(tests)*
- Harden coordinate frames against degenerate geometry *(celldesigner.io)*
- Remap pre-4.0 modifier types to KnownOrUnknownModulator subclasses *(celldesigner.io)*
- Restore _writing module import in writer *(celldesigner.io)*
- Read gene/RNA/AntisenseRNA templates without type attribute *(celldesigner.io)*
- Narrow unsupported-map-type error reporting *(sbgn.io.sbgnml)*
- Return map when set_nodes_to_fit_labels is a no-op *(sbgn.utils)*
- Set font_weight initial value to FontWeight.NORMAL *(rendering)*
- Correct RBG/RBGA typos in error messages *(coloring)*
- Stop swallowing exceptions in super_or_builder *(builder)*
- Drop duplicate LineTo in _TruncatedProteinShape *(celldesigner)*

### Miscellaneous

- Remove unused imports in pd/af layouts and models *(sbgn)*
- Extend default style to new compartment layouts *(celldesigner.utils)*
- Remove Claude sandbox artifact gitignore entries
- Drop unused with_styles reader parameter *(sbgn.io.sbgnml)*
- Drop unused lxml import *(celldesigner.io)*

### Styling

- Ruff-format unrelated test/conftest files
- Ruffed demos
- Apply ruff format across src/

### Testing

- Assert singleton participant mappings *(sbgn.io.sbgnml)*
- Forbid raw super(...) in the frozen hierarchy
## [0.9.1] - 2026-04-20

### Changed

- Class RDFAnnotation plain dataclass, sbo_term as str *(sbml core)*
## [0.9.0] - 2026-04-20

### Added

- Add descendants() to Model and ModelElement *(core)*

### Changed

- Collapse build_id_mappings signature to a single obj *(io.utils)*
- Rename SBase to SBMLModelElement; detach SBMLModel from it *(sbml)*
- Split real_source_ids by model/layout side *(celldesigner.io)*

### Documentation

- Added codebase specification

### Fixed

- Populate source_id_to_model_element for models that aren't ModelElements *(io)*
- Repair is_submodel in SBGNAFModel and CellDesignerModel *(model)*
- Iterate children in make_annotations/make_notes and deduplicate *(io)*
- Harden make_notes and replace deprecated .getchildren() *(io)*
- Use float | None for stoichiometry across all formats
- Fix broken CrossPoint drawing_elements *(meta shapes)*
- Fix broken matrix() transform output *(rendering svg_native)*
- Return None for source_id_to_model/layout_element when not requested *(io)*

### Miscellaneous

- Remove animating module
## [0.8.1] - 2026-04-16

### Added

- Change --tidy to -t, add --to-top-left to export and visualize *(cli)*
- Snap arc endpoints to closest anchor point when tidying *(celldesigner utils)*
- Snap arc endpoints to closest anchor point when tidying *(celldesigner)*

### Changed

- Replace set_arcs_to_orthogonal with straighten_arcs *(celldesigner utils)*

### Fixed

- Initialize logic_arc before layout block in logic gate reader *(celldesigner io)*
## [0.8.0] - 2026-04-16

### Added

- Add colors subcommand to list named colors *(cli)*
- Add style subcommand and list styles *(cli)*
- Add implicit stdin/stdout piping support *(cli)*
- Add tidy subcommand with granular layout operations *(cli)*
- Add  subcommand for inspecting stylable properties *(cli)*
- Set model and layout ids from SBML model id *(celldesigner io)*
- Add BooleanLogicGateInput model element *(celldesigner)*
- Set map, model and layout ids from sbgnml map id *(sbgn io)*
- Add visualize subcommand for interactive map viewing *(cli)*
- Added stdout output and -o option for export and info *(cli)*
- Add info subcommand for map file inspection *(cli)*
- Add get_info utility function *(celldesigner)*
- Add get_info utility function *(sbgn)*
- Add list subcommand for readers, writers, and renderers *(cli)*

### Changed

- Align tidy default separations across formats *(utils)*
- Replace ids with id_to_element, source_id_to_model/layout_element *(io)*
- Rename annotations/notes to element_to_annotations/element_to_notes *(io)*
- Require metaid for modifier elements *(celldesigner io)*
- Use distinct ids for model and layout elements *(sbgn io)*

### Documentation

- Note space replacement in structural state ID documentation
- Make ID assignment docstrings consistent between SBGN and CellDesigner readers
- Update CellDesigner ID assignment documentation
- Add BooleanGateInput to CellDesigner ID table and docstring
- Update CellDesigner ID assignment documentation
- Add ID assignment documentation to reader module docstrings
- Update boolean gate, logic arc and modulator in CellDesigner ID table
- Update boolean gate and logic arc in CellDesigner ID table
- Update modification and structural state in CellDesigner ID table
- Mark modulator as registered in CellDesigner ID table
- Update ID assignment patterns for CellDesigner
- Add ID assignment patterns to CLAUDE.md

### Fixed

- Handle missing notes on complex subunit species *(celldesigner io)*
- Catch all exceptions in pickle check_file methods *(io)*
- Resolve correct alias for boolean gate inputs in writer *(celldesigner io)*
- Fix roundtrip bugs in writer for model and MINERVA validation *(celldesigner io)*
- Fix roundtrip bugs in writer for model and MINERVA validation *(celldesigner io)*
- Fix roundtrip ordering bugs in writer *(celldesigner io)*
- Update active layout when resizing nodes and complexes *(celldesigner tidy)*
- Apply styling before tidying *(cli)*
- Fit complexes using subunit model mappings *(celldesigner tidy)*
- Increase default compartment padding to 25 *(celldesigner tidy)*
- Include child compartments when fitting compartment size *(celldesigner)*
- Detect prefixed presentation attributes by suffix matching *(styling)*
- Add modification and structural state to layout_model_mapping *(celldesigner io)*
- Use deterministic ids for reactant and product layout elements *(celldesigner io)*
- Use deterministic ids for boolean gate and logic arc elements *(celldesigner io)*
- Use deterministic ids for species modification and structural state elements *(celldesigner io)*
- Register modifier model and layout elements in xml_id lookup dicts *(celldesigner io)*
- Use distinct ids for reaction, modulation and modifier layout elements *(celldesigner io)*
- Register frozen child elements in xml_id lookup dicts *(sbgn io)*
- Use anchor elements only when building layout-to-model id mapping for visualize subcommand *(cli)*
- Set missing id_ on arc layout elements *(sbgn io)*
- Close temp file before writing to fix Windows PermissionError *(cli)*
- Render hypothetical species with dashed stroke *(celldesigner)*
- Fix modification residue angle computation *(celldesigner)*
- Fix species and modification residue writing *(celldesigner)*
- Add AF map classes to writer classification *(sbgn io)*
- Replace deprecated pyparsing.delimited_list with DelimitedList *(styling)*
- Harmonize intersection boundary checks to parametric t with PARAMETER_TOLERANCE *(geometry)*

### Testing

- Added roundtrip tests *(celldesigner io)*
## [0.7.0] - 2026-04-13

### Added

- Add get_stylable_attributes utility function *(styling)*
- Read line width and color from CellDesigner XML *(celldesigner io)*
- Write line width, color, and font size from layout *(celldesigner io)*
- Read line width and color from CellDesigner XML *(celldesigner io)*
- Add export subcommand for map export *(cli)*
- Support tidy flag for CellDesigner maps *(cli)*
- Add set_arcs_to_orthogonal utility function *(celldesigner)*
- Added tyding functions *(celldesigner)*
- Added tidying functions *(celldesigner)*
- Added experimental writer *(celldesigner io)*
- Added indentation markers *(pretty print)*
- Added utils module *(celldesigner)*

### Changed

- Removed defaults for sbgn tidy *(cli)*
- Set sensible defaults for tidy function parameters *(sbgn)*
- Clean CellDesigner writer conventions *(celldesigner io)*
- Clean CellDesigner reader with reading_context API *(celldesigner io)*
- Clean SBGN reader with reading_context API *(sbgn io)*
- Now uses reaction node anchor functions *(celldesigner io)*
- Renamed functions and variables more appropriately for writer *(celldesigner io)*
- Added _reading prefix for reading modules *(celldesigner io)*
- Added _reading prefix for reading modules *(celldesigner io)*
- Added _reading prefix for reading modules *(celldesigner io)*

### Documentation

- Add documentation for export subcommand *(cli)*
- Improved for map vs map builder *(sbgn)*
- Simplified the top example *(momapy)*

### Fixed

- Use correct coordinate frame bases in writer inverse transforms *(celldesigner io)*
- Derive reaction link participants from layout arcs *(celldesigner io)*
- Derive reaction link participants from layout arcs *(celldesigner.io)*
- Use correct coordinate frame bases for arc edit point transforms *(celldesigner io)*
- Correct connector tip fractions to 0.375/0.625 *(celldesigner)*
- Use target anchor as coordinate frame basis for modifier arcs *(celldesigner io)*
- Fixed writing gates when input is a subunit *(celldesigner io)*
- Now has correct metaids for reactants/products/modifiers
- Fixed dedup issues and refactor of deduplication *(celldesigner io)*
- Fixed dedup issues and refactor of deduplication *(sbgn io)*
- Added fallback for undocumented anchor points (e.g., 'INACTIVE') *(celldesigner io)*
- Added missing source and target to modulation layouts *(celldesigner io)*
- Fix layout-model mapping consistency after dedup *(celldesigner io)*
- Fix mapping for Boolean gates *(celldesigner io)*
- Added subunit remap when identical complexes *(celldesigner io)*
- Fix bug in adding subunits where no replacement was done *(celldesigner io)*
- Fix setting .base to true for base reactants/products *(celldesigner io)*
- Fix flattening of reactions and gates *(celldesigner io)*
- Fixed expansion of reactions and modulations in layout model mapping *(celldesigner io)*
- Fixed bug when reading with no return type *(celldesigner io)*

### Miscellaneous

- Exclude .venv-sandbox from build *(gitignore)*
- Add full-word variable naming convention to CLAUDE.md
- Added new layout model mapping philosophy *(AGENTS)*
- Added poubelle *(gitignore)*
- Cleaned file *(gitignore)*
- Formatting with ruff
- Updated reactome analysis *(demos)*

### Testing

- Add layout_model_mapping integrity tests for SBGN and CellDesigner *(io)*
## [0.6.1] - 2026-03-18

### Added

- Added a demo on map comparison
- Added colinear case when reading reactions *(celldesigner)*

### CI/CD

- Bumped action versions

### Changed

- Hid wip celldesigner writer
- Moved demos from demo to demos
- Moved utils to root *(demo)*
- Rearranged demo files
- Removed unnecessary re-export of reader *(celldesigner io)*

### Documentation

- Moved demo to new paths and name

### Fixed

- Replaced with correct apt deps *(binder)*
- Removed escaping brackets *(binder)*
- Model elements such as modulations are now mapped to the full set of layout elements *(sbgn io)*
- Removed >>> from examples
- User manual files after refactor
- Added skia extra dep to binder
- Updated the demo with latest refactors *(demo)*
- Fixed bug in coordinates of logic gate arcs *(celldesigner)*

### Miscellaneous

- Updated reactome analysis with maps display *(demos)*
- Updated reactome analysis *(demos)*
- Added apt packages required for skia-python
- Simplified entries
- Updated deps
- Added jupyterlab dev dep
- Wip implement celldesigner writer
- Ruff formatting

### Testing

- Fixed new paths *(demo)*
## [0.6.0] - 2026-03-10

### Added

- Added cache for font queries *(fonts)*
- Added a helper function for creating a bbox around points and refactored to use it
- Added group araound textlayout; made better svg element ids and classes
- Replaced shapely and bezier geometry by custom analytical geometry

### Changed

- Replaced named tuple by dataclass *(fonts)*
- Replaced matplotlib fonts finding by custom one
- Renamed self_* methods to own_* methods
- Replaced Bezier approximations with direct elliptical arc calculations *(geometry)*
- Removed unnecessary helper functions *(geometry)*

### Fixed

- Set modifications to own_angle rather than angle *(celldesigner)*

### Miscellaneous

- Added support for python 3.13 and 3.14
- Added TODO.txt to .gitignore

### Testing

- Updated test after refactor *(geometry)*
- Added tests for union of bbox and making bbox around points
## [0.5.0] - 2026-03-04

### Added

- Added optional dict cache to replace
- Added singleton mapping for anchor layout element *(layout model mapping)*
- Removed collection builders by mutable collections *(builder)*

### CI/CD

- Removed commit and made CHANGELOG.md directly from docs.yml *(changelog)*

### Changed

- Moved building builders outside of registering function
- Complete split of model functions, with reader as an orchestrator
- Complete split of layout and model functions, with reader as an orchestrator
- Moved annotations and notes parsing to sbml
- Replace model name from Model to SBMLModel
- Removed duplicate modification and changed order
- Complete refactor of celldesigner io
- Arc flattening and associated refactor + writer cleaning
- Complete refactor with code cleaning *(sbgnml)*
- Complete refactor, separated parsing/model/layout *(sbgnml)*
- Made subpackage and divided into modules *(core)*

### Fixed

- Active borders are now layout elements (fix #3)
- Absence of modification is now treated as a modification with state='empty' *(celldesigner)*
- Now hashable *(builder)*

### Miscellaneous

- Added instructions for debates/ and plans/ directories
- Added debates/
- Added CLAUDE.md and disallowed use of dangerouslyDisableSandbox
- Added claude sandbox artifacts

### Testing

- Added tests for new active layout elements
- Added tests for notes and annotations
- Added tests for sbml
- Added tests for sbgn.utils
## [0.4.4] - 2026-02-24

### Added

- Added tidy option *(cli)*
- Changed default font to Arial for macos and win and deja vu sans for linux
- Added support for af compartment uoi
- Added support for uoi for compartments and submap terminals in af
- Added support for cardinality (a la newt)

### CI/CD

- Changed regex for version; made release conditional to testing; made docs independant of release

### Fixed

- Fixed label position for compartments; fixed rerouting equivalence arcs *(tidy)*
- Activity is now a dataclass
- Added uoi to ad compartment model element
- Default font sizes are now closer to newt
- Or nodes in af were stored and rendererd as and
- Bug in shapely for bezier and elliptical curves
- Bug in fraction for Arc
- Accepts tag with no orientation

### Miscellaneous

- Added AGENTS.md for code agents
- Cleaned useless function *(sbgn.io.sbgnml)*

### Testing

- Added tests for Arc fraction and
## [0.4.3] - 2026-02-13

### Documentation

- Removed linenums for code snippets
- Update example with new io and render_map api

### Fixed

- Changed stoichiometry type from int to float

### Miscellaneous

- Uv sync
- Removed tracking of site/
## [0.4.2] - 2026-02-12

### Documentation

- Changed order of sections
- Added symlink to CHANGELOG.md from root to docs/

### Fixed

- Bug in point to fortranarray and in handling shapely polygons
- Bug in invert of scaling

### Miscellaneous

- Added coverage files

### Testing

- Added new tests
- Added coverage
## [0.4.1] - 2026-02-10

### Documentation

- Added docs for cli and styling
## [0.4.0] - 2026-02-10

### Added

- Added precommit linting (@conventional)
- Added renderer and format autodetection *(rendering)*

### CI/CD

- Added automated changelog with git-cliff

### Fixed

- Distinguish scenario min and all for rendering images

### Miscellaneous

- Removed old testing file
- Docs/plans->plans

### Other

- Added test for demo
- Plugins.registry->plugins.core
- Updated docs
- Updated docs
- Removed version; updated docs
- _renderer_registry->renderer_registry
- Added docs/plans and .tox
- Rendering.*, io.*: changed registering renderers/readers/writers to plugin system; plugins: new
- Updated; rendering._cairo: rm
- Update with renderer changes

### Styling

- Changed default fonts to DejaVu Sans

### Testing

- Update with new plugin api
## [0.3.0] - 2026-02-03

### Other

- Fixed bug in argument names
- Update
- Init
- Added entry point momapy
- Changed 'formats' attributes to 'supported_formats'; added ValueError for unsupported formats
## [0.2.8] - 2026-01-27

### Fixed

- Fixed python version to 3.13 for packaging

### Other

- Io.core; celldesigner.io.celldesigner: replaced ReaderResult's ids by FrozenSurjectionDict
- Modified so it gets the latest tag on the main branch when triggering manually (Claude)
- Add workflow_dispatch option to trigger manually
## [0.2.7] - 2026-01-26

### Other

- Fixed id of layout element taking id of the cd element it comes from
## [0.2.6] - 2026-01-21

### Other

- Fixed layout model mapping for subunits
## [0.2.5] - 2026-01-14

### Other

- Merge branch 'develop' for release
- Added layout model mapping for compartments
## [0.2.4] - 2026-01-13

### Other

- Merge branch 'develop' for release
- Fixed order of compartment aliases so they respect z-order
## [0.2.3] - 2026-01-08

### Other

- Merge branch 'develop' for release
- Added specific supported python 3 versions
- Fixed bug in COPYING badge url
- Fixed bug in COPYING badge url
- Added badges
- Merge branch 'develop'
- Added binder link and how to run the demo locally
- Removed useless demo extra; binder/requirements.txt: replaced demo extra by jupyter dep
- Added demo extra and moved jupyter dep from dev to demo; binder/requirements.txt: added file for binder
## [0.2.2] - 2026-01-07

### Documentation

- Update with new default rendering and reading modules
- Removed copyright

### Other

- Merge branch 'develop'
- Merge branch 'develop'
## [0.2.1] - 2026-01-07

### Other

- Merge branch 'develop'
- Fixed bug where rendering.skia was imported
- Celldesigner.core, celldesigner.io.celldesigner: changed default font to Arial
- Replaced celldesigner_pickle by celldesigner-pickle
- Fixed bug momapy.io.WriterResult->momapy.io.core.WriterResult
- Fixed type hint for .selectors attribute
- Added tests (Claude)
- Replaced pp by pyparsing
- Added Not and Compound selectors
- Update with new core for io and svg for rendering
- Update explaining optional deps
- Made true release conditional to TestPyPi release's success
## [0.2.0] - 2026-01-06

### Fixed

- Fixed bug in checking files: added try in case the file is binary
- Fixed bug where super was called in FrozenSurjectionDict init
- Fixed test
- Fixed import and extents bug
- Fixed bug in class names for logical operators
- Fixed bug: replaced ink_bbox by bbox
- Fixed bug in value=='' for state variables
- Fixed bugs in writing sbgnml
- Fixed bug
- Fixed bug where only macos would be tested
- Fixed bug with group_transform in rendering; added transform if no group_transform
- Fixed bug
- Fixed bug: LogicArc->LogicArcLayout
- Fixed bug in making LayoutModelMappingBuilder with new keys as frozendict
- Fixed bug in filter vs filter_ and filter_.id vs filter_.id_
- Fixed absent NoneValueType type hint for dahsarrays and others
- Fixed bug in make_boolean_logic_gate

### Other

- Merge branch 'develop'
- Made automatic github release
- Updated tests to have frozendict notes and annotations
- Changed type of notes and annotations to frozendict
- One tox job per os
- Adapted workflow to test all python versions on all os with tox
- Added explicit utf-8 encoding when writing files to handle windows
- Added tox.ini and python version
- Typing.Self->typing_extensions.Self for 3.10 compat
- Switched from pdm to uv; pdm-bachend to hatchling; made test dep group
- Changed typing.Self to typing_extensions.Self for compat with 3.10
- Added ModuleNotFoundError as potential source for not available renderer
- Update
- Added pytest tests to push on testing branch
- Updated with new rendering tests
- Merge branch 'develop'
- Cleaned github actions
- Removed comments and unnecessary asserts
- Udpated tests
- Removed all extras
- Added insallation github action
- Added pytest and tests generated by Claude
- Update
- Solved circular imports when registering; fixed bug in sbgn/io/sbgmml.py
- Moved readers and writers registration to init of subpackage for sbml and celldesigner
- Removed buged sbgnml-0.2 writer
- Moved io to own subpackage; moved registering readers and writers to subpackage init
- Moved registering svg-native renderer to base of subpackage
- Changed default renderer to svg-native
- Moved cairo and skia to extras
- Added warning about installing extras
- Added uharfbuzz and matplotlib
- Replaced ink_bbox by bbox
- Change default font to DejaVu Sans; replaced ink_bbox by bbox
- Changed pango layout to harfbuzz and matplotlib (for fonts)
- Merge branch 'develop' into freetype
- Added freetype-py dep
- Added test layout with freetype
- Updated installation instructions
- Updated dependencies
- Added dependencies
- Added frozen annotations
- Added reading id
- Added more layout model mappings
- Added sbgn/io/pickle.py and rendering/cairo.py that were ai generated based on template files
- Updated demo
- Update
- Update
- Added print_source function
- Update
- Added participants of model elements to layout model mapping for: modulations, processes, logical operators
- Added support for HAlignment in TextLayout; added HAligment.CENTER to all sbgn labels
- Updated demo
- Updated demo
- Added NoneValue to edge_mode translation
- Updated demo
- Id->id_
- Mod demo: added example; fixed bug in display where markers were transformed
- _ReactionLayout->ReactionLayout
- In Filter: id->id_
- Made left/right_connector_fraction public attributes
- Added function to set label font size
- Updated packages
## [0.1.3] - 2025-08-28

### Fixed

- Fixed link to doc
## [0.1.2] - 2025-08-28

### Other

- Updated docs/index.md and README.md
- Cleaned
- Made version regex start with number after v
- Publish to testpipy first
## [0.1.1] - 2025-08-28

### Other

- Added module level doc
- Build only if version
- Only on version tags
- Back to version as v.*
- Added dynamic versioning
- Added cd/ci for automatic release on tags
- Moved to pdm build backend
- Updated doc page
## [0.1.0] - 2025-08-12

### Changed

- Refactored; fixed bugs; added truncation layout; id->id_
- Refactored
- Refactored reactions and taken into account transport
- Refactored cairo renderer
- Refactoring and bugs
- Refactored code and fixed in set_arcs_to_borders; added tidy function
- Refactored rendering; render multiple maps

### Fixed

- Fixed typo
- Fixed merge
- Fixed bugs and cleaned up
- Fixed bug in to_top_left
- Fixed return type of fit function
- Fixed bug in biology-qualifiers: isValue->is
- Fix #8
- Fixed bug outputing wrong map element types depending on mode
- Fixed typo
- Fixed bug in intersection of line and shapely object; added rounding
- Fixed bug type selector
- Fixed bug no species in map
- Fixed bug no reaction in map
- Fixed bug in handling undefined state variables
- Fixed bug in product from product link: was using Reactant
- Fixed bug in processing annotations
- Fixed bug in make_notes...: return [] rather than None
- Fixed typo in _make_model_no_subelements...: layout->model
- Fixed bug in finding correct module
- Fixed bug: compartments and species templates were not added to the model
- Fixed bug not taking into account subunits
- Fixed bugs
- Fixed bug: species_aliases includes subunits; removed subunits from those
- Fixed bug: species_aliases includes subunits; removed subunits from those
- Fixed bug in reading structural states
- Fixed bug in start_arrowhead_base
- Fixed bug biology-model->model-qualifiers
- Fixed bug when no tagetLink in reaction modification
- Fixed imports
- Fixed module name after moving annotations to sbml
- Fixed imports
- Fixed bug: need to escape text values
- Fixed import bug
- Fixed childless functions: layout_elements=None->layout_elements=tuple([])
- Fixed bug in arrowhead_border: is None->isnan
- Fixed TransportLayout._end_arrowhead_border_drawing_elements: RIGTH->LEFT
- Fixe bug intersection of line and segment
- Fixed dimensions of layout
- Fixed calls to new signature of momapy.positioning.fraction_of function
- Fixed calls to new signature of momapy.positioning.fit function
- Fixed bug self_children not implemented for arcs
- Fixed bug in writer
- Fixed bugs; took into account AF
- Fixed variable names
- Fixed border_*->*
- Fixed bug with layout.fill being NoneValue
- Fixed id->id_
- Fixed bug in arrowhead_drawing_elements
- Fixed id->id_
- Fixed bug with file names
- Fixed type hints
- Fixed ) bug
- Fixed type hint: self->Self
- Fixed bugs with names
- Fixed bug in Point: __div__ to __truediv__
- Fixed label_center
- Fixed bug in product and reactant links
- Fixed bugs in arrowhead_*
- Fixed bug in call with wrong signature
- Fixed bug in end and start arrowhead length
- Fixed bug in grouplayout bbox
- Fixed typo group drawing elements
- Fixed bug in start_arrowhead for double_headed_arcs
- Fixed bug shorten_bezier_curve, shorten_elliptical_arc: segment->bezier_curve, elliptical_arc
- Fixed bug transform_elliptical_arc: self->elliptical_arc
- Fixed bug: north_north_easr->north_north_east
- Fixed bug setting dasharray to dashoffset
- Fixed bug with doubleheadedarc
- Fixed bugs
- Fixed bugd in DoubleTriangle: momapy.nodes->momapy.meta.shapes, border_drawing_elements->drawing_elements
- Fixed xsdata version to 23.8
- Fixed bug position of layouts
- Fixed bug RectangleCompartment
- Fixed not right model element when already exists in set
- Fixed bugs in shapes and receptor_layout
- Fixed bug in multi_mixin
- Fixed bug outside_model_element in make_and_add_compartment
- Fixed bug in build function for frozendict: self->obj
- Fixed bug with names of celldesignerspeciesreference and gene, rna, antisenserna
- Fixed bug with name of protein that was a property: species already have a name (from SBML)
- Fixed bug: did not take into account compartments
- Fixed few bugs
- Fixed bug: not taking into account compartment
- Fixed names
- Fixed bug
- Fixed bug
- Fixed type hint bug in association layout
- Fixed bug type hint BQ
- Fixed union bug
- Fixed bug: color alpha int->float
- Fixed bug: colors float->int
- Fixed bug: product was made with Reactant cls
- Fixed bug: uois added to svs
- Fixed buggy inheritance of stimulation layout and equivalence arc layout
- Fixed buggy inheritance of logic arc layout
- Fixed builder for forward refs; added type | new_type in builder to allow non builders in builders
- Fixed bug with colors: if colors not in list of color definitions, assumes its hex def
- Fixed bug when no list_of_color_definitions or no list_of_styles
- Fixed bug in split_line_coords
- Fixed with new presentation attributes
- Fixed type of transform from transformation to tuple[transformation]
- Fixed bug: subunit attr can be None
- Fixed typo
- Fixed bug: no unset in simple value grammar
- Fixed typo
- Fixed font_color to new stroke/fill
- Fixed typo
- Fixed typing bug
- Fixed imports
- Fixed cairo import
- Fixed bug render_curve_to
- Fixed bug when saving state
- Fixed bugs
- Fixed import errors
- Fixed kw_only in making skia renderer
- Fixed fill and stroke for textlayouts
- Fixed Close->ClosePath
- Fixed bugs
- Fixed bug font weight
- Fixed transformed for text
- Fixed new meta imports
- Fixed bug on subunit presentation attributes
- Fixed typo
- Fixed typo
- Fixed typos
- Fixed typo
- Fixed bug in bbox for shapely obj
- Fixed bugs
- Fixed typos
- Fixed bug: two times slope1
- Fixed Ellipse.to_path: now 4 elliptical arcs
- Fixed bug: use arrohead_base for computing arrohead angle
- Fixed bug: render_curve_to->add_curve_to
- Fixed bug: to_cubic->to_curve_to
- Fixed bug: fx->fX,fy->fY
- Fixed bug
- Fixed bugs
- Fixed bugs
- Fixed bug: n_segs not passed through for bezier curve to shapely
- Fixed bug: no compartment
- Fixed bug comparing points
- Fixed multipages
- Fixed bug: inverted is_sublayout relation
- Fixed bug in compartment_ref
- Fixed typo
- Fixed bbox for whole map
- Fixed bug when no state in sv
- Fixed bug in hex output
- Fixed bug: hex repr to 'x'
- Fixed bug: hex on int not float
- Fixed bug
- Fixed bug in get_mapping
- Fixed bug when no extension
- Fixed reverse order for points of consumption
- Fixed bugs
- Fixed bug when color_str started with '#'
- Fixed bugs with new layout_model_mapping
- Fixed bug for ior: now like or and not dict.__ior__
- Fixed bug
- Fixed bug with or selector
- Fixed bug in is_ovav: fields->dataclasses.fields
- Fixed bug in shortened when self.length() == 0
- Fixed bug in typing
- Fixed typo in model: switched SpeciesReference and SimpleSpeciesReference
- Fixed bug in coinsident lines
- Fixed bug points to segments
- Fixed bug: arc.x and arc.y
- Fixed typo in angle
- Fixed bug in crosspoint border drawing element
- Fixed bug: TextLayoutElement -> TextLayout
- Fixed label textlayout width and height
- Fixed bug
- Fixed bug in stylesheet list
- Fixed bug in reading list of stylesheets
- Fixed bug with returning results
- Fixed bug when builders were used instead of built objects
- Fixed unused imports
- Fixed namespace error
- Fixed tidy; set_arcs_to_borders does not do anything if no intersection is found
- Fixed imports
- Fixed imports
- Fixed import
- Fixed bug
- Fix + vanted.css
- Fixed bug in frozendict ini
- Fixed frozendict bug: initialization from dict rather than list
- Fix bug
- Fixed bugs
- Fixed bug in set_arcs_to_borders
- Fixed bug when last_segment.length() == 0 in arc anchors
- Fixed bug: set_matrix -> transform in cairo renderer
- Fixed bug in intersection of line and circle
- Fixed bug in render_maps
- Fixed bug in textlayoutelement
- Fixed bugs
- Fixed import bug
- Fixed bugs and replaced nodelabel by textlayout
- Fixed bugs in render_maps: calculation of min_x and min_y
- Fixed bug with labels of compartments in set_compartments...
- Fixed bug with PhantomLayoutElement
- Fixed bugs with arrowhead bboxes
- Fixed bug in copying in render_map with to_top_left==True
- Fixed bugs
- Fixed typo
- Fixed make_builder: Builder is now always a base class, and connectable_attributes are well set
- Fixed imports
- Fixed rendering of text with new coord system
- Fixed import
- Fixed imports

### Other

- Updated docs
- Added workflow for building docs
- Updated doc
- Updated demo
- Rm unused import
- Updated with proper display for layout elements with transformations
- Bbox now takes into account ink_bbox of text
- Ruff
- Merge branch 'develop' into shapely_transform
- Merge branch 'demo' into develop
- Updated demo; fixed bug in utils
- Added transform
- Made transform a tuple of transformation
- Udpated docs
- Added ruff, pygments
- Rm red layout stroke
- Removed config from param for creating a skia renderer
- Updated doc
- Updated packages and removed sphinx related and black deps
- Updated doc
- Updated layout_model_mapping
- Update
- Merged
- Updated doc
- Updated documentation
- Updated documentation
- Merge branch 'develop' into docs_mkdocs
- Updated documentation
- Update
- Added reading sbml skeleton
- Updated demo
- Added EMPTY_SET key; fixed bug in writing compartmentRef attribute
- Updated functions to new layout_model_mapping
- Added replace=True to add_mappings
- Added replace option in add_mapping
- Support for annotations, compartment_refs
- Merge branch 'develop' into write_sbgnml
- Replaced call to Pango.extents_to_pixels by pos / Pango.SCALE to avoid new bug with function
- Merge branch 'develop' into write_sbgnml
- Added pdm-readiness
- Added cross_hv_of; cross_vh_of; set_mid_of; set_cross_hv_of; set_cross_vh_of functions
- Added support in CellDesignerModel for Regions
- Added mid_of function
- Closes #19
- Closes #18
- Closes #14: replace is not NoneValue by != NoneValue
- Closes #13: fixed bug in Color.to_rgba; fixed range to float in skia fill and stroke
- Closes #10
- Closes #9
- Updated dependencies
- Cleaned dependencies
- Added id and class in rendering
- Added structural state layout
- Added post_init to pointbuilder
- Replaced is momapy.drawing.NoneValue by ==
- For notes, annotations, ids: frozendict to dict
- Added hash and eq methods for NoneValue singleton
- Added handling non text file exception in read
- Added celldesigner pickle read and write
- Removed reduduntant exceptions from WriterResult
- Added _active to ids of active species
- Added support for dasharray in SingleNode
- Added support for stroke_dasharray
- Mappings are now frozendicts
- Merge branch 'develop' into cd_layout_model_mapping
- Rounded for shapely
- Rm unused import
- Replaced typing for source and target of arc to LayoutElement
- Added layout model mapping for reactions and modulations
- Added layout_model_mapping for species
- Changed require-python to >=3.10
- Added SurjectionDict
- Merge branch 'develop' into write_sbgnml
- Modification residues are now sorted following their angle (ascending)
- Taken into account undefined names for modification residues with an order attribute
- Added order to modification residue
- Update with new sbgnml export
- Updated writing sbgnml
- Changed function to make notes; added support for map/model notes and annotations
- Added support for notes and annotations on the map itself
- Rm annotations to frozendict
- Added notes support for elements
- Added notes for compartments
- Added export of notes
- Updated to python 3.12
- Rm transformation of annotations and notes into frozen sets
- Changed python
- Start of new writer
- Added support for af unit of informations
- Added specific function for making activities
- Removed unnecessary _sbgnml_parser*
- Added support for labels in submaps
- Added new support for reading af without xsdata
- Added ids to map_element_to_ids
- Added ids to ReaderResult
- Removed print
- Merge branch 'develop' into cd_ids
- Merged sbgn_revamp
- Added model layout mapping
- Continued revamping
- Removed annotations and notes
- Added biomodel qualifiers
- Rvamped
- Removed old unused parse file
- Added map_element_to_ids mapping
- Removed useless dict transform of model_element_to_layout_element
- Removed unused parser file
- Annotations is now frozen
- Sbml.Annotation->sbml.RDFAnnotation
- List->set
- Added ids for reactants and products
- Stoichiometry can be None
- Finished model maker
- Added Palmytoylated
- Added PALMITOYLATED
- DON'T CARE->DON_T_CARE
- Removed unused re import
- AntisenseRNA->AntisenseRNA
- Optional listOfModification in reaction
- Added annotations
- Removed map_element_to_annotations from CellDesignerMap
- Added boolean logic gates for modulations
- Added logic gates
- Added class for logic arc layouts
- Changed size and font of logic gates
- Added gate layouts
- Continued revamping
- Removed useless newline
- Removed useless print
- Continued revamping
- Udpated
- Updated with_model/with_layout options
- Read/write_file->read/write; added os.PathLike type annotation
- More new methods
- In Writer: write()->write_file()
- Beginning of refactoring celldesigner reading
- Update
- Added annotations for included species
- First fix read_file
- New way of parsing: model, layout, map; annotations are outside of objects
- Udpate with doc
- Added undoc-members
- Changed conf.py location for new org
- Update docs/ organization
- Mv .readthedocs.yaml to root
- Added files for readthedocs
- Mv sphinx_docs->docs
- Removed ipykernel dependency
- Udpated demo
- Added dist/
- Udpate with classifiers and urls
- Updated package description
- Update
- Update
- Remove intersection of line with drawing and layout elements
- Added docs
- Updated demo
- Updated demo
- Moved demo to /; cleaned up
- Added documentation
- Udpated docs
- Udpated doc
- Updated doc
- Update doc
- New_builder->new_builder_object; added type hints
- New_builder->new_builder_object
- Added full input of SBGN AF maps
- Update
- Updated demo
- Updated type hints and methods
- Added from_top_left option
- Removed unused import
- Update demo
- Update with new attr names
- Added center to border and angle functions
- Update with new attr names
- Fill of layout set to NoneValue
- Changed qualified attrs to unqualified attrs (default)
- Added notebook
- Added docs"
- Added __init__.py
- Added __init__.py
- To python 3.12
- Added documentation
- Updated
- Added particular anchors for celldesigner shapes
- Moved labels of modifications
- Taken into account active; fixed bug in position of compartments
- Added some anchor points
- Added support for modulations
- Taken into account catalysis
- Put labels in right place
- Added replacement of _text_ by character
- Added functions to find angle and border of shapely_object and collection of drawing elements
- Update with dissociation
- Replaced fit layout by the size of the layout
- Added super_or_builder method
- Added todos
- Remade taking into account edit points with center or link anchor
- Added anchor_point method to layout element
- Added comment
- Add get_transformation_for_frame_function
- Partially fixed bug when no link anchor
- Taken into account omitted transition, unknown transition, transcription, translation
- Taken into account start node in base reactant layout
- Refacrtored state_transition_layout and add heterodimer_association_layout
- Took into account base reactants and edit points for association
- Added layout for state transition, with reactants and products
- Begined adding layout for reactions
- Added with_layout option to prevent from making the layout
- Added intermediate cardinal points
- Added state transition layout prototype
- Added compartment layouts; refactored code
- Add_or_replace_element_in_set now returns the element that is in the set at the end
- Code layout
- In _Modifier: species->referred_species
- Replaced .species by .referred_species in SpeciesReferences; replaced CellDesignerSpeciesReference by SpeciesTemplate
- Added reading of empty state variable
- Readded Annotation
- Removed notes and annotations from sbase
- Support for parsing sbml annotations inside notes
- Added support for reduced boolean logic gates
- Added listOfGateMember to reaction
- Rm make layout and model_layout_mapping for celldesigner
- Added None to model, layout and layout_model_mapping
- Added annotations
- Map_element_to_annotation->map_element_to_annotations
- Added rdf annotations for species
- Added function to make annotations
- Qdded attributeFormDefault='qualified' for rdf
- Added map_element_to_annotation to Map
- Added attributes of annotations
- Added empty state which arises sometimes
- Changed to using aliases instead of species
- Added acetylated modification
- Updated schemas and changed location
- Now transforming aliases rather than species
- Added hypothetical for species
- Taken into account: outside for complexed; modifiers with gates
- Modification->modificationType
- Homodimer->homomultimer
- Adapted to minerva bug on type for rna, gene and anitsenserna references
- Added # abstract
- Removed momapy-model from ids for model elements
- Removed metaid, notes and annotations of comparison for species
- Udpated the celldesigner schema with reduced notation
- Update
- Cleaned model
- Cleaned the model
- Update
- Cleaned modulations in CellDesignerModel
- Cleaned modulations and modifiers
- Cleaned modifier and added comment
- Modulators->modifiers
- No printing of base types or objects evaluating to False (e.g., empty collections)
- Removed structuralstatevalue: now always str
- Checks for subclass rather than exact type matching in exclude_cls
- Cleaned make parser for celldesigner
- Merge branch 'develop' into celldesigner
- Updated python version to >3.10 and <3.11
- Added AuxiliaryUnit concept
- Redid tpying.union for forwardref
- Replaced referes_to attribute by reference attribute
- Got rid of typing.Union
- Made the ids of model elements deterministic
- Cleaned
- Added add_or_replace_elemement_in_set function
- Merge branch 'fix_builder' into celldesigner
- Removed UndefinedVariable class; use order instead
- Added annotations reading for macromolecules
- Added superclass BiomodelQualifier for BQModel and BQBiol
- Added module for forwardref of logicaloperator
- Moved make_pango to new _pango module; forced ids to str
- Cleaned up
- Applying stylesheet to objects; to builder becomes _ function
- Update
- Shortening a segment of length 0 now returns a copy of the segment
- Update
- Updated code
- Update with new way: build objects
- Exluded Point from collections in pretty_print function
- Added class exclusion feature in pretty print; changed color:black->green
- Simplified names of mappings
- Added  make_union option to the transform_type
- Removed add_element method
- Builder transform type: now returns type_ | new_type
- Bug fix: stopped transforming default factory functions
- Changed variable names: field_->field, mappings to more conventional names
- Antisens->Antisense
- Merge branch 'develop' into celldesigner
- Can perform functions on map
- Changed check_file methods: no use of parser anymore
- Render extension: made attributes qualified
- Cleaned up; moved schemas and make_parser outside of src
- Added parser for sbgnml_0_2 and _0_3
- Updated the README with link to demo
- Udpated the demo
- Update
- Added License
- Added text to README
- Merge branch 'develop' into celldesigner
- Removed tests from git
- Readded celldesigner/
- Readded sbml/core.py
- Deleted sbml/ and celldesigner/ to move them to branches
- Pipenv->pdm; cleaned up
- Changed rectangle compartment
- Merge branch 'develop' into celldesigner
- Added script for making a css template file from a module
- Updated and added styles with @import
- Updated demo
- Changed defaults for subunits attributes
- Updated with new presentation attributes
- Changed defaults for presentation attributes
- LogicArc->LogicArcLayout;EquivalenceArc->EquivalenceArcLayout
- Added | None to types for stroke_width
- Path_shorten->shorten; added start_shorten to Arc
- Now built with @import cs_black_and_white and newt_no_cs
- Added chdir for relative css @import
- Added import statement feature inside css
- StyleSheet read_file->StyleSheet.from_file; join_style_sheets->combine_style_sheets;read_string->from_string; added from_files classmethod
- Update
- Pseudo-fixed bug with unset
- Update
- Added script to make a css template
- Harmonize initial values
- Layout is now a Node
- Added unset css value, that is transformed to Python's None
- Added default values for presentation attrs of SBGNNode
- Changed list_colors to print_colors; list_colors now list all pairs (color_name, color) of the module
- Cleaned up code: new SBGNSingle/DoubleHeadedArc; arrowhead_drawing elements coded for arcs instead of subclassing; cleaned attributes order
- Updated layouts with new shapes
- Cleaned typing
- File creation
- Added make_node and make_arc functions
- Changed default values for presentation attritubutes in TextLayout; use of make_pango_layout from utils in textLayout
- Added get-initial_value method; fixed bug font weight mapping
- Added get_initial_value method
- Added FONT_WEIGHT_VALUE_MAPPING
- Moved testing functions to testing; added make_pango_layout to utils; removed print_classes from utils
- Added transformation of elliptical arc to bezier curves; cleaning
- Cleaning
- Cleaned up
- Added sbmlutils
- Continued coding drawing_elements methods
- Update
- Font family and size become mandatory on text layouts
- Filter on all drawing elements
- Added new StatefulRenderer
- Added fill to textlayout
- To python 3.11
- Normalized presentation attributes; support in svg-native renderer
- Update with new drawing elements
- Added new classes following the spec
- Added import for svg_native renderer
- Added styling: fill, stroke, font
- Added support for font style and weight; added support for text-anchor (not skia)
- Added fill rule
- Merge branch 'develop' into sbml_layout
- Removed childless method from GroupLayout
- NodeLayout->Node; ArcLayout->Arc
- Update
- Shorten->path_shorten
- Added defaults for nodes and arcs; cleaned up
- Removed nodes width and height in render function
- Changed defaults of metas
- Taken into account new shape buisness
- Simple and Multi mixins return shapes instead of nodes
- Cleaned up
- Moved Shape to core
- Shapes, nodes and arcs to meta dir
- Revamped to shapely for elliptical arc function
- Revamped _split_line_string function
- Removed translated method from layout_element since not used anywhere
- Updated nodes
- Finished nodes and added all arcs
- Removed arrowhead_fill from defaults
- Reverted width for Bar: should only be arrowhead_stroke_width
- Added width for Bar
- Added rendering_testing for arcs; changed rendering nodes on grid to rendering_layout_elements
- Finished rendering function
- Cleaned up
- Renamed geometry functions; added some new functions
- Added rendering utility functions
- Revamped intersection function
- Changed defaults and attributes' order
- Revamped nodes
- New styling attributes for connectors
- Revamped sbgn nodes
- Cleaned defaults
- Increased error tolerance for elliptical_arc to shapely
- Added new arcs
- Cleaned code and fixed bug with arrowhead_length==0
- Shapes->nodes
- Now SingleHeaded and DoubleHeaded arcs
- Shapes->nodes
- Started to change to new border style
- New start and end arrowheads in arc; new border in node
- New and updated functions for segments, elliptical arcs and bezier curves
- Cleaned up
- Added beginning of layout and render
- First commit
- Added x and y attribute to Layout
- MapLayout->Layout
- Added anchors for MapLayout
- Width cannot be < to height
- Removed arrowhead_bbox from arcs
- Removed addition in path; Close->ClosePath action
- Update
- Vanted->sbgned
- Cleaned up
- Updated demo
- Updated demo
- Added pretty print function
- Added apply_style_sheet to map
- Removed return map from write
- Added compartments to entities
- Model and layout are now non optional
- Added support for notes
- Update
- Changed notes parsing to strict
- Added listOfBackgroundImages
- Added annotations to map, notes to map, model, model_element
- Cleaned up
- Added option for reading and writing annotations
- Support for writing annotations
- Added annotations to sbgnmodel
- Specified annotation class
- Added support for sbml miriam annotation
- Package name from momapy.__about__
- Added package name
- Added option for render_information
- Added support for more glyphs
- Added __init__.py
- Remade parser
- Added render information attributes
- Added writing render information
- Added about with version and author
- Added leading # to to_hex and to_hexa return string
- Added to_hex and to_hexa methods
- Update sbgnml writer
- Update
- Udpate
- Updated tidy function and nodes fit labels function
- Udpated set_arcs_to_borders
- Update
- Updated newt.css
- Added reversibility of processes; left-to-right of processes and operators
- Added get_mapping to mapbuilder
- Added upack option to get_mapping: unpacks the frozenset(frozenset) result; added get_mapping to map
- Added left_to_right attribute to layout with connectors
- Removed source and target from children in ArcLayout
- Added reversibility for processes
- New set_arcs_to_borders function
- Added monitoring
- Changed default renderer to skia
- Update
- Cleaned up
- New subpackage
- Cleaned up
- Changed to reader class
- Staticmethod->classmethod
- Staticmethod->classmethod
- Added new reader class
- Changed parser file name
- Updated read function; added perturbation unit of informaion to schema
- Take into account map bbox
- New read write functions
- Added additional error: class where add_element is called
- Base_left/right_connector->left/right_connector_base/g
- Added two new anchors: left_connector_tip and right_connector_tip
- Update
- Update
- Added utils module with a new str func
- Added new layout_model_mapping
- To python 3.11
- Added pyparsing to setup
- Cleaned
- ObjectBoundingBox->ObjectBoundingBox
- Writes to file only if output_file is defined in config
- Added reactant and product edit points
- Changed default width and height of reaction node
- New nodes taken into account
- Update
- Fixed bug in copying dict for joining two stylesheets
- Removed geometry import
- Update
- State variable set to '' is now considered to be None
- Child can now be None and
- Added default width and height to Arrow
- More shapes taken into account
- Added CellDesigner shapes and layout elements
- Update
- Added SBGNPD/AFLayout
- Update
- Cleaned up
- Update
- Build methods and from_object methods now take a mapping as parameter which avoids rebuilding identical object
- Remove colors object: momapy.coloring.colors.* -> momapy.coloring.*; rgb, rgba, hex, hexa functions->from_rgb, from_rgba,... methods of Color
- Update
- Model_layout_mapping -> layout_model_mapping
- Updated dependencies
- Kw_only and new defaults
- Updated to python 3.10; added Pipfile*
- - in css is now possible; replace _ by - in css of sbgn
- Updated notebook
- Revert "updated notebook and cleaned up"

This reverts commit c115e10923928ebf55f116931bfbf39504451429.
- Updated notebook and cleaned up
- Changed defaults for af units of information
- Made style for logic arc
- Redeveloped svg native renderer
- Changed arguments order in SkiaRenderer
- Bug in renderer ini and added antialiasing to imagefilter painting
- Added new reaction types
- Added reactions and reactionmofication
- Added PHYSICAL_STIMULATION to reaction types
- Preserves __init__ from being overwritten by xsdata
- Trigger-> triggering + typo
- Updated CellDesigner schema
- Added Compartment
- Other gates; complexes; compartments
- Typo
- Added Modulator and changed modifiers ontology
- Added rest of modifier types
- Updated read_file
- Modulators -> modifiers
- Modulator to Modifier
- Added boolean logic gates
- Added return value for read_file
- Update
- Cleaned
- Added white colorscheme
- Added classselector; simplified typeselector code
- Update
- Added rendering methods for all filter effects
- Fixed bug;added enums for filter effects
- Added with_alpha method
- Added notebook
- Added is_submapping for ModelLayoutMapping; cleaned is_sublayout
- Position of text in TextMixin is now label_center() rather than position
- Updated
- Cleaned up
- Added dasharray property
- Svg implementation of get_region_filter
- Updated newt style
- Updated demo
- Added get_filter_region method to drawing element
- Bug in shapely method of elleptical arc
- Implemented drop shadow filter
- Replaced path in stadium by rectangle
- Updated demo
- Cleaned up
- Cleaned up
- Updated to_shapely method for elliptical arc
- Changed sweep flag of stadium shape
- Udpated demo
- Added to_polygons option to to_shapely method
- Fit nodes to labels: to logical bbox
- Reverted Direction back to momapy.core
- Anchors no longer abstractmethods, but implemented in parent nodelayout class
- Moved Direction to sbgn.core
- Added file
- Updated gitignore
- Updated dependencies
- Fraction moved to core
- New intersection method with shapely
- Intersection function: new name
- Updated demo
- Added demo as subpackage
- Cleaned; added general intersection function
- Added shapely geometry
- Added shapely dependency
- Cleaned up and added __div__ for point(builder)
- Take into account bezier curves
- Rearranged fraction function for bezier curve
- Added bezier curve; core/arc: changed points to segments
- Changed to python 3.9; added bezier module
- Reworked transformed method for elliptical arc
- Arrowhead now used transformed method instead of svg-style transform attribute
- Typo
- Removed arc drawing element
- Removed arc drawing element
- Added transformed methods
- Updated rendereres
- Bug skia renderer no dataclass decorator
- Updated demo
- Added fraction method to arclayout
- Cleaned up
- Updated demo
- Added default width and height to SBGN glyphs
- Cleaned up
- Updated demo
- Update
- Added anchors to textlayout; fixed bugs in angles
- Added anchors for crosspoint
- Merged
- Updated demo
- Ignore demo/*.svg
- Added demo
- Moved is_sublayout method from LayoutElement to MapLayout
- Updated vanted and newt styles with filter: none
- Ink_bbox() -> bbox()
- Updated vanted and newt styles with filter: none
- Updated newt style sheet
- Updated stylesheet
- Descendants->ancestors in apply_style_sheet function
- Added newt stylesheet
- Cleaned up
- Added submap, submodel and sublayout methods; added translated method
- Added crosspoint
- Updated demo
- Anchors are computed automatically; shapes are computed using joints
- Added demo and cleaned up
- Updated celldesigner model and io
- Merge branch 'cd' into developpment
- Cd model elements now inherit from sbml core elements
- Merge skia
- Updated with skia
- Added skia renderer
- X/ysep for nodes set to 5
- Updated with required package skia-python
- New filter effects and new svg-native-compat renderer
- Implemented af model, layout and rendering
- Merge remote-tracking branch 'origin/cd_dev' into cd
- New model elements
- Merge branch 'main_dev' into cd_dev
- New celldesigner model
- Added connectors stroke width
- Added CardinalityLayout
- Added support for cardinality and stoichiometry
- Added package data
- Import sbgn stylesheets
- Upadted setup.py
- New terminal layout
- Shadows for subunits
- Added filter for subunits in sbgn shape
- Added none possibility for filters
- Clean up
- Color for subunits of macromolecule multimer layout
- Added list value type
- New fit submaps to content function
- New styles for sumap and tag layout
- Added new directions
- Added submap and tag layouts
- Set position of layout to position of label with anchor label_center
- Added inverted hexagon shape and perturbing agent layout
- Updated to new SBGNShape style
- Updated with beginning of metaclass
- Cleaned up
- Is_ovav method
- Clean up
- Clean up code
- Updated style sheets
- Changed default filter units to object bounding box
- Translation->translate in svg-native renderer
- +import momapy.drawing
- Impl copy and deepcopy for NoneValue singleton
- Update
- Added set_complexes_to_fit_content utils function
- Fill of consumption to none
- Removed shadows for arcs
- Emptyset must have a stroke color
- Set stroke to none
- Bug _render_filters
- Typo
- Typo
- Typo
- Typo
- Added shadows.css stylsheet
- Added drop-shadow in styling css
- Added filter with drop shadow effect
- Typo
- Layout fill to white
- Changed font sizes in shapes with text
- Aux units font
- Font to Cantarell
- Font to cantarell
- Text drawing element: font_color replaced by fill and stroke
- Rgba to rgb and opacity
- Layout fill: none; textlayout: font_color
- Default sbgn style: fill of layout set to none
- Styling none returns NoneValue
- Default fill value to black
- Set_size->set_absolute_size in pango font description
- String to output file
- Set_size->set_absolute_size for pango font description
- Merge branch 'arc_to_elliptical' into native_svg
- Changed arc to elliptical arc in shapes
- More methods for native svg renderer
- First class and methods for nativesvgrenderer
- Int to float
- Multiple style sheets; join style sheets
- Update
- Added default_colorscheme.css
- +width and height
- Added default stylesheet for sbgn
- Added strict option to applying collection of styles
- Removed _ from color names to be consistent with css
- Added none value that does not work
- Added has_color method to colors
- Added none value in style_sheets
- Added set_auilliary_units_to_borders function
- Added self_border and self_angle functions
- Splited fontdescription into fontsize and fontfamily
- +pyparsing
- Added parser for stylesheets
- Clean up
- In node layout: removed foreground_path; renamed background_path to border_drawing_element
- Render_maps(): changed bbox to self_bbox to compute surface width and height
- Changed drawing path of Layout: bbox() -> self_bbox()
- Cleanup
- Added ancestor and parent selectors;type selector->class selector; now ancestors in select method
- Added children mehtod to layouts
- Added tidy and stylesheet options to read_file
- Can now supply a mapbuilder to apply_style_sheet
- Added set_arcs_to_borders function
- Cleaning
- Addition of point to point builder
- Added automatic border functions and related changes
- New function for intersection of line and ellipse
- Removed y_from_x methods (not much sense)
- New geometry shapes: Arc, Circle; new intersection functions
- Recodes parallel lines; added slope and intercept to line; recoded intersection of lines
- Added set_layout_to_fit_content function
- Added set_nodes_to_fit_labels
- Label_center taken into account and bold text in shapes
- Added label_center anchor
- Added vertical alignment for textlayoutelement
- Bugs and replaces text by new text and textlayout
- Changed nodelabel to textlayoutelement
- New text drawing element and textlayoutelement
- Added style_sheets from styling to render_map(s)
- Added position to sbgn maps when reading sbgn-ml file
- Added position to layout
- Removed optional from transform attribute of drawing element (default is tuple)
- Dfault for transform attribute is set to tuple
- Merge branch 'main_dev' into sbgn_dev
- Fit now return position, width, height and not bbox: fixed related bugs in self.bbox() functions
- Bug in set_compartments_to_fit_content
- Merge branch 'main_dev' into sbgn_dev
- Bug in set_fit function
- New set_compartments_to_fit_content function
- Merge branch 'main_dev' into sbgn_dev
- Fit returns position, width and height rather than a bbox; implemented set_fit function
- Added new sbgn shapes
- Added EmptySetLayout to emptyset and source and sink
- New styling feature
- Completed fraction function
- Recoded arcs with anchors
- Cleaned code
- Maj
- Bug restore after stroke and fill; factored _stroke_and_fill
- Added height and width in _make_renderer_for_render_function
- Typo in parameter name
- Added a function to render a collection of drawing elements and factored make_renderer_for_render_function
- Added ellipse to drawing and rendering
- Added arcs to drawing and rendering
- Typo
- Added origin point for rotation
- Experimental update with updated_object
- Revamped relative_point to updated_object
- Removed prints
- New animating module
- Bug fix
- Bug fix in Color.__or__
- Bug fix in Color.__or__
- Added png rendering
- Updated Pipfile
- Cleanup
- Cleanup
- Cleanup
- Cleaned imports
- Added alpha modification to Color
- Mod essai.py
- Cleanup
- Reference->phantomlayoutelement, fixed bugs, fixed positioning with new coord sys
- Added self_bbox to grouplayout and to nodelayout
- Mod bbox to follow new coord system
- Mod essai.py
- Inverted y axis to mimick svg and sbgnml
- Cleaned rendering and drawing code
- Updated gitignore
- Updated grouplayoutelement
- Cleanup
- Renderer to rendering
- Renderer.py to rendering.py
- Cleanup
- Removed position.py.save
- Added folder momapy/
- Removed submodule momapy
- Updated gitignore
- Updated pipfile
- Initial commit

### Styling

- Styles to/from render_information: border>group attrs for nodes, arrowhead>path>group attrs for arcs
- Stylesheet is now unfrozen so it can be easily modified
- Styles in grouplayoutelement applied to the top group element; arcs have styles for arrowhead
- Style_sheets from files and multiple style_sheets
- Stylesheet applied to layout instead of map

