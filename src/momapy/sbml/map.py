"""Map class for SBML maps."""

import dataclasses

from momapy.core.map import Map
from momapy.sbml.model import SBMLModel


@dataclasses.dataclass(frozen=True, kw_only=True)
class SBMLMap(Map):
    """Class for SBML maps.

    SBML support is model only: an `SBMLMap` carries an `SBMLModel` and no
    layout: its `layout` and `layout_model_mapping` fields are typed `None`.
    """

    model: SBMLModel | None = None
    layout: None = None
    layout_model_mapping: None = None
