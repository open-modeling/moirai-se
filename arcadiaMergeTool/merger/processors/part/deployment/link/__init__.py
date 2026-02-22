"""Find and merge Part Deployment Links.

Part Deployment Link mapping is based on match between the port Part Deployment Links
Generel logic is
Part Deployment Link checks if either
    - Parts exist - legitimate case, updates mapping

In both cases - iterate through the linkss and match them by name
"""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import (
    MergerElementMappingMap,
)
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Fault,
    Postponed,
    clone,
    doProcess,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = mm.pa.deployment.PartDeploymentLink

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    sourcePartDeploymentLinkMap = mapping.get((x.deployed_element.parent._model.uuid, x.deployed_element.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetPartDeploymentLinkMap = mapping.get((x.location.parent._model.uuid, x.location.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context
    sourcePartDeploymentLink = sourcePartDeploymentLinkMap[0] if sourcePartDeploymentLinkMap is not None else None
    targetPartDeploymentLink = targetPartDeploymentLinkMap[0] if targetPartDeploymentLinkMap is not None else None

    srcLinkMapping = mapping.get((x._model.uuid, x.uuid))
    srcLinkMappedLink: T = srcLinkMapping[0] if srcLinkMapping is not None else None # pyright: ignore[reportAssignmentType] expect element has correct type

    lst: list[T] = []

    if srcLinkMappedLink is not None:
        # for already mapped Part Deployment Links no need no do something
        lst.append(srcLinkMappedLink)
        return lst

    for tgtLink in coll:

        # NOTE: weak match against Part Deployment Link name
        # TODO: replace weak match with PVMT based strong match
        if (x.deployed_element is not None and tgtLink.deployed_element is not None
            and tgtLink.deployed_element.name == x.deployed_element.name):
            # for case of name we have to do complex check
            # 1. there might be several Part Deployment Links with the same name
            # 2. Part Deployment Link is mapped before Comp and may have empty source and target

            if tgtLink.deployed_element is None or tgtLink.location is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one Part Deployment Link from another
                # we might be facing potentinal twin Part Deployment Link, but need to postpone processing
                # True means that Part Deployment Link processing must be postponed
                return Postponed

            tgtLinkMappedSourceFunc = mapping.get((tgtLink._model.uuid, tgtLink.deployed_element.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect deployed_element is there
            tgtLinkMappedTargetFunc = mapping.get((tgtLink._model.uuid, tgtLink.location.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect location is there

            if tgtLinkMappedSourceFunc is not None and tgtLinkMappedTargetFunc is not None and tgtLinkMappedSourceFunc == sourcePartDeploymentLink and tgtLinkMappedTargetFunc == targetPartDeploymentLink:
                # if name, source function and target function are equal, map existing Part Deployment Link to a candidate
                lst.append(tgtLink)

    # if collection is exceeded, allow to add new Part Deployment Link
    return lst

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    sourcePartDeploymentLinkMap = mapping.get((x.deployed_element.parent._model.uuid, x.deployed_element.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetPartDeploymentLinkMap = mapping.get((x.location.parent._model.uuid, x.location.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context
    sourcePartDeploymentLink = sourcePartDeploymentLinkMap[0] if sourcePartDeploymentLinkMap is not None else None
    targetPartDeploymentLink = targetPartDeploymentLinkMap[0] if targetPartDeploymentLinkMap is not None else None

    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    )

    if sourcePartDeploymentLinkMap is not None:
        newComp.deployed_element = sourcePartDeploymentLink # pyright: ignore[reportAttributeAccessIssue] expect deployed_element exists on model
    if targetPartDeploymentLinkMap is not None:
        newComp.location = targetPartDeploymentLink # pyright: ignore[reportAttributeAccessIssue] expect location exists on model
    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.deployed_element, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect source exists
        return Postponed
    if doProcess(x.location, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect target exists
        return Postponed
    # Fast fail, postpone exchange processing to component
    # Note, functions are deployed independently to the physical links
    # at least for now, this means correct deployment order is
    # 1. components
    # 2. deployment links
    # 3. ports
    return Continue

@process.register
def _(
    x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    targetCollection = None

    destParent = getDestParent(x, mapping)

    if (isinstance(destParent, mm.cs.Part)
    ):
        targetCollection = destParent.deployment_links # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        return Fault

    return targetCollection
