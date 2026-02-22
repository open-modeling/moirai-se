"""Find and merge Mission Involvement."""

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

LOGGER = getLogger(__name__)

T = mm.sa.MissionInvolvement

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        involved = mapping.get((x._model.uuid, x.involved.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
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
    if doProcess(x.involved, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect source exists
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

    if (isinstance(destParent, mm.sa.Mission)
    ):
        targetCollection = destParent.involvements
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    mappedSource = mapping.get((x._model.uuid, x.parent.uuid))  # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
    mappedTarget = mapping.get((x._model.uuid, x.involved.uuid)) # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
    src = mappedSource[0] if mappedSource is not None else None
    tgt = mappedTarget[0] if mappedTarget is not None else None

    return list(filter(lambda y: y.parent == src and x.involved == tgt, coll))
