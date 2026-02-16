import sys

import capellambse.model as m

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap

LOGGER = getLogger(__name__)

def getDestParent(x: m.ModelElement, mapping: MergerElementMappingMap):
    modelParent = x.parent
    destParentEntry = mapping.get((modelParent._model.uuid, modelParent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement

    if destParentEntry is None:
        LOGGER.fatal(f"[{getDestParent.__qualname__}] Element parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.__class__,
            modelParent.name, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
            modelParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
            modelParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        sys.exit(str(ExitCodes.MergeFault))

    return destParentEntry[0]
