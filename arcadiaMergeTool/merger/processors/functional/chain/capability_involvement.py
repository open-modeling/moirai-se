"""Find and merge Functional Chain Involvement Function."""

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

T =  mm.sa.interaction.FunctionalChainAbstractCapabilityInvolvement

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

    if (isinstance(destParent, mm.fa.FunctionalChain)
    ):
        targetCollection = destParent.involvements
    elif isinstance(destParent, (mm.la.CapabilityRealization, mm.sa.Capability)):
        targetCollection = destParent.chain_involvements
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    mappedSource = mapping.get((x._model.uuid, x.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect parent has uuid
    mappedTarget = mapping.get((x._model.uuid, x.involved.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect involved is already there
    if mappedSource is None or mappedTarget is None:
        # if source or target is not mapped, postpone allocation processing
        return Postponed

    return list(filter(lambda y: y.parent == mappedSource[0] and y.involved == mappedTarget[0], coll))
