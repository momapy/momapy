"""Abstract model base class."""

import abc
import dataclasses

from momapy.core.elements import MapElement


@dataclasses.dataclass(frozen=True, kw_only=True)
class Model(MapElement, abc.ABC):
    """Abstract base class for models."""

    @abc.abstractmethod
    def is_submodel(self, other: "Model") -> bool:
        """Return whether this model is a submodel of another model.

        Args:
            other: The model to test against.

        Returns:
            `True` if this model is a submodel of `other`.
        """
        pass
