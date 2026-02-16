"""Find and merge Component Ports.

General Cases
1. Port is bounded to disjoint set of exchanges
2. Port is bounded to subset of exchanges
3. Port is bounded to superset of exchanges
4. Port is bounded to intersecting of exchanges

Merge logic
1. Port depends on ComponentExchange, not opposite
2. Exchange defines transferrable elements
3. If exchange from source model is not landed, delay port landing as well

For subset of exchanges - nothing to do
For superset of exchanges - add new exchanges to known port, mark those exchanges as policy violation
For disjoint set of exchanges - current port is the main port, mark port and exchanges as policy violation
For intersected set - merge fault, do not try to guess, request explicit model update
"""

import sys

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Postponed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import allocation

__all__ = [
    "allocation"
]

LOGGER = getLogger(__name__)

T =  mm.fa.ComponentPort
U = mm.fa.ComponentExchange
V = mm.cs.Component
W = mm.modellingcore.InformationsExchanger

def __findMatchingPort(x: T, targetCollection: m.ElementList[T], destParent: V, source: bool, srcExch: U | None = None)-> T | None:
    """Find port based on exchange props.

    Parameters
    ----------
    x:
        Source Element to check against
    targetCollection:
        Port collection to test
    destParent:
        destination parent to check
    source:
        Flag for checking source or target end of link
    srcExch:
        Exchange to match against

    Returns
    -------
    Matching port or None
    """
    if srcExch is None:
        for port in targetCollection:
            if len(port.exchanges) == 0 and port.name == x.name:
                return port
    else:
        for port in targetCollection:
            for ex in port.exchanges:
                # NOTE: weak match against exchange name
                # TODO: replace weak match with PVMT based strong match
                # if ((ex.name == srcExch.name and port.parent == destParent and x.orientation == port.orientation)
                #     or (source and ex.source is not None and ex.source.name == x.name)
                #     or (not source and ex.target is not None and ex.target.name == x.name)):
                if ex.name == srcExch.name and port.parent == destParent and x.orientation == port.orientation:
                    return port

    return None

@clone.register
def __createCompoentPort(x: T, targetCollection: m.ElementList[T], _mapping: MergerElementMappingMap) -> T:
    LOGGER.debug(
        f"[{clone.__qualname__}] Create a non-library Component Port name [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )
    return targetCollection.create(helpers.xtype_of(x._element),
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


@process.register
def _(
    x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    targetCollection: m.ElementList[T]

    destParent = getDestParent(x, mapping)

    if (isinstance(destParent, (mm.pa.PhysicalComponent, mm.la.LogicalComponent, mm.sa.SystemComponent))
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
        sys.exit(str(ExitCodes.MergeFault))

    return targetCollection

@match.register
def _(x: T,
    destParent: V,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    portCandidates: dict[str, W] = {}
    postpone = False
    newPort = None
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
            postpone = True
            continue

        mappedEx: U = exMap[0] # pyright: ignore[reportAssignmentType] expect it's correct type
        if ex.source == x:
            # when exchange is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedEx.source is None:
                # potential superset case - exchange exists, but not mapped
                # find first matching port with exchange sharing same properties
                port= __findMatchingPort(x, coll, destParent, True, ex)
                if port is not None:
                    portCandidates[port.uuid] = port
                    mappedEx.source = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, coll, mapping)
                    portCandidates[newPort.uuid] = newPort
                    mappedEx.source = newPort
                    mapping[(x._model.uuid, x.uuid)] = (newPort, False)
            else:
                portCandidates[mappedEx.source.uuid] = mappedEx.source
        elif ex.target == x:
            # when exchange is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedEx.target is None:
                # potential superset case - exchange exists, but not mapped
                # find first matching port with exchange sharing same properties
                port = __findMatchingPort(x, coll, destParent, False, ex)
                if port is not None:
                    portCandidates[port.uuid] = port
                    mappedEx.target = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, coll, mapping)
                    portCandidates[newPort.uuid] = newPort
                    mappedEx.target = newPort
                    mapping[(x._model.uuid, x.uuid)] = (newPort, False)
            else:
                portCandidates[mappedEx.target.uuid] = mappedEx.target

    if postpone:
        if newPort is not None:
            # if new port was created, record it in the mapping to avoid duplication
            mapping[(x._model.uuid, x.uuid)] = (newPort, False)
        return Postponed

    if len(portCandidates) == 0:
        # port without exchanges
        port = __findMatchingPort(x, coll, destParent, False)
        if port is None:
            port = __createCompoentPort(x, coll, mapping)
        mapping[(x._model.uuid, x.uuid)] = (port, False)
        portCandidates[port.uuid] = port

    return list(portCandidates.values())
