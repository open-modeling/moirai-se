import capellambse.metamodel as mm
from capellambse import helpers
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors._processor import process
from capellambse.metamodel import capellamodeller as ca
from capellambse.model import ModelElement
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: ca.SystemEngineering,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = None
        if isinstance(x, ca.SystemEngineering):
            package = dest.model.project
        
        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True

@process.register
def _(
    x: mm.epbs.PhysicalArchitectureRealization | mm.pa.LogicalArchitectureRealization | mm.la.SystemAnalysisRealization | mm.sa.OperationalAnalysisRealization,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge  Architecture Realizations

    Parameters
    ==========
    x:
         Architecture Realization to process
    dest:
        Destination model to add Architecture Realizations to
    src:
        Source model to take Architecture Realizations from
    base:
        Base model to check Architecture Realizations against
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

    if isinstance(destParent, mm.epbs.EPBSArchitecture):
        targetCollection = destParent.physical_architecture_realizations
    elif isinstance(destParent, mm.pa.PhysicalArchitecture):
        targetCollection = destParent.logical_architecture_realizations
    elif isinstance(destParent, mm.la.LogicalArchitecture):
        targetCollection = destParent.system_analysis_realizations
    elif isinstance(destParent, mm.sa.SystemAnalysis):
        targetCollection = destParent.operational_analysis_realizations
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Architecture Realization parent is not a valid parent, Port uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.uuid,
            x.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        exit(str(ExitCodes.MergeFault))

    mappedSource = mapping.get((x._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect source is already there
    mappedTarget = mapping.get((x._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target is already there
    if mappedSource is None or mappedTarget is None:
        # if source or target is not mapped, postpone allocation processing
        return False
    
    matchingPort = list(filter(lambda y: y.source == mappedSource[0] and x.target == mappedTarget[0], targetCollection)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe

    if (len(matchingPort) > 0):
        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingPort[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create new Architecture Realization uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.uuid,
            x.parent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            x.parent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
            x.parent.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )

        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
            source = mappedSource[0],
            target = mappedTarget[0],
            description = x.description,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
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

        if x.status is not None:
            newComp.status = x.status

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)


    return True
