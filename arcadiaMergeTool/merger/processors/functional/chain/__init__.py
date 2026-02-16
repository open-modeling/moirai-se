"""Find and merge Functional Chains."""

import sys

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import involvement

__all__ = [
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
        LOGGER.fatal(
            f"[{process.__qualname__}] Functional Chain parent is not a valid parent, Functional Chain name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        sys.exit(str(ExitCodes.MergeFault))

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
