"""Find and merge Boolean Literal Values."""

import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information.datavalue as dv
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T =  dv.LiteralBooleanValue

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        is_abstract = x.is_abstract,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        value = x.value,
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

    if (isinstance(destParent, dt.BooleanType)):
        targetCollection = destParent.literals
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
