from arcadiaMergeTool.merger.processors._processor import process, doProcess
from capellambse.metamodel import sa
from capellambse.model import ModelElement
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger


from . import capability_pkg, mission_pkg, system_component_pkg, system_function_pkg

__all__ = [
    "capability_pkg",
    "mission_pkg",
    "system_component_pkg",
    "system_function_pkg",
]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: sa.SystemAnalysis,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
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
        if isinstance(x, sa.SystemAnalysis):
            package = dest.model.sa

        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True
