from capellambse.metamodel import oa

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import Processed, process
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import entity, role

__all__ = [
    "entity",
    "role",
]

LOGGER = getLogger(__name__)

T = oa.OperationalActivityPkg | oa.OperationalCapabilityPkg | oa.OperationalAnalysis

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = None
        if isinstance(x, oa.OperationalAnalysis):
            package = dest.model.oa
        elif isinstance(x, oa.OperationalActivityPkg):
            package = dest.model.oa.function_pkg
        elif isinstance(x, oa.OperationalCapabilityPkg):
            package = dest.model.oa.capability_pkg

        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return Processed
