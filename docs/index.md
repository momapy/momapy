# momapy

momapy is a library for working with molecular maps.
It currently supports [SBGN](https://www.sbgn.org) and [CellDesigner](https://www.celldesigner.org/) maps.
Its key feature is its definition of a map, that is formed of two entities: a model, that describes what concepts are represented, and a layout, that describes how these concepts are represented.
This definition is borrowed from [SBML](https://www.sbml.org) and its extensions layout+render, that allow users to add a layout to an SBML model.
momapy aims at extending this definition to SBGN and CellDesigner maps.

Features of momapy include the following:

* support for SBGN PD and AF maps (read/write SBGN-ML with annotations, rendering information, and notes) and CellDesigner (read/write, with annotations and notes)
* read-only support for SBML (model only, no layout)
* decomposition of a map object into:
    * a model object;
    * a layout object;
    * a mapping from layout element objects to model element objects.
* map, model, layout and mapping objects comparison; fast object in set checking
* rendering of maps to images (SVG, PDF, JPEG, PNG, WebP), or onto a Skia canvas for live rendering (via the `skia` renderer)
* support for styling and CSS-like stylesheets (including effects such as shadows)
* automatic geometry and anchors (for arcs, shape borders)
* local positioning (e.g. right of shape, fit set of shapes)
* easy extension with new model and layout element types

## Installation

momapy is available as a Python package and can be installed with pip as follows (Python >=3.10,<=3.14):

`pip install momapy`

### Optional dependencies

momapy includes several optional dependencies for rendering maps with the skia or cairo backends:

**skia**

`pip install momapy[skia]`

This extra depends on skia-python (<https://github.com/kyamagu/skia-python>), which itself depends on the following system packages:

* opengl
* libegl
* fontconfig

**cairo**

`pip install momapy[cairo]`

This extra depends on pygobject (<https://pygobject.gnome.org/guide/sysdeps.html>), which itself depends on the following system packages:

* glib
* libffi

**all**

All optional dependencies can also be installed together:

`pip install momapy[all]`

## Usage

Typical usage of momapy includes reading a map and exploring its model:

```python
from momapy.io import read

map_ = read("my_map.sbgn").obj
for process in map_.model.processes:
    print(process)
```

Or rendering its layout:

```python
from momapy.io import read
from momapy.rendering import render_map

map_ = read("my_map.sbgn").obj
render_map(map_, "my_file.svg")
```

momapy also provides a command-line interface:

```bash
momapy render my_map.sbgn -o output.pdf
momapy export my_map.sbgn -o output.sbgn
```

See [CLI reference](cli.md) for details.

You can also customize the appearance using [CSS-like stylesheets](styling.md):

```python
from momapy.styling import StyleSheet, apply_style_sheet

style_sheet = StyleSheet.from_file("my_style.css")
styled_map = apply_style_sheet(map_, style_sheet)
```

## User manual

A user manual showcasing the main feature of momapy is available here: [User manual](user_manual/main.ipynb).

## Documentation

A complete documentaton for momapy's API is available here: [API reference](api_reference/index.md).
