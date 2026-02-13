
from arcadiaMergeTool.helpers import ExitCodes
import capellambse.model as m
from arcadiaMergeTool.merger.processors._processor import clone, process, doProcess
import capellambse.metamodel.information as inf
from arcadiaMergeTool.merger.processors.recordMatch import recordMatch
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from capellambse import helpers

from arcadiaMergeTool import getLogger

from . import datavalue, datatype, exchange_item

__all__ = [
    "datatype",
    "datavalue",
    "exchange_item",
]

LOGGER = getLogger(__name__)

T = inf.Unit

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    ) 

    # TODO: fix PVMT
    # .applied_property_value_groups = 
    # .applied_property_values = []
    # .property_value_groups = [0]
    # .property_value_pkgs = []
    # .property_values = []
    # .pvmt = 

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
    """Find and merge Units

    Parameters
    ==========
    x:
        Unit to process
    dest:
        Destination model to add Units to
    src:
        Source model to take Units from
    base:
        Base model to check Units against
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

    if isinstance(destParent, inf.DataPkg):
        targetCollection = destParent.units
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Units parent is not a valid parent, Units name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
