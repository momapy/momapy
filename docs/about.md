# About

## Project

**momapy** is a Python library for working with molecular maps. It supports [SBGN](https://www.sbgn.org) PD and AF maps and [CellDesigner](https://www.celldesigner.org/) maps, providing a unified API for reading, writing, inspecting, styling, and rendering them.

The project is developed at the [University of Luxembourg](https://wwwen.uni.lu/).

## Authors

- **Adrien Rougny** — lead developer (<adrien.rougny@uni.lu>)

## Contributing

Bug reports and feature requests are welcome via the [GitHub issue tracker](https://github.com/adrienrougny/momapy/issues).

To contribute code:

1. Fork the repository on GitHub.
2. Create a feature branch.
3. Make your changes, following the coding conventions in `CLAUDE.md`.
4. Run the test suite: `pytest tests/`
5. Open a pull request against `main`.

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/) (enforced via commitlint). See `CLAUDE.md` for the list of valid types and examples.

## Versioning

momapy loosely follows [semantic versioning](https://semver.org/) as a
guideline, not a strict contract.

Below `1.0` the public API is not stable and may change in a breaking way in any
release.

The public API is what the documentation and each subpackage's `__all__`
describe. Underscore-prefixed names are not public and may change at any time.

## License

This code is distributed under the [GPLv3 license](https://www.gnu.org/licenses/gpl-3.0.html).
