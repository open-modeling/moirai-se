from arcadiaMergeTool.merger.processors._processor import process
from capellambse.metamodel import sa
from capellambse.model import ModelElement
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: sa.SystemComponentPkg | sa.SystemFunctionPkg | sa.CapabilityPkg | sa.MissionPkg | sa.SystemAnalysis,
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
        elif isinstance(x, sa.SystemComponentPkg):
            package = dest.model.sa.component_pkg
        elif isinstance(x, sa.SystemFunctionPkg):
            package = dest.model.sa.function_pkg
        elif isinstance(x, sa.CapabilityPkg):
            package = dest.model.sa.capability_pkg
        elif isinstance(x, sa.MissionPkg):
            package = dest.model.sa.mission_pkg
        
        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True
