from functools import singledispatch
import capellambse.metamodel as mm

from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.model import ModelElement
import capellambse.metamodel.modellingcore as mc
import capellambse.metamodel.capellacore as cc
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

        # if not doProcess(x.parent, dest, src, base, mapping): # pyright: ignore[reportArgumentType] expect parent is valid here
        #     return False

        if isinstance(x, mc.AbstractTypedElement) and x.type is not None:
            # HACK: add pre-processors
            if (x._model != src.model):
                # assume it's safe to check model source to distinct "own" elements from imported
                # as long as all libraries were linked earlier
                mapping[(x._model.uuid, x.uuid)] = (x, True)
            elif not doProcess(x.type, dest, src, base, mapping):
                return False

        if not process(x, dest, src, base, mapping):
            return False

        mappedX = mapping.get((x._model.uuid, x.uuid)) # pyright: ignore[reportAssignmentType] expect correct element type in this position

        if mappedX is not None:
            mappedXEl = mappedX[0]
            if x.__class__ != mappedXEl.__class__:
                if isinstance(x, mm.capellacore.NamedElement):
                    LOGGER.debug(
                        f"[{doProcess.__qualname__}] Source and destination elements have different classifiers source name [%s], uuid [%s], class [%s], dest name [%s], uuid [%s], class [%s]",
                        x.name,
                        x.uuid,
                        x.__class__,
                        mappedXEl.name,
                        mappedXEl.uuid,
                        mappedXEl.__class__,
                    )
                else:
                    LOGGER.debug(
                        f"[{doProcess.__qualname__}] Source and destination elements have different classifiers source uuid [%s], class [%s], dest uuid [%s], class [%s]",
                        x.uuid,
                        x.__class__,
                        mappedXEl.uuid,
                        mappedXEl.__class__,
                    )

            if isinstance(mappedXEl, mc.AbstractTypedElement) and x.type is not None:
                # HACK: add post-processors
                mappedXElType = mapping[(x.type._model.uuid, x.type.uuid)][0] 
                mappedXEl.type = mappedXElType

            if (isinstance(mappedXEl, cc.CapellaElement)):

                for p in x.applied_property_values:
                    mappedPV = mapping.get((p._model.uuid, p.uuid))
                    if mappedPV is None:
                        return False
                    mappedXEl.applied_property_values.append(mappedPV[0])

                for p in x.applied_property_value_groups:
                    mappedPVG = mapping.get((p._model.uuid, p.uuid))
                    if mappedPVG is None:
                        return False
                    mappedXEl.applied_property_values.append(mappedPVG[0])

            if x.name == "Control Steering system according to active Steering Mode":
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"!!!!!!!!!!!!!!!      {mappedXEl}             !!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                exit()


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
