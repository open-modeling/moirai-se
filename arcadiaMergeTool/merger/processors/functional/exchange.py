import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from .._processor import process

LOGGER = getLogger(__name__)

def __findMatchingExchange(coll, exch, mappedSourceComp, mappedTargetComp, mapping: MergerElementMappingMap) -> m._obj.ModelElement | None:
    """Find port basen on exchange props
    
    Parameters
    ==========
    coll:
        Exchange collection to lookup at
    exch:
        Exchange to match against

    Returns
    =======
    Matching port or None
    """
    exchMap = mapping.get((exch._model.uuid), exch.uuid)
    mappedExch = exchMap[0] if exchMap is not None else None

    for ex in coll:
        # NOTE: weak match against exchange name
        # TODO: replace weak match with PVMT based strong match
        if ex.name == exch.name:
            exMap = mapping.get((ex._model.uuid, ex.uuid))
            mappedEx = exMap[0] if exMap is not None else None
            if mappedExch == mappedEx:
                # if already mapped, use it
                return ex
            if ex.source is None and ex.target is None and mappedEx is None:
                # unassigned and unmapped exchange, impossible case but get one
                return ex
            
            if ex.source.parent == mappedSourceComp and ex.target.parent == mappedTargetComp:
                # matching exchange round
                return ex


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

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        # for Functional Exchange - if not found in cache, in general it's a violation of the merging rules
        # at this point all Functional Exchange must come from base library
        LOGGER.debug(
            f"[{process.__qualname__}] New Functional Exchange, name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # recursively check all direct parents for existence and continue only if parents agree
        modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
        if not process(modelParent, dest, src, base, mapping):
            return False
        
        # check source and target and postpone processing if both weren't processed
        # if not (process(x.source, dest, src, base, mapping) # pyright: ignore[reportOptionalMemberAccess] expect source is there
        #     and process(x.target, dest, src, base, mapping)): # pyright: ignore[reportOptionalMemberAccess] expect sotargeturce is there
        #     return False

        destParent = None
        try:
            destParent = mapping[modelParent._model.uuid, modelParent.uuid][0] # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
        except Exception as ex:
            LOGGER.fatal(f"[{process.__qualname__}] Functional Exchange parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.__class__,
                modelParent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                modelParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                modelParent.__class__,
                x._model.name,
                x._model.uuid,
                exc_info=ex
            )
            exit(str(ExitCodes.MergeFault))

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

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # Unknown fault creates broken Physical Architecture allocation
        # TODO: fix and eliminate
        if x.layer.name == "Physical Architecture":
            return True


        # FunctionalExchange mapping is based on match between the port components
        # Generel logic is
        # Exchange checks if either
        #  - FunctionPorts exist - legitimate case, updates mapping, note, functions are mapped after exchange to ensure correct ports merge
        #  - Function exist - legitimate case, updates mapping
        # 
        # In both cases - iterate through the exchanges and match them by name

        sourceFunctionPortMap = mapping.get((x.source._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect source exists in this context
        sourceFunctionMap = mapping.get((x.source.parent._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
        targetFunctionPortMap = mapping.get((x.target._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target exists in this context
        targetFunctionMap = mapping.get((x.target.parent._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

        if sourceFunctionMap is None or targetFunctionMap is None:
            # Fast fail, postpone exchange processing to Function existence
            return False

        ex = __findMatchingExchange(targetCollection, x, sourceFunctionMap, targetFunctionMap, mapping)
        if ex is not None:
            LOGGER.debug(
                f"[{process.__qualname__}] Record Function Exchange, name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                destParent.name,
                destParent.uuid,
                x._model.name,
                x._model.uuid,
            )

            # assume it's same to take first, but theme might be more
            mapping[(x._model.uuid, x.uuid)] = (ex, False)
        else:

            LOGGER.debug(
                f"[{process.__qualname__}] Create Function Exchange, name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
            )
            newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

            # if x.layer.name == "System Architecture" and x.layer.parent.name == "Steering-fl":
            # print ("!!!!!!!!!!!!!!!!!!!!!!!!", x)
            # print ("$$$$$$$$$$$$$$$$$$$$$$$$", newComp)
            #         # print ("@@@@@@@@@@@@@@@@@@@@@@@@", x.parent)
            #         # print ("########################", x.layer)
            #         exit()

            # TODO: fix PVMT
            # .property_value_groups = []
            # .property_values = []
            # .pvmt = 

            # TODO: find a way to copy these properties
            # newComp.progress_status = x.progress_status

            newComp.description = x.description
            newComp.is_multicast = x.is_multicast
            newComp.is_multireceive = x.is_multireceive
            newComp.is_visible_in_doc = x.is_visible_in_doc
            newComp.is_visible_in_lm = x.is_visible_in_lm
            newComp.name = x.name
            newComp.rate = x.rate
            newComp.rate_kind = x.rate_kind
            newComp.review = x.review
            newComp.sid = x.sid
            newComp.summary = x.summary
            newComp.weight = x.weight

            if x.selection is not None:
                newComp.selection = x.selection
            if x.status is not None:
                newComp.status = x.status
            if sourceFunctionPortMap is not None:
                newComp.source = sourceFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
            if targetFunctionPortMap is not None:
                newComp.target = targetFunctionPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
            if x.transformation is not None:
                newComp.transformation = x.transformation

            mapping[(x._model.uuid, x.uuid)] = (newComp, False)
    else:
        (cachedFunctionalExchange, fromLibrary) = cachedElement

        errors = {}
        # if cachedFunction.name != x.name:
        #     errors["name warn"] = (
        #         f"known name [{cachedFunction.name}], new name [{x.name}]"
        #     )
        # if cachedFunction.description != x.description:
        #     errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Fields does not match recorded, element uuid [%s], model name [%s], uuid [%s], warnings [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                errors,
            )


    return True
