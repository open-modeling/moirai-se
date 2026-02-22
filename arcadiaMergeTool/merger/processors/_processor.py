import sys
import typing as t
from collections.abc import Callable
from enum import Enum
from functools import singledispatch

import capellambse.metamodel as mm
import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.modellingcore as mc
import capellambse.model as m
from capellambse.model import ModelElement

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

class ProcessingResult(Enum):
    Processed = 1
    Postponed = 2
    Continue = 3
    Fault = 4

type ProcessedType = t.Literal[ProcessingResult.Processed]
type PostponeType = t.Literal[ProcessingResult.Postponed]
type ContinueType = t.Literal[ProcessingResult.Continue]
type FaultType = t.Literal[ProcessingResult.Fault]

Processed: ProcessedType = ProcessingResult.Processed
Postponed: PostponeType = ProcessingResult.Postponed
Continue: ContinueType = ProcessingResult.Continue
Fault: FaultType = ProcessingResult.Fault

T = m.T_co
ProcessReturnType = m.ElementList[T] | ProcessedType | PostponeType | FaultType
MatchReturnType = list[T] | ProcessedType | PostponeType
DoProcessReturnType = ProcessedType | PostponeType

type PreProcessReturnType = ProcessedType | PostponeType | ContinueType

type GeneratorCallback = Callable[[T, m.ElementList[T], MergerElementMappingMap] , T]

@singledispatch
def preprocess(_x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    _mapping: MergerElementMappingMap
) -> PreProcessReturnType:
    """Default preprocessor.

    Parameters
    ----------
    :param x: current element

    Returns
    -------
    processing flag

    Description
    -----------
    Preprocess method is optional method fo running safety checks against
    existing element
    """
    return Continue # allow to proceed if not overloaded

@singledispatch
def clone (x: T,
    _coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
) -> T: ...

@singledispatch
def match (x: T,
    destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
) -> MatchReturnType: ...

# generic function; will be extended across modules
@singledispatch
def process(x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    _mapping: MergerElementMappingMap,
) -> ProcessReturnType:
    if isinstance(x, mm.capellacore.NamedElement):
        LOGGER.warning(
            f"[{process.__qualname__}] element processing skipped name [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",  # noqa: G004
            x.name,
            x.__class__,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )
    else:
        LOGGER.warning(
            f"[{process.__qualname__}] element processing skipped class [%s], uuid [%s], model name [%s], uuid [%s]",  # noqa: G004
            x.__class__,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )
    # default behavior for any ModelElement if no more specific overload is found
    return Processed # mark elements processed by default

def doRecord(matchColl: list[T], x: T, destParent: T, destColl: m.ElementList[T], mapping: MergerElementMappingMap):
    """Record match in cache or fail.

    Parameters
    ----------
    matchColl:
        Collection of Elements to record in cache
    x:
        Source element to make cache key from
    destParent:
        Potential parent element
    destColl:
        Collection of Elements to add element to
    mapping:
        Cache to put element in

    Returns
    -------
    True for success, False otherwise
    """

    destEl = None
    fromLibrary = False

    if len(matchColl) > 1:
        # potentional conflict, raise the flag
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.fatal(
                f"[{process.__qualname__}] Several candidates detected, cannot proceed with merge. Element name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]: [%s]",
                x.name,
                x.uuid,
                x.__class__,
                destParent.name,
                destParent.uuid,
                x._model.name,
                x._model.uuid,
                matchColl,
                stack_info=True
            )
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Several candidates detected, cannot proceed with merge. Element uuid [%s], class [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]: [%s]",
                x.uuid,
                x.__class__,
                destParent.name,
                destParent.uuid,
                x._model.name,
                x._model.uuid,
                matchColl,
                stack_info=True
            )
        sys.exit(str(ExitCodes.MergeFault))

    if len(matchColl) > 0:
        # assume it's same to take first, but theme might be more
        destEl = matchColl[0]

        mappedEl = mapping.get((destEl._model.uuid, destEl.uuid))
        fromLibrary = mappedEl[1] if mappedEl is not None else False

    else:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{doRecord.__qualname__}] Create new model element name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",  # noqa: G004
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
                f"[{doRecord.__qualname__}] Create new model element uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",  # noqa: G004
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

def doProcess (
    x: ModelElement | None,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> DoProcessReturnType:
    if x is None:
        return Processed

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{doProcess.__qualname__}] Add new element to model name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",  # noqa: G004
                x.name,
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )
        else:
            LOGGER.debug(
                f"[{doProcess.__qualname__}] Add new element to model uuid [%s], class [%s], model name [%s], uuid [%s]",  # noqa: G004
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )

        if isinstance(x, mm.capellamodeller.Project):
            # TODO: rework for common processing path
            mapping[(x._model.uuid, x.uuid)] = (dest.model.project, True)
            return Processed

        #######################################
        # PREPROCESSORS
        #######################################

        if isinstance(x, m.ModelElement) and isinstance(x.parent, m.ModelElement):  # noqa: SIM102
            # parent processing is a must to avoid cases when child lands to unprocessed element
            if doProcess(x.parent, dest, src, base, mapping) == Postponed:
                return Postponed

        if isinstance(x, mc.AbstractTypedElement) and x.type is not None:  # noqa: SIM102
            # hack for processing of typed elements types, they are not processed by matcher
            if doProcess(x.type, dest, src, base, mapping) == Postponed:
                return Postponed

        prep = preprocess(x, dest, src, base, mapping)
        if prep == Postponed:
            # for both cases - exit processing loop
            return prep

        #######################################
        # PREPROCESSORS END
        #######################################

        # find correct collection to add element to
        destColl = process(x, dest, src, base, mapping)

        if destColl == Postponed:
            return Postponed

        if destColl == Fault:
            if isinstance(x, mm.capellacore.NamedElement):
                LOGGER.fatal(f"[{getDestParent.__qualname__}] Element parent cannot be found, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
                    x.name,
                    x.uuid,
                    x.__class__,
                    x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
                    x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
                    x.parent.__class__,
                    x._model.name,
                    x._model.uuid,
                )
            else:
                LOGGER.fatal(f"[{getDestParent.__qualname__}] Element parent cannot be found, uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
                    x.uuid,
                    x.__class__,
                    x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
                    x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expext parent is ModelElement
                    x.parent.__class__,
                    x._model.name,
                    x._model.uuid,
                )
            sys.exit(str(ExitCodes.MergeFault))

        if destColl != Processed:
            # note, for already processed elements it's necessary to run post-processors

            destParent = getDestParent(x, mapping)

            # check for existing elements
            matchColl = match(x, destParent, destColl, mapping)
            if matchColl in (Processed, Postponed):
                return matchColl

            # complete record of element into destination model
            doRecord(matchColl, x, destParent, destColl,mapping)

        #######################################
        # POSTROCESSORS
        #######################################
        mappedX = mapping.get((x._model.uuid, x.uuid)) # pyright: ignore[reportAssignmentType] expect correct element type in this position
        if mappedX is None:
            return Processed

        mappedXEl = mappedX[0]
        if x.__class__ != mappedXEl.__class__:
            if isinstance(x, mm.capellacore.NamedElement):
                LOGGER.debug(
                    f"[{doProcess.__qualname__}] Source and destination elements have different classifiers source name [%s], uuid [%s], class [%s], dest name [%s], uuid [%s], class [%s]",  # noqa: G004
                    x.name,
                    x.uuid,
                    x.__class__,
                    mappedXEl.name if mappedXEl is not None else "NONE NAME",
                    mappedXEl.uuid if mappedXEl is not None else "NONE UUID",
                    mappedXEl.__class__ if mappedXEl is not None else "NONE CLASS",
                )
            else:
                LOGGER.debug(
                    f"[{doProcess.__qualname__}] Source and destination elements have different classifiers source uuid [%s], class [%s], dest uuid [%s], class [%s]",  # noqa: G004
                    x.uuid,
                    x.__class__,
                    mappedXEl.uuid if mappedXEl is not None else "NONE UUID",
                    mappedXEl.__class__  if mappedXEl is not None else "NONE CLASS",
                )

        if isinstance(x, mm.capellacore.CapellaElement) and x.status is not None:
            # TODO: check statuses on other models to get lowest one
            mappedXEl.status = x.status

        if isinstance(mappedXEl, mc.AbstractTypedElement) and x.type is not None:
            # TODO: implement as post-processor
            mappedXElType = mapping[(x._model.uuid, x.type.uuid)][0]
            mappedXEl.type = mappedXElType

        if (isinstance(mappedXEl, cc.CapellaElement)):
            for p in x.applied_property_values:
                doProcess(p, dest, src, base, mapping)
                v = mapping[(p._model.uuid, p.uuid)][0]
                if len(mappedXEl.applied_property_values.filter(lambda y: y.uuid == v.uuid)) == 0:
                    mappedXEl.applied_property_values.append(v)

            for p in x.applied_property_value_groups:
                doProcess(p, dest, src, base, mapping)
                v = mapping[(p._model.uuid, p.uuid)][0]
                if len(mappedXEl.applied_property_value_groups.filter(lambda y: y.uuid == v.uuid)) == 0:
                    mappedXEl.applied_property_value_groups.append(v)

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

        if len(errors) > 0:
            LOGGER.warning(
                f"[{doProcess.__qualname__}] Fields does not match recorded, element uuid [%s], model name [%s], uuid [%s], warnings [%s]",  # noqa: G004
                x.uuid,
                x._model.name,
                x._model.uuid,
                errors,
            )

    return Processed
