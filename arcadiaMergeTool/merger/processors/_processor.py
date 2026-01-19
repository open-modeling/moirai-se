from functools import singledispatch
import capellambse.metamodel as mm

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

def doProcess (
    x: ModelElement,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:

    if x == x._model.project:
        # edge case, root node reached
        mapping[(x._model.uuid, x.uuid)] = (x, False)

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{doProcess.__qualname__}] Add new element to model name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )
        else:
            LOGGER.debug(
                f"[{doProcess.__qualname__}] Add new element to model uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )

        return process(x, dest, src, base, mapping)

    else:
        (cachedFunction, fromLibrary) = cachedElement

        errors = []
        # if cachedFunction.name != x.name:
        #     errors["name warn"] = (
        #         f"known name [{cachedFunction.name}], new name [{x.name}]"
        #     )
        # if cachedFunction.description != x.description:
        #     errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{doProcess.__qualname__}] Fields does not match recorded, element uuid [%s], model name [%s], uuid [%s], warnings [%s]",
                x.uuid,
                x._model.name,
                x._model.uuid,
                errors,
            )

    return True
