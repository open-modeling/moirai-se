from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors._processor import clone, doProcess, process
from capellambse.metamodel import pa
import capellambse.model as m
from arcadiaMergeTool.merger.processors.recordMatch import recordMatch
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: pa.PhysicalArchitecture,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        element = dest.model.pa
        mapping[(x._model.uuid, x.uuid)] = (element, False)

    return True

@process.register
def _(
    x: pa.PhysicalComponentPkg,
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
        package = dest.model.pa.component_pkg
        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return True

T = pa.PhysicalFunctionPkg

@clone.register
def _ (srcEl: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(srcEl._element),
        description = srcEl.description,
        is_visible_in_doc = srcEl.is_visible_in_doc,
        is_visible_in_lm = srcEl.is_visible_in_lm,
        name = srcEl.name,
        review = srcEl.review,
        sid = srcEl.sid,
        summary = srcEl.summary,
    ) 

    # TODO: fix PVMT
    # .applied_property_value_groups = []
    # .applied_property_values = []
    # .property_value_groups = []
    # .property_values = []
    # .pvmt = 

    if srcEl.status is not None:
        newComp.status = srcEl.status

    return newComp

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Function Packages

    Parameters
    ==========
    x:
        Function Package to process
    dest:
        Destination model to add Function Packages to
    src:
        Source model to take Function Packages from
    base:
        Base model to check Function Packages against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
    if not doProcess(modelParent, dest, src, base, mapping): # pyright: ignore[reportArgumentType] expect modelParent is of type ModelElement
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

    if isinstance(destParent, pa.PhysicalArchitecture):
        # HACK: use hardcoded property define a root function package
        mapping[(x._model.uuid, x.uuid)] = (destParent.function_pkg, False) # pyright: ignore[reportArgumentType] assume root function_pkg is always there
        return True
    elif (isinstance(destParent, T)
            or isinstance(destParent, pa.PhysicalFunction)
    ):
        targetCollection = destParent.packages
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Invalid parent, elemment name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    # use weak match by name
    # TODO: implement strong match by PVMT properties
    matchList = list(filter(lambda y: y.name == x.name, targetCollection))

    return recordMatch(matchList, x, destParent, targetCollection, mapping)
