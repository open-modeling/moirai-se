import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

LOGGER = getLogger(__name__)

def __findMatchingPort(targetCollection, srcExch, destParent, source: bool)-> mm.fa.FunctionPort | None:
    """Find port based on exchange props
    
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
    for port in targetCollection:
        for ex in port.exchanges:
            # NOTE: weak match against exchange name
            # TODO: replace weak match with PVMT based strong match
            if ex.name == srcExch.name and port.parent == destParent and ((source and ex.source is None) or (not source and ex.target is None)) :
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
    newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
        is_control = x.is_control,
        is_control_type = x.is_control_type,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        node_kind = x.node_kind,
        ordering = x.ordering,
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

    # TODO: find a way to copy these properties

    if x.selection is not None:
        newComp.selection = x.selection
    if x.represented_component_port is not None:
        newComp.represented_component_port = x.represented_component_port
    if x.status is not None:
        newComp.status = x.status


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
                destParent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                destParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                destParent.__class__,
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
    postpone = False
    for ex in x.exchanges:
        exMap = mapping.get((ex._model.uuid, ex.uuid))
        if exMap is None:
            # for unmapped exchanges - wait until they are merged into the model
            LOGGER.debug(
                f"[{process.__qualname__}] dependent Functional Exchange is not mapped, exchange name [%s], uuid [%s], model name [%s], uuid [%s]",
                ex.name,
                ex.uuid,
                x._model.name,
                x._model.uuid,
            )
            # keep port in queue if any single exchange is not mapped
            # but keep returning to proceed with updated exchanges
            postpone = True
            continue
            
        mappedEx = exMap[0]
        if ex.source == x:
            # when exchange is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedEx.source is None:
                # potential superset case - exchange exists, but not mapped
                # find first matching port with exchange sharing same properties
                port= __findMatchingPort(targetCollection, ex, destParent, True)
                if port is not None:
                    portCandidates[port.uuid] = port
                    mappedEx.source = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, targetCollection)
                    portCandidates[newPort.uuid] = newPort
                    mappedEx.source = newPort
        elif ex.target == x:
            # when exchange is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedEx.target is None:
                # potential superset case - exchange exists, but not mapped
                # find first matching port with exchange sharing same properties
                port = __findMatchingPort(targetCollection, ex, destParent, False)
                if port is not None:
                    portCandidates[port.uuid] = port
                    mappedEx.target = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, targetCollection)
                    portCandidates[newPort.uuid] = newPort
                    mappedEx.target = newPort
    if postpone:
        return False

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

    return True
