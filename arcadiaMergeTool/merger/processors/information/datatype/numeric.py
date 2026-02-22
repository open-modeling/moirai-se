"""Find and merge Numeric Type."""

import capellambse.metamodel.information as inf
import capellambse.metamodel.information.datatype as dt
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

T = dt.NumericType

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        is_abstract = x.is_abstract,
        is_discrete = x.is_discrete,
        is_final = x.is_final,
        is_max_inclusive = x.is_max_inclusive,
        is_min_inclusive = x.is_min_inclusive,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        kind = x.kind,
        name = x.name,
        pattern = x.pattern,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        visibility = x.visibility,
    )

    if x.super is not None:
        newComp.super = x.super

    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.super, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect source exists
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

    if (isinstance(destParent, inf.DataPkg)
    ):
        targetCollection = destParent.data_types
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
    return list(filter(lambda y: y.name == x.name, coll))
