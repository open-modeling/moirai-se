import capellambse.model as m
from capellambse.metamodel import epbs

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import Processed, process
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = epbs.ConfigurationItemPkg | epbs.EPBSArchitecture

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
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

    return Processed
