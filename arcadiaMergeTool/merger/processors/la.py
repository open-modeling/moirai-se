from arcadiaMergeTool.merger.processors._processor import process
from capellambse.metamodel import la
from capellambse.model import ModelElement
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: la.LogicalComponentPkg | la.CapabilityRealizationPkg | la.LogicalFunctionPkg | la.LogicalArchitecture,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] processing logical component package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = None
        if isinstance(x, la.LogicalArchitecture):
            package = dest.model.la
        elif isinstance(x, la.LogicalComponentPkg):
            package = dest.model.la.component_pkg
        elif isinstance(x, la.LogicalFunctionPkg):
            package = dest.model.la.function_pkg
        elif isinstance(x, la.CapabilityRealizationPkg):
            package = dest.model.la.capability_pkg

        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True
