# API reference

The momapy public API is organized into the following subpackages.

## Core library

- [Core](core.md) — base classes for `Map`, `Model`, `Layout`, `LayoutElement`, `Node`, `Arc`
- [Builder](builder.md) — builder pattern for modifying frozen dataclasses
- [Drawing](drawing.md) — drawing primitives (`Path`, `Rectangle`, `Ellipse`, `Text`, `Group`)
- [Coloring](coloring.md) — colors and named color constants
- [Geometry](geometry.md) — `Point`, `Bbox`, path operations
- [Positioning](positioning.md) — layout positioning helpers
- [Styling](styling.md) — CSS-like stylesheet parsing and application
- [I/O](io.md) — reader/writer registries and entry points

## Rendering

- [Core](rendering/core.md) — renderer registry and render functions
- [Skia](rendering/skia.md) — Skia backend
- [Cairo](rendering/cairo.md) — Cairo backend
- [SVG-native](rendering/svg_native.md) — native SVG backend

## SBGN

- [SBGN](sbgn/sbgn.md) — base SBGN classes
- [PD](sbgn/pd.md) — Process Description glyphs
- [AF](sbgn/af.md) — Activity Flow glyphs
- [SBGN-ML I/O](sbgn/io/sbgnml.md) — SBGN-ML reader/writer

## CellDesigner

- [CellDesigner](celldesigner/celldesigner.md) — CellDesigner model and layout
- [CellDesigner I/O](celldesigner/io/celldesigner.md) — CellDesigner reader/writer

## SBML

- [SBML](sbml/sbml.md) — SBML model classes
- [SBML I/O](sbml/io/sbml.md) — SBML reader
