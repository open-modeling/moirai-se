import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from ._processor import process

LOGGER = getLogger(__name__)

def __findMatchingPort(coll, exch):
    """Find port basen on exchange props
    
    Parameters
    ==========
    coll:
        Port collection to test
    exch:
        Exchange to match against

    Returns
    =======
    Matching port or None
    """
    for port in coll:
        for ex in port.exchanges:
            # NOTE: weak match against exchange name
            # TODO: replace weak match with PVMT based strong match
            if ex.name == exch.name:
                return port

def __createCompoentPort(x: mm.fa.FunctionPort, targetCollection: m._obj.ElementList) -> mm.fa.FunctionPort:
    """Create port in model

    Parameters
    ==========
    x: 
        Source to copy port properties from
    targetCollection:
        Collection to add new port into

    """

    LOGGER.debug(
        f"[{process.__qualname__}] Create Function Port name [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )
    newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

    # TODO: fix PVMT
    # .applied_property_value_groups = []
    # .applied_property_values = []
    # .property_value_groups = []
    # .property_values = []
    # .pvmt =

    # TODO: find a way to copy these properties

    newComp.is_control = x.is_control
    newComp.is_control_type = x.is_control_type
    newComp.is_visible_in_doc = x.is_visible_in_doc
    newComp.is_visible_in_lm = x.is_visible_in_lm
    newComp.name = x.name
    newComp.node_kind = x.node_kind
    newComp.ordering = x.ordering
    newComp.review = x.review
    newComp.sid = x.sid
    newComp.summary = x.summary

    if x.selection is not None:
        newComp.selection = x.selection
    if x.represented_component_port is not None:
        newComp.represented_component_port = x.represented_component_port
    if x.status is not None:
        newComp.status = x.status
    if x.type is not None:
        newComp.type = x.type

    return newComp

@process.register
def _(
    x: mm.fa.FunctionPort,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Functuon Ports

    Parameters
    ==========
    x:
        Functuon port to process
    dest:
        Destination model to add functuon ports to
    src:
        Source model to take functuon ports from
    base:
        Base model to check functuon ports against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        # for Function port - if not found in cache, in general it's a violation of the merging rules
        # at this point all function ports must come from base library
        LOGGER.debug(
            f"[{process.__qualname__}] New Function Port found, name [%s], uuid [%s], model name [%s], uuid [%s]",
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
            LOGGER.fatal(f"[{process.__qualname__}] Function Port parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

        if (isinstance(destParent, mm.pa.PhysicalFunction)
            or isinstance(destParent, mm.la.LogicalFunction)
            or isinstance(destParent, mm.sa.SystemFunction)
            or isinstance(destParent, mm.oa.OperationalActivity)
        ):
            if isinstance(x, mm.fa.FunctionInputPort):
                targetCollection = destParent.inputs
            elif isinstance(x, mm.fa.FunctionOutputPort):
                targetCollection = destParent.outputs
            else:
                LOGGER.fatal(f"[{process.__qualname__}] Unknown Function Port type, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Function Port parent is not a valid parent, Function Port name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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


        # General Cases
        # 1. Port is bounded to disjoint set of exchanges
        # 2. Port is bounded to subset of exchanges
        # 3. Port is bounded to superset of exchanges
        # 4. Port is bounded to intersecting of exchanges

        # Merge logic
        # 1. Port depends on FunctionExchange, not opposite
        # 2. Exchange defines transferrable elements
        # 3. If exchange from source model is not landed, delay port landing as well
        # 
        # For subset of exchanges - nothing to do
        # For superset of exchanges - add new exchanges to known port, mark those exchanges as policy violation
        # For disjoint set of exchanges - current port is the main port, mark port and exchanges as policy violation
        # For intersected set - merge fault, do not try to guess, request explicit model update

        portCandidates = {}
        for ex in x.exchanges:
            exMap = mapping.get((ex._model.uuid, ex.uuid))
            if exMap is None:
                # for unmapped exchanges - wait until they are merged into the model
                # do not proceed with other exchanges, it will be done in one shot
                LOGGER.debug(
                    f"[{process.__qualname__}] dependent Function Exchange is not mapped, exchange name [%s], uuid [%s], model name [%s], uuid [%s]",
                    ex.name,
                    ex.uuid,
                    x._model.name,
                    x._model.uuid,
                )
                
                return False
            mappedEx = exMap[0]
            if ex.source == x:
                # when exchange is landed from source model it does not have port mapped
                # port mapping performed here to avoid recursive model processing
                if mappedEx.source is None:
                    # potential superset case - exchange exists, but not mapped
                    # find first matching port with exchange sharing same properties
                    port = __findMatchingPort(targetCollection, ex)
                    if port:
                        portCandidates[port.uuid] = port
                        mappedEx.source = port
                    else:
                        # port was not mapped, add port to the collection
                        newPort = __createCompoentPort(x, targetCollection)
                        portCandidates[newPort.uuid] = newPort
                        mappedEx.source = newPort
                        
            if ex.target == x:
                # when exchange is landed from source model it does not have port mapped
                # port mapping performed here to avoid recursive model processing
                if mappedEx.target is None:
                    # potential superset case - exchange exists, but not mapped
                    # find first matching port with exchange sharing same properties
                    port = __findMatchingPort(targetCollection, ex)
                    if port:
                        portCandidates[port.uuid] = port
                        mappedEx.target = port
                    else:
                        # port was not mapped, add port to the collection
                        newPort = __createCompoentPort(x, targetCollection)
                        portCandidates[newPort.uuid] = newPort
                        mappedEx.target = newPort

        if len(portCandidates.items()) > 1:
            # potential intersected set case, go fault
            LOGGER.fatal(
                f"[{process.__qualname__}] Several port candidates detected, cannot proceed with merge. Function Port name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                destParent.name,
                destParent.uuid,
                x._model.name,
                x._model.uuid,
                extra={"ports": portCandidates}
            )
            exit(str(ExitCodes.MergeFault))

        if len(portCandidates.items()) == 1:
            port = list(portCandidates.values()).pop()
            mappedPort = mapping.get((port._model.uuid, port.uuid))
            if not mappedPort:
                # coming here means that function was directly added into the model, not taken from the library
                LOGGER.debug(
                    f"[{process.__qualname__}] Adding Function Port into model name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                    x.name,
                    x.uuid,
                    destParent.name,
                    destParent.uuid,
                    x._model.name,
                    x._model.uuid,
                )
                mapping[(x._model.uuid, x.uuid)] = (port, False)
                mapping[(port._model.uuid, port.uuid)] = (port, False)
        else:
            # port without exchanges
            newPort = __createCompoentPort(x, targetCollection)
            mapping[(newPort._model.uuid, newPort.uuid)] = (newPort, False)
            mapping[(x._model.uuid, x.uuid)] = (newPort, False)

    else:
        (cachedFunction, fromLibrary) = cachedElement

        errors = {}
        if cachedFunction.name != x.name:
            errors["name warn"] = (
                f"known name [{cachedFunction.name}], new name [{x.name}]"
            )
        if cachedFunction.name != x.name:
            errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Function Port fields does not match known, Function Port name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                extra=errors,
            )

    return True
