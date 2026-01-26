import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.model import ModelElement

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingEntry, MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

LOGGER = getLogger(__name__)

def __findMatchingLink(targetCollection: m.ElementList[mm.pa.deployment.PartDeploymentLink], srcLink: mm.pa.deployment.PartDeploymentLink, 
                           mappedSourcFuncEntry: MergerElementMappingEntry | None, 
                           mappedTargetFuncEntry: MergerElementMappingEntry | None, 
                           mapping: MergerElementMappingMap) -> ModelElement | bool:
    """Find Comp basen on links props
    
    Parameters
    ==========
    targetCollection:
        Part Deployment Links collection to lookup at
    srcLink:
        Part Deployment Links to match against

    Returns
    =======
    Matching Comp or None
    """
    srcLinkMapping = mapping.get((srcLink._model.uuid, srcLink.uuid))
    srcLinkMappedLink = srcLinkMapping[0] if srcLinkMapping is not None else None

    if srcLinkMappedLink is not None:
        # for already mapped Part Deployment Links no need no do something
        return srcLinkMappedLink

    for tgtLink in targetCollection:

        # NOTE: weak match against Part Deployment Link name
        # TODO: replace weak match with PVMT based strong match
        if (srcLink.deployed_element is not None and tgtLink.deployed_element is not None
            and tgtLink.deployed_element.name == srcLink.deployed_element.name):
            # for case of name we have to do complex check
            # 1. there might be several Part Deployment Links with the same name
            # 2. Part Deployment Link is mapped before Comp and may have empty source and target

            if tgtLink.deployed_element is None or tgtLink.location is None:
                # when one of ports is not mapped, don't create twins in same collection
                # otherwise it will not be possible to distict one Part Deployment Link from another
                # we might be facing potentinal twin Part Deployment Link, but need to postpone processing
                # True means that Part Deployment Link processing must be postponed
                return True

            tgtLinkMappedSourceFunc = mapping.get((tgtLink._model.uuid, tgtLink.deployed_element.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect deployed_element is there
            tgtLinkMappedTargetFunc = mapping.get((tgtLink._model.uuid, tgtLink.location.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue] expect location is there

            if tgtLinkMappedSourceFunc is not None and tgtLinkMappedTargetFunc is not None and tgtLinkMappedSourceFunc == mappedSourcFuncEntry and tgtLinkMappedTargetFunc == mappedTargetFuncEntry:
                # if name, source function and target function are equal, map existing Part Deployment Link to a candidate
                return tgtLink

    # if collection is exceeded, allow to add new Part Deployment Link
    return False

@process.register
def _(
    x: mm.pa.deployment.PartDeploymentLink,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Part Deployment Links

    Parameters
    ==========
    x:
        Part Deployment Link to process
    dest:
        Destination model to add Part Deployment Links to
    src:
        Source model to take Part Deployment Links from
    base:
        Base model to check Part Deployment Links against
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


    if (isinstance(destParent, mm.cs.Part)
    ):
        targetCollection = destParent.deployment_links # pyright: ignore[reportAttributeAccessIssue] expect ports are already there
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Part Deployment Link parent is not a valid parent, Part Deployment Link name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    # Part Deployment Link mapping is based on match between the port Part Deployment Links
    # Generel logic is
    # Part Deployment Link checks if either
    #  - Parts exist - legitimate case, updates mapping
    # 
    # In both cases - iterate through the linkss and match them by name

    doProcess(x.deployed_element, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expected x of right type
    doProcess(x.location, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expected x of right type

    sourcePartDeploymentLinkMap = mapping.get((x.deployed_element.parent._model.uuid, x.deployed_element.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect source exists in this context
    targetPartDeploymentLinkMap = mapping.get((x.location.parent._model.uuid, x.location.parent.uuid)) # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess] expect target exists in this context

    if sourcePartDeploymentLinkMap is None or targetPartDeploymentLinkMap is None:
        # Fast fail, postpone links processing to Part Deployment Link existence
        return False
    
    sourcePartDeploymentLink = sourcePartDeploymentLinkMap[0]
    targetPartDeploymentLink = targetPartDeploymentLinkMap[0]

    ex = __findMatchingLink(targetCollection, x, sourcePartDeploymentLink, targetPartDeploymentLink, mapping) # pyright: ignore[reportArgumentType] expect links exists

    if ex is True:
        # postpone exececution on boolean true
        # TODO: add more convenient return type
        LOGGER.debug(
            f"[{process.__qualname__}] No Part Deployment Link match, postpone processing of Part Deployment Link uuid [%s], model name [%s], uuid [%s]",
            x.uuid,
            x._model.name,
            x._model.uuid,
        )
        return False

    if ex is not False:
        # coming here means that Part Deployment Link was added in a project, not taken from the library
        # TODO: add to report
        LOGGER.error(
            f"[{process.__qualname__}] Non-library Part Deployment Link detected. Part Deployment Link uuid [%s], deployed element [%s], uuid [%s], arent name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.uuid,
            x.deployed_element.name, # pyright: ignore[reportOptionalMemberAccess] expect element is there
            x.deployed_element.uuid, # pyright: ignore[reportOptionalMemberAccess] expect element is there
            destParent.name,
            destParent.uuid,
            x._model.name,
            x._model.uuid,
        )

        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (ex, False)
    else:

        LOGGER.debug(
            f"[{process.__qualname__}] Create a non-library Part Deployment Link uuid [%s], deployed element [%s], uuid [%s], model name [%s], uuid [%s]",
            x.uuid,
            x.deployed_element.name, # pyright: ignore[reportOptionalMemberAccess] expect element is there
            x.deployed_element.uuid, # pyright: ignore[reportOptionalMemberAccess] expect element is there
            x._model.name,
            x._model.uuid,
        )

        newComp = targetCollection.create(helpers.xtype_of(x._element),
            description = x.description,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
        ) 

        # TODO: fix PVMT
        # .property_value_groups = []
        # .property_values = []
        # .pvmt = 

        if x.status is not None:
            newComp.status = x.status
            
        if sourcePartDeploymentLinkMap is not None:
            newComp.deployed_element = sourcePartDeploymentLink # pyright: ignore[reportAttributeAccessIssue] expect deployed_element exists on model
        if targetPartDeploymentLinkMap is not None:
            newComp.location = targetPartDeploymentLink # pyright: ignore[reportAttributeAccessIssue] expect location exists on model

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
