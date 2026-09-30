# momapy — API Reference

Condensed module-by-module inventory of public classes and function signatures for fast orientation in future Claude Code sessions. Pairs with `CLAUDE.md` (which covers architecture, conventions, and I/O patterns); this file covers the *surface*.

**Scope**: every Python source file under `src/momapy/`. Private helpers (`_reading_*`, `_writing_*`) are included because their `make_*` functions are inventoried here for maintainer orientation — they are internal helpers, not part of the public I/O contract. Large glyph/shape families are summarized rather than enumerated exhaustively.

**When this drifts**: regenerate by launching three Explore agents in parallel (one for `core/` + top-level + `meta/` + `rendering/` + `io/` + `plugins/`, one for `sbgn/*`, one for `celldesigner/*` + `sbml/*`), asking each for signatures as-written in this same Markdown format. Include `make_*` private helpers — they are internal helpers of the `_reading_*`/`_writing_*` modules, inventoried here for maintainer orientation. Expect drift on every substantive refactor of `core/`, `io/`, or a format subtree.

---

## Core library (`src/momapy/core/` and top-level)

### `src/momapy/core/__init__.py`
Re-exports: `Direction`, `Orientation`, `HAlignment`, `VAlignment`, `MapElement`, `ModelElement`, `LayoutElement`, `Model`, `Map`, `LayoutModelMapping`, `LayoutModelMappingBuilder`, `TextLayout`, `Shape`, `GroupLayout`, `Node`, `Arc`, `SingleHeadedArc`, `DoubleHeadedArc`, `Layout`. (`find_font` is **not** re-exported here — use `momapy.core.fonts.find_font`.)

### `src/momapy/core/elements.py`
Purpose: base element classes for maps, models, and layouts.

Classes:
- `Direction(enum.Enum)` — four cardinals (`UP`, `RIGHT`, `DOWN`, `LEFT`)
- `Orientation(enum.Enum)` — axes (`HORIZONTAL`, `VERTICAL`)
- `HAlignment(enum.Enum)`, `VAlignment(enum.Enum)`
- `MapElement` — root of everything; `id_: str` (not part of equality/hash).
- `ModelElement(MapElement)` — base for model-level elements; `descendants() -> list[ModelElement]` walks reachable model elements via scalar refs and `frozenset`/`tuple` fields, deduped by identity, excluding `self`.
- `LayoutElement(MapElement, ABC)` — visual elements; `bbox() -> Bbox`, `drawing_elements() -> list[DrawingElement]`, `children() -> list[LayoutElement]`, `childless() -> Self`, `descendants() -> list[LayoutElement]`, `flattened() -> list[LayoutElement]`, `equals(other, flattened=False, unordered=False) -> bool`, `contains(other) -> bool`, `to_geometry() -> list[Segment|Curve|Arc]`, `anchor_point(anchor_name: str) -> Point`.

### `src/momapy/core/model.py`
- `Model(MapElement)` — abstract; `is_submodel(other) -> bool`, `descendants() -> list[ModelElement]` (same walk as `ModelElement.descendants()`, seeded from the `Model`'s fields). **Note**: `Model` extends `MapElement`, NOT `ModelElement`, in all formats. Enforced by `tests/test_io_mappings.py`.

### `src/momapy/core/map.py`
- `Map(MapElement)` — `model`, `layout`, `layout_model_mapping`; `is_submap(other) -> bool`, `get_mapping(map_element)`.

### `src/momapy/core/mapping.py`
- `LayoutModelMapping(FrozenIdentitySurjectionDict)` — immutable; `get_mapping(map_element)`, `get_child_layout_elements(child_model_element, parent_model_element) -> list[LayoutElement]`, `is_submapping(other)`, `representative_to_key -> FrozenSurjectionDict` (read-only property mapping each frozenset representative to its frozenset key).
- `LayoutModelMappingBuilder(IdentitySurjectionDict, Builder)` — mutable; `get_mapping(map_element)`, `get_child_layout_elements(child_model_element, parent_model_element) -> list[LayoutElement]`, `add_mapping(layout_element, model_element, representative=None)`, `build(builder_to_object=None) -> LayoutModelMapping`, `from_object(obj, object_to_builder=None) -> Self`, `representative_to_key -> SurjectionDict` (property).

### `src/momapy/core/layout.py`
- `TextLayout(LayoutElement)` — `text`, `position`, font styling, `fill`/`stroke`, alignment, `transform`.
- `Shape(LayoutElement)` — abstract geometric shape.
- `GroupLayout(LayoutElement)` — `layout_elements: tuple[LayoutElement, ...]`, plus `group_*` styling fields (`group_fill`, `group_stroke`, `group_font_*`, …) and `group_transform`.
- `Node(GroupLayout)` — `position`, `width`, `height`, `fill`, `stroke`, `stroke_width`, `filter_`; anchors `north/south/east/west/center() -> Point`.
- `Arc(GroupLayout)` — `segments: tuple[Segment|Curve|Arc, ...]`, line styling.
- `SingleHeadedArc(Arc)` / `DoubleHeadedArc(Arc)` — add arrowhead classes.
- `Layout(Node)` — root container for a map's layout tree.

### `src/momapy/core/fonts.py`
- `find_font(family: str, weight: FontWeight|int, style: FontStyle) -> str | None`.
- Internal: `_FontEntry`, `_get_font_directories() -> list[str]`, `_read_font_metadata(path: str) -> list[_FontEntry]`.

### `src/momapy/geometry.py`
Classes: `GeometryObject(ABC)`, `Point`, `Line`, `Segment`, `QuadraticBezierCurve`, `CubicBezierCurve`, `EllipticalArc`, `Bbox`, `Transformation(ABC)`, `MatrixTransformation`, `Rotation`, `Translation`, `Scaling`.

Key `Point` methods: `__add__/sub/mul/truediv`, `to_matrix() -> ndarray`, `to_tuple() -> tuple[float, float]`, `get_intersection_with_line(line) -> list[Point]`, `get_angle_to_horizontal() -> float`, `transformed(transformation)`, `reversed()`, `round(ndigits=None)`, `bbox()`, `isnan()`, `from_tuple(t) -> Self`.

Key `Bbox` members: constructed as `Bbox(position: Point, width, height)`; `center()`, `size() -> tuple[float, float]`, `anchor_point(anchor_name)`, `isnan()`, and the compass anchors (`north/south/east/west`, `north_east`, …). Classmethods: `around_points(points: Iterable[Point]) -> Bbox`, `union(bboxes: list[Bbox]) -> Bbox`. (There is no `bbox()`, `contains_point()`, `intersects_bbox()`, or `from_points()`.)

Constants: `ROUNDING: int = 4` (in `__all__`; imported by `drawing`), `COMPASS_ANCHOR_NAMES: tuple[str, ...]` (in `__all__`; the 16 compass anchor names supported by `Bbox`/`Node`, excluding `center`). Internal-only (underscored, not exported): `_ROUNDING_TOLERANCE`, `_ZERO_TOLERANCE`, `_PARAMETER_TOLERANCE`, `_CONVERGENCE_TOLERANCE`.

Functions (all in `__all__`, used cross-module by `drawing`/`celldesigner`): `get_primitives_border(primitives, point, center=None) -> Point | None`, `get_primitives_angle(primitives, angle, unit="degrees", center=None) -> Point | None`, `get_primitives_anchor_point(primitives, anchor_point, center=None) -> Point | None` (where `primitives: list[Segment | QuadraticBezierCurve | CubicBezierCurve | EllipticalArc]`), `get_normalized_angle(angle: float) -> float`, `get_transformation_for_frame(origin, unit_x, unit_y) -> MatrixTransformation`.

### `src/momapy/drawing.py`
Classes: `NoneValueType`, `FilterEffect(ABC)` + (`DropShadowEffect`, `CompositeEffect`, `FloodEffect`, `GaussianBlurEffect`, `OffsetEffect`), `FilterEffectInput(Enum)`, `CompositionOperator(Enum)`, `EdgeMode(Enum)`, `FilterUnits(Enum)`, `Filter`, `GradientUnits(Enum)`, `SpreadMethod(Enum)`, `GradientStop`, `Gradient(ABC)` + (`LinearGradient`, `RadialGradient`), `FontStyle(Enum)`, `FontWeight(Enum)`, `TextAnchor(Enum)`, `FillRule(Enum)`, `LineJoin(Enum)`, `LineCap(Enum)`, `DrawingElement(ABC)`, `Text(DrawingElement)`, `Group(DrawingElement)`, `PathAction(ABC)` + (`MoveTo`, `LineTo`, `EllipticalArc`, `CurveTo`, `QuadraticCurveTo`, `ClosePath`), `Path(DrawingElement)`, `Ellipse(DrawingElement)`, `Rectangle(DrawingElement)`.

`DrawingElement.fill`/`stroke` (and the `*fill`/`*stroke` fields of layout elements) accept a `Color`, a `Gradient`, `NoneValue` or `None`. Gradients follow SVG's `linearGradient`/`radialGradient` (no `href`, coordinates are floats).

`DrawingElement.stroke_linejoin: LineJoin | None` and `stroke_linecap: LineCap | None` follow SVG's `stroke-linejoin`/`stroke-linecap` (inherited; initial `MITER`/`BUTT`). Layout elements carry matching `*stroke_linejoin`/`*stroke_linecap` fields wherever they have a `*stroke_dashoffset` field.

Functions: `get_initial_value(attr_name: str) -> Any`, `drawing_elements_to_geometry(elements) -> list[Segment|Curve|Arc]`, `get_drawing_elements_border(drawing_elements, point, center=None) -> Point | None`, `get_drawing_elements_angle(drawing_elements, angle, unit="degrees", center=None) -> Point | None`, `get_drawing_elements_bbox(drawing_elements) -> Bbox`, `get_drawing_elements_anchor_point(drawing_elements, anchor_point, center=None) -> Point | None`.

Constants (in `__all__`, imported cross-module): `DEFAULT_FONT_FAMILY: str`, `INITIAL_VALUES: dict[str, Any]`, `PRESENTATION_ATTRIBUTES: dict[str, dict[str, Any]]`, and `NoneValue` — the singleton instance of `NoneValueType` used to mark an explicitly-unset presentation attribute (compare with `is`/`is not`, not `==`).

### `src/momapy/builder.py`
- `Builder(ABC)` — `build(builder_to_object=None)`, `from_object(obj, object_to_builder=None) -> Self`.
- `get_or_make_builder_cls(cls, builder_fields=None, builder_bases=None, builder_namespace=None) -> type[Builder]`
- `has_builder_cls(cls) -> bool`, `get_builder_cls(cls) -> type[Builder] | None`
- `object_from_builder(builder, builder_to_object=None) -> Any`
- `builder_from_object(obj, object_to_builder=None) -> Builder`
- `isinstance_or_builder(obj, cls) -> bool`, `issubclass_or_builder(cls, parent) -> bool`, `super_or_builder(type_, obj) -> super`
- `new_builder_object(cls, *args, **kwargs) -> Builder`
- `register_builder_cls(builder_cls)`

### `src/momapy/styling/__init__.py`
Re-exports: `StyleCollection`, `StyleSheet`, `Selector`, `TypeSelector`, `ClassSelector`, `IdSelector`, `ChildSelector`, `DescendantSelector`, `OrSelector`, `CompoundSelector`, `NotSelector`, `combine_style_sheets`, `apply_style_collection`, `apply_style_sheet`, `get_stylable_attributes`.

### `src/momapy/styling/core.py`
Purpose: CSS-like style sheets.

- `StyleCollection(dict)`, `StyleSheet(dict)` — `StyleSheet.from_file(path)`, `.from_string(s)`, `.from_files(paths)`, `__or__` merge.
- `Selector(ABC)` and concrete subclasses: `TypeSelector`, `ClassSelector`, `IdSelector`, `ChildSelector`, `DescendantSelector`, `OrSelector`, `CompoundSelector`, `NotSelector`.
- `combine_style_sheets(style_sheets: Sequence[StyleSheet]) -> StyleSheet | None`
- `apply_style_collection(layout_element, style_collection, strict=True)`
- `apply_style_sheet(map_or_layout_element, style_sheet, strict=True, ancestors=None)`
- `get_stylable_attributes(layout_element_or_class, presentation_only=False) -> list[str]`
- Values: named and hex (`#rrggbb`, `#rrggbbaa`) colors; `miter`/`round`/`bevel`/`butt`/`square` keywords for `*stroke-linejoin`/`*stroke-linecap` (resolved to `LineJoin`/`LineCap` from the property name); `drop-shadow(...)`; `linear-gradient(...)`, `repeating-linear-gradient(...)`, `radial-gradient(...)` (resolved to `LinearGradient`/`RadialGradient` at parse time).

### `src/momapy/coloring.py`
- `Color` — `red`, `green`, `blue`, `alpha=1.0`; `__or__(alpha)`, `to_rgba/to_rgb/to_hex/to_hexa`, `with_alpha`, `from_rgba/from_rgb/from_hex/from_hexa`. Plus 144 named module-level constants.
- `list_colors() -> list[str]`, `get_color(color_name: str) -> Color`, `print_colors() -> None`, `has_color(color_name: str) -> bool`.

### `src/momapy/positioning.py`
- `right_of/left_of/above_of/below_of(obj, distance: float) -> Point`
- `above_left_of/above_right_of/below_left_of/below_right_of(obj, distance_y: float, distance_x: float | None = None) -> Point`
- `fit(elements, xsep=0, ysep=0) -> Bbox`
- `mid_of(obj1, obj2) -> Point`
- `cross_vh_of/cross_hv_of(obj1, obj2) -> Point`
- `fraction_of(arc_layout_element, fraction: float) -> tuple[Point, float]`
- `set_position(obj, position: Point, anchor: str | None = None)`
- `set_right_of/set_left_of/set_above_of/set_below_of(obj1, obj2, distance, anchor=None)`
- `set_above_left_of/set_above_right_of/set_below_left_of/set_below_right_of(obj1, obj2, distance_y, distance_x=None, anchor=None)`
- `set_fit(obj, elements, xsep=0, ysep=0, anchor=None)`
- `set_fraction_of(obj, arc_layout_element, fraction, anchor=None)`
- `set_mid_of(obj1, obj2, obj3, anchor=None)`
- `set_cross_hv_of/set_cross_vh_of(obj1, obj2, obj3, anchor=None)`

### `src/momapy/utils.py`
- Mapping family — six dict-like classes, each a forward mapping plus a value→keys `.inverse` index returning `frozendict[K, frozenset[key]]` (`K` = the value for equality variants, `id(value)` for identity variants; buckets always `frozenset`). Frozen classes precompute `.inverse` (O(1)); mutable classes return a fresh snapshot on each access.
- `_freeze_inverse(inverse) -> frozendict` — module-private: snapshots a `{key: set}` index as `frozendict[key, frozenset]`; single source of truth for the family's `.inverse` shape.
- `SurjectionDict(dict)` — mutable, equality-keyed surjection; `.inverse` snapshot.
- `IdentitySurjectionDict(dict)` — mutable surjection, inverse keyed by `id()`; `.inverse` snapshot.
- `FrozenSurjectionDict(frozendict.frozendict)` — immutable equality-keyed surjection; `.inverse` precomputed O(1).
- `FrozenIdentitySurjectionDict(frozendict.frozendict)` — immutable surjection, inverse keyed by `id()`; `.inverse` precomputed O(1).
- `IdentityMultiDict(mapping=None)` — mutable, identity-keyed n-to-m multidict; a read-only `Mapping[str, frozenset]` (`[]`/`.get`/`.keys`/`.items`/`.values`) plus `add(key, value)`/`remove(key, value)`/`replace_value(old, new)` mutators and `.inverse` (snapshot). Not a `dict` subclass: `d[k]=v` raises. `mapping` seeds it from a `str -> Iterable` mapping.
- `FrozenIdentityMultiDict(frozendict.frozendict, mapping=None)` — immutable identity multidict; already a `Mapping[str, frozenset]` via `frozendict`, plus `.inverse` (precomputed O(1)). `mapping` is a `str -> Iterable` mapping.
- `pretty_print(obj, max_depth=0, exclude_cls=None)` — `max_depth=None` prints the whole structure (unlimited).
- `get_element_from_collection(element: _T, collection: Iterable[_T]) -> _T | None`, `get_or_return_element_from_collection(element: _T, collection: Iterable[_T]) -> _T`, `add_or_replace_element_in_set(element: _T, set_: set[_T], func: Callable[[_T, _T], bool] | None = None, cache: dict[_T, _T] | None = None) -> _T` — match by equality (`==`), not identity
- `make_uuid4_as_str() -> str`
- `check_file_exists(file_path: str | os.PathLike) -> None` — input-side existence check; raises `FileNotFoundError`. Used by `read()` and every reader.
- `check_parent_dir_exists(file_path: str | os.PathLike) -> None`
- `display(obj, markers=None, xsep=20.0, ysep=20.0, scale=1.0, style_sheet=None)`, `print_source(obj) -> None` — optional-notebook-dependency helpers.

### `src/momapy/cli.py`
- `main()` is the single public entry: parses args and dispatches subcommands (`render`, `export`, `list`, `info`, `visualize`, `tidy`, `style`) to the internal `_run(args)`.
- Built-in presets registry `_BUILTIN_PRESETS` (cs_default, sbgned, newt, ...).

---

## I/O (`src/momapy/io/`)

### `src/momapy/io/__init__.py`
- `get_reader(name) -> type[Reader]`, `get_writer(name) -> type[Writer]`, `list_readers() -> list[str]`, `list_writers() -> list[str]`.
- `read(file_path, reader=None, **options)`, `write(obj, file_path, writer=None, **options)` (writer auto-detected from the map type when `None`: SBGN→`sbgnml`, CellDesigner→`celldesigner`, SBML→clear read-only error).
- `register_reader(name, cls)`, `register_lazy_reader(name, import_path)`, `register_writer(name, cls)`, `register_lazy_writer(name, import_path)`.
- Re-exports the base classes `Reader`, `Writer`, and the result classes `IOResult`, `ReaderResult`, `WriterResult`.
- Module state: `reader_registry: PluginRegistry[type[Reader]]`, `writer_registry: PluginRegistry[type[Writer]]`.

### `src/momapy/io/core.py`
Purpose: reader/writer base classes + dispatch.

- `IOResult` — base class for I/O results (`kw_only=True`; mutable).
- `ReaderResult(IOResult)` — `kw_only=True`; 9 fields: `obj`, `element_to_annotations`, `element_to_notes`, `id_to_element`, `source_id_to_model_element` (`FrozenIdentityMultiDict | None`), `source_id_to_layout_element` (`FrozenSurjectionDict | None`), `source_id_to_annotations`, `source_id_to_notes`, `file_path`.
- `WriterResult(IOResult)` — `kw_only=True`; `obj`, `file_path`.
- `Reader(ABC)` — `read(file_path, **options) -> ReaderResult`, `check_file(file_path) -> bool`.
- `Writer(ABC)` — `write(obj, file_path, **options) -> WriterResult`.

### `src/momapy/io/_utils.py`
Purpose: reader-side helpers; shared base contexts. Wholly internal (`__all__ = []`).

- `ReadingContext` — base context with `xml_root`, `map_key`, `model`, `layout`, `xml_id_to_model_element` (`IdentityMultiDict`), `xml_id_to_layout_element`, `xml_id_to_xml_element`, `element_to_annotations`, `element_to_notes`, `source_id_to_annotations`, `source_id_to_notes`, `layout_model_mapping`, `with_annotations`, `with_notes`, `model_element_cache`, `model_element_remap`, `evicted_elements`.
- `WritingContext` — base context with `map_`, `element_to_annotations`, `element_to_notes`, `source_id_to_model_element`, `source_id_to_layout_element`, `source_id_to_annotations`, `source_id_to_notes`, `with_annotations`, `with_notes`, `element_to_xml_id`, `used_xml_ids`, `candidate_to_xml_id`.
- `make_unique_xml_id(candidate, used_xml_ids) -> str`
- `build_id_to_element(obj) -> frozendict` — context-free `id_to_element` walk over a `Map`/`Model`/`Layout` (every element `id_` -> element). Used by `build_id_mappings` and by the pickle reader (which has no reading context).
- `build_id_mappings(reading_context, obj, real_model_source_ids=None, real_layout_source_ids=None) -> (frozendict, FrozenIdentityMultiDict|None, FrozenSurjectionDict|None)` — builds the `ReaderResult` id dicts. Dispatches `obj` internally: `Map` → uses its `.model`/`.layout`; `Model`/`Layout` → treated as the model/layout itself. `id_to_element` comes from `build_id_to_element`.
- `register_model_element(reading_context, model_element, collection, id_)` (the `id_` is required) and related remap helpers (`remap_model_element`, `resolve_remap`, `apply_remap_to_layout_model_mapping`).

### `src/momapy/io/pickle.py`
Purpose: format-agnostic pickle reader/writer. Registered as `"pickle"` in `momapy.io`.

- `PickleReader(Reader)` — `check_file` (inspects only the pickle protocol header byte, never unpickles), `read(file_path, return_type="map", with_model=True, with_layout=True, with_annotations=True, with_notes=True, **options)`.
- `PickleWriter(Writer)` — `write(obj, file_path, element_to_annotations=None, element_to_notes=None, source_id_to_model_element=None, source_id_to_layout_element=None, source_id_to_annotations=None, source_id_to_notes=None, with_annotations=True, with_notes=True, **options)`.

---

## Plugins (`src/momapy/plugins/`)

### `src/momapy/plugins/__init__.py`
- Re-exports `PluginRegistry`; `__all__ = ["PluginRegistry"]`.

### `src/momapy/plugins/core.py`
- `PluginRegistry(Generic[T])` — `register(name, plugin)`, `register_lazy(name, import_path)`, `get(name) -> T|None`, `is_available(name) -> bool`, `list_available() -> list[str]` (sorted, for display), `list_available_in_registration_order() -> list[str]` (registration order; used by `read()` auto-detection so a more specific reader registered first wins), `list_loaded() -> list[str]`.

---

## Meta shapes (`src/momapy/meta/`)

`src/momapy/meta/__init__.py` intentionally re-exports nothing (no `__all__`): the submodules share many overlapping names, so classes are accessed via their submodule, e.g. `momapy.meta.shapes.Rectangle`.

### `src/momapy/meta/nodes.py`
Generic node classes (all extend `Node`): `Rectangle`, `Ellipse`, `Stadium`, `Hexagon`, `TurnedHexagon`, `Parallelogram`, `CrossPoint`, `Triangle`, `Diamond`, `Bar`, `ArcBarb`, `StraightBarb`, `To`. Configurable corner radii on rectangles; `direction`/`angle` fields on directional shapes.

### `src/momapy/meta/arcs.py`
Generic arc classes. Single-headed (extend `SingleHeadedArc`): `PolyLine` (no head), `Triangle`, `ReversedTriangle`, `Rectangle`, `Ellipse`, `Diamond`, `Bar`, `ArcBarb`, `StraightBarb`, `To`. Double-headed (extend `DoubleHeadedArc`): `DoubleTriangle`.

### `src/momapy/meta/shapes.py`
Shape classes (extend `Shape`, override `drawing_elements()`): `Rectangle`, `Ellipse`, `Stadium`, `Hexagon`, `TurnedHexagon`, `Parallelogram`, `CrossPoint`, `Triangle`, `Diamond`, `Bar`, `ArcBarb`, `StraightBarb`, `To`.

---

## Rendering (`src/momapy/rendering/`)

### `src/momapy/rendering/__init__.py`
- `get_renderer(name) -> type[Renderer]`, `list_renderers() -> list[str]`, `register_renderer(name, renderer_cls)`, `register_lazy_renderer(name, import_path)`. Registry: `renderer_registry: PluginRegistry[type[Renderer]]`.
- `render_layout_element(layout_element, file_path, format_=None, renderer=None, style_sheet=None, to_top_left=False)`
- `render_layout_elements(layout_elements, file_path, format_=None, renderer=None, style_sheet=None, to_top_left=False, multi_pages=False)`
- `render_map(map_, file_path, format_=None, renderer=None, style_sheet=None, to_top_left=False)`
- `render_maps(maps, file_path, format_=None, renderer=None, style_sheet=None, to_top_left=False, multi_pages=False)`
- Re-exports the base classes `Renderer`, `StatefulRenderer`, `SupportsFileOutput`.

### `src/momapy/rendering/core.py`
- `Renderer(ABC)` — abstract backend surface: `begin_session()`, `end_session()`, `new_page(width, height)`, `render_layout_element(layout_element)`, `render_drawing_element(drawing_element)`. `render_map(map_)` is a **concrete convenience method** (default renders `map_.layout` via `render_layout_element`), not part of the abstract contract; the file pipeline does not call it. Also two concrete, overridable classmethods resolving the CSS `bolder`/`lighter` keywords against `font_weight_value_mapping`: `get_bolder_font_weight(font_weight) -> float`, `get_lighter_font_weight(font_weight) -> float`. File output is **not** on this contract; non-file renderers subclass `Renderer` directly.
- `SupportsFileOutput(ABC)` — mixin declaring the file-output *capability* (not an identity — a renderer mixing it in may also target live canvases/in-memory surfaces): `supported_formats: ClassVar[list[str]]`, `default_format: ClassVar[str | None]` (format used when `from_file` gets `format_=None`; subclasses set it) + abstract classmethod `from_file(file_path, width, height, format_=None) -> Self`. Mix into a `Renderer` subclass. The file-output entry points require it; `render_layout_elements` raises `ValueError` for a renderer that does not mix it in.
- `make_gradient_matrix(gradient, bbox) -> numpy.ndarray` — 3x3 matrix from gradient space to user space (box matrix for `OBJECT_BOUNDING_BOX`, then `gradient_transform`); used by the Skia and Cairo renderers.
- `StatefulRenderer(Renderer)` — adds state-management helpers: `save()`/`restore()`, `self_save()`/`self_restore()`, `get_current_state()`, `get_current_value(attr_name)`, `get_initial_value(attr_name)`, `set_current_value(attr_name, attr_value)`, `set_current_state(state)`, `set_current_state_from_drawing_element(drawing_element)`.

### `src/momapy/rendering/cairo.py`
- `CairoRenderer(StatefulRenderer, SupportsFileOutput)` — formats: pdf, svg, png, ps (`default_format = "pdf"`). Requires pycairo/PyGObject. `from_file(file_path, width, height, format_=None) -> Self`.

### `src/momapy/rendering/skia.py`
- `SkiaRenderer(StatefulRenderer, SupportsFileOutput)` — formats: pdf, svg, png, jpeg, webp (`default_format = "pdf"`). Requires skia-python. `from_file(file_path, width, height, format_=None) -> Self`.

### `src/momapy/rendering/svg_native.py`
- `SVGElement` — manual SVG DOM; `to_string(indent=0)`, `add_element(element)`.
- `SVGNativeRenderer(Renderer, SupportsFileOutput)` — `supported_formats = ["svg"]` (`default_format = "svg"`); `begin_session()`, `end_session()`, `new_page(width, height)`, `render_layout_element(layout_element)`, `render_drawing_element(drawing_element)` (inherits `render_map` from `Renderer`), classmethod `from_file(file_path, width, height, format_=None) -> Self`.
- `SVGNativeCompatRenderer(SVGNativeRenderer)` — compatibility variant registered as `"svg-native-compat"`.

---

## SBGN (`src/momapy/sbgn/`)

### `src/momapy/sbgn/__init__.py`
Re-exports: `DEFAULT_AUXILIARY_UNIT_FONT_SIZE`, `DEFAULT_FONT_SIZE`, `SBGNAuxiliaryUnit`, `SBGNDoubleHeadedArc`, `SBGNLayout`, `SBGNMap`, `SBGNModel`, `SBGNModelElement`, `SBGNNode`, `SBGNRole`, `SBGNSingleHeadedArc`.

### `src/momapy/sbgn/elements.py`
Purpose: shared SBGN bases and mixins for PD and AF.

- `SBGNModelElement(ModelElement)` — base for SBGN model elements.
- `SBGNAuxiliaryUnit(SBGNModelElement)` — base for state variables, units of information, terminals, tags.
- `SBGNRole(SBGNModelElement)` — `referred_element: SBGNModelElement`.
- `SBGNNode(Node)` — base for SBGN glyphs; `fill`, `stroke`, `stroke_width`.
- `SBGNSingleHeadedArc(SingleHeadedArc)` — arc with one arrowhead; `arrowhead_*`, `path_*` styling fields.
- `SBGNDoubleHeadedArc(DoubleHeadedArc)` — arc with two arrowheads; `start_arrowhead_*`, `end_arrowhead_*`, `path_*`.
- `_ConnectorsMixin` — private mixin for process nodes; `orientation: Orientation`, `left_to_right`, `left_connector_length`, `right_connector_length`, per-connector styling.

### `src/momapy/sbgn/model.py`
- `SBGNModel(Model)` — abstract base shared by PD and AF.

### `src/momapy/sbgn/layout.py`
- `SBGNLayout(Layout)` — abstract base; `fill: NoneValueType | Color | Gradient | None = white`.
- Constants (reader defaults, re-exported from `momapy.sbgn`, `momapy.sbgn.pd`, `momapy.sbgn.af`): `DEFAULT_FONT_SIZE = 11.0` (glyph / entity-pool labels), `DEFAULT_AUXILIARY_UNIT_FONT_SIZE = 8.0` (state variable & unit-of-information labels).

### `src/momapy/sbgn/map.py`
- `SBGNMap(Map)` — abstract base; `model: SBGNModel | None = None`, `layout: SBGNLayout | None = None`.

### `src/momapy/sbgn/utils.py`
Functions (all accept `SBGNMap | Builder`, return same):
- `set_compartments_to_fit_content(map_, xsep=0, ysep=0, *, snap_arcs=False)`
- `set_complexes_to_fit_content(map_, xsep=0, ysep=0, *, snap_arcs=False)`
- `set_submaps_to_fit_content(map_, xsep=0, ysep=0, *, snap_arcs=False)`
- `set_nodes_to_fit_labels(map_, xsep=0, ysep=0, omit_width=False, omit_height=False, restrict_to=None, exclude=None, *, snap_arcs=False)`
- `set_arcs_to_borders(map_)`
- `set_auxiliary_units_to_borders(map_, *, snap_arcs=False)`
- `set_auxiliary_units_label_font_size(map_, font_size)`
- `set_layout_to_fit_content(map_, xsep=0, ysep=0)`
- `tidy(map_, auxiliary_units_omit_width=False, auxiliary_units_omit_height=True, nodes_xsep=4, nodes_ysep=4, auxiliary_units_xsep=1, auxiliary_units_ysep=1, complexes_xsep=10, complexes_ysep=10, compartments_xsep=25, compartments_ysep=25, layout_xsep=0, layout_ysep=0)`
- `sbgned_tidy(map_)`, `newt_tidy(map_)` — preset parameters.
- `get_info(map_: SBGNMap) -> dict[str, typing.Any]` (keys `map_type: str`, `model: dict[str, int]`, `layout: dict` with `width`/`height`/`elements`)

### `src/momapy/sbgn/styling/__init__.py`
Module-level `StyleSheet` constants: `cs_default`, `cs_black_and_white`, `sbgned`, `newt`, `fs_shadows`.

### `src/momapy/sbgn/pd/__init__.py`
Re-exports: default font-size constants (`DEFAULT_FONT_SIZE`, `DEFAULT_AUXILIARY_UNIT_FONT_SIZE`), auxiliary units (`StateVariable`, `UnitOfInformation`, `Subunit` family), `Compartment`, entity pools (`EntityPool`, `PerturbingAgent`, `UnspecifiedEntity`, `Macromolecule`, `NucleicAcidFeature`, `SimpleChemical`, `Complex`, `Multimer` family), flux roles (`FluxRole`, `Reactant`, `Product`), logical operators (`LogicalOperator`, `OrOperator`, `AndOperator`, `NotOperator`, `LogicalOperatorInput`), equivalence operators (`EquivalenceOperator`, `EquivalenceOperatorInput`, `EquivalenceOperatorOutput`), processes (`Process`, `StoichiometricProcess`, `GenericProcess`, `UncertainProcess`, `Association`, `Dissociation`, `OmittedProcess`, `Phenotype`), modulations (`Modulation`, `Inhibition`, `Stimulation`, `Catalysis`, `NecessaryStimulation`), tags/terminals/submaps (`Tag`, `TagReference`, `Terminal`, `TerminalReference`, `Submap`), `SBGNPDModel`, all `*Layout` variants, `SBGNPDMap`.

### `src/momapy/sbgn/pd/model.py`
Purpose: SBGN-PD model classes.

- **Auxiliary units**: `StateVariable(SBGNAuxiliaryUnit)` — `variable`, `value`, `order`; `UnitOfInformation` — `value`, `prefix`; `Subunit` family with per-type subclasses (`UnspecifiedEntitySubunit`, `MacromoleculeSubunit`, `NucleicAcidFeatureSubunit`, `SimpleChemicalSubunit`, `ComplexSubunit`, `MultimerSubunit` (+ `cardinality`) and the four multimer variants).
- **Compartment**: `Compartment(SBGNModelElement)` — `label`, `units_of_information`.
- **Entity pools**: `EntityPool(SBGNModelElement)` (`compartment`); subclasses `PerturbingAgent`, `UnspecifiedEntity`, `Macromolecule`, `NucleicAcidFeature`, `SimpleChemical`, `Complex` (+ `subunits`), `Multimer(Complex)` (+ `cardinality`) and the four multimer variants. (The empty set has a layout only, `EmptySetLayout`; there is no `EmptySet` model class.)
- **Flux roles**: `FluxRole(SBGNRole)` — `referred_element: EntityPool`, `stoichiometry`; `Reactant`, `Product`.
- **Processes**: `Process(SBGNModelElement)` (no fields); `StoichiometricProcess(Process)` (`reactants`, `products`, `reversible`, `has_external_source`, `has_external_sink`) → `GenericProcess`, `UncertainProcess`; `GenericProcess` → `Association`, `Dissociation`, `OmittedProcess`; `Phenotype(Process)` (no `reactants`/`products`).
- **Logical operators**: `LogicalOperator(SBGNModelElement)` (`inputs: frozenset[LogicalOperatorInput]`) → `OrOperator`, `AndOperator`, `NotOperator`. `LogicalOperatorInput(SBGNRole)` — `referred_element: EntityPool | LogicalOperator`.
- **Equivalence operators**: `EquivalenceOperator` (`inputs`, `output`), `EquivalenceOperatorInput`, `EquivalenceOperatorOutput`.
- **Modulations**: `Modulation(SBGNModelElement)` (`source`, `target`) → `Inhibition`, `Stimulation`. `Stimulation` → `Catalysis`, `NecessaryStimulation`.
- **Tags/terminals/submaps**: `Tag(SBGNModelElement)` (`label`, `referred_element`), `TagReference(SBGNRole)`, `Terminal(SBGNAuxiliaryUnit)` (`label`, `referred_element`), `TerminalReference(SBGNRole)`, `Submap(SBGNModelElement)` (`label`, `terminals`).
- **Model**: `SBGNPDModel(SBGNModel)` — `compartments`, `entity_pools`, `processes`, `modulations`, `logical_operators`, `equivalence_operators`, `submaps`, `tags`.

### `src/momapy/sbgn/pd/layout.py`
- `SBGNPDLayout(SBGNLayout)`; per-element `*Layout` classes mirroring the model families: auxiliary unit layouts (`StateVariableLayout`, `UnitOfInformationLayout`, `TerminalLayout`, `CardinalityLayout`, subunit layouts), compartment/submap layouts, entity pool node layouts, process layouts (with `_ConnectorsMixin`), operator layouts, arc layouts (`Consumption`, `Production`, `Modulation`, `Stimulation`, `NecessaryStimulation`, `Catalysis`, `Inhibition`, `LogicArc`, `EquivalenceArc`), tag layouts.

### `src/momapy/sbgn/pd/map.py`
- `SBGNPDMap(SBGNMap)` — combines `SBGNPDModel` and `SBGNPDLayout`.

### `src/momapy/sbgn/af/__init__.py`
Re-exports: default font-size constants (`DEFAULT_FONT_SIZE`, `DEFAULT_AUXILIARY_UNIT_FONT_SIZE`), AF unit-of-information family (`UnitOfInformation`, `MacromoleculeUnitOfInformation`, `NucleicAcidFeatureUnitOfInformation`, `ComplexUnitOfInformation`, `SimpleChemicalUnitOfInformation`, `UnspecifiedEntityUnitOfInformation`, `PerturbationUnitOfInformation`), `Compartment`, activities (`Activity`, `BiologicalActivity`, `Phenotype`), logical operators (`LogicalOperator`, `OrOperator`, `AndOperator`, `NotOperator`, `DelayOperator`, `LogicalOperatorInput`), influences (`Influence`, `UnknownInfluence`, `PositiveInfluence`, `NegativeInfluence`, `NecessaryStimulation`), tags/terminals/submaps, `SBGNAFModel`, layout classes, `SBGNAFMap`.

### `src/momapy/sbgn/af/model.py`
Purpose: SBGN-AF model classes.

- **Units of information**: `UnitOfInformation(SBGNAuxiliaryUnit)` (`label`) plus AF-specific subclasses: `MacromoleculeUnitOfInformation`, `NucleicAcidFeatureUnitOfInformation`, `ComplexUnitOfInformation`, `SimpleChemicalUnitOfInformation`, `UnspecifiedEntityUnitOfInformation`, `PerturbationUnitOfInformation`.
- **Compartment**: `Compartment(SBGNModelElement)` — `label`, `units_of_information`.
- **Activities**: `Activity(SBGNModelElement)` — `label`, `compartment`; `BiologicalActivity` (+ `units_of_information`), `Phenotype`.
- **Logical operators**: `LogicalOperator` (`inputs`) → `OrOperator`, `AndOperator`, `NotOperator`, `DelayOperator`. `LogicalOperatorInput(SBGNRole)` — `referred_element: BiologicalActivity | LogicalOperator`.
- **Influences**: `Influence(SBGNModelElement)` (`source`, `target: Activity`) → `UnknownInfluence`, `PositiveInfluence`, `NegativeInfluence`, `NecessaryStimulation`.
- **Tags/terminals/submaps**: AF `Tag(SBGNModelElement)` and `Terminal(SBGNAuxiliaryUnit)` both use field `referred_element` (AF `Terminal` extends `SBGNAuxiliaryUnit`, matching PD `Terminal`); plus `Submap` and the reference roles.
- **Model**: `SBGNAFModel(SBGNModel)` — `compartments`, `activities`, `influences`, `logical_operators`, `submaps`, `tags`.

### `src/momapy/sbgn/af/layout.py`
- `SBGNAFLayout(SBGNLayout)`; activity layouts, operator layouts (with `_ConnectorsMixin`) incl. `DelayOperatorLayout`, unit-of-information layouts, influence arc layouts (unknown/positive/negative/necessary stimulation), logic and equivalence arc layouts.

### `src/momapy/sbgn/af/map.py`
- `SBGNAFMap(SBGNMap)` — combines `SBGNAFModel` and `SBGNAFLayout`.

### `src/momapy/sbgn/io/sbgnml/_reading_context.py`
- `SBGNMLReadingContext(ReadingContext)` — adds `sbgnml_compartments`, `sbgnml_entity_pools`, `sbgnml_logical_operators`, `sbgnml_stoichiometric_processes`, `sbgnml_phenotypes`, `sbgnml_submaps`, `sbgnml_activities`, `sbgnml_modulations`, `sbgnml_tags`, `sbgnml_glyph_id_to_sbgnml_arcs`.

### `src/momapy/sbgn/io/sbgnml/reader.py`
- `_SBGNMLReader(Reader)` — internal base; `read(file_path, return_type="map", with_model=True, with_layout=True, with_annotations=True, with_notes=True, xsep=0, ysep=0, **options)`.
- Registered as `sbgnml-0.2` (`SBGNML0_2Reader`) and `sbgnml-0.3` / `sbgnml` (`SBGNML0_3Reader`).

### `src/momapy/sbgn/io/sbgnml/writer.py`
- `SBGNML0_3Writer(Writer)` — the single SBGN-ML writer, registered as both `sbgnml-0.3` and `sbgnml`.

### `src/momapy/sbgn/io/sbgnml/_reading_model.py` (`make_*` internal helpers)
- `make_annotations_from_element(sbgnml_element)`, `make_notes_from_element(sbgnml_element)`, `make_and_add_annotations_and_notes(reading_context, sbgnml_element, model_element)`
- `set_label(model_element, sbgnml_element)`, `set_compartment(model_element, sbgnml_element, sbgnml_id_to_model_element)`, `set_stoichiometry(model_element, sbgnml_stoichiometry)`
- `make_compartment(reading_context, sbgnml_compartment)`
- `make_entity_pool_or_subunit(reading_context, sbgnml_entity_pool_or_subunit, model_element_cls)`
- `make_activity(reading_context, sbgnml_activity, model_element_cls)`
- `make_state_variable(reading_context, sbgnml_state_variable, order=None)`
- `make_unit_of_information(reading_context, sbgnml_unit_of_information, model_element_cls)`
- (+ ~15 more for processes, flux roles, logical operators, modulations, tags, terminals, submaps, AF influences)

### `src/momapy/sbgn/io/sbgnml/_reading_layout.py` (`make_*`)
- `make_text_layout(text, position, font_size=11.0) -> TextLayout`
- `make_points(sbgnml_points) -> list[Point]`, `make_segments(points) -> list[Segment]`, `make_arc_segments(sbgnml_arc, reverse=False) -> list[Segment]`
- `make_stoichiometry_layout(sbgnml_stoichiometry, layout_element)`
- `set_connector_lengths(layout_element, sbgnml_element)`, `set_position_and_size(layout_element, sbgnml_glyph)`, `get_label_position(sbgnml_label, default_position) -> Point`
- `make_compartment(reading_context, sbgnml_compartment)`
- `make_entity_pool_or_subunit(reading_context, sbgnml_entity_pool_or_subunit, layout_element_cls)`
- (+ ~20 more for processes, arcs, logical operators, auxiliary units, activities, influences)

### `src/momapy/sbgn/io/sbgnml/_reading_parsing.py`
- `transform_class(sbgnml_class: str) -> str`
- `has_undefined_variable(sbgnml_state_variable) -> bool`
- `get_glyphs(sbgnml_element)`, `get_glyphs_recursively(sbgnml_element)`
- `get_arcs(sbgnml_element)`, `get_ports(sbgnml_element)`
- `get_nexts(sbgnml_arc)`, `get_sbgnml_points(sbgnml_arc)`
- `get_annotation(sbgnml_element)`, `get_notes(sbgnml_element)`, `get_rdf(sbgnml_element)`
- Sets: `_SBGNML_STATE_VARIABLE_CLASSES`, `_SBGNML_UNIT_OF_INFORMATION_CLASSES`, `_SBGNML_TERMINAL_CLASSES`, `_SBGNML_SUBUNIT_CLASSES`.

### `src/momapy/sbgn/io/sbgnml/_reading_classification.py`
- `KEY_TO_MODULE: dict` — `"PROCESS_DESCRIPTION"` → `momapy.sbgn.pd`, `"ACTIVITY_FLOW"` → `momapy.sbgn.af`.
- `KEY_TO_CLASS: dict[tuple|str, tuple[type | None, type]]` — ~70 entries like `("PROCESS_DESCRIPTION", "GLYPH", "MACROMOLECULE") -> (Macromolecule, MacromoleculeLayout)`; the model slot is `None` for `SOURCE_AND_SINK`/`EMPTY_SET` (e.g. `-> (None, EmptySetLayout)`).
- `get_glyph_key(sbgnml_glyph, map_key)`, `get_subglyph_key(sbgnml_subglyph, map_key)`, `get_arc_key(sbgnml_arc, map_key)`, `get_module(map_key)`, `get_module_from_object(obj)`.

### `src/momapy/sbgn/io/sbgnml/_writing.py` (serialization helpers, public-named)
- `make_sbgnml_map(writing_context)`; the XML-id helpers `reserve_source_xml_ids`, `get_xml_id`; the builders `get_layout_elements`, `get_frozenset_keys`, `get_child_layout_element`, `make_sbgnml_glyph`, `make_sbgnml_stoichiometry_glyph`, `make_sbgnml_arc_element`, `make_sbgnml_child_glyphs`, `collect_model_elements`.
- `NSMAP: dict` — SBGN/RDF/BioModels XML namespaces.
- `make_lxml_element(tag, namespace=None, attributes=None, text=None, nsmap=None)`
- `ensure_ncname(id_str) -> str` — coerces an id to XML NCName (`xs:ID`) syntax. (Replaces the removed `get_sbgnml_id`; XML-id assignment now lives in the `_writing.py` helpers `reserve_source_xml_ids`/`get_xml_id`.)
- `make_sbgnml_bbox_from_node(node)`, `make_sbgnml_bbox_from_text_layout(text_layout)`
- `make_sbgnml_label(text_layout)`, `make_sbgnml_state(text_layout)`, `make_sbgnml_entity(...)`
- `make_sbgnml_port(point, port_id)`, `make_sbgnml_points(points)`
- `make_sbgnml_annotation(annotations, sbgnml_id)`, `add_annotations_and_notes(writing_context, sbgnml_element, model_element)`

### `src/momapy/sbgn/io/sbgnml/_writing_classification.py`
- `CLASS_TO_SBGNML_CLASS: dict` — 72 entries mapping momapy layout classes to SBGN-ML class-attribute strings.
- `CLASS_TO_SBGNML_ENTITY_NAME: dict` — momapy model classes → SBGN-ML entity-name strings (for AF units of information).
- `DIRECTION_TO_SBGNML_ORIENTATION: dict` — `Orientation`/`Direction` enum → orientation string.
- `REVERSED_ARC_TYPES: tuple` — `ConsumptionLayout`, `LogicArcLayout` (PD + AF), `EquivalenceArcLayout` (reversed during serialization).

---

## CellDesigner (`src/momapy/celldesigner/`)

### `src/momapy/celldesigner/__init__.py`
Re-exports: default constants (`DEFAULT_FONT_SIZE`, `DEFAULT_MODIFICATION_FONT_SIZE`, `DEFAULT_ACTIVE_XSEP`, `DEFAULT_ACTIVE_YSEP`); bases (`CellDesignerModelElement`, `CellDesignerNode`, `CellDesignerSingleHeadedArc`, `CellDesignerDoubleHeadedArc`, `CellDesignerLayout`, `CellDesignerMap`); modifications (`ModificationResidue`, `ModificationState`, `Modification`, `StructuralState`); regions (`Region`, `ModificationSite`, `CodingRegion`, `RegulatoryRegion`, `TranscriptionStartingSiteL`, `TranscriptionStartingSiteR`, `ProteinBindingDomain`); templates (`SpeciesTemplate`, `ProteinTemplate`, `GenericProteinTemplate`, `TruncatedProteinTemplate`, `ReceptorTemplate`, `IonChannelTemplate`, `GeneTemplate`, `RNATemplate`, `AntisenseRNATemplate`); compartment + species (`Compartment`, `Species`, `Protein`, `GenericProtein`, `TruncatedProtein`, `Receptor`, `IonChannel`, `Gene`, `RNA`, `AntisenseRNA`, `Phenotype`, `Ion`, `SimpleMolecule`, `Drug`, `Unknown`, `Complex`); reaction participants (`Reactant`, `Product`); boolean logic (`BooleanLogicGateInput`, `BooleanLogicGate`, `AndGate`, `OrGate`, `NotGate`, `UnknownGate`); modulators (`KnownOrUnknownModulator`, `Modulator`, `UnknownModulator`, `Inhibitor`, `PhysicalStimulator`, `Catalyzer`, `Trigger`, `UnknownCatalyzer`, `UnknownInhibitor`); reactions (`Reaction`, `StateTransition`, `KnownTransitionOmitted`, `UnknownTransition`, `Transcription`, `Translation`, `Transport`, `HeterodimerAssociation`, `Dissociation`, `Truncation`); modulations (`KnownOrUnknownModulation`, `Modulation`, `Catalysis`, `Inhibition`, `PhysicalStimulation`, `Triggering`, `PositiveInfluence`, `NegativeInfluence`, `UnknownModulation`, `UnknownCatalysis`, `UnknownInhibition`, `UnknownPositiveInfluence`, `UnknownNegativeInfluence`, `UnknownPhysicalStimulation`, `UnknownTriggering`); `CellDesignerModel`; plus 50+ layout classes.

### `src/momapy/celldesigner/elements.py`
Purpose: base classes for CellDesigner layout and model.

- `CellDesignerModelElement(ModelElement)` — abstract base.
- `CellDesignerNode(SBGNNode)` — base for all CellDesigner nodes.
- `CellDesignerSingleHeadedArc(SingleHeadedArc)` — `arrowhead_*`, `path_*` styling; `own_drawing_elements()`.
- `CellDesignerDoubleHeadedArc(DoubleHeadedArc)` — `path_*` styling; `own_drawing_elements()`.
- `_SimpleNodeMixin(_SimpleMixin)`, `_MultiNodeMixin(_MultiMixin)` — drawing mixins; `_n` property.

### `src/momapy/celldesigner/model.py`
Purpose: CellDesigner model classes.

- **Regions**: `Region(CellDesignerModelElement)` (`name`, `active=False`) → `ModificationSite`, `CodingRegion`, `RegulatoryRegion`, `TranscriptionStartingSiteL`, `TranscriptionStartingSiteR`, `ProteinBindingDomain`.
- **Modifications**: `ModificationResidue` (`name`, `order`); `ModificationState(Enum)` — 13 values (PHOSPHORYLATED, ACETYLATED, UBIQUITINATED, …); `Modification`; `StructuralState` (`value`).
- **Templates**: `SpeciesTemplate(CellDesignerModelElement)` (`name`) → `ProteinTemplate` (`modification_residues`) → `GenericProteinTemplate`, `TruncatedProteinTemplate`, `ReceptorTemplate`, `IonChannelTemplate`; `GeneTemplate` (`regions`), `RNATemplate` (`regions`), `AntisenseRNATemplate` (`regions`).
- **Compartment / species**: `Compartment(SBMLCompartment, CellDesignerModelElement)`; `Species(SBMLSpecies, CellDesignerModelElement)` (`hypothetical`, `active`, `homomultimer`); `Protein` (`template`, `modifications`, `structural_states`) → `GenericProtein`, `TruncatedProtein`, `Receptor`, `IonChannel`; `Gene`, `RNA`, `AntisenseRNA` (each with `template`, `modifications`); `Phenotype`, `Ion`, `SimpleMolecule`, `Drug`, `Unknown`; `Complex` (`structural_states`, `subunits`). The degraded glyph is layout-only (`DegradedLayout`/`DegradedActiveLayout`, no model class); it is encoded on `Reaction` via `has_external_source`/`has_external_sink`.
- **Reaction participants**: `Reactant(SpeciesReference, CellDesignerModelElement)` (`base`), `Product(SpeciesReference, CellDesignerModelElement)` (`base`).
- **Boolean logic**: `BooleanLogicGateInput(SimpleSpeciesReference, CellDesignerModelElement)` (`referred_element: Species`, inherited — every CD participation class shares the `SimpleSpeciesReference` base); `BooleanLogicGate` (`inputs`) → `AndGate`, `OrGate`, `NotGate`, `UnknownGate`.
- **Modulators**: `KnownOrUnknownModulator(ModifierSpeciesReference, CellDesignerModelElement)` (`referred_element: Species | BooleanLogicGate`) → `Modulator`, `UnknownModulator`; `Modulator` → `Inhibitor`, `PhysicalStimulator`, `Trigger`; `PhysicalStimulator` → `Catalyzer`; `UnknownModulator` → `UnknownCatalyzer`, `UnknownInhibitor`.
- **Reactions**: `Reaction(SBMLReaction, CellDesignerModelElement)` (`reactants`, `products`, `modifiers`) → `StateTransition`, `KnownTransitionOmitted`, `UnknownTransition`, `Transcription`, `Translation`, `Transport`, `HeterodimerAssociation`, `Dissociation`, `Truncation`.
- **Modulations**: `KnownOrUnknownModulation` (`source`, `target`) → `Modulation` → `Catalysis`, `Inhibition`, `PhysicalStimulation`, `Triggering`, `PositiveInfluence`, `NegativeInfluence`; `UnknownModulation` → `UnknownCatalysis`, `UnknownInhibition`, `UnknownPositiveInfluence`, `UnknownNegativeInfluence`, `UnknownPhysicalStimulation`, `UnknownTriggering`.
  The CellDesigner reader picks the negative-modulation class from the target rather than
  from the reaction type string: `Inhibition` / `UnknownInhibition` when the target is a
  `Phenotype`, `NegativeInfluence` / `UnknownNegativeInfluence` otherwise. CellDesigner
  itself rewrites a phenotype-targeting `INHIBITION` to `NEGATIVE_INFLUENCE` on save, so
  both spellings can name the same arc.
- **Model**: `CellDesignerModel(SBMLModel)` — `species_templates`, `boolean_logic_gates`, `modulations`; `is_submodel(other) -> bool`.

### `src/momapy/celldesigner/layout.py`
Purpose: CellDesigner layout classes.

- **Constants** (reader/build defaults, re-exported from `momapy.celldesigner`): `DEFAULT_FONT_SIZE = 12.0` (species / node labels), `DEFAULT_MODIFICATION_FONT_SIZE = 9.0` (modifications / structural states), `DEFAULT_ACTIVE_XSEP = 4.0`, `DEFAULT_ACTIVE_YSEP = 4.0` (active-state border padding, used in the active-layout field defaults).
- **Container**: `CellDesignerLayout(Layout)`.
- **Species layouts** (each with active variant, all `_MultiNodeMixin, CellDesignerNode`): `GenericProteinLayout`, `IonChannelLayout`, `ComplexLayout`, `SimpleMoleculeLayout`, `IonLayout`, `UnknownLayout`, `DegradedLayout`, `GeneLayout`, `PhenotypeLayout`, `RNALayout`, `AntisenseRNALayout`, `TruncatedProteinLayout`, `ReceptorLayout`, `DrugLayout`.
- **Compartments**: `OvalCompartmentLayout`, `RectangleCompartmentLayout`, `CornerCompartmentLayout`, `LineCompartmentLayout`; enums `CompartmentCorner`, `CompartmentSide`.
- **Modifications & states**: `StructuralStateLayout`, `ModificationLayout`.
- **Arcs**: `CellDesignerSingleHeadedArc` subclasses (`ConsumptionLayout`, `ProductionLayout`, modulation arcs `CatalysisLayout`/`UnknownCatalysisLayout`, `InhibitionLayout`/`UnknownInhibitionLayout`, `PhysicalStimulationLayout`/`UnknownPhysicalStimulationLayout`, `ModulationLayout`/`UnknownModulationLayout`, `PositiveInfluenceLayout`/`UnknownPositiveInfluenceLayout`, `TriggeringLayout`/`UnknownTriggeringLayout`); `CellDesignerDoubleHeadedArc`; `ReactionLayout` subclasses (`StateTransitionLayout`, `KnownTransitionOmittedLayout`, `UnknownTransitionLayout`, `TranscriptionLayout`, `TranslationLayout`, `TransportLayout`, `HeterodimerAssociationLayout`, `DissociationLayout`, `TruncationLayout`); `LogicArcLayout`.
- **Logic gates**: `AndGateLayout`, `OrGateLayout`, `NotGateLayout`, `UnknownGateLayout`.

### `src/momapy/celldesigner/map.py`
- `CellDesignerMap(Map)` — `model: CellDesignerModel | None`, `layout: CellDesignerLayout | None`.

### `src/momapy/celldesigner/utils.py`
Functions (accept `CellDesignerMap | Builder`, return same):
- `highlight_layout_elements(map_, layout_elements)`
- `set_layout_to_fit_content(map_, xsep=0, ysep=0)`
- `set_nodes_to_fit_labels(map_, xsep=0, ysep=0, omit_width=False, omit_height=False, restrict_to=None, exclude=None, *, snap_arcs=False)`
- `set_compartments_to_fit_content(map_, xsep=0, ysep=0, *, snap_arcs=False)`
- `set_complexes_to_fit_content(map_, xsep=0, ysep=0, *, snap_arcs=False)`
- `set_modifications_to_borders(map_, *, snap_arcs=False)`
- `set_modifications_label_font_size(map_, font_size)`
- `set_arcs_to_borders(map_)`
- `straighten_arcs(map_, angle_tolerance=5.0)`
- `tidy(map_, modifications_omit_width=False, modifications_omit_height=False, nodes_xsep=4, nodes_ysep=4, modifications_xsep=2, modifications_ysep=2, complexes_xsep=10, complexes_ysep=10, compartments_xsep=25, compartments_ysep=25, layout_xsep=0, layout_ysep=0, arcs_angle_tolerance=5.0)`
- `get_info(map_: CellDesignerMap) -> dict[str, typing.Any]` (keys `map_type: str`, `model: dict[str, int]`, `layout: dict` with `width`/`height`/`elements`)

### `src/momapy/celldesigner/io/celldesigner/_reading_context.py`
- `CellDesignerReadingContext(ReadingContext)` — adds `cd_complex_alias_id_to_cd_included_species_ids`, `cd_compartment_aliases`, `cd_compartments`, `cd_species_templates`, `cd_species_aliases`, `cd_reactions`, `cd_modulations`, `real_model_source_ids` / `real_layout_source_ids` (split ID tracking), `canvas_width`, `canvas_height`, `cd_degraded_alias_ids`, `cd_degraded_species_ids`.

### `src/momapy/celldesigner/io/celldesigner/reader.py`
- `CellDesignerReader(Reader)` — `read(file_path, return_type="map", with_model=True, with_layout=True, with_annotations=True, with_notes=True, **options)`. Also `_make_empty_map`/`_make_empty_model`/`_make_empty_layout` and `_make_and_add_*` orchestration classmethods (mirroring SBGN-ML/SBML).

### `src/momapy/celldesigner/io/celldesigner/_reading_classification.py`
- `KEY_TO_CLASS: dict[tuple[str, str], type | tuple[type | None, type]]` — 66 entries keyed by `(category, type)` (e.g. `("SPECIES", "GENERIC") -> (GenericProtein, GenericProteinLayout)`, `("TEMPLATE", "GENE") -> GeneTemplate`). Template/region keys map to a bare model class; species/reaction/modifier/gate keys map to a `(model, layout)` pair (model `None` for `DEGRADED`, whose layout is `DegradedLayout`). Mirrors the SBGN-ML reader's classification module.

### `src/momapy/celldesigner/io/celldesigner/_writing_context.py`
- `CellDesignerWritingContext(WritingContext)` — adds `subunit_to_complex`, `degraded_entries`.

### `src/momapy/celldesigner/io/celldesigner/writer.py`
- `CellDesignerWriter(Writer)` — `write(obj, file_path, element_to_annotations=None, element_to_notes=None, source_id_to_model_element=None, source_id_to_layout_element=None, source_id_to_annotations=None, source_id_to_notes=None, with_annotations=True, with_notes=True, **options)`. **Round-trip caveat:** CellDesigner's link-geometry encoding (anchors, edit points, angles, line directions) is recomputed from momapy's resolved coordinates, so a read/write round-trip yields equivalent (not byte-identical) link geometry (see class docstring). All serialization helpers (the `make_celldesigner_*` / `make_sbml_document_*` builders, id helpers `reserve_source_xml_ids` / `get_xml_id` / `get_species_id`, the `DegradedEntry` dataclass, and the `NSMAP` / class→type-map constants) live in `_writing.py`, public-named (the CD namespace comes from `_constants.CD_NAMESPACE`).

### `src/momapy/celldesigner/io/celldesigner/_reading_model.py` (`make_*`)
- `make_annotations_from_element(cd_element)`, `make_annotations_from_notes(cd_notes)`, `make_notes_from_element(cd_element)`, `make_and_add_annotations(reading_context, cd_element, model_element)`
- `make_compartment(reading_context, cd_compartment)`
- `make_species_template(reading_context, cd_species_template, model_element_cls)`
- `make_modification_residue(reading_context, cd_modification_residue, super_cd_element, order)`
- `make_region(reading_context, cd_region, model_element_cls, super_cd_element, order)`
- `make_species(reading_context, cd_species, model_element_cls, name, homomultimer, hypothetical, active)`
- `make_species_modification(reading_context, modification_state, cd_modification_residue_id)`
- `make_species_structural_state(reading_context, cd_species_structural_state)`
- `make_reaction(reading_context, cd_reaction, model_element_cls)`
- `make_reactant_from_base(reading_context, cd_base_reactant, cd_reaction)` / `make_reactant_from_link(...)`
- `make_product_from_base(...)` / `make_product_from_link(...)`
- `make_modifier(reading_context, model_element_cls, source_model_element, metaid)`
- `make_logic_gate(reading_context, model_element_cls)`, `make_logic_gate_input(reading_context, input_model_element)`
- `make_modulation(reading_context, cd_reaction, model_element_cls, source_model_element, target_model_element)`

### `src/momapy/celldesigner/io/celldesigner/_reading_layout.py` (`make_*`)
- `set_layout_size_and_position(reading_context, cd_model)`
- `make_segments(points)`, `make_points(cd_edit_points)`
- `make_species(reading_context, cd_species, ...)`, `make_species_modification(...)`, `make_species_structural_state(...)`
- `make_compartment_from_alias(reading_context, cd_compartment, cd_compartment_alias)`
- `make_segments_non_t_shape(reading_context, cd_reaction)`, `make_segments_left_t_shape(...)`, `make_segments_right_t_shape(...)`
- `make_reaction(reading_context, cd_reaction, ...)`
- `make_reactant_from_base(...)` / `make_reactant_from_link(...)`, `make_product_from_base(...)` / `make_product_from_link(...)`
- `make_modifier(reading_context, ...)`
- `make_logic_gate(reading_context, cd_element, layout_element_cls)`, `make_logic_arc(reading_context, gate_layout_element, input_layout_element)`
- `make_modulation(reading_context, ...)`
- Internal constants: `_LAYOUT_TO_ACTIVE_LAYOUT`, `_CD_CLASS_TO_CORNER`, `_CD_CLASS_TO_SIDE`, `_TARGET_LINE_INDEX_TO_ANCHOR_NAME`.

### `src/momapy/celldesigner/io/celldesigner/_constants.py`
- Shared CellDesigner format constants (internal module, public-named content), imported by the reader and writer: `CD_NAMESPACE: str`, `TEXT_TO_CHARACTER: dict[str, str]` (special-character decoding table), `LINK_ANCHOR_POSITION_TO_ANCHOR_NAME: dict[str, str]` (link-anchor position codes -> momapy anchor names). `celldesigner.utils` no longer imports any of these — it uses `momapy.geometry.COMPASS_ANCHOR_NAMES` for its anchor list.

### `src/momapy/celldesigner/io/celldesigner/_reading_parsing.py`
- `get_name(name: str|None) -> str|None` — handles CellDesigner name encoding.
- `get_id_to_element_mapping(cd_model) -> dict`
- `get_complex_alias_to_included_ids_mapping(cd_model) -> dict`
- XML traversal helpers: `get_annotation`, `get_extension`, `get_species`, `get_reactions`, `get_species_aliases`, `get_included_species_aliases`, `get_complex_species_aliases`, `get_compartments`, `get_compartment_aliases`, `get_protein_templates`, `get_gene_templates`, `get_rna_templates`, `get_antisense_rna_templates`, `get_notes`, `get_rdf`, `get_rdf_from_notes`, `get_width`, `get_height`, `get_bounds`, `get_edit_points_from_participant_link`, `get_edit_points_from_reaction`, etc.
- Participant-id helpers: `get_reactant_id(cd_base_reactant_or_link, cd_reaction) -> str`, `get_product_id(cd_base_product_or_link, cd_reaction) -> str`, `get_modifier_metaid(cd_reaction_modification, cd_reaction) -> str|None`.
- Constants: `CD_NAMESPACE`, `TEXT_TO_CHARACTER`, and `LINK_ANCHOR_POSITION_TO_ANCHOR_NAME` are imported from the shared `_constants` module (above), not defined here.

### `src/momapy/celldesigner/io/celldesigner/_writing.py`
- Geometry helpers: `are_collinear(p1, p2, p3, epsilon=1e-6) -> bool`, `is_degenerate_frame(origin, unit_x, unit_y, epsilon=1e-6) -> bool`, `make_non_degenerate_frame(origin, unit_x, unit_y, epsilon=1e-6, scale=1.0) -> (Point, Point, Point)`.
- Encoding helpers: `color_to_cd_hex(color) -> str`, `encode_name(name) -> str`, `compute_cd_angle(...)`, `node_to_bounds_attrs(node) -> dict`.
- Reverse mapping constants: `_ANCHOR_NAME_TO_LINK_ANCHOR_POSITION`, `_CHARACTER_TO_TEXT`, `_CLASS_TO_CD_STRING`, `_CLASS_TO_REACTION_TYPE`, `_CLASS_TO_MODIFIER_TYPE`, `_MODIFICATION_STATE_TO_CD` (the CD namespace is imported as `CD_NAMESPACE` from `_constants`; `NSMAP` uses it).

---

## SBML (`src/momapy/sbml/`)

### `src/momapy/sbml/__init__.py`
Re-exports: `SBMLModelElement`, `SBMLMap`, `BiomodelQualifier`, `BQBiol`, `BQModel`, `Compartment`, `ModifierSpeciesReference`, `RDFAnnotation`, `Reaction`, `SBMLModel`, `SimpleSpeciesReference`, `Species`, `SpeciesReference`.

### `src/momapy/sbml/map.py`
- `SBMLMap(Map)` — `model: SBMLModel | None = None`. Model only; SBML has no layout, so the inherited `layout` / `layout_model_mapping` are always `None`.

### `src/momapy/sbml/utils.py`
- `get_info(map_: SBMLMap) -> dict[str, typing.Any]` (keys `map_type: str`, `model: dict[str, int] | None` with `compartments`/`species`/`reactions` — `None` when the map has no model, `layout: None` — SBML has no layout).

### `src/momapy/sbml/elements.py`
- `SBMLModelElement(ModelElement)` — abstract; `name: str | None`, `sbo_term: str | None`, `metaid: str | None` (`compare=False, hash=False`). **(Formerly named `SBase`; renamed so that `Model` is never a `ModelElement` — see `tests/test_io_mappings.py`.)**

### `src/momapy/sbml/model.py`
Purpose: concrete SBML model classes and BioModels qualifier enums.

- **Qualifiers**: `BiomodelQualifier(Enum)` (abstract); `BQModel(BiomodelQualifier)` (HAS_INSTANCE, IS, IS_DERIVED_FROM, IS_DESCRIBED_BY, IS_INSTANCE_OF); `BQBiol(BiomodelQualifier)` (ENCODES, HAS_PART, HAS_PROPERTY, HAS_VERSION, IS, IS_DESCRIBED_BY, IS_ENCODED_BY, IS_HOMOLOG_TO, IS_PART_OF, IS_PROPERTY_OF, IS_VERSION_OF, OCCURS_IN, HAS_TAXON).
- **Annotation**: `RDFAnnotation` — plain frozen dataclass (metadata, not a model element); `qualifier`, `resources: frozenset[str]`.
- **Structure**: `Compartment(SBMLModelElement)` — `outside: Compartment | None`; `Species(SBMLModelElement)` — `compartment: Compartment | None`; `SimpleSpeciesReference(SBMLModelElement)` — `referred_element: Species`; `ModifierSpeciesReference(SimpleSpeciesReference)`; `SpeciesReference(SimpleSpeciesReference)` — `stoichiometry: float | None`; `Reaction(SBMLModelElement)` — `reversible`, `compartment`, `reactants`, `products`, `modifiers`.
- **Model**: `SBMLModel(Model)` — **does NOT inherit `SBMLModelElement`**; declares its own `name`, `sbo_term`, `metaid`, plus `compartments`, `species`, `reactions`. `is_submodel(other) -> bool`.

### `src/momapy/sbml/io/sbml/_reading_context.py`
- `SBMLReadingContext(momapy.io._utils.ReadingContext)` — adds `sbml_model`, `sbml_id_to_model_element` (SBML id -> frozen model element, for cross-ref resolution).

### `src/momapy/sbml/io/sbml/reader.py`
- `SBMLReader(Reader)` — `check_file(file_path) -> bool`, `read(file_path, return_type="map", with_model=True, with_layout=True, with_annotations=True, with_notes=True, **options) -> ReaderResult`. `return_type="map"` returns an `SBMLMap` (layout `None`), `"model"` returns the `SBMLModel`, `"layout"` raises `NotImplementedError`. Also `_make_empty_map`/`_make_empty_model` and `_make_and_add_*` orchestration classmethods (mirroring SBGN-ML/CellDesigner).

### `src/momapy/sbml/io/sbml/_reading_model.py` (`make_*` internal helpers)
- `make_annotations(rdf) -> list[RDFAnnotation]`, `make_notes(notes_element) -> list[str]` (shared with SBGN-ML/CellDesigner readers)
- `make_annotations_from_element(sbml_element)`, `make_notes_from_element(sbml_element)`
- `make_and_add_annotations_and_notes(reading_context, sbml_element, model_element, source_id=None)`
- `register_model_element(reading_context, model_element, collection, id_)` — id-based dedup + records in `reading_context.sbml_id_to_model_element`
- `make_compartment(reading_context, sbml_compartment)`
- `make_species(reading_context, sbml_species)`
- `make_reaction(reading_context, sbml_reaction)`
- `make_species_reference(reading_context, sbml_species_reference, reaction_id)`
- `make_modifier_species_reference(reading_context, sbml_modifier_species_reference, reaction_id)`

### `src/momapy/sbml/io/sbml/_reading_parsing.py`
- `_RDF_NAMESPACE` constant.
- `get_prefix_and_name(tag)`, `get_description(rdf)`, `get_bags(bq_element)`, `get_list_items(bag)`
- `get_annotation(sbml_element)`, `get_species(sbml_model)`, `get_reactions(sbml_model)`, `get_compartments(sbml_model)`, `get_reactants(sbml_reaction)`, `get_products(sbml_reaction)`, `get_modifiers(sbml_reaction)`, `get_notes(sbml_element)`, `get_rdf(sbml_element)`

### `src/momapy/sbml/io/sbml/_qualifiers.py`
- `QUALIFIER_MEMBER_TO_QUALIFIER_ATTRIBUTE` — `BQBiol | BQModel` → `(namespace_url, local_name)` (18 entries).
- `QUALIFIER_ATTRIBUTE_TO_QUALIFIER_MEMBER` — reverse (19 entries; biology-qualifiers/hasInstance maps to `BQModel.HAS_INSTANCE`).

---

## Cross-cutting reminders

- **Frozen dataclasses everywhere**: mutate only via builders (`builder_from_object` → change → `build()`).
- **`Model` is a `MapElement`, never a `ModelElement`** in any format. `model.descendants()` traverses the `Model` directly by field walking, and the `Model` itself is excluded from its own element set.
- **Equality on elements**: structural (all fields except `id_`, `metaid`); dedup during read relies on it.
- **I/O `make_*` functions** are internal helpers of the `_reading_*` / `_writing_*` modules (underscore filenames), inventoried here for maintainer orientation — not part of the public I/O contract (which is `read`/`write`, `Reader`/`Writer`, `get_*`/`list_*`/`register_*`, and `ReaderResult`/`WriterResult`). The context dataclasses (`ReadingContext`/`WritingContext` and subclasses) are likewise internal (`momapy.io._utils.__all__` is empty); each format's subclass lives in its own `_reading_context.py` / `_writing_context.py`.
- **ReaderResult public dicts**: `id_to_element`, `source_id_to_model_element`, `source_id_to_layout_element` — the SBGN and CellDesigner readers populate both `source_id_to_*` dicts; the split ensures alias ids appear only on the layout side and SBML ids only on the model side for CellDesigner (via `real_model_source_ids` / `real_layout_source_ids` in `build_id_mappings`). The SBML reader (layout-less) populates `id_to_element` and `source_id_to_model_element` via the same `build_id_mappings` helper, leaving `source_id_to_layout_element` `None`.
