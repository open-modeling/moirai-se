import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.model import ModelElement

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process
from . import involvement

__all__ = [
    "involvement"
]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.fa.FunctionalChain,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Functional Chains

    Parameters
    ==========
    x:
        Functional Chain to process
    dest:
        Destination model to add Functional Chains to
    src:
        Source model to take Functional Chains from
    base:
        Base model to check Functional Chains against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    # recursively check all direct parents for existence and continue only if parents agree
    modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
    if not process(modelParent, dest, src, base, mapping): # pyright: ignore[reportArgumentType] expect model parent is a valid argument
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

    if (
        isinstance(destParent, mm.fa.AbstractFunction)
        or isinstance(destParent, mm.pa.PhysicalFunction)
        or isinstance(destParent, mm.sa.SystemFunction)
        or isinstance(destParent, mm.la.LogicalFunction)
        or isinstance(destParent, mm.fa.FunctionalChain)
        or isinstance(destParent, mm.la.CapabilityRealization)
        or isinstance(destParent, mm.sa.Capability)
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
        exit(str(ExitCodes.MergeFault))

    # use weak match by name
    # TODO: implement strong match by PVMT properties
    matchingFunctionalChain = list(filter(lambda y: y.name == x.name, targetCollection))

    if (len(matchingFunctionalChain) > 0):
        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingFunctionalChain[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create new Functional Chain name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            kind = x.kind,
            name = x.name,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
        ) 

        # TODO: fix PVMT
        # .applied_property_value_groups = []
        # .applied_property_values = []
        # .property_value_groups = []
        # .property_values = []
        # .pvmt = 

        if x.postcondition is not None:
            newComp.postcondition = x.postcondition
        if x.precondition is not None:
            newComp.precondition = x.precondition
        if x.status is not None:
            newComp.status = x.status

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
