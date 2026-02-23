import capellambse.metamodel.capellacommon as cc
import capellambse.model as m
from capellambse import helpers
from capellambse.metamodel import cs, fa, interaction

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

LOGGER = getLogger(__name__)

T = cc.TransfoLink

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        source = mapping.get((x._model.uuid, x.source.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect source is already there
        target = mapping.get((x._model.uuid, x.target.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    )

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

    if (isinstance(destParent, (cs.Component, fa.AbstractFunction, cs.ComponentPkg, fa.FunctionPkg, cs.Interface, interaction.Scenario))
    ):
        targetCollection = destParent.owned_traces
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
    mappedTarget = mapping.get((x._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target is already there
    if mappedSource is None or mappedTarget is None:
        # if source or target is not mapped, postpone allocation processing
        return Postponed

    return list(filter(lambda y: y.source == mappedSource[0] and y.target == mappedTarget[0], coll)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe
