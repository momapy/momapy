# Styling Guide

## Overview

momapy supports CSS-like stylesheets for customizing the appearance of molecular maps. Stylesheets allow you to control colors, fonts, strokes, and other visual properties of map elements without modifying the underlying map data.

Stylesheets are applied during rendering and can be used via the command line (`-s` flag) or the Python API.

## Basic Syntax

Stylesheets follow a CSS-like syntax with rules, selectors, and declaration blocks:

```css
MacromoleculeLayout {
    fill: royalblue;
    stroke: white;
    stroke-width: 2.0;
}
```

A rule consists of:

- **Selector**: The element(s) to style (e.g., `MacromoleculeLayout`)
- **Declaration block**: Properties and values inside `{ }`
- **Properties**: Visual attributes (e.g., `fill`, `stroke-width`)
- **Values**: The setting for each property (e.g., `royalblue`, `2.0`)

## Selectors

### Type Selector

Matches elements by their exact class name:

```css
MacromoleculeLayout {
    fill: lightblue;
}
```

This matches only `MacromoleculeLayout` elements, not subclasses.

### Class Selector

Matches a class and all its subclasses (prefix with dot):

```css
.Shape {
    stroke-width: 2.0;
}
```

This matches `Shape` and any subclass like `Rectangle`, `Ellipse`, etc.

### ID Selector

Matches an element by its `id_` attribute:

```css
#my_protein {
    fill: red;
}
```

### Child Selector

Matches direct children only (use `>`):

```css
StateVariableLayout > TextLayout {
    font-size: 8.0;
}
```

### Descendant Selector

Matches elements at any depth:

```css
GroupLayout TextLayout {
    fill: white;
}
```

### Or Selector

Matches any of multiple selectors (comma-separated):

```css
MacromoleculeLayout, SimpleChemicalLayout {
    stroke: black;
}
```

## Value Types

### Numbers

- **Floats**: `2.0`, `10.5`
- **Integers**: `42`

### Strings

Quoted strings for font names and other text values:

```css
font-family: "DejaVu Sans";
```

### Colors

Colors are given as names (any color defined in `momapy.coloring`) or as hex values, with 6 digits (`#rrggbb`) or 8 digits (`#rrggbbaa`, where `aa` is the alpha):

```css
fill: royalblue;
stroke: #8a6421;
fill: #d4a34080;
```

### Special Values

- **`none`**: No value (e.g., `fill: none;`)
- **`unset`**: Reset to default/inherited value

### Lists

Comma-separated lists:

```css
stroke-dasharray: 5, 5;
```

### Filters

Drop shadow effect:

```css
filter: drop-shadow(2.0, 2.0, 3.0, 0.5, gray);
```

Parameters: `drop-shadow(dx, dy, std_dev, opacity, color)`

### Gradients

`fill` and `stroke` accept gradients, written as in CSS:

```css
fill: linear-gradient(90deg, white 0%, lightgray 100%);
fill: repeating-linear-gradient(135deg, #bf8f33 0 3, #d4a340 3 13);
fill: radial-gradient(white, lightblue);
```

- `linear-gradient(angle, color stops)`: the angle is in `deg` and is optional (defaults to `180deg`, i.e. from top to bottom).
- `repeating-linear-gradient(angle, color stops)`: same, the part between the first and last stops is repeated.
- `radial-gradient(color stops)`: an ellipse centered in the element, going through its corners. Shape, size and position arguments are not supported.

A color stop is a color followed by zero, one or two positions (`#bf8f33 0 3` is two stops with the same color, which gives a sharp edge). Positions are:

- **percentages**: the gradient is laid out on the bounding box of each element. Missing positions are spread evenly, as in CSS. On a non-square element the angle follows the shape of the box (`45deg` goes from corner to corner);
- **plain numbers** (only in `repeating-linear-gradient`): lengths in map coordinates. The gradient is then laid out on the whole map, so stripes keep the same spacing and line up across elements.

Gradients are converted to `momapy.drawing.LinearGradient` and `momapy.drawing.RadialGradient` objects, which follow SVG's `linearGradient` and `radialGradient` and can also be built directly in Python.

With the Skia and Cairo renderers, a gradient laid out on the bounding box (percentages) is not painted on text, as text has no bounding box in momapy.

## Common Properties

### Drawing Properties

| Property | Description | Example |
|----------|-------------|---------|
| `fill` | Fill color or gradient | `fill: royalblue;`, `fill: radial-gradient(white, lightblue);` |
| `stroke` | Stroke/border color or gradient | `stroke: black;` |
| `stroke-width` | Stroke thickness | `stroke-width: 2.0;` |
| `stroke-dasharray` | Dash pattern | `stroke-dasharray: 5, 5;` |
| `stroke-linejoin` | Shape of corners: `miter` (default), `round`, `bevel` | `stroke-linejoin: round;` |
| `stroke-linecap` | Shape of line ends: `butt` (default), `round`, `square` | `stroke-linecap: round;` |
| `filter` | Visual effects | `filter: drop-shadow(2.0, 2.0, 3.0, 0.5, gray);` |

Like the other stroke properties, `stroke-linejoin` and `stroke-linecap` also exist with prefixes (`path-stroke-linejoin`, `arrowhead-stroke-linejoin`, ...).

A shape filled and stroked with the same color and `stroke-linejoin: round` gets its corners rounded by half the stroke width. The stroke also makes the shape bigger by half the stroke width on each side:

```css
GenericProcessLayout {
    width: 14.0;
    height: 14.0;
    fill: #4c4c4c;
    stroke: #4c4c4c;
    stroke-width: 6.0;
    stroke-linejoin: round;
}
```

### Text Properties

| Property | Description | Example |
|----------|-------------|---------|
| `font-family` | Font name | `font-family: "DejaVu Sans";` |
| `font-size` | Font size | `font-size: 14.0;` |
| `fill` | Text color | `fill: white;` |
| `font-style` | Font style | `font-style: "italic";` |
| `font-weight` | Font weight (numeric) | `font-weight: 700;` |

### Shape Properties

| Property | Description | Example |
|----------|-------------|---------|
| `width` | Element width | `width: 100.0;` |
| `height` | Element height | `height: 60.0;` |
| `rounded-corners` | Corner radius | `rounded-corners: 5.0;` |
| `cut-corners` | Cut corner size | `cut-corners: 10.0;` |

**Note**: Some node and arc classes have specific attributes that define their shape geometry. For example, `angle` and `offset` are parameters used by certain shape types (like hexagons with specific corner angles) and are not rotation angles or position offsets. Refer to the specific node or arc class implementation to see which shape-specific properties are available.

### Connector Properties

| Property | Description | Example |
|----------|-------------|---------|
| `left-connector-length` | Left connector size | `left-connector-length: 10.0;` |
| `left-connector-stroke` | Left connector color | `left-connector-stroke: gray;` |
| `right-connector-length` | Right connector size | `right-connector-length: 10.0;` |
| `right-connector-stroke` | Right connector color | `right-connector-stroke: gray;` |

### Arrowhead Properties

| Property | Description | Example |
|----------|-------------|---------|
| `arrowhead-fill` | Arrowhead fill color | `arrowhead-fill: black;` |
| `arrowhead-stroke` | Arrowhead stroke color | `arrowhead-stroke: gray;` |
| `arrowhead-stroke-width` | Arrowhead stroke width | `arrowhead-stroke-width: 1.5;` |

Note: Not all arcs have arrowheads. For example, `ConsumptionLayout` is rendered as a simple line (polyline) without an arrowhead.

### Path Properties

| Property | Description | Example |
|----------|-------------|---------|
| `path-stroke` | Path color | `path-stroke: gray;` |
| `path-stroke-width` | Path thickness | `path-stroke-width: 1.5;` |
| `end-shorten` | Shorten path at end | `end-shorten: 1.0;` |

### Group Properties

Prefix with `group-` to style child elements collectively:

```css
MacromoleculeLayout {
    group-stroke: black;
    group-fill: lightgray;
}
```

## Imports

Stylesheets can import other stylesheets using the `@import` rule:

```css
@import "base.css";
@import "overrides.css";

MacromoleculeLayout {
    fill: blue;
}
```

Imports are processed in order, with later rules overriding earlier ones.

## Usage

### Command Line

Apply a stylesheet when rendering:

```bash
momapy render map.sbgn -o output.svg -s my_style.css
```

Apply a stylesheet when exporting:

```bash
momapy export map.sbgn -o output.sbgn -s my_style.css
```

Apply multiple stylesheets (applied in order):

```bash
momapy render map.sbgn -o output.svg -s base.css -s overrides.css
```

### Python API

Load from file:

```python
from momapy.styling import StyleSheet

style_sheet = StyleSheet.from_file("my_style.css")
```

Load from string:

```python
style_sheet = StyleSheet.from_string("""
MacromoleculeLayout {
    fill: blue;
}
""")
```

**Note:** Both `from_file()` and `from_string()` raise a `ParseException` if the CSS cannot be parsed. Selectors that do not match any element are silently ignored, but a property name that is not a field of a matched element raises `AttributeError` when the stylesheet is applied. Pass `strict=False` to `apply_style_sheet()` to skip such unknown properties instead.

Bake the styles into the map. `apply_style_sheet` returns a new, styled copy
(the map is frozen), so capture the return value:

```python
from momapy.styling import apply_style_sheet

styled_map = apply_style_sheet(map_, style_sheet)
```

Or apply during rendering, leaving the map unchanged:

```python
from momapy.rendering import render_map

render_map(map_, "output.svg", style_sheet=style_sheet)
```

## Complete Example

Here's a custom stylesheet for some layout elements of SBGN PD (note that the
grammar has no comment syntax, so the rules speak for themselves):

```css
@import "my_base_stylesheet.css";

StateVariableLayout {
    fill: royalblue;
    stroke: white;
    stroke-width: 1.5;
}

StateVariableLayout > TextLayout {
    font-size: 7.0;
    fill: white;
}

MacromoleculeLayout {
    fill: royalblue;
    stroke: white;
    stroke-width: 2.0;
}

MacromoleculeLayout > TextLayout {
    font-size: 14.0;
    fill: white;
}

SimpleChemicalLayout {
    fill: gold;
    stroke: white;
    stroke-width: 2.0;
}

SimpleChemicalLayout > TextLayout {
    font-size: 10.0;
    fill: black;
}

GenericProcessLayout {
    fill: gray;
    stroke: white;
    right-connector-stroke: gray;
    right-connector-length: 10.0;
    left-connector-stroke: gray;
    left-connector-length: 10.0;
}

ConsumptionLayout {
    path-stroke: gray;
    path-stroke-width: 1.5;
    end-shorten: 1.0;
}

ProductionLayout {
    arrowhead-fill: gray;
    arrowhead-stroke: gray;
    path-stroke: gray;
    path-stroke-width: 1.5;
    end-shorten: 1.0;
}
```
