import sys

import capellambse.model as m
from capellambse import helpers
from capellambse.metamodel import pa

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Processed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

@process.register
def _(
    x: pa.PhysicalArchitecture,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        element = dest.model.pa
        mapping[(x._model.uuid, x.uuid)] = (element, False)

    return Processed

@process.register
def _(
    x: pa.PhysicalComponentPkg,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = dest.model.pa.component_pkg
        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return Processed

T = pa.PhysicalFunctionPkg

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    return list(filter(lambda y: y.name == x.name, coll))

@clone.register
def _ (srcEl: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(srcEl._element),
        description = srcEl.description,
        is_visible_in_doc = srcEl.is_visible_in_doc,
        is_visible_in_lm = srcEl.is_visible_in_lm,
        name = srcEl.name,
        review = srcEl.review,
        sid = srcEl.sid,
        summary = srcEl.summary,
    )

    if srcEl.status is not None:
        newComp.status = srcEl.status

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

    if isinstance(destParent, pa.PhysicalArchitecture):
        mapping[(x._model.uuid, x.uuid)] = (destParent.function_pkg, False) # pyright: ignore[reportArgumentType] assume root function_pkg is always there
        return Processed

    if isinstance(destParent, (T, pa.PhysicalFunction)):
        targetCollection = destParent.packages
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Invalid parent, elemment name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
