"""Find and merge Catalog Element Link."""

import capellambse.model as m
from capellambse import helpers
from capellambse.metamodel import re

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

T =  re.CatalogElementLink

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):

    src = mapping[(x._model.uuid, x.source.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect spurce is already there
    tgt = mapping[(x._model.uuid, x.target.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect target is already there

    newComp = coll.create(helpers.xtype_of(x._element),
        is_suffixed = x.is_suffixed,
        sid = x.sid,
        source = src[0],
        target = tgt[0],
        unsynchronized_features = x.unsynchronized_features,
    ) 

    if x.origin is not None:
        newComp.origin = coll._model.by_uuid(x.origin.uuid)

    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.target, dest, src, base, mapping) == Postponed:
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

    if (isinstance(destParent, re.CatalogElement)
    ):
        targetCollection = destParent.links
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
    return list(filter(lambda y: (y.origin is not None and y.origin.uuid == x.origin.uuid) or y.target.uuid == x.target.uuid, coll)) # pyright: ignore[reportOptionalMemberAccess] expect origin is already there
