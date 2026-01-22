import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.cs.Interface,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Interfaces

    Parameters
    ==========
    x:
        Interface to process
    dest:
        Destination model to add Interfaces to
    src:
        Source model to take Interfaces from
    base:
        Base model to check Interfaces against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
    if not doProcess(modelParent, dest, src, base, mapping): # pyright: ignore[reportArgumentType] expect modelParent is of tyoe ModelElement
        # safeguard for direct call
        return False

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
        exit(str(ExitCodes.MergeFault))

    (destParent, fromLibrary) = destParentEntry

    targetCollection = None

    if isinstance(destParent, mm.cs.InterfacePkg):
        targetCollection = destParent.interfaces
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Interface parent is not a valid parent, Interface name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    matchingExchangeItem = list(filter(lambda y: y.name == x.name, targetCollection)) # pyright: ignore[reportAttributeAccessIssue] expect name is there

    if (len(matchingExchangeItem) > 0):
        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingExchangeItem[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create new Interface name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            x.parent.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )

        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
            description = x.description,
            is_abstract = x.is_abstract,
            is_final = x.is_final,
            is_structural = x.is_structural,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            mechanism = x.mechanism,
            name = x.name,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
            visibility = x.visibility,
        ) 

        # TODO: fix PVMT
        # .property_value_groups = []
        # .property_values = []
        # .pvmt = 

        if x.status is not None:
            newComp.status = x.status
        if x.super is not None:
            newComp.super = x.super

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
