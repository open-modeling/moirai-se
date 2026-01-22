import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.model import ModelElement

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingEntry, MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

from . import allocation

__all__ = [
    "allocation"
]

LOGGER = getLogger(__name__)

def __findMatchingExchange(targetCollection, srcExch, 
                           mappedSourcFuncEntry: MergerElementMappingEntry | None, 
                           mappedTargetFuncEntry: MergerElementMappingEntry | None, 
                           mapping: MergerElementMappingMap) -> ModelElement | bool:
    """Find Comp basen on exchange props
    
    Parameters
    ==========
    targetCollection:
        Exchange collection to lookup at
    srcExch:
        Exchange to match against

    Returns
    =======
    Matching Comp or None
    """
    srcExchMapping = mapping.get((srcExch._model.uuid, srcExch.uuid))
    srcExchMappedExch = srcExchMapping[0] if srcExchMapping is not None else None

    if srcExchMappedExch is not None:
        # for already mapped exchanges no need no do something
        return srcExchMappedExch

    for tgtExch in targetCollection:

        # NOTE: weak match against exchange name
        # TODO: replace weak match with PVMT based strong match
        if tgtExch.name == srcExch.name:
            # for case of name we have to do complex check
            # 1. there might be several exchanges with the same name
            # 2. exchange is mapped before Comp and may have empty source and target

            if tgtExch.source is None or tgtExch.target is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one exchange from another
                # we might be facing potentinal twin exchange, but need to postpone processing
                # True means that exchange processing must be postponed
                return True

            tgtExchMappedSourceFunc = mapping.get((tgtExch._model.uuid, tgtExch.source.parent.uuid))
            tgtExchMappedTargetFunc = mapping.get((tgtExch._model.uuid, tgtExch.target.parent.uuid))

            if tgtExchMappedSourceFunc is not None and tgtExchMappedTargetFunc is not None and tgtExchMappedSourceFunc == mappedSourcFuncEntry and tgtExchMappedTargetFunc == mappedTargetFuncEntry:
                # if name, source function and target function are equal, map existing exchange to a candidate
                return tgtExch

    # if collection is exceeded, allow to add new exchange
    return False
            
@process.register
def _(
    x: mm.fa.FunctionalExchange,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Functional Exchanges

    Parameters
    ==========
    x:
        Functional Exchange to process
    dest:
        Destination model to add Functional Exchanges to
    src:
        Source model to take Functional Exchanges from
    base:
        Base model to check Functional Exchanges against
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

    if (isinstance(destParent, mm.sa.SystemFunctionPkg)
        or isinstance(destParent, mm.la.LogicalFunctionPkg)
        or isinstance(destParent, mm.pa.PhysicalFunctionPkg)
        or isinstance(destParent, mm.pa.PhysicalFunction)
        or isinstance(destParent, mm.la.LogicalFunction)
        or isinstance(destParent, mm.sa.SystemFunction)
    ):
        targetCollection = destParent.exchanges
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Functional Exchange parent is not a valid parent, Functional Exchange name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    # FunctionalExchange mapping is based on match between the port components
    # Generel logic is
    # Exchange checks if either
    #  - FunctionPorts exist - legitimate case, updates mapping, note, functions are mapped after exchange to ensure correct ports merge
    #  - Function exist - legitimate case, updates mapping
    # 
    # In both cases - iterate through the exchanges and match them by name

    doProcess(x.source, dest, src, base, mapping)
    doProcess(x.target, dest, src, base, mapping)

    sourceFunctionMap = mapping.get((x._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetFunctionMap = mapping.get((x._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

    if sourceFunctionMap is None or targetFunctionMap is None:
        # Fast fail, postpone exchange processing to function existence
        # Note, functions are deployed independently to the exchanges
        # at least for now, this means correct deployment order is
        # 1. functions
        # 2. exchanges
        # 3. ports
        return False

    ex = __findMatchingExchange(targetCollection, x, sourceFunctionMap, targetFunctionMap, mapping)

    if ex is True:
        # postpone exececution on boolean true
        # TODO: add more convenient return type
        LOGGER.debug(
            f"[{process.__qualname__}] No Functional Exchange match, postpone processing of Functional Exchange name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )
        return False

    if ex is not False:
        LOGGER.debug(
            f"[{process.__qualname__}] Record Function Exchange, name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            destParent.name,
            destParent.uuid,
            x._model.name,
            x._model.uuid,
        )

        mapping[(x._model.uuid, x.uuid)] = (ex, False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create Function Exchange, name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # newComp = targetCollection.create(xtype=helpers.qtype_of(x._element), source=sourceFunctionPortMap, target=targetFunctionPortMap) 
        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
            description = x.description,
            is_multicast = x.is_multicast,
            is_multireceive = x.is_multireceive,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            name = x.name,
            rate = x.rate,
            rate_kind = x.rate_kind,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
            weight = x.weight,       
        ) 

        # TODO: fix PVMT
        # .property_value_groups = []
        # .property_values = []
        # .pvmt = 

        # TODO: find a way to copy these properties
        # newComp.progress_status = x.progress_status

        if x.selection is not None:
            newComp.selection = x.selection
        if x.status is not None:
            newComp.status = x.status

        # NOTE: do not assign ports, port assignment logic is in function/port
        # if sourceFunctionPortMap is not None:
        #     newComp.source = sourceFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
        # if targetFunctionPortMap is not None:
        #     newComp.target = targetFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
        if x.transformation is not None:
            newComp.transformation = x.transformation

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
