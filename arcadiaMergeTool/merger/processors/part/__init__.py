import sys

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    clone,
    doProcess,
    process,
    recordMatch,
)
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import deployment

__all__ = [
    "deployment"
]

LOGGER = getLogger(__name__)

T = mm.cs.Part

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        type = mapping[(x._model.uuid, x.type.uuid)][0], # pyright: ignore[reportOptionalMemberAccess] expect type exists and uuid is valid
        name = x.name,
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
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        visibility = x.visibility,
    )

    if x.status is not None:
        newComp.status = x.status  # pyright: ignore[reportAttributeAccessIssue] assume status is already there

    return newComp


@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Parts.

    Parameters
    ----------
    x:
        Part to process
    dest:
        Destination model to add parts to
    src:
        Source model to take parts from
    base:
        Base model to check parts against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    -------
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
    if (not doProcess(modelParent, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect modelParent is of type ModelElement
        or not doProcess(x.type, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect x.type is valid property
    ):
        # part is merely a link to a component, check if component can be referenced
        # if not, stop processing to retry later
        return False  # safeguard for direct call

    destParentEntry = mapping.get((modelParent._model.uuid, modelParent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
    if destParentEntry is None:
        LOGGER.fatal(f"[{process.__qualname__}] Element parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.__class__,
            modelParent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            modelParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            modelParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        sys.exit(str(ExitCodes.MergeFault))

    (destParent, _fromLibrary) = destParentEntry

    targetCollection = None

    if (isinstance(destParent, (mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg, mm.pa.PhysicalComponentPkg))
        ) and destParent.parts[0] == x:
        # HACK: assume System is a very first root part
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.parts[0], False)
        return True

    if isinstance(destParent, mm.epbs.ConfigurationItemPkg) and destParent.configuration_items[0] == x:
        # HACK: assume System is a very first root configuratiobn item
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items[0], False)
        return True

    if (isinstance(destParent, (mm.cs.Component, mm.pa.PhysicalComponentPkg, mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg))
    ):
        targetCollection = destParent.owned_parts # pyright: ignore[reportAttributeAccessIssue] expect owned_parts exists in this context
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
        targetCollection = destParent.configuration_items
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Part parent is not a valid parent, Part name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    # use weak match by name
    # TODO: implement strong match by PVMT properties
    matchList = list(filter(lambda y: y.name == x.name, targetCollection))

    return recordMatch(matchList, x, destParent, targetCollection, mapping)
