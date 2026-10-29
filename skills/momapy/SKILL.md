---
name: momapy
description: Build, read, write, modify, or render SBGN (Process Description / Activity Flow) and CellDesigner molecular maps with the momapy Python library. Trigger when a project imports `momapy`, when the user asks about the momapy API (Map / Model / Layout / `LayoutModelMapping`, frozen dataclasses, the builder pattern, `read()` / `write()`, rendering to SVG/PDF/PNG), or when working with `.sbgn`, `.sbgnml`, `.xml` (CellDesigner) files in a momapy context.
---

# momapy

`momapy` is a Python library for working with **molecular maps**: SBGN (PD and AF) and CellDesigner. It separates a map's **semantics** (what the diagram represents) from its **visual layout** (how it is drawn) and provides readers, writers, renderers, and CSS-like styling.

This skill captures the rules and recipes you need to write correct momapy code. **Read `momapy`'s installed source** (or its docs at <https://adrienrougny.github.io/momapy/>) for exact signatures — class hierarchies are large.

---

## Mental model

A `momapy.core.Map` has three fields:

- **`model`** — semantic content. Biological concepts such as entity pools, processes, modulations, compartments, … (subclasses of `ModelElement`).
- **`layout`** — visual content. Shapes with positions, sizes, styles (subclasses of `LayoutElement`).
- **`layout_model_mapping`** — a `LayoutModelMapping` that maps each layout element (or frozenset of layout elements, for processes/modulations/operators) to the model element it represents.

You can have several layout elements representing the same model element (for example the same pool of entities drawn twice). The mapping is what tells you "this glyph represents *that* pool of entities".

```python
from momapy.io import read

result = read("map.sbgn")
map_ = result.obj
print(map_.model)              # SBGNPDModel / SBGNAFModel / CellDesignerModel
print(map_.layout)             # the visual tree
print(map_.layout_model_mapping)  # bidirectional links
```

---

## CRITICAL: frozen dataclasses and the builder pattern

**Every** model element, layout element, mapping, and `Map` is a **frozen dataclass**. You cannot assign to its fields. Trying to mutate one will raise `dataclasses.FrozenInstanceError`.

To "modify" an object, transform it into a builder, mutate the builder, then build a new immutable object:

```python
from momapy.builder import builder_from_object, object_from_builder

builder = builder_from_object(map_)            # returns a MapBuilder
builder.layout.fill = momapy.coloring.lightgray
new_map = object_from_builder(builder)                       # frozen Map again
```

Rules:

- Never write `obj.field = value` on a frozen dataclass — always go through a builder.
- `builder_from_object()` recursively wraps every nested frozen dataclass into a builder, so you can mutate deeply nested fields directly on the returned builder.
- `object_from_builder()` recursively re-freezes everything.
- For collections of children: `frozenset` and `tuple` fields become `set` and `list` in the builder; mutate them in place.
- To create a fresh element, use `new_builder_object(SomeClass, …)` from `momapy.builder`, set fields, then use `object_from_builder()`.

```python
from momapy.builder import new_builder_object, object_from_builder
from momapy.sbgn.pd import Macromolecule

builder = new_builder_object(Macromolecule, label="ATP")
macromolecule = object_from_builder(builder)
```

If you ever feel tempted to do `object.__setattr__(obj, "field", value)` to bypass the freeze — stop. You will silently break equality, hashing, and the cached id maps. Use a builder.

---

## Reading a map

```python
from momapy.io import read

# Format auto-detected from the file content; pass reader="sbgnml" / "celldesigner" to force.
# Pickle is never auto-detected: read it with reader="pickle" (trusted files only).
result = read("map.sbgn")
```

`read()` returns a **`ReaderResult`** (`momapy.io.core.ReaderResult`) — a dataclass carrying the parsed object together with everything the reader learned about the source file that could not be stored on the frozen object itself. Every field is immutable (`frozendict` / `FrozenSurjectionDict` / frozen dataclass).

| Field | Type | What it holds |
|---|---|---|
| `obj` | `Map` \| `Model` \| `Layout` \| `None` | The parsed object. Top-level object depends on `return_type` (default `"map"`). |
| `element_to_annotations` | `frozendict[MapElement, frozenset[Annotation]]` | RDF/MIRIAM annotations attached to each element. Merged view: when reader dedup collapses several source elements into one model element, their annotation sets are unioned. |
| `element_to_notes` | `frozendict[MapElement, frozenset[str]]` | Free-text `<notes>` blocks attached to each element. Merged view, same semantics as `element_to_annotations`. |
| `source_id_to_annotations` | `frozendict[str, frozenset[Annotation]]` | Per-source view of annotations, keyed by the raw source XML id. Preserves per-source granularity even when several source elements deduplicate into a single model element — combine with `source_id_to_model_element.inverse` to recover which annotations came from which source. Only keys from source elements with a stable XML id are populated. |
| `source_id_to_notes` | `frozendict[str, frozenset[str]]` | Per-source view of notes, keyed by the raw source XML id. Same semantics as `source_id_to_annotations`. |
| `id_to_element` | `frozendict[str, MapElement]` | Looks up any momapy element (model **or** layout) by its `id_`. Built by walking `obj.descendants()`. Keys are the momapy-assigned IDs — see "momapy IDs vs source IDs" below. |
| `source_id_to_model_element` | `FrozenSurjectionDict[str, ModelElement]` \| `None` | Maps IDs that appeared verbatim in the source file to the model element they named. `None` when no model was read. |
| `source_id_to_layout_element` | `FrozenSurjectionDict[str, LayoutElement]` \| `None` | Same, for layouts. `None` when no layout was read. |
| `file_path` | `str` \| `os.PathLike` \| `None` | The path that was read. |

### momapy IDs vs source IDs

momapy elements carry a stable `id_` attribute (see the **ID Assignment Patterns** table in `CLAUDE.md`) that is *derived* from the source file — e.g. for SBGN-ML a model element's `id_` is `f"{xml_id}_model"` and the paired layout's `id_` is the raw `xml_id`. For CellDesigner the derivation is more involved (composite IDs, metaids, dual registration of species under both `species_id` and `speciesAlias_id`).

Because of this, there are **two different lookup dicts**:

- **`id_to_element`** is keyed by the **momapy `id_`** of the element. Use it when you already have a momapy ID in hand — e.g. a reference you stored earlier, a value from `element.id_`.
- **`source_id_to_model_element`** / **`source_id_to_layout_element`** are keyed by the **original identifier from the source file** (e.g. `<glyph id="…">` in SBGN-ML, `<species id="…">` or `<speciesAlias id="…">` in CellDesigner). Use these when you need to correlate a momapy element back to the raw file — for roundtrip fidelity, cross-file references, or debugging.

Only IDs that existed *verbatim* in the source land in `source_id_to_model_element` / `source_id_to_layout_element`. Synthetic / composite / auto-generated IDs (e.g. CellDesigner modification composite IDs, UUID fallbacks) are **excluded** — they would not make sense to a tool reading the source file. `id_to_element` has no such filter and contains every element in the map.

### `FrozenSurjectionDict` and `.inverse`

`source_id_to_model_element` and `source_id_to_layout_element` are **`FrozenSurjectionDict`** (`momapy.utils.FrozenSurjectionDict`) — an immutable dict that additionally exposes a cached **inverse mapping** from values back to keys. This is what you need when a single momapy element was registered under several source IDs (e.g. a CellDesigner species registered under both its `species_id` and its `speciesAlias_id`).

```python
source_id_to_model_element["s1"]                      # → the Macromolecule model element
source_id_to_model_element.inverse[macromolecule]     # → ['s1', 'sa1']  (list of source IDs)
```

`.inverse` returns a `frozendict[value, list[key]]`. Each value maps to the **list** of source IDs that pointed to it. Writers use this to recover the original source IDs for roundtrip fidelity:

```python
# Inside a writer, wanting to reuse the original XML id for a model element
original_ids = writing_context.source_id_to_model_element.inverse.get(model_element)
xml_id = original_ids[0] if original_ids else generate_new_id()
```

Related surjection helpers — both live in `momapy.utils`:

- **`SurjectionDict`** — the mutable equivalent, used inside the builder for `LayoutModelMapping.representative_to_key` (the representative → frozenset lookup). `.inverse` is rebuilt incrementally on every mutation.
- **`IdentitySurjectionDict`** — identity-keyed variant; the inverse is keyed by `id(value)` so distinct objects that compare equal are kept distinct. Used internally by reading contexts (`xml_id_to_model_element`, `model_element_remap`) to avoid conflating model-element-equal-but-not-identical duplicates.

You will normally only touch `FrozenSurjectionDict` on a `ReaderResult`. The other two are implementation details of the reader and builder.

### Reader options

Reader-specific options can be passed as kwargs to `read()`:

- `return_type`: `"map"` (default), `"model"`, or `"layout"` — controls what `result.obj` is.
- `with_annotations`, `with_notes`: set to `False` to skip parsing those blocks.
- Format-specific options (e.g. `xsep`, `ysep` for SBGN-ML) — see each reader's `read()` signature.

When `return_type != "map"`, the unused side's source-id dict is `None` (e.g. `source_id_to_layout_element is None` for `return_type="model"`).

### Listing readers and writers

```python
from momapy.io import list_readers, list_writers
list_readers()   # ['sbgnml', 'celldesigner', 'pickle', ...]
list_writers()
```

---

## Writing a map

```python
from momapy.io import write

write(map_, "out.sbgn", writer="sbgnml")
write(map_, "out.xml", writer="celldesigner")
write(map_, "out.pkl", writer="pickle")
```

The writer is **not** auto-detected from the extension — pass `writer=` explicitly.

---

## Rendering

Three rendering backends are available:

| Backend | Formats | Install |
|---|---|---|
| `svg-native` | svg | always available |
| `cairo` | pdf, svg, png, ps | `pip install momapy[cairo]` |
| `skia` | pdf, svg, png, jpeg, webp | `pip install momapy[skia]` |

```python
from momapy.rendering import render_map
from momapy.styling import StyleSheet

render_map(map_, "out.svg")                       # svg-native, auto-detected from extension
render_map(map_, "out.pdf", renderer="cairo")
render_map(map_, "out.png", renderer="skia")
```

For multi-page output or rendering a list of maps, use `render_maps([...], ...)`.

---

## Modifying a map

The full pattern: read → builder → mutate → build → write.

```python
from momapy.builder import builder_from_object, object_from_builder, isinstance_or_builder
from momapy.io import read, write
from momapy.coloring import lightyellow

result = read("map.sbgn")
map_builder = builder_from_object(result.obj)

# Tweak every macromolecule layout's fill colour
from momapy.sbgn.pd import MacromoleculeLayout
for layout_element_builder in map_builder.layout.descendants():
    if isinstance_or_builder(layout_element_builder, MacromoleculeLayout):
        layout_element_builder.fill = lightyellow

map_ = object_from_builder(map_builder)
write(map_, "tinted.sbgn", writer="sbgnml")
```

`descendants()` and `flattened()` walk the tree for you — prefer them over hand-written recursion.

### Adding a new element

The easy way, for any map class, is to take the map apart, add the new elements, and build it again with `momapy.core.make_map`. It takes the top-level model elements, the top-level layout elements (in drawing order) and the `(layout_element, model_element)` pairs, and computes the model collections and every frozenset key; `get_layout_model_pairs(mapping)` gives the pairs of an existing map:

```python
from momapy.core import get_layout_model_pairs, make_map

pairs = get_layout_model_pairs(map_.layout_model_mapping)
# process_glyph: a layout element of map_; arc ends must be the layout's own objects
process = map_.layout_model_mapping.get_mapping(process_glyph)
enzyme_glyph = MacromoleculeLayout(position=Point(100, 50), width=60, height=30)
catalysis_arc = CatalysisLayout(source=enzyme_glyph, target=process_glyph, segments=(...))
enzyme = Macromolecule(label="E")
catalysis = Catalysis(source=enzyme, target=process)
new_map = make_map(
    type(map_),
    map_.model.children() + [enzyme, catalysis],
    map_.layout.children() + [enzyme_glyph, catalysis_arc],
    pairs + [(enzyme_glyph, enzyme), (catalysis_arc, catalysis)],
)
```

Every top-level model element must be listed, and the elements of a pair must be listed elements or their descendants (the same objects). Equal top-level elements become one (the one with the smallest `id_`), and references are made to point to the kept objects. A model element that is changed (e.g. a process with a new reactant) is a new object: replace the old one in the model elements and in the pairs. `momapy.core.merge_maps(maps)` merges whole maps.

By hand, with builders:

1. Build the model element (`object_from_builder(new_builder_object(<ModelClass>, …))`).
2. Add it to the appropriate model collection on the builder (`map_builder.model.entity_pools.add(...)`).
3. Build the layout element similarly and add it to a parent `layout_elements`'.
4. Register the link in the mapping: `map_builder.layout_model_mapping.add_mapping(layout_element, model_element)`.
5. When a model element is represented by a **cluster** of layout elements — a process plus its participant arcs and targets, a modulation arc with its source and target clusters, a logical operator and its inputs, a tag or terminal with its reference arcs — the key is a `frozenset` of those layouts. Pass `representative=<layout_element>` to designate the element that stands for the cluster on its own (the process glyph for a process, the modulation arc for a modulation, the operator glyph for a logical operator, the tag glyph for a tag); `get_mapping(representative)` then resolves back to the model element, and other composite keys can reference the cluster by its representative.

   The exact key shape and representative for each model element type is documented at the top of each format's module: see the "Layout-model mapping catalogue" section in `momapy.sbgn.pd`, `momapy.sbgn.af`, and `momapy.celldesigner.model`.

---

## Styling

CSS-like stylesheets, applied either directly to a layout or when rendering:

```python
from momapy.styling import StyleSheet, apply_style_sheet

style = StyleSheet.from_string("""
MacromoleculeLayout { fill: lightblue; stroke-width: 2; }
""")
apply_style_sheet(map_, style)
```

Predefined stylesheets live in `momapy.sbgn.styling`: `cs_default`, `cs_black_and_white`, `sbgned`, `newt`, `fs_shadows`. Combine with `|` or `combine_style_sheets([...])`.

Maps can be rendered directly with a stylesheet:

```python
style = StyleSheet.from_file("style.css")
render_map(map_, "out.svg", style_sheet=style, to_top_left=True)
```

---

## CLI

The `momapy` CLI wraps the most common operations:

```bash
momapy render map.sbgn -o out.svg
momapy render map.sbgn -o out.pdf -r cairo -s style.css
momapy export map.sbgn -o out.xml          # convert SBGN-ML → CellDesigner
momapy visualize map.sbgn                  # opens an interactive viewer in the browser
momapy tidy all map.sbgn -o tidied.sbgn
momapy style map.sbgn -p sbgned -o styled.sbgn
momapy list readers                        # also: writers, renderers, styles, colors, attributes
momapy info map.sbgn                       # inspect a map file (add --format json for JSON)
```

---

## Where to look

When you need an exact signature, prefer reading the source over guessing — class hierarchies are large and many fields are format-specific.

| You need… | Look in… |
|---|---|
| Base classes (`Map`, `Model`, `Layout`, `Node`, `Arc`) | `momapy/core/` |
| Geometry (`Point`, `Bbox`, transformations) | `momapy/geometry.py` |
| Drawing primitives | `momapy/drawing.py` |
| Builder utilities | `momapy/builder.py` |
| SBGN PD model + layout classes | `momapy/sbgn/pd/` |
| SBGN AF model + layout classes | `momapy/sbgn/af/` |
| CellDesigner model + layout classes | `momapy/celldesigner/` |
| SBGN-ML reader/writer | `momapy/sbgn/io/sbgnml/` |
| CellDesigner reader/writer | `momapy/celldesigner/io/celldesigner/` |
| Generic shapes / nodes / arcs | `momapy/meta/` |
| SBGN tidying helpers | `momapy/sbgn/utils.py` (`tidy`, `sbgned_tidy`, `newt_tidy`) |
| CellDesigner tidying helpers | `momapy/celldesigner/utils.py` (`tidy`) |

An `API_REFERENCE.md` ships alongside this skill (and is symlinked at the repo root for contributors working inside the `momapy` source tree). It is a curated module-by-module signature inventory — read it first for orientation.

---

## Common pitfalls

- **Mixing model and layout responsibilities.** Semantic data (label, type, references) belongs on the model element. Visual data (position, size, fill, stroke, font) belongs on the layout element. Don't put a colour on a `Macromolecule`; put it on the `MacromoleculeLayout`.
- **Mutating a frozen dataclass.** Will raise `FrozenInstanceError`. Use `builder_from_object` / `new_builder_object`.
- **Reaching past `result.obj`.** `read()` returns a `ReaderResult` — the `Map` is on `.obj`
- **Auto-detecting the writer.** `write()` does *not* infer from the file extension — pass `writer="sbgnml"` (or similar) explicitly.
- **Forgetting to register a layout element in `layout_model_mapping`.** The element will render but won't round-trip through writers, won't be looked up by `map_.get_mapping(...)`, and won't survive serialisation cleanly.

---

## Conventions when generating momapy code

Match the project's own style so your output drops into the codebase cleanly:

- Absolute imports, spelling the full `momapy.x.y` path: `from momapy.sbgn.pd import Macromolecule`. No relative imports, no bare `import momapy.x.y`.
- Re-exports in `__init__.py` use `from momapy.x.y import Name as Name` and list `Name` in `__all__`.
- Rename on collision: `from momapy.meta.shapes import Rectangle as RectangleShape`.
- `kw_only=True, frozen=True` on every dataclass that subclasses a momapy element.
- Trailing underscore for reserved-word attributes: `id_`, `map_`, `type_`.
- Full names for variables — `direction_x`, not `dx`; `length`, not `len`.
- Type hints on everything; modern syntax (`list[T]`, `str | None`, `typing_extensions.Self`).
- Google-style docstrings on public functions and classes.
- Run `ruff format` on any file you write.
