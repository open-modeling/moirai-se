"""Find and merge Functions."""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    Processed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import allocation, port, realization

__all__ = [
    "allocation",
    "port",
    "realization"
]

LOGGER = getLogger(__name__)

T = mm.fa.AbstractFunction | mm.sa.SystemFunction | mm.la.LogicalFunction | mm.pa.PhysicalFunction | mm.oa.OperationalActivity

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        aggregation_kind = x.aggregation_kind,
        condition = x.condition,
        description = x.description,
        is_abstract = x.is_abstract,
        is_derived = x.is_derived,
        is_final = x.is_final,
        is_max_inclusive = x.is_max_inclusive,
        is_min_inclusive = x.is_min_inclusive,
        is_ordered = x.is_ordered,
        is_part_of_key = x.is_part_of_key,
        is_read_only = x.is_read_only,
        is_static = x.is_static,
        is_unique = x.is_unique,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        kind = x.kind,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        visibility = x.visibility,
    )

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

    if (isinstance(destParent, (mm.sa.SystemAnalysis, mm.la.LogicalArchitecture, mm.pa.PhysicalArchitecture))
        ) and destParent.root_function == x:
        mapping[(x._model.uuid, x.uuid)] = (destParent.root_function, False)
        return Processed
    if isinstance(destParent, mm.oa.OperationalActivityPkg):
        targetCollection = destParent.activities
    elif (
        isinstance(destParent, (mm.fa.AbstractFunction, mm.pa.PhysicalFunctionPkg, mm.sa.SystemFunctionPkg, mm.la.LogicalFunctionPkg))
    ):
        targetCollection = destParent.functions
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
