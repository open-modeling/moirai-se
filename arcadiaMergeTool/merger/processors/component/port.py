import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.model import ModelElement

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process

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

def __createCompoentPort(x: mm.fa.ComponentPort, targetCollection: m._obj.ElementList) -> mm.fa.ComponentPort:
    """Create port in model

    Parameters
    ==========
    x: 
        Source to copy port properties from
    targetCollection:
        Collection to add new port into

    """

    LOGGER.debug(
        f"[{process.__qualname__}] Create a non-library Component Port name [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )
    newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
        aggregation_kind = x.aggregation_kind,
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
        kind = x.kind,
        name = x.name,
        orientation = x.orientation,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        visibility = x.visibility,
    ) 

    # TODO: fix PVMT
    # .applied_property_value_groups = []
    # .applied_property_values = []
    # .property_value_groups = []
    # .property_values = []
    # .pvmt = 

    # TODO: find a way to copy these properties
    # .default_value = None
    # .max_card = None
    # .max_length = None
    # .max_value = None
    # .min_card = None
    # .min_length = None
    # .min_value = None
    # .null_value = None
    # newComp.progress_status = x.progress_status

    if x.status is not None:
        newComp.status = x.status
    if x.type is not None:
        newComp.type = x.type

    return newComp

@process.register
def _(
    x: mm.fa.ComponentPort,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Component Ports

    Parameters
    ==========
    x:
        Component port to process
    dest:
        Destination model to add component ports to
    src:
        Source model to take component ports from
    base:
        Base model to check component ports against
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

    if (isinstance(destParent, mm.sa.SystemComponentPkg)
        or isinstance(destParent, mm.la.LogicalComponentPkg)
        or isinstance(destParent, mm.pa.PhysicalComponent)
        or isinstance(destParent, mm.la.LogicalComponent)
        or isinstance(destParent, mm.sa.SystemComponent)
    ):
        targetCollection = destParent.ports # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Component Port parent is not a valid parent, Component Port name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    # 1. Port depends on ComponentExchange, not opposite
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
                f"[{process.__qualname__}] dependent Component Exchange is not mapped, exchange name [%s], uuid [%s], model name [%s], uuid [%s]",
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
            f"[{process.__qualname__}] Several port candidates detected, cannot proceed with merge. Component port name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
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
            # coming here means that component was directly added into the model, not taken from the library
            LOGGER.error(
                f"[{process.__qualname__}] Non-library component port detected. Component port name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
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
