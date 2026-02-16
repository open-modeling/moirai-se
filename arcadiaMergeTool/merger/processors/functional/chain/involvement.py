"""Find and merge Functional Chain Involvement Function."""

import sys

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Postponed,
    clone,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T =  mm.fa.FunctionalChainInvolvement

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        involved = mapping.get((x._model.uuid, x.involved.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
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
    mappedInvolved = mapping.get((x._model.uuid, x.involved.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target is already there
    if mappedInvolved is None:
        # postpone processing until involved function resolved
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

    if (isinstance(destParent, mm.fa.FunctionalChain)
    ):
        targetCollection = destParent.involvements
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Functional Exchange Realization parent is not a valid parent, Functional Exchange Realization uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    mapping: MergerElementMappingMap
):
    mappedInvolved = mapping.get((x._model.uuid, x.involved.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target is already there
    return list(filter(lambda y: y.parent == mappedInvolved[0], coll)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe
