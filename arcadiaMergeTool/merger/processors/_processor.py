from functools import singledispatch
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.model import ModelElement
from arcadiaMergeTool.helpers.types import MergerElementMappingMap


from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

# generic function; will be extended across modules
@singledispatch
def process(
    x: ModelElement,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.warning(
        f"[{process.__qualname__}] element processing skipped name [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )
    # default behavior for any ModelElement if no more specific overload is found
    return True  # mark elements processed by default
