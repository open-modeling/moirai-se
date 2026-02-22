"""Find and merge Functional Chains."""

import capellambse.metamodel as mm
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

from . import capability_involvement, involvement

__all__ = [
    "capability_involvement",
    "involvement"
]

LOGGER = getLogger(__name__)

T = mm.fa.FunctionalChain

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        kind = x.kind,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    )

    if x.postcondition is not None:
        newComp.postcondition = x.postcondition
    if x.precondition is not None:
        newComp.precondition = x.precondition

    return newComp

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

    if (
        isinstance(destParent, (mm.fa.AbstractFunction, mm.pa.PhysicalFunction, mm.sa.SystemFunction, mm.la.LogicalFunction, mm.fa.FunctionalChain, mm.la.CapabilityRealization, mm.sa.Capability))
    ):
        targetCollection = destParent.functional_chains
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
