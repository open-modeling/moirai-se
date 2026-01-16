from arcadiaMergeTool.merger.processors._processor import process
from capellambse.metamodel import pa
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: pa.PhysicalComponentPkg | pa.PhysicalFunctionPkg,
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
        if isinstance(x, pa.PhysicalComponentPkg):
            package = dest.model.pa.component_pkg
        elif isinstance(x, pa.PhysicalFunctionPkg):
            package = dest.model.sa.function_pkg
        
        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True
