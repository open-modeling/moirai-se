"""Find and merge Functional Exchanges.

FunctionalExchange mapping is based on match between the port components
Generel logic is
Exchange checks if either
  - FunctionPorts exist - legitimate case, updates mapping, note, functions are mapped after exchange to ensure correct ports merge
  - Function exist - legitimate case, updates mapping

In both cases - iterate through the exchanges and match them by name
"""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import (
    MergerElementMappingMap,
)
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Fault,
    Postponed,
    clone,
    doProcess,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import allocation

__all__ = [
    "allocation"
]

LOGGER = getLogger(__name__)

T = mm.fa.FunctionalExchangeSpecification

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    sourceComponentMap = mapping.get((x.source.parent._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetComponentMap = mapping.get((x.target.parent._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context
    mappedSourceFuncEntry = sourceComponentMap[0] if sourceComponentMap is not None else None
    mappedTargetFuncEntry = targetComponentMap[0] if targetComponentMap is not None else None

    srcExchMapping = mapping.get((x._model.uuid, x.uuid))
    srcExchMappedExch: T = srcExchMapping[0] if srcExchMapping is not None else None # pyright: ignore[reportAssignmentType] expect element is or correct type

    lst: list[T] = []

    if srcExchMappedExch is not None:
        # for already mapped exchanges no need no do something
        lst.append(srcExchMappedExch)
        return lst

    for tgtExch in coll:

        # NOTE: weak match against exchange name
        # TODO: replace weak match with PVMT based strong match
        if tgtExch.name == x.name:
            # for case of name we have to do complex check
            # 1. there might be several exchanges with the same name
            # 2. exchange is mapped before Comp and may have empty source and target

            if tgtExch.source is None or tgtExch.target is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one exchange from another
                # we might be facing potentinal twin exchange, but need to postpone processing
                # True means that exchange processing must be postponed
                return Postponed

            tgtExchMappedSourceFunc = mapping.get((tgtExch._model.uuid, tgtExch.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect uuid is there
            tgtExchMappedTargetFunc = mapping.get((tgtExch._model.uuid, tgtExch.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect uuid is there

            if tgtExchMappedSourceFunc is not None and tgtExchMappedTargetFunc is not None and tgtExchMappedSourceFunc == mappedSourceFuncEntry and tgtExchMappedTargetFunc == mappedTargetFuncEntry:
                # if name, source function and target function are equal, map existing exchange to a candidate
                lst.append(tgtExch)

    # if collection is exceeded, allow to add new exchange
    return lst

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    # NOTE: do not assign ports, port assignment logic is in function/port
    # if sourceFunctionPortMap is not None:
    #     newComp.source = sourceFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model  # noqa: ERA001
    # if targetFunctionPortMap is not None:
    #     newComp.target = targetFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model  # noqa: ERA001
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_multicast = x.is_multicast,
        is_multireceive = x.is_multireceive,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        rate = x.rate,
        rate_kind = x.rate_kind,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        weight = x.weight,
    )

    if x.selection is not None:
        newComp.selection = x.selection
    if x.transformation is not None:
        newComp.transformation = x.transformation
    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    doProcess(x.source, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect source exists
    doProcess(x.target, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect target exists

    sourceComponentMap = mapping.get((x.source.parent._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetComponentMap = mapping.get((x.target.parent._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

    if (x.source is not None and sourceComponentMap is None) or (x.target is not None and targetComponentMap is None):
        # Fast fail, postpone exchange processing to function existence
        # Note, functions are deployed independently to the exchanges
        # at least for now, this means correct deployment order is
        # 1. functions
        # 2. exchanges
        # 3. ports
        return Postponed
    return Continue

@process.register
def _(
    x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    targetCollection = None

    destParent = getDestParent(x, mapping)

    if (isinstance(destParent, (mm.sa.SystemFunctionPkg, mm.la.LogicalFunctionPkg, mm.pa.PhysicalFunctionPkg))
    ):
        targetCollection = destParent.exchanges
    else:
        return Fault

    return targetCollection
