from functools import singledispatch
from typing import Callable

import capellambse.metamodel as mm
import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.modellingcore as mc
import capellambse.model as m
from capellambse.model import ModelElement

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = m.T_co

type GeneratorCallback = Callable[[T, m.ElementList[T], MergerElementMappingMap] , T]

def recordMatch(matchColl: list[T], x: T, destParent: T, destColl: m.ElementList[T], mapping: MergerElementMappingMap) -> bool:
    """Record match in cache or fail
    
    Parameters
    ==========
    matchColl:
        Collection of Elements to record in cache
    x:
        Source element to make cache key from
    destParent:
        Potential parent element
    mapping:
        Cache to put element in
    
    Returns
    =======
    True for success, False otherwise
    """

    destEl = None
    fromLibrary = False

    if len(matchColl) > 0:
        # assume it's same to take first, but theme might be more
        destEl = matchColl[0]

        mappedTargetPart = mapping.get((destEl._model.uuid, destEl.uuid))
        fromLibrary = mappedTargetPart[1] if mappedTargetPart is not None else False

    else:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{recordMatch.__qualname__}] Create new model element name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                x.parent.__class__,
                destParent.name,
                destParent.uuid,
                destParent.__class__,
                x._model.name,
                x._model.uuid,
            )
        else:
            LOGGER.debug(
                f"[{recordMatch.__qualname__}] Create new model element uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.uuid,
                x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                x.parent.__class__,
                destParent.name,
                destParent.uuid,
                destParent.__class__,
                x._model.name,
                x._model.uuid,
            )        
        destEl = clone(x, destColl, mapping)

    mapping[(x._model.uuid, x.uuid)] = (destEl, fromLibrary)

    return True


@singledispatch
def clone (x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap) -> T:
    LOGGER.fatal(f"[{clone.__qualname__}] default generator called, must be overloaded")
    exit(str(ExitCodes.MergeFault))

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
):
    if x is None:
        return True

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

        #######################################
        # PREPROCESSORS
        #######################################

        if isinstance(x, mc.AbstractTypedElement) and x.type is not None:
            # HACK: add pre-processors
            if (x._model != src.model):
                # assume it's safe to check model source to distinct "own" elements from imported
                # as long as all libraries were linked earlier
                mapping[(x._model.uuid, x.uuid)] = (x, True)
            elif not doProcess(x.type, dest, src, base, mapping):
                return False

        # if (isinstance(x, cc.CapellaElement)):

        #     for p in x.applied_property_values:
        #         mappedPV = mapping.get((p._model.uuid, p.uuid))
        #         if mappedPV is None:
        #             return False

        #     for p in x.applied_property_value_groups:
        #         mappedPVG = mapping.get((p._model.uuid, p.uuid))
        #         if mappedPVG is None:
        #             return False
        #######################################
        # PREPROCESSORS END
        #######################################

        if not process(x, dest, src, base, mapping):
            return False

        #######################################
        # POSTROCESSORS
        #######################################
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

            # if isinstance(mappedXEl, mc.AbstractTypedElement) and x.type is not None:
            #     # HACK: add post-processors
            #     mappedXElType = mapping[(x.type._model.uuid, x.type.uuid)][0] 
            #     mappedXEl.type = mappedXElType

            if (isinstance(mappedXEl, cc.CapellaElement)):

                for p in x.applied_property_values:
                    if doProcess(p, dest, src, base, mapping):
                        mappedXEl.applied_property_values.append(mapping[(p._model.uuid, p.uuid)][0])
                    else:
                        LOGGER.fatal(
                            f"[{doProcess.__qualname__}] Component could not be resolved in post-processing name [%s], uuid [%s], class [%s]",
                            p.name,
                            p.uuid,
                            p.__class__,
                        )
                        exit(str(ExitCodes.MergeFault))

                for p in x.applied_property_value_groups:
                    if doProcess(p, dest, src, base, mapping):
                        mappedXEl.applied_property_value_groups.append(mapping[(p._model.uuid, p.uuid)][0])
                    else:
                        LOGGER.fatal(
                            f"[{doProcess.__qualname__}] Component could not be resolved in post-processing name [%s], uuid [%s], class [%s]",
                            p.name,
                            p.uuid,
                            p.__class__,
                        )
                        exit(str(ExitCodes.MergeFault))

        #######################################
        # POSTPROCESSORS END
        #######################################

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
