"""Find and merge Component Exchanges.

ComponentExchange mapping is based on match between the port components
Generel logic is
Exchange checks if either
    - ComponentPorts exist - legitimate case, updates mapping, note, components are mapped after exchange to ensure correct ports merge
    - Components exist - legitimate case, updates mapping

In both cases - iterate through the exchanges and match them by name
"""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Fault,
    Postponed,
    clone,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import allocation, realization

__all__ = [
    "allocation",
    "realization"
]

LOGGER = getLogger(__name__)

T = mm.fa.ComponentExchange

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    sourceFunctionMap = mapping.get((x._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetFunctionMap = mapping.get((x._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context
    mappedSourceFuncEntry = sourceFunctionMap[0] if sourceFunctionMap is not None else None
    mappedTargetFuncEntry = targetFunctionMap[0] if targetFunctionMap is not None else None

    srcExchMapping = mapping.get((x._model.uuid, x.uuid))
    srcExchMappedExch: T | None = srcExchMapping[0] if srcExchMapping is not None else None # pyright: ignore[reportAssignmentType] expect collection type matches T

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

            if tgtExch.source is None and tgtExch.target is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one exchange from another
                # we might be facing potentinal twin exchange, but need to postpone processing
                # True means that exchange processing must be postponed
                return Postponed

            if (tgtExch.source is not None and tgtExch.source.parent == mappedSourceFuncEntry) and (tgtExch.target is not None and tgtExch.target.parent == mappedTargetFuncEntry):
                # if name, source function and target function are equal, map existing exchange to a candidate
                lst.append(tgtExch)

    # if collection is exceeded, allow to add new exchange
    return lst

@preprocess.register
def _(x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    sourceComponentMap = mapping.get((x._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetComponentMap = mapping.get((x._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

    if sourceComponentMap is None or targetComponentMap is None:
        # Fast fail, postpone exchange processing to component existence
        return Postponed
    return Continue

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_oriented = x.is_oriented,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        kind =x.kind,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    )

    sourceComponentPortMap = mapping.get((x._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect exchange has source
    targetComponentPortMap = mapping.get((x._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect exchange has target
    if sourceComponentPortMap is not None:
        newComp.source = sourceComponentPortMap[0] # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
    if targetComponentPortMap is not None:
        newComp.target = targetComponentPortMap[0] # pyright: ignore[reportAttributeAccessIssue] expect source exists on model

    return newComp

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

    if (isinstance(destParent, (mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg, mm.pa.PhysicalComponentPkg))
    ):
        targetCollection = destParent.exchanges
    elif (isinstance(destParent, (mm.pa.PhysicalComponent, mm.la.LogicalComponent, mm.sa.SystemComponent))
    ):
        targetCollection = destParent.component_exchanges # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        return Fault

    return targetCollection
