"""Base element classes for maps."""

import abc
import dataclasses
import typing
import typing_extensions
import enum
from momapy.drawing import drawing_elements_to_geometry
from momapy.drawing import DrawingElement
from momapy.geometry import Bbox
from momapy.geometry import CubicBezierCurve
from momapy.geometry import EllipticalArc
from momapy.geometry import Point
from momapy.geometry import QuadraticBezierCurve
from momapy.geometry import Segment
from momapy.utils import make_uuid4_as_str


class Direction(enum.Enum):
    """Cardinal direction a layout element points to.

    One of the four cardinals (up, right, down, left). For an axis (horizontal
    or vertical), see `Orientation`.
    """

    UP = 1
    RIGHT = 2
    DOWN = 3
    LEFT = 4


class Orientation(enum.Enum):
    """Orientation along an axis.

    Either horizontal or vertical. For a cardinal direction (up, right, down,
    left), see `Direction`.
    """

    HORIZONTAL = 1
    VERTICAL = 2


class HAlignment(enum.Enum):
    """Horizontal alignment of text or content.

    Selects how content is positioned along the horizontal axis.
    """

    LEFT = 1
    CENTER = 2
    RIGHT = 3


class VAlignment(enum.Enum):
    """Vertical alignment of text or content.

    Selects how content is positioned along the vertical axis.
    """

    TOP = 1
    CENTER = 2
    BOTTOM = 3


@dataclasses.dataclass(frozen=True, kw_only=True)
class MapElement:
    """Base class for map elements.

    Common ancestor of every model and layout element making up a map.
    """

    id_: str = dataclasses.field(
        hash=False,
        compare=False,
        default_factory=make_uuid4_as_str,
        metadata={
            "description": """The id of the map element. This id is purely for the user to keep track
    of the element, it does not need to be unique and is not part of the
    identity of the element, i.e., it is not considered when testing for
    equality between two map elements or when hashing the map element"""
        },
    )

    def children(self) -> list["MapElement"]:
        """Return the children of the map element.

        The children are the map elements held by the fields of the map
        element that are not reference fields (see `is_reference_field`),
        directly or as items of a tuple or a frozenset.

        Returns:
            The children of the map element.
        """
        children = []
        for field in dataclasses.fields(self):
            if not is_reference_field(type(self), field.name):
                children += get_field_map_elements(getattr(self, field.name))
        return children

    def descendants(self) -> list["MapElement"]:
        """Return the descendants of the map element.

        The descendants are the children of the map element and their
        descendants, depth-first, without the map element itself.

        Returns:
            The descendants of the map element.
        """
        descendants = []
        for child in self.children():
            descendants.append(child)
            descendants += child.descendants()
        return descendants

    def references(self) -> list["MapElement"]:
        """Return the map elements the map element refers to.

        These are the map elements held by the reference fields of the map
        element (see `is_reference_field`), directly or as items of a tuple
        or a frozenset. References of references and references of
        descendants are not included.

        Returns:
            The map elements the map element refers to.
        """
        references = []
        for field in dataclasses.fields(self):
            if is_reference_field(type(self), field.name):
                references += get_field_map_elements(getattr(self, field.name))
        return references


def is_reference_field(cls: type, field_name: str) -> bool:
    """Return whether a field of a map element class refers to another element.

    A field refers to another element when a class of `cls.__mro__` that
    declares the field marks it with `"reference": True` in its metadata, so a
    subclass that declares the field again needs no mark.

    Args:
        cls: The map element class.
        field_name: The name of the field.

    Returns:
        `True` if the field is a reference field, `False` otherwise.
    """
    for base in cls.__mro__:
        field = base.__dict__.get("__dataclass_fields__", {}).get(field_name)
        if field is not None and field.metadata.get("reference", False):
            return True
    return False


def get_field_map_elements(field_value: typing.Any) -> list[MapElement]:
    """Return the map elements held by a field value.

    Args:
        field_value: The field value.

    Returns:
        The value itself if it is a map element, its items that are map
        elements if it is a tuple or a frozenset, and an empty list otherwise.
    """
    if isinstance(field_value, MapElement):
        return [field_value]
    if isinstance(field_value, (tuple, frozenset)):
        return [item for item in field_value if isinstance(item, MapElement)]
    return []


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModelElement(MapElement):
    """Base class for model elements.

    Common ancestor of every element carrying the semantic information of a map.
    """


@dataclasses.dataclass(frozen=True, kw_only=True)
class LayoutElement(MapElement, abc.ABC):
    """Abstract base class for layout elements.

    Common ancestor of every element carrying the visual information of a map.
    """

    @abc.abstractmethod
    def bbox(self) -> Bbox:
        """Compute and return the bounding box of the layout element."""
        pass

    @abc.abstractmethod
    def drawing_elements(self) -> list[DrawingElement]:
        """Return the drawing elements of the layout element."""
        pass

    @abc.abstractmethod
    def children(self) -> list["LayoutElement"]:
        """Return the children of the layout element."""
        pass

    @abc.abstractmethod
    def childless(self) -> typing_extensions.Self:
        """Return a copy of the layout element with no children."""
        pass

    def flattened(self) -> list["LayoutElement"]:
        """Return a list containing copy of the layout element with no children and all its descendants with no children."""
        flattened = [self.childless()]
        for child in self.children():
            flattened += child.flattened()
        return flattened

    def equals(
        self, other: "LayoutElement", flattened: bool = False, unordered: bool = False
    ) -> bool:
        """Return `True` if the layout element is equal to another layout element, `False` otherwise."""
        if type(self) is type(other):
            if not flattened:
                return self == other
            else:
                if not unordered:
                    return self.flattened() == other.flattened()
                else:
                    return set(self.flattened()) == set(other.flattened())
        return False

    def contains(self, other: "LayoutElement") -> bool:
        """Return `True` if another layout element is a descendant of the layout element, `False` otherwise."""
        return other in self.descendants()

    def to_geometry(
        self,
    ) -> list[Segment | QuadraticBezierCurve | CubicBezierCurve | EllipticalArc]:
        """Return a list of geometry primitives from the drawing elements."""
        return drawing_elements_to_geometry(self.drawing_elements())

    def anchor_point(self, anchor_name: str) -> Point:
        """Return an anchor point of the layout element."""
        return getattr(self, anchor_name)()
