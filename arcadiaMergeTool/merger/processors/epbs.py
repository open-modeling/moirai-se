from arcadiaMergeTool.merger.processors._processor import process, doProcess
from capellambse.metamodel import epbs
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: epbs.ConfigurationItemPkg | epbs.EPBSArchitecture,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] processing configuration item package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        if isinstance(x, epbs.EPBSArchitecture):
            mapping[(x._model.uuid, x.uuid)] = (dest.model.epbs, False)
        elif isinstance(x, epbs.ConfigurationItemPkg):
            mapping[(x._model.uuid, x.uuid)] = (dest.model.epbs.configuration_item_pkg, False)

    return True

epbs.PhysicalArtifactRealization