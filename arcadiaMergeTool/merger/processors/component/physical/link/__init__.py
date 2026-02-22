"""Find and merge Physical Links.

Physical Link mapping is based on match between the port components
Generel logic is
Physical Link checks if either
    - ComponentPorts exist - legitimate case, updates mapping, note, components are mapped after links to ensure correct ports merge
    - Components exist - legitimate case, updates mapping

In both cases - iterate through the linkss and match them by name
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
    doProcess,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import category

__all__ = [
    "category",
]

LOGGER = getLogger(__name__)

T = mm.cs.PhysicalLink

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
        # for already mapped physical links no need no do something
        lst.append(srcExchMappedExch)
        return lst

    for tgtExch in coll:

        # NOTE: weak match against physical link name
        # TODO: replace weak match with PVMT based strong match
        if tgtExch.name == x.name:
            # for case of name we have to do complex check
            # 1. there might be several physical links with the same name
            # 2. physical link is mapped before Comp and may have empty source and target

            if tgtExch.source is None or tgtExch.target is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one physical link from another
                # we might be facing potentinal twin physical link, but need to postpone processing
                # True means that physical link processing must be postponed
                return Postponed

            tgtExchMappedSourceFunc = mapping.get((tgtExch._model.uuid, tgtExch.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect uuid is there
            tgtExchMappedTargetFunc = mapping.get((tgtExch._model.uuid, tgtExch.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect uuid is there

            if tgtExchMappedSourceFunc is not None and tgtExchMappedTargetFunc is not None and tgtExchMappedSourceFunc == mappedSourceFuncEntry and tgtExchMappedTargetFunc == mappedTargetFuncEntry:
                # if name, source function and target function are equal, map existing physical link to a candidate
                lst.append(tgtExch)

    # if collection is exceeded, allow to add new physical link
    return lst

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    # NOTE: do not assign ports, port assignment logic is in function/port
    # if sourceComponentPortMap is not None:
    #     newComp.source = sourceComponentPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model  # noqa: ERA001
    # if targetComponentPortMap is not None:
    #     newComp.target = targetComponentPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model  # noqa: ERA001
    return  coll.create(helpers.xtype_of(x._element),
            description = x.description,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            name = x.name,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
        )

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if x.source is not None and doProcess(x.source.parent, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect source exists
        return Postponed
    if x.target is not None and doProcess(x.target.parent, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect target exists
        return Postponed
    # Fast fail, postpone exchange processing to component
    # Note, functions are deployed independently to the physical links
    # at least for now, this means correct deployment order is
    # 1. components
    # 2. physical links
    # 3. ports
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

    if (isinstance(destParent, (mm.pa.PhysicalComponent, mm.la.LogicalComponent, mm.sa.SystemComponent, mm.pa.PhysicalComponentPkg, mm.la.LogicalComponentPkg, mm.sa.SystemComponentPkg))
    ):
        targetCollection = destParent.physical_links # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        return Fault

    return targetCollection
