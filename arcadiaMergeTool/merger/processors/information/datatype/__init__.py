import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information as inf
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

from . import boolean, numeric, enum, string

__all__ = [
    "boolean",
    "enum",
    "numeric",
    "string",
]

LOGGER = getLogger(__name__)
