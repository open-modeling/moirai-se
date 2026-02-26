"""Find and merge CapellaIncomingRelation."""

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
    Processed,
    clone,
    doProcess,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = cr.CapellaIncomingRelation

@clone.register
def _ (x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        description = x.description,
        identifier = x.identifier,
        long_name = x.long_name,
        relation_type_proxy = x.relation_type_proxy,
        sid = x.sid,
        source = mapping[(x._model.uuid, x.source.uuid)][0] if x.source is not None else None,
        target = mapping[(x._model.uuid, x.target.uuid)][0] if x.target is not None else None,
        type = mapping[(x._model.uuid, x.type.uuid)][0] if x.type is not None else None
    )

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if x.source is None or x.target is None:
        LOGGER.warning("[%s] Skip processing of the Capella Incoming Relation, source is [%s], target is [%s], ends can't be None, element name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            preprocess.__qualname__,
            "None" if x.source is None else x.source.uuid,
            "None" if x.target is None else x.target.uuid,
            x.long_name,
            x.uuid,
            x.__class__,
            x._model.name,
            x._model.uuid
        )
        return Processed

    if doProcess(x.source, dest, src, base, mapping) == Postponed:
        return Postponed
    if doProcess(x.target, dest, src, base, mapping) == Postponed:
        return Postponed
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

    if isinstance(destParent, r.Requirement):
        targetCollection = destParent.owned_relations
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    mappedSource = mapping.get((x._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect source is already there
    mappedTarget = mapping.get((x._model.uuid, x.target.uuid)) if x.target is not None else (None)
    mappedType= mapping.get((x._model.uuid, x.type.uuid)) if x.type is not None else (None)

    if (x.source is not None and mappedSource is None) or (x.target is not None and mappedTarget is None) or (x.type is not None and mappedType is None):
        # if source or target is not mapped, postpone allocation processing
        return Postponed

    return list(filter(lambda y: y.source == mappedSource[0] and y.target == mappedTarget[0] and x.type == mappedType[0], coll)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe
