import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process

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
    x: mm.fa.ComponentExchange,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Component Exchanges

    Parameters
    ==========
    x:
        Component exchange to process
    dest:
        Destination model to add component exchanges to
    src:
        Source model to take component exchanges from
    base:
        Base model to check component exchanges against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        # for Component exchange - if not found in cache, in general it's a violation of the merging rules
        # at this point all component exchanges must come from base library
        LOGGER.debug(
            f"[{process.__qualname__}] New component found, name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # recursively check all direct parents for existence and continue only if parents agree
        modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
        if not process(modelParent, dest, src, base, mapping):
            return False
        
        destParent = None
        try:
            destParent = mapping[modelParent._model.uuid, modelParent.uuid][0] # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
        except Exception as ex:
            LOGGER.fatal(f"[{process.__qualname__}] Component parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

        if (isinstance(destParent, mm.sa.SystemComponentPkg)
            or isinstance(destParent, mm.la.LogicalComponentPkg)
            or isinstance(destParent, mm.pa.PhysicalComponentPkg)
        ):
            targetCollection = destParent.exchanges
        elif (isinstance(destParent, mm.pa.PhysicalComponent)
            or isinstance(destParent, mm.la.LogicalComponent)
            or isinstance(destParent, mm.sa.SystemComponent)
        ):
            targetCollection = destParent.component_exchanges # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Component exchange parent is not a valid parent, Component exchange name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

        # ComponentExchange mapping is based on match between the port components
        # Generel logic is
        # Exchange checks if either
        #  - ComponentPorts exist - legitimate case, updates mapping, note, components are mapped after exchange to ensure correct ports merge
        #  - Components exist - legitimate case, updates mapping
        # 
        # In both cases - iterate through the exchanges and match them by name

        sourceComponentPortMap = mapping.get((x.source._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect source exists in this context
        sourceComponentMap = mapping.get((x.source.parent._model.uuid, x.source.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
        targetComponentPortMap = mapping.get((x.target._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target exists in this context
        targetComponentMap = mapping.get((x.target.parent._model.uuid, x.target.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

        if sourceComponentMap is None or targetComponentMap is None:
            # Fast fail, postpone exchange processing to component existence
            return False

        ex = __findMatchingExchange(targetCollection, x, sourceComponentMap, targetComponentMap, mapping)
        if ex is not None:
            # coming here means that component exchange was added in a project, not taken from the library
            LOGGER.error(
                f"[{process.__qualname__}] Non-library component exchange detected. Component exchange name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
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
                f"[{process.__qualname__}] Create a non-library component exchange name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
            )
            newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

            # if x.layer.name == "System Architecture" and x.layer.parent.name == "Steering-fl":
            #         print ("!!!!!!!!!!!!!!!!!!!!!!!!", x)
            #         print ("$$$$$$$$$$$$$$$$$$$$$$$$", newComp)
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
            newComp.is_oriented = x.is_oriented
            newComp.is_visible_in_doc = x.is_visible_in_doc
            newComp.is_visible_in_lm = x.is_visible_in_lm
            newComp.kind =x.kind
            newComp.name = x.name
            newComp.review = x.review
            newComp.sid = x.sid
            newComp.summary = x.summary

            if x.status is not None:
                newComp.status = x.status
            if sourceComponentPortMap is not None:
                newComp.source = sourceComponentPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model
            if targetComponentPortMap is not None:
                newComp.target = targetComponentPortMap # pyright: ignore[reportAttributeAccessIssue] expect source exists on model

            mapping[(x._model.uuid, x.uuid)] = (newComp, False)
    else:
        (cachedComponent, fromLibrary) = cachedElement

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
