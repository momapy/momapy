"""Layout-model mapping classes."""

import typing
import typing_extensions

from momapy.builder import Builder
from momapy.builder import builder_from_object
from momapy.builder import object_from_builder
from momapy.builder import register_builder_cls
from momapy.core.elements import LayoutElement
from momapy.core.elements import MapElement
from momapy.core.elements import ModelElement
from momapy.utils import FrozenIdentitySurjectionDict
from momapy.utils import FrozenSurjectionDict
from momapy.utils import IdentitySurjectionDict
from momapy.utils import SurjectionDict


class LayoutModelMapping(FrozenIdentitySurjectionDict):
    """Mapping between model elements and layout elements.

    A [Map][momapy.core.Map] can draw the same model element several
    times, so the relation between layouts and model elements is a
    many-to-one mapping whose keys are layout elements and whose values
    are model elements. Two kinds of keys are used:

    - **Singleton key**: a single [LayoutElement][momapy.core.LayoutElement]
      that represents a model element on its own.
    - **Frozenset key**: a ``frozenset`` of several layout elements
      that *jointly* represent one model element. Used whenever a
      model concept is drawn as a cluster of shapes.

    When the key is a frozenset, it is useful to designate one of the
    layouts as the **representative**: the element that stands for the cluster
    on its own. The representative is typically the "central" layout (e.g., the
    process glyph for a process). Representatives are registered through the ``representative`` argument of
    [add_mapping][momapy.core.mapping.LayoutModelMappingBuilder.add_mapping]. Once registered,
    [get_mapping][momapy.core.mapping.LayoutModelMapping.get_mapping] resolves the representative back to the model element
    stored under the frozenset key, and `representative_to_key` gives the
    frozenset key of a representative.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the mapping and its frozen representative index."""
        super().__init__(*args, **kwargs)
        object.__setattr__(
            self,
            "_representative_to_key",
            FrozenSurjectionDict(),
        )

    @property
    def representative_to_key(self) -> "FrozenSurjectionDict":
        """Return the read-only table mapping representatives to frozenset keys."""
        return self._representative_to_key

    def get_mapping(
        self,
        map_element: "MapElement",
    ) -> "ModelElement | list[LayoutElement | frozenset[LayoutElement]] | None":
        """Return the model element or layout elements mapped to `map_element`.

        Lookup order:
        1. Direct key: `map_element` is a singleton or frozenset key in the
           mapping; returns the associated model element directly.
        2. Inverse: `map_element` is a model element; returns the list of
           layout elements (or frozenset keys) whose stored model value
           **is** ``map_element`` by object identity. Two content-equal
           but id-distinct model instances are *not* aliased.
        3. Representative fallback: `map_element` was registered as the representative of a
           frozenset key via the ``representative`` argument of ``add_mapping``;
           returns the model element stored under that frozenset key.

        Returns ``None`` when no match is found.
        """
        if map_element in self:
            return self[map_element]
        result = self.inverse.get(id(map_element))
        if result:
            return list(result)
        key = self._representative_to_key.get(map_element)
        if key is not None:
            return self[key]
        return None

    def get_child_layout_elements(
        self,
        child_model_element: "ModelElement",
        parent_model_element: "ModelElement",
    ) -> "list[LayoutElement]":
        """Return the layout elements representing ``child_model_element`` under ``parent_model_element``.

        Computes the intersection of two sets:

        - ``S1``: layouts that belong under ``parent_model_element`` — the
          children of each singleton layout mapped to the parent, plus the
          members of each frozenset key mapped to the parent and the
          children of its representatives.
        - ``S2``: layouts that represent ``child_model_element`` — each
          singleton layout mapped to the child, plus the representatives of each
          frozenset key mapped to the child.

        The inverse is identity-keyed, so two content-equal but id-distinct
        model instances are not aliased: layouts under one parent do not
        cross-pollute the result for the sibling instance.
        """
        child_s2 = set()
        for key in self.inverse.get(id(child_model_element), ()):
            if isinstance(key, frozenset):
                for representative in self._representative_to_key.inverse.get(key, []):
                    child_s2.add(representative)
            else:
                child_s2.add(key)
        parent_s1 = set()
        for parent_layout in self.inverse.get(id(parent_model_element), ()):
            if isinstance(parent_layout, frozenset):
                parent_s1 |= parent_layout
                container_layouts = self._representative_to_key.inverse.get(
                    parent_layout, []
                )
            else:
                container_layouts = [parent_layout]
            for container_layout in container_layouts:
                if hasattr(container_layout, "layout_elements"):
                    parent_s1.update(container_layout.layout_elements)
        return list(parent_s1 & child_s2)

    def get_representative_layout_elements(
        self, model_element: "ModelElement"
    ) -> "list[LayoutElement]":
        """Return the layout elements that draw a model element.

        These are the representatives of the keys mapped to `model_element`:
        a single key is its own representative. The order is not specified.

        Args:
            model_element: The model element.

        Returns:
            The layout elements that draw `model_element`, without duplicates.
        """
        layout_element_id_to_layout_element = {}
        for key in self.inverse.get(id(model_element), ()):
            if isinstance(key, frozenset):
                representatives = self._representative_to_key.inverse.get(key, [])
            else:
                representatives = [key]
            for representative in representatives:
                layout_element_id_to_layout_element[id(representative)] = representative
        return list(layout_element_id_to_layout_element.values())

    def get_layout_model_pairs(self) -> list[tuple[LayoutElement, ModelElement]]:
        """Return the pairs the mapping is made from.

        Returns:
            A `(key, model_element)` pair for each single key, and a
            `(representative, model_element)` pair for each representative of
            each frozenset key.
        """
        layout_model_pairs = []
        for key, model_element in self.items():
            if isinstance(key, frozenset):
                for representative in self._representative_to_key.inverse.get(key, []):
                    layout_model_pairs.append((representative, model_element))
            else:
                layout_model_pairs.append((key, model_element))
        return layout_model_pairs

    def is_submapping(self, other: "LayoutModelMapping") -> bool:
        """Return `True` if the mapping is a submapping of another `LayoutModelMapping`, `False` otherwise."""
        return self.items() <= other.items()

    def __reduce__(self) -> tuple[typing.Any, ...]:
        """Pickle hook that preserves `_representative_to_key` across round-trips.

        The inherited `frozendict.__reduce__` only serialises the dict
        contents, which drops the representative table added by this subclass.
        """
        return (
            type(self),
            (dict(self),),
            {"_representative_to_key": dict(self._representative_to_key)},
        )

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        """Restore `_representative_to_key` after `__reduce__`-driven unpickle."""
        object.__setattr__(
            self,
            "_representative_to_key",
            FrozenSurjectionDict(state["_representative_to_key"]),
        )


class LayoutModelMappingBuilder(IdentitySurjectionDict, Builder):
    """Mutable builder for [LayoutModelMapping][momapy.core.LayoutModelMapping].

    Builds a layout-to-model mapping incrementally, then produces a frozen
    [LayoutModelMapping][momapy.core.LayoutModelMapping] via `build()`. It
    keeps the same key conventions as the frozen mapping (singleton layout
    keys and frozenset keys, each frozenset with a representative registered in `_representative_to_key`),
    but uses mutable containers so elements can be added or replaced while a
    map is being constructed.
    """

    _cls_to_build: typing.ClassVar[type] = LayoutModelMapping

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the mapping builder and its representative index."""
        super().__init__(*args, **kwargs)
        self._representative_to_key = SurjectionDict()

    @property
    def representative_to_key(self) -> "SurjectionDict":
        """Return the table mapping representatives to frozenset keys."""
        return self._representative_to_key

    def get_mapping(
        self,
        map_element: "MapElement",
    ) -> "ModelElement | list[LayoutElement | frozenset[LayoutElement]] | None":
        """Return the element(s) mapped to the given map element.

        If `map_element` is a key (a layout element or frozenset of layout
        elements), returns the model element it maps to. If it is a model
        element, returns the list of layout keys mapped to it. If it is the
        representative of a frozenset key, returns the model element mapped
        to that key.

        Args:
            map_element: The layout or model element to look up.

        Returns:
            The mapped model element, the list of mapped layout keys, or
            `None` if the element is not in the mapping.
        """
        if map_element in self:
            return self[map_element]
        result = self.inverse.get(id(map_element))
        if result:
            return list(result)
        key = self._representative_to_key.get(map_element)
        if key is not None:
            return self[key]
        return None

    def get_child_layout_elements(
        self,
        child_model_element: "ModelElement",
        parent_model_element: "ModelElement",
    ) -> "list[LayoutElement]":
        """Return the layout elements representing ``child_model_element`` under ``parent_model_element``."""
        child_s2 = set()
        for key in self.inverse.get(id(child_model_element), ()):
            if isinstance(key, frozenset):
                for representative in self._representative_to_key.inverse.get(key, []):
                    child_s2.add(representative)
            else:
                child_s2.add(key)
        parent_s1 = set()
        for parent_layout in self.inverse.get(id(parent_model_element), ()):
            if isinstance(parent_layout, frozenset):
                parent_s1 |= parent_layout
                container_layouts = self._representative_to_key.inverse.get(
                    parent_layout, []
                )
            else:
                container_layouts = [parent_layout]
            for container_layout in container_layouts:
                if hasattr(container_layout, "layout_elements"):
                    parent_s1.update(container_layout.layout_elements)
        return list(parent_s1 & child_s2)

    def get_representative_layout_elements(
        self, model_element: "ModelElement"
    ) -> "list[LayoutElement]":
        """Return the layout elements that draw a model element.

        These are the representatives of the keys mapped to `model_element`:
        a single key is its own representative. The order is not specified.

        Args:
            model_element: The model element.

        Returns:
            The layout elements that draw `model_element`, without duplicates.
        """
        layout_element_id_to_layout_element = {}
        for key in self.inverse.get(id(model_element), ()):
            if isinstance(key, frozenset):
                representatives = self._representative_to_key.inverse.get(key, [])
            else:
                representatives = [key]
            for representative in representatives:
                layout_element_id_to_layout_element[id(representative)] = representative
        return list(layout_element_id_to_layout_element.values())

    def add_mapping(
        self,
        layout_element: "LayoutElement",
        model_element: "ModelElement",
        representative: "LayoutElement | None" = None,
    ) -> None:
        """Add a layout-element to model-element entry to the mapping.

        The mapping is many-to-one: several layout elements may map to the
        same model element, so adding a new entry for a model element that is
        already mapped simply registers an additional layout key — existing
        keys are kept.

        Args:
            layout_element: The layout element (or frozenset of layout
                elements) to use as the key.
            model_element: The model element to associate with the layout
                element.
            representative: When ``layout_element`` is a frozenset and this argument
                is provided, registers ``representative`` as the representative of the
                frozenset key. This allows ``get_mapping(representative)`` to resolve
                to the model element stored under the frozenset key, even when
                the same element participates in other frozensets (e.g. a
                logical operator that is both the representative of its own gate
                frozenset and a participant in a modulation frozenset).
        """
        self[layout_element] = model_element
        if representative is not None:
            self._representative_to_key[representative] = layout_element

    def build(
        self,
        builder_to_object: dict[int, typing.Any] | None = None,
    ) -> LayoutModelMapping:
        """Build a frozen `LayoutModelMapping` from this builder.

        Args:
            builder_to_object: Optional cache mapping builder `id()` to
                already-built objects, to preserve shared references.

        Returns:
            A frozen `LayoutModelMapping` with all keys and values built
            from their builders.
        """
        mapping = self._cls_to_build(
            {
                object_from_builder(
                    key, builder_to_object=builder_to_object
                ): object_from_builder(value, builder_to_object=builder_to_object)
                for key, value in self.items()
            }
        )
        representative_to_key = FrozenSurjectionDict(
            {
                object_from_builder(
                    representative, builder_to_object=builder_to_object
                ): object_from_builder(key, builder_to_object=builder_to_object)
                for representative, key in self._representative_to_key.items()
            }
        )
        object.__setattr__(mapping, "_representative_to_key", representative_to_key)
        return mapping

    def __reduce__(self) -> tuple[typing.Any, ...]:
        """Pickle hook that preserves `_representative_to_key` across round-trips.

        The default `dict`-subclass pickle emits SETITEMS before BUILD, so
        `IdentitySurjectionDict.__setitem__` fires before
        `_identity_inverse` exists and crashes. Routing through
        `__init__` fixes both that and the `_representative_to_key` loss.
        """
        return (
            type(self),
            (dict(self),),
            {"_representative_to_key": dict(self._representative_to_key)},
        )

    def __setstate__(self, state: dict[str, typing.Any]) -> None:
        """Restore `_representative_to_key` after `__reduce__`-driven unpickle."""
        self._representative_to_key = SurjectionDict(state["_representative_to_key"])

    @classmethod
    def from_object(
        cls,
        obj: LayoutModelMapping,
        object_to_builder: "dict[int, Builder] | None" = None,
    ) -> typing_extensions.Self:
        """Build a `LayoutModelMappingBuilder` from a frozen mapping.

        Args:
            obj: The frozen `LayoutModelMapping` to convert.
            object_to_builder: Optional cache mapping object `id()` to
                already-created builders, to preserve shared references.

        Returns:
            A `LayoutModelMappingBuilder` mirroring `obj`.
        """
        items = []
        for key, value in obj.items():
            if isinstance(key, frozenset):
                new_key = frozenset(
                    [
                        builder_from_object(
                            element, object_to_builder=object_to_builder
                        )
                        for element in key
                    ]
                )
            else:
                new_key = builder_from_object(key, object_to_builder=object_to_builder)
            new_value = builder_from_object(value, object_to_builder=object_to_builder)
            items.append(
                (
                    new_key,
                    new_value,
                )
            )
        builder = cls(items)
        representative_to_key_items = {}
        for representative, key in obj._representative_to_key.items():
            new_representative = builder_from_object(
                representative, object_to_builder=object_to_builder
            )
            if isinstance(key, frozenset):
                new_key = frozenset(
                    builder_from_object(element, object_to_builder=object_to_builder)
                    for element in key
                )
            else:
                new_key = builder_from_object(key, object_to_builder=object_to_builder)
            representative_to_key_items[new_representative] = new_key
        builder._representative_to_key = SurjectionDict(representative_to_key_items)
        return builder


register_builder_cls(LayoutModelMappingBuilder)
