"""Find and merge Requirement."""

import capellambse.model as m
from capellambse import helpers
from capellambse.extensions.reqif import capellarequirements as cr
from capellambse.extensions.reqif import requirements as r

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

T = r.Requirement

@clone.register
def _ (x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        chapter_name = x.chapter_name,
        description = x.description,
        foreign_id = x.foreign_id,
        identifier = x.identifier,
        long_name = x.long_name,
        name = x.name,
        prefix = x.prefix,
        requirement_type_proxy = x.requirement_type_proxy,
        sid = x.sid,
        text = x.text,
    )

    if x.type is not None:
        mappedType = mapping[(x._model.uuid, x.type.uuid)]
        newComp.type = mappedType[0]

    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.type, dest, src, base, mapping) == Postponed:
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
    destParent = getDestParent(x, mapping)

    if isinstance(destParent, cr.CapellaModule):
        targetCollection = destParent.requirements
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    # use weak match by name
    # TODO: implement strong match by PVMT properties
    return list(filter(lambda y: y.long_name == x.long_name, coll))
