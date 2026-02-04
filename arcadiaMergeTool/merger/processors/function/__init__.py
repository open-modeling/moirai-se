import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

import capellambse.model as m
from arcadiaMergeTool.merger.processors._processor import clone, process, doProcess, recordMatch

from . import allocation, port, realization

__all__ = [
    "allocation",
    "port",
    "realization"
]

LOGGER = getLogger(__name__)

T = mm.fa.AbstractFunction | mm.sa.SystemFunction | mm.la.LogicalFunction | mm.pa.PhysicalFunction | mm.oa.OperationalActivity

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        aggregation_kind = x.aggregation_kind,
        condition = x.condition,
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
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        visibility = x.visibility,
    ) 

    # TODO: fix PVMT
    # .property_value_groups = []
    # .property_values = []
    # .pvmt = 

    # TODO: find a way to copy these properties
    # newComp.behavior = x.behavior
    # newComp.default_value = x.default_value
    # newComp.local_postcondition = x.local_postcondition
    # newComp.local_precondition = x.local_precondition
    # newComp.max_card = x.max_card
    # newComp.max_length = x.max_length
    # newComp.max_value = x.max_value
    # newComp.min_card = x.min_card
    # newComp.min_length = x.min_length
    # newComp.min_value = x.min_value
    # newComp.null_value = x.null_value

    if x.status is not None:
        newComp.status = x.status

    return newComp

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Functions

    Parameters
    ==========
    x:
        Function to process
    dest:
        Destination model to add functions to
    src:
        Source model to take functions from
    base:
        Base model to check functions against
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

    if (isinstance(destParent, mm.sa.SystemAnalysis) 
        or isinstance(destParent, mm.la.LogicalArchitecture)
        or isinstance(destParent, mm.pa.PhysicalArchitecture)
        ) and destParent.root_function == x:
        mapping[(x._model.uuid, x.uuid)] = (destParent.root_function, False)
        return True
    elif isinstance(destParent, mm.oa.OperationalActivityPkg):
        targetCollection = destParent.activities
    elif (
        isinstance(destParent, mm.fa.AbstractFunction)
        or isinstance(destParent, mm.pa.PhysicalFunctionPkg)
        or isinstance(destParent, mm.sa.SystemFunctionPkg)
        or isinstance(destParent, mm.la.LogicalFunctionPkg)
    ):
        targetCollection = destParent.functions
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Function parent is not a valid parent, Function name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
