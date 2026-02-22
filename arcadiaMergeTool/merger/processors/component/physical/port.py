"""Find and merge Physical Ports.

General Cases
1. Port is bounded to disjoint set of links
2. Port is bounded to subset of links
3. Port is bounded to superset of links
4. Port is bounded to intersecting of links

Merge logic
1. Port depends on Physical Link, not opposite
2. Physical Link defines transferrable elements
3. If link from source model is not landed, delay port landing as well

For subset of links - nothing to do
For superset of links - add new links to known port, mark those links as policy violation
For disjoint set of links - current port is the main port, mark port and links as policy violation
For intersected set - merge fault, do not try to guess, request explicit model update
"""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    Postponed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = mm.cs.PhysicalPort
U = mm.cs.PhysicalLink
V = mm.cs.Component
W = mm.cs.AbstractPhysicalLinkEnd

def __findMatchingPort(x: T, targetCollection: m.ElementList[T], _destParent: V, source: bool, srcExch: U | None = None)-> T | None:
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
            if len(port.links) == 0 and port.name == x.name:
                return port
    else:
        for port in targetCollection:
            for ex in port.links:
                # NOTE: weak match against exchange name
                # TODO: replace weak match with PVMT based strong match
                if (ex.name == srcExch.name
                    or (source and ex.source is not None and ex.source.name == x.name)
                    or (not source and ex.target is not None and ex.target.name == x.name)):
                    return port

    return None

@clone.register
def __createCompoentPort(x: T, targetCollection: m.ElementList[T], _mapping: MergerElementMappingMap) -> T:
    LOGGER.debug(
        f"[{process.__qualname__}] Create a non-library Physical Port name [%s], uuid [%s], model name [%s], uuid [%s]",
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
        name = x.name,
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
    targetCollection = None

    destParent: V = getDestParent(x, mapping) # pyright: ignore[reportAssignmentType] expect component is correct type

    if (isinstance(destParent, (mm.pa.PhysicalComponent, mm.la.LogicalComponent, mm.sa.SystemComponent))
    ):
        targetCollection = destParent.physical_ports # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        return Fault

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
    for ex in x.links:
        exMap = mapping.get((ex._model.uuid, ex.uuid))
        if exMap is None:
            # for unmapped links - wait until they are merged into the model
            # do not proceed with other links, it will be done in one shot
            LOGGER.debug(
                f"[{process.__qualname__}] dependent Physical Link is not mapped, link name [%s], uuid [%s], model name [%s], uuid [%s]",
                ex.name,
                ex.uuid,
                x._model.name,
                x._model.uuid,
            )
            postpone = True
            continue

        mappedLink: U = exMap[0] # pyright: ignore[reportAssignmentType] expect physical link is correct type
        if ex.source == x:
            # when link is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedLink.source is None:
                # potential superset case - link exists, but not mapped
                # find first matching port with link sharing same properties
                port= __findMatchingPort(x, coll, destParent, True,  ex)
                if port is not  None:
                    portCandidates[port.uuid] = port
                    mappedLink.source = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, coll, mapping)
                    portCandidates[newPort.uuid] = newPort
                    mappedLink.source = newPort
                    mapping[(x._model.uuid, x.uuid)] = (newPort, False)
            else:
                portCandidates[mappedLink.source.uuid] = mappedLink.source
        if ex.target == x:
            # when link is landed from source model it does not have port mapped
            # port mapping performed here to avoid recursive model processing
            if mappedLink.target is None:
                if mappedLink.source is None:
                    # sanity check, attempt to set target on port with no source crashes
                    LOGGER.warning(
                        f"[{process.__qualname__}] Target Physical Port assigned before source, postpone processing to avoid crash. Physical Port name [%s], uuid [%s], link name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                        x.name,
                        x.uuid,
                        mappedLink.name,
                        mappedLink.uuid,
                        destParent.name,
                        destParent.uuid,
                        x._model.name,
                        x._model.uuid,
                    )
                    postpone = True
                    continue

                # potential superset case - link exists, but not mapped
                # find first matching port with link sharing same properties
                port = __findMatchingPort(x, coll, destParent, False, ex)
                if port is not None:
                    portCandidates[port.uuid] = port
                    mappedLink.target = port
                else:
                    # port was not mapped, add port to the collection
                    newPort = __createCompoentPort(x, coll, mapping)
                    portCandidates[newPort.uuid] = newPort
                    mappedLink.target = newPort
                    mapping[(x._model.uuid, x.uuid)] = (newPort, False)
            else:
                portCandidates[mappedLink.target.uuid] = mappedLink.target

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
