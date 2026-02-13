import capellambse.metamodel as mm
from capellambse.metamodel import re
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors.recordMatch import recordMatch
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import clone, process, doProcess

LOGGER = getLogger(__name__)

T =  re.CatalogElementLink

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):

    src = mapping[(x._model.uuid, x.source.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect spurce is already there
    tgt = mapping[(x._model.uuid, x.target.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect target is already there

    newComp = coll.create(helpers.xtype_of(x._element),
        is_suffixed = x.is_suffixed,
        sid = x.sid,
        source = src[0],
        target = tgt[0],
        unsynchronized_features = x.unsynchronized_features,
    ) 

    if x.origin is not None:
        newComp.origin = coll._model.by_uuid(x.origin.uuid)

    return newComp


@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Catalog Element Link

    Parameters
    ==========
    x:
        Catalog Element Link to process
    dest:
        Destination model to add Catalog Element Link to
    src:
        Source model to take Catalog Element Link from
    base:
        Base model to check Catalog Element Link against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
    if (not doProcess(modelParent, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect modelParent is of type ModelElement
        or (x.target is not None and not doProcess(x.target, dest, src, base, mapping))
    ):
        # safeguard for direct call
        return False

    destParentEntry = mapping.get((modelParent._model.uuid, modelParent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
    if destParentEntry is None:
        LOGGER.fatal(f"[{process.__qualname__}] Element parent was not found in cache, uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
            x.uuid,
            x.__class__,
            modelParent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            modelParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            modelParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        exit(str(ExitCodes.MergeFault))

    (destParent, fromLibrary) = destParentEntry

    targetCollection = None

    if (isinstance(destParent, re.CatalogElement)
    ):
        targetCollection = destParent.links
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Catalog Element Link parent is not a valid parent, Catalog Element Link name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        exit(str(ExitCodes.MergeFault))

    # use weak match by name
    # TODO: implement strong match by PVMT properties
    matchList = list(filter(lambda y: y.origin is not None and y.origin.uuid == x.origin.uuid or y.target.uuid == x.target.uuid, targetCollection)) # pyright: ignore[reportOptionalMemberAccess] expect origin is already there

    return recordMatch(matchList, x, destParent, targetCollection, mapping)
