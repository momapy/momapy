"""Utility classes and functions for momapy.

This module provides general-purpose utilities including bidirectional
mappings, pretty printing for dataclasses, and collection manipulation
helpers.

Mapping family
--------------

Six dict-like classes form a uniform family. Every one is a forward
mapping that also maintains a value->keys ``.inverse`` index, exposed as a
``frozendict[K, frozenset[key]]`` (``K`` is the value for equality
variants, ``id(value)`` for identity variants; buckets are always
``frozenset``). Frozen classes precompute the inverse once and return it
in O(1); mutable classes return a fresh snapshot built on each access, so
it is safe to read while the mapping is mutated.

================================  ========  ==============  ===================
Class                             Mutable?  Inverse keying  Forward cardinality
================================  ========  ==============  ===================
``SurjectionDict``                yes       value (``==``)  one value per key
``IdentitySurjectionDict``        yes       ``id(value)``   one value per key
``FrozenSurjectionDict``          no        value (``==``)  one value per key
``FrozenIdentitySurjectionDict``  no        ``id(value)``   one value per key
``IdentityMultiDict``             yes       ``id(value)``   many values per key
``FrozenIdentityMultiDict``       no        ``id(value)``   many values per key
================================  ========  ==============  ===================

The surjections subclass ``dict`` / ``frozendict`` directly. The
multidicts expose the same read surface -- a ``Mapping[str, frozenset]``
(``[]`` / ``.get`` / ``.keys`` / ``.items`` / ``.values``) plus
``.inverse`` -- with the mutable one adding ``add`` / ``remove`` /
``replace_value``. There is no equality-keyed multidict variant (unused).
"""

import collections.abc
import dataclasses
import os
import typing
import uuid
import types

import colorama
import frozendict
import typing_extensions

from momapy.geometry import Point

__all__ = [
    "FrozenIdentityMultiDict",
    "FrozenIdentitySurjectionDict",
    "FrozenSurjectionDict",
    "IdentityMultiDict",
    "IdentitySurjectionDict",
    "SurjectionDict",
    "check_file_exists",
    "check_parent_dir_exists",
    "display",
    "get_element_from_collection",
    "get_or_return_element_from_collection",
    "make_uuid4_as_str",
    "pretty_print",
    "print_source",
]


def _freeze_inverse(
    inverse: collections.abc.Mapping[typing.Any, collections.abc.Iterable],
) -> frozendict.frozendict:
    """Snapshot a ``{key: set}`` index as ``frozendict[key, frozenset]``.

    Single source of truth for the family's ``.inverse`` shape, so the six
    mapping classes cannot drift apart again.

    Args:
        inverse: A mapping from each inverse key to a ``set`` (or any
            iterable) of forward keys.

    Returns:
        A ``frozendict`` mapping each key to a ``frozenset`` of forward
        keys, decoupled from the source buckets.
    """
    return frozendict.frozendict(
        {key: frozenset(bucket) for key, bucket in inverse.items()}
    )


class SurjectionDict(dict):
    """A mutable, equality-keyed surjection with a value->keys inverse.

    A surjection (onto mapping) where each value maps back to one or more
    keys. The inverse is maintained incrementally as the dict is modified
    and exposed as a ``frozendict[value, frozenset[key]]`` snapshot.

    Note:
        Code adapted from https://stackoverflow.com/a/21894086 by Basj.

    Examples:
        ```python
        d = SurjectionDict({'a': 1, 'b': 1, 'c': 2})
        d.inverse
        d['d'] = 1
        d.inverse
        ```
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the dict and build the value->keys inverse index."""
        super().__init__(*args, **kwargs)
        self._inverse: dict = {}
        for key, value in self.items():
            self._inverse.setdefault(value, set()).add(key)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        """Set a key to a value, updating the inverse index."""
        if key in self:
            old_value = self[key]
            self._inverse[old_value].discard(key)
            if not self._inverse[old_value]:
                del self._inverse[old_value]
        super().__setitem__(key, value)
        self._inverse.setdefault(value, set()).add(key)

    def __delitem__(self, key: typing.Any) -> None:
        """Delete a key, updating the inverse index."""
        value = self[key]  # throws expected KeyError if key not in self
        super().__delitem__(key)
        # we know key was in self, hence value is expected to be in self.inverse
        self._inverse[value].discard(key)
        if not self._inverse[value]:
            del self._inverse[value]

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. This is a
        fresh **snapshot** built on each access from the internally
        maintained index, so it is safe to read while the mapping is
        mutated.

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return _freeze_inverse(self._inverse)


class IdentitySurjectionDict(dict):
    """A mutable dict with an identity-keyed value->keys inverse.

    Like ``SurjectionDict``, but the inverse is keyed by ``id(value)``
    instead of by value equality. This allows looking up all keys whose
    value is a specific object even when several distinct objects compare
    equal.

    The forward dict uses normal equality for key lookup. The inverse is
    safe from ``id()`` address reuse because the forward dict holds a
    reference to each value, keeping it alive.

    Examples:
        ```python
        d = IdentitySurjectionDict()
        a, b = object(), object()
        d['x'] = a
        d['y'] = a
        d['z'] = b
        d.inverse[id(a)]  # frozenset({'x', 'y'})
        d.inverse[id(b)]  # frozenset({'z'})
        ```
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the dict and build the identity-keyed inverse index."""
        super().__init__(*args, **kwargs)
        self._identity_inverse: dict[int, set] = {}
        for key, value in self.items():
            self._identity_inverse.setdefault(id(value), set()).add(key)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        """Set a key to a value, updating the identity-keyed inverse index."""
        if key in self:
            old_value = self[key]
            old_identity = id(old_value)
            if old_identity in self._identity_inverse:
                self._identity_inverse[old_identity].discard(key)
                if not self._identity_inverse[old_identity]:
                    del self._identity_inverse[old_identity]
        super().__setitem__(key, value)
        self._identity_inverse.setdefault(id(value), set()).add(key)

    def __delitem__(self, key: typing.Any) -> None:
        """Delete a key, updating the identity-keyed inverse index."""
        value = self[key]
        value_identity = id(value)
        super().__delitem__(key)
        if value_identity in self._identity_inverse:
            self._identity_inverse[value_identity].discard(key)
            if not self._identity_inverse[value_identity]:
                del self._identity_inverse[value_identity]

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. This is a
        fresh **snapshot** built on each access from the internally
        maintained index, so it is safe to read while the mapping is
        mutated.

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return _freeze_inverse(self._identity_inverse)


class IdentityMultiDict(collections.abc.Mapping):
    """A mutable, identity-keyed multidict for n-to-m ``str`` -> object maps.

    Forward: ``dict[str, set[object]]`` -- a key may name several values.
    Inverse: ``frozendict[int, frozenset[str]]`` keyed by ``id(value)``.

    The class is a read-only ``Mapping[str, frozenset]`` on the forward
    side (``[]`` / ``.get`` / ``.values`` yield ``frozenset`` buckets,
    ``.keys`` yields the ``str`` keys, ``.items`` yields
    ``(key, frozenset)`` pairs) plus the ``add`` / ``remove`` /
    ``replace_value`` mutators and the ``.inverse`` index.

    It deliberately does **not** subclass ``dict``, so an accidental
    ``d[key] = value`` write (which would replace the whole bucket with a
    single object) raises instead of silently corrupting state.

    The forward dict holds references to every value, so the
    identity-keyed inverse is safe from ``id()`` address reuse for the
    lifetime of the multidict.

    Args:
        mapping: An optional initial ``str`` -> ``Iterable[object]``
            mapping to seed the multidict from. Defaults to ``None``
            (empty).

    Examples:
        ```python
        a, b = object(), object()
        d = IdentityMultiDict({'x': [a, b]})
        d['x']            # frozenset({a, b})
        d.add('y', a)
        d.inverse[id(a)]  # frozenset({'x', 'y'})
        ```
    """

    def __init__(
        self,
        mapping: collections.abc.Mapping[str, collections.abc.Iterable] | None = None,
    ) -> None:
        """Initialize the multidict, optionally seeding it from a mapping."""
        self._forward: dict[str, set] = {}
        self._inverse: dict[int, set[str]] = {}
        if mapping is not None:
            for key, values in mapping.items():
                for value in values:
                    self.add(key, value)

    def add(self, key: str, value: object) -> None:
        """Register ``value`` under ``key``.  Idempotent on identity."""
        bucket = self._forward.setdefault(key, set())
        for existing in bucket:
            if existing is value:
                return
        bucket.add(value)
        self._inverse.setdefault(id(value), set()).add(key)

    def remove(self, key: str, value: object) -> None:
        """Drop ``value`` from ``key``.  Raises ``KeyError`` if absent."""
        bucket = self._forward.get(key)
        if bucket is None:
            raise KeyError(key)
        target = None
        for existing in bucket:
            if existing is value:
                target = existing
                break
        if target is None:
            raise KeyError(key)
        bucket.discard(target)
        if not bucket:
            del self._forward[key]
        keys_for_value = self._inverse.get(id(value))
        if keys_for_value is not None:
            keys_for_value.discard(key)
            if not keys_for_value:
                del self._inverse[id(value)]

    def replace_value(self, old: object, new: object) -> None:
        """Replace ``old`` with ``new`` everywhere it appears (by identity).

        Drives the dedup remap path: every key whose set contains
        ``old`` (compared by identity) drops ``old`` and adds ``new``.
        """
        keys = self._inverse.pop(id(old), None)
        if not keys:
            return
        for key in keys:
            bucket = self._forward.get(key)
            if bucket is None:
                continue
            target = None
            for existing in bucket:
                if existing is old:
                    target = existing
                    break
            if target is not None:
                bucket.discard(target)
            already_present = False
            for existing in bucket:
                if existing is new:
                    already_present = True
                    break
            if not already_present:
                bucket.add(new)
            self._inverse.setdefault(id(new), set()).add(key)

    def __getitem__(self, key: str) -> frozenset:
        """Return the ``frozenset`` of values registered under ``key``.

        Raises:
            KeyError: If ``key`` is not present.
        """
        return frozenset(self._forward[key])

    def __iter__(self) -> collections.abc.Iterator[str]:
        """Iterate over the keys of the multidict."""
        return iter(self._forward)

    def __len__(self) -> int:
        """Return the number of keys in the multidict."""
        return len(self._forward)

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. This is a
        fresh **snapshot** built on each access from the internally
        maintained index, so it is safe to read while the mapping is
        mutated.

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return _freeze_inverse(self._inverse)


class FrozenIdentityMultiDict(frozendict.frozendict):
    """An immutable, identity-keyed multidict.

    Forward: ``frozendict[str, frozenset[object]]`` -- already a read-only
    ``Mapping[str, frozenset]`` (``[]`` / ``.get`` / ``.items`` /
    ``.values`` yield ``frozenset`` buckets). Inverse:
    ``frozendict[int, frozenset[str]]`` keyed by ``id(value)``, precomputed
    once at construction.

    The forward dict holds references to every value, so the
    identity-keyed inverse is safe from ``id()`` address reuse for the
    lifetime of the multidict.

    Args:
        mapping: An optional ``str`` -> ``Iterable[object]`` mapping to
            build from. Defaults to ``None`` (empty).

    Examples:
        ```python
        a, b = object(), object()
        d = FrozenIdentityMultiDict({'x': [a, b], 'y': [a]})
        d['x']            # frozenset({a, b})
        d.inverse[id(a)]  # frozenset({'x', 'y'})
        ```
    """

    def __new__(
        cls,
        mapping: collections.abc.Mapping[str, collections.abc.Iterable] | None = None,
    ) -> typing_extensions.Self:
        """Create the frozen forward dict with ``frozenset`` buckets."""
        frozen_forward: dict[str, frozenset] = {}
        if mapping is not None:
            for key, values in mapping.items():
                frozen_forward[key] = frozenset(values)
        return super().__new__(cls, frozen_forward)

    def __init__(
        self,
        mapping: collections.abc.Mapping[str, collections.abc.Iterable] | None = None,
    ) -> None:
        """Precompute the identity-keyed inverse index from the forward dict."""
        inverse: dict[int, set[str]] = {}
        for key, bucket in self.items():
            for value in bucket:
                inverse.setdefault(id(value), set()).add(key)
        object.__setattr__(self, "_identity_inverse", _freeze_inverse(inverse))

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. It is
        **precomputed once at construction** and returned in O(1).

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return self._identity_inverse


class FrozenSurjectionDict(frozendict.frozendict):
    """An immutable, equality-keyed surjection with a value->keys inverse.

    A frozen dict that precomputes its inverse mapping from values to keys
    once at construction. The inverse is exposed as a
    ``frozendict[value, frozenset[key]]`` and cannot be modified.

    Examples:
        ```python
        d = FrozenSurjectionDict({'a': 1, 'b': 1, 'c': 2})
        d.inverse
        ```
    """

    def __init__(self, *args, **kwargs) -> None:
        """Precompute the value->keys inverse index from the forward dict."""
        inverse: dict = {}
        for key, value in self.items():
            inverse.setdefault(value, set()).add(key)
        object.__setattr__(self, "_inverse", _freeze_inverse(inverse))

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. It is
        **precomputed once at construction** and returned in O(1).

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return self._inverse


class FrozenIdentitySurjectionDict(frozendict.frozendict):
    """An immutable dict with an identity-keyed value->keys inverse.

    A frozen dict whose inverse is keyed by ``id(value)`` rather than by
    value equality, precomputed once at construction. The forward dict
    keeps normal ``frozendict`` (``==`` on keys) semantics; only the
    value-side index is identity-keyed.

    The inverse is safe from ``id()`` address reuse because the forward
    dict holds a reference to each value, keeping it alive for the lifetime
    of the dict.

    Examples:
        ```python
        a, b = object(), object()
        d = FrozenIdentitySurjectionDict({'x': a, 'y': a, 'z': b})
        d.inverse[id(a)]  # frozenset({'x', 'y'})
        d.inverse[id(b)]  # frozenset({'z'})
        ```
    """

    def __init__(self, *args, **kwargs) -> None:
        """Precompute the identity-keyed inverse index from the forward dict."""
        inverse: dict[int, set] = {}
        for key, value in self.items():
            inverse.setdefault(id(value), set()).add(key)
        object.__setattr__(self, "_identity_inverse", _freeze_inverse(inverse))

    @property
    def inverse(self) -> frozendict.frozendict:
        """Return the value->keys inverse as a ``frozendict[K, frozenset]``.

        ``K`` is the value (equality variants) or ``id(value)`` (identity
        variants); each bucket is a ``frozenset`` of forward keys. It is
        **precomputed once at construction** and returned in O(1).

        Returns:
            A ``frozendict`` mapping each value (or ``id(value)``) to the
            ``frozenset`` of keys that map to it.
        """
        return self._identity_inverse


def pretty_print(
    obj: typing.Any,
    max_depth: int | None = 0,
    exclude_cls: list[type] | None = None,
    _depth: int = 0,
    _indent: int = 0,
) -> None:
    """Pretty print a dataclass or iterable object with colors.

    Recursively prints the structure of dataclasses and iterables with
    type information and color coding for better readability.

    Args:
        obj: The object to print (dataclass, iterable, or other).
        max_depth: Maximum recursion depth. `0` (the default) prints the object
            and its direct fields only; higher values recurse that many levels
            deeper. `None` means unlimited (print the whole structure).
        exclude_cls: List of classes to exclude from recursive printing.
        _depth: Internal parameter for tracking current depth.
        _indent: Internal parameter for tracking current indentation.

    Examples:
        ```python
        import dataclasses
        @dataclasses.dataclass
        class Point:
            x: float
            y: float

        p = Point(x=1.0, y=2.0)
        pretty_print(p)
        ```
    """

    def _print_with_indent(s: str, indent: int) -> None:
        dark = f"{colorama.Style.DIM}│{colorama.Style.RESET_ALL} "
        light = f"{colorama.Fore.WHITE}│{colorama.Style.RESET_ALL} "
        guides = "".join(dark if i % 2 == 0 else light for i in range(indent))
        print(f"{guides}{s}")

    def _get_value_string(attr_value: typing.Any, max_len: int = 30) -> str:
        s = str(attr_value)
        if len(s) > max_len:
            s = f"{s[:max_len]}..."
        return s

    if max_depth is not None and _depth > max_depth:
        return
    if exclude_cls is None:
        exclude_cls = []
    obj_typing = type(obj)
    if issubclass(obj_typing, tuple(exclude_cls)):
        return
    obj_value_string = _get_value_string(obj)
    obj_string = f"{colorama.Fore.GREEN}{obj_typing}{colorama.Fore.RED}: {obj_value_string}{colorama.Style.RESET_ALL}"
    _print_with_indent(obj_string, _indent)
    if dataclasses.is_dataclass(type(obj)):
        for field in dataclasses.fields(obj):
            attr_name = field.name
            if not attr_name.startswith("_"):
                attr_value = getattr(obj, attr_name)
                attr_typing = field.type
                attr_value_string = _get_value_string(attr_value)
                attr_string = f"{colorama.Fore.BLUE}* {attr_name}{colorama.Fore.MAGENTA}: {attr_typing} = {colorama.Fore.RED}{attr_value_string}{colorama.Style.RESET_ALL}"
                _print_with_indent(attr_string, _indent + 1)
                if (
                    not isinstance(attr_value, (str, float, int, bool, types.NoneType))
                    and attr_value
                ):
                    pretty_print(
                        attr_value,
                        max_depth=max_depth,
                        exclude_cls=exclude_cls,
                        _depth=_depth + 1,
                        _indent=_indent + 2,
                    )
    if isinstance(obj, collections.abc.Iterable) and not isinstance(
        obj, (str, bytes, bytearray, Point)
    ):
        for i, elem_value in enumerate(obj):
            elem_typing = type(elem_value)
            elem_value_string = _get_value_string(elem_value)
            elem_string = f"{colorama.Fore.BLUE}- {i}{colorama.Fore.MAGENTA}: {elem_typing} = {colorama.Fore.RED}{elem_value_string}{colorama.Style.RESET_ALL}"
            _print_with_indent(elem_string, _indent + 1)
            pretty_print(
                elem_value,
                max_depth=max_depth,
                exclude_cls=exclude_cls,
                _depth=_depth + 1,
                _indent=_indent + 2,
            )


_T = typing.TypeVar("_T")


def get_element_from_collection(
    element: _T, collection: collections.abc.Iterable[_T]
) -> _T | None:
    """Find and return an element from a collection using equality.

    Matching is by equality (``==``), not identity: the returned element
    is the one already in ``collection`` that compares equal to
    ``element``, which may be a distinct object.

    Args:
        element: The element to search for.
        collection: An iterable collection to search in.

    Returns:
        The existing element from the collection if found, None otherwise.

    Examples:
        ```python
        items = [1, 2, 3]
        get_element_from_collection(2, items)
        get_element_from_collection(4, items) is None
        ```
    """
    for e in collection:
        if e == element:
            return e
    return None


def get_or_return_element_from_collection(
    element: _T, collection: collections.abc.Iterable[_T]
) -> _T:
    """Get existing element from collection or return the input element.

    Matching is by equality (``==``), not identity.

    Args:
        element: The element to search for.
        collection: An iterable collection to search in.

    Returns:
        The existing element from the collection if found, otherwise
        the input element.

    Examples:
        ```python
        items = [1, 2, 3]
        get_or_return_element_from_collection(2, items)
        get_or_return_element_from_collection(4, items)
        ```
    """
    existing_element = get_element_from_collection(element, collection)
    if existing_element is not None:
        return existing_element
    return element


def make_uuid4_as_str() -> str:
    """Generate a UUID4 as a string.

    Returns:
        A string representation of a random UUID (version 4).

    Examples:
        ```python
        uuid_str = make_uuid4_as_str()
        isinstance(uuid_str, str)
        len(uuid_str)  # Standard UUID string length
        ```
    """
    return str(uuid.uuid4())


def check_file_exists(file_path: str | os.PathLike) -> None:
    """Raise a clear `FileNotFoundError` if `file_path` does not exist.

    Centralizes the input-side existence check so every read path reports a
    missing file the same way, naming the path, instead of the format-specific
    `OSError` / `ValueError` each parser would otherwise raise. Mirrors
    `check_parent_dir_exists`, which guards the output side.

    Args:
        file_path: Path of the file to check.

    Raises:
        FileNotFoundError: If no file exists at `file_path`.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"no such file: '{file_path}'")


def check_parent_dir_exists(file_path: str | os.PathLike) -> None:
    """Raise `FileNotFoundError` if the parent directory of `file_path` is missing.

    Guards against C-backed writers (notably skia's `FILEWStream`) that
    segfault when handed a path whose parent directory does not exist.

    Args:
        file_path: Output file path. The file itself does not need to exist.

    Raises:
        FileNotFoundError: If the parent directory does not exist.
    """
    parent_dir = os.path.dirname(os.path.abspath(os.fspath(file_path)))
    if not os.path.isdir(parent_dir):
        raise FileNotFoundError(f"parent directory does not exist: {parent_dir}")


def display(
    obj: typing.Any,
    markers: typing.Any = None,
    xsep: float = 20.0,
    ysep: float = 20.0,
    scale: float = 1.0,
    style_sheet: typing.Any = None,
) -> None:
    """Render maps, layout elements, or files as an inline SVG in a notebook.

    Renders one or more objects to a single SVG and displays it using
    IPython, fitting all objects into a common bounding box with a margin.

    This is a notebook helper: it requires IPython (install with
    `pip install momapy[notebook]`). It is imported lazily so momapy keeps
    no hard dependency on IPython/Jupyter.

    Args:
        obj: A single object or an iterable of objects to display. Each object
            may be a `momapy.core.Map`, a `momapy.core.LayoutElement`, or a
            path (`str`) to a map file to read.
        markers: An optional `momapy.geometry.Point` or iterable of points to
            draw as red cross markers. Defaults to `None`.
        xsep: Horizontal margin around the rendered content. Defaults to `20.0`.
        ysep: Vertical margin around the rendered content. Defaults to `20.0`.
        scale: Scale factor applied to the rendered SVG. Defaults to `1.0`.
        style_sheet: An optional `momapy.styling.StyleSheet` (or path to a CSS
            file) applied to the layout elements before rendering. Defaults to
            `None`.

    Raises:
        ImportError: If IPython is not installed.
        ValueError: If an object has an unsupported type.
    """
    import collections.abc
    import functools
    import operator

    try:
        import IPython.display
    except ImportError as error:
        raise ImportError(
            "display() requires IPython. Install it with "
            "'pip install momapy[notebook]'."
        ) from error

    import momapy.builder
    import momapy.coloring
    import momapy.core
    import momapy.drawing
    import momapy.geometry
    import momapy.io.core
    import momapy.meta.nodes
    import momapy.positioning
    import momapy.rendering.svg_native
    import momapy.styling

    if markers is None:
        markers = []
    if isinstance(style_sheet, str):
        style_sheet = momapy.styling.StyleSheet.from_file(style_sheet)
    if not isinstance(obj, collections.abc.Iterable) or isinstance(
        obj, (str, bytes, bytearray)
    ):
        obj = [obj]
    layout_elements = []
    for element in obj:
        if isinstance(element, str):
            layout_element = momapy.io.core.read(element, return_type="layout").obj
        elif isinstance(element, momapy.core.Map):
            layout_element = element.layout
        elif isinstance(element, momapy.core.LayoutElement):
            layout_element = element
        else:
            raise ValueError(f"unsupported type {type(element)}")
        layout_elements.append(layout_element)
    bboxes = []
    if style_sheet is not None:
        layout_elements = [
            momapy.styling.apply_style_sheet(layout_element, style_sheet)
            for layout_element in layout_elements
        ]
    for layout_element in layout_elements:
        bbox = layout_element.bbox()
        if (
            layout_element.group_transform is not None
            and layout_element.group_transform != momapy.drawing.NoneValue
        ):
            total_transformation = functools.reduce(
                operator.mul, layout_element.group_transform
            )
            bbox = momapy.positioning.fit(
                [
                    bbox.north_west().transformed(total_transformation),
                    bbox.north_east().transformed(total_transformation),
                    bbox.south_west().transformed(total_transformation),
                    bbox.south_east().transformed(total_transformation),
                ]
            )
        bboxes.append(bbox)
    bbox = momapy.positioning.fit(bboxes)
    min_x = bbox.x - bbox.width / 2 - xsep
    min_y = bbox.y - bbox.height / 2 - ysep
    max_x = bbox.x + bbox.width / 2 - min_x + xsep
    max_y = bbox.y + bbox.height / 2 - min_y + ysep
    translation = momapy.geometry.Translation(-min_x, -min_y)
    final_layout_elements = []
    for layout_element in layout_elements:
        layout_element_builder = momapy.builder.builder_from_object(layout_element)
        if layout_element.group_transform is None:
            layout_element_builder.group_transform = []
        layout_element_builder.group_transform.insert(0, translation)
        final_layout_elements.append(
            momapy.builder.object_from_builder(layout_element_builder)
        )
    cp_builder_cls = momapy.builder.get_or_make_builder_cls(
        momapy.meta.nodes.CrossPoint
    )
    if isinstance(markers, momapy.geometry.Point):
        markers = [markers]
    for marker in markers:
        position = marker
        cp_builder = cp_builder_cls(
            width=12.0,
            height=12.0,
            stroke_width=1.5,
            stroke=momapy.coloring.red,
            position=position,
        )
        final_layout_elements.append(momapy.builder.object_from_builder(cp_builder))
    width = max_x
    height = max_y
    renderer = momapy.rendering.svg_native.SVGNativeRenderer(
        svg=momapy.rendering.svg_native.SVGElement(
            name="svg",
            attributes={
                "xmlns": "http://www.w3.org/2000/svg",
                "viewBox": f"0 0 {width} {height}",
                "width": width * scale,
                "height": height * scale,
            },
        )
    )
    renderer.begin_session()
    for layout_element in final_layout_elements:
        renderer.render_layout_element(layout_element)
    renderer.end_session()
    svg_string = str(renderer.svg)
    IPython.display.display(IPython.display.SVG(data=svg_string))


def print_source(obj: typing.Any) -> None:
    """Display the syntax-highlighted source of an object in a notebook.

    This is a notebook helper: it requires IPython and pygments (install with
    `pip install momapy[notebook]`). Both are imported lazily so momapy keeps
    no hard dependency on them.

    Args:
        obj: Any object whose source can be retrieved with `inspect.getsource`
            (e.g. a function, class, or module).

    Raises:
        ImportError: If IPython or pygments is not installed.
    """
    import inspect

    try:
        import IPython.display
        import pygments
        import pygments.formatters
        import pygments.lexers
    except ImportError as error:
        raise ImportError(
            "print_source() requires IPython and pygments. Install them with "
            "'pip install momapy[notebook]'."
        ) from error

    code = inspect.getsource(obj)
    formatter = pygments.formatters.HtmlFormatter(full=True, style="friendly")
    IPython.display.display(
        IPython.display.HTML(
            pygments.highlight(code, pygments.lexers.PythonLexer(), formatter)
        )
    )
