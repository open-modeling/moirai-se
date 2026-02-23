"""Find and merge Enum Property Valuea."""

import sys

import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.capellamodeller as cm
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

T = cc.KeyValue

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        key = x.key,
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

    if (isinstance(destParent, (cm.Project))
    ):
        targetCollection = destParent.key_value_pairs
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    return list(filter(lambda y: y.key == x.key, coll))
