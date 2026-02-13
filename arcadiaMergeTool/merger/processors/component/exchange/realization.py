import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors.recordMatch import recordMatch
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

import capellambse.model as m
from arcadiaMergeTool.merger.processors._processor import clone, process, doProcess

LOGGER = getLogger(__name__)

T = mm.fa.ComponentExchangeRealization

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        source = mapping.get((x._model.uuid, x.source.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect source is already there
        target = mapping.get((x._model.uuid, x.target.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
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

    return newComp

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Component Exchange Realizations

    Parameters
    ==========
    x:
        Component Exchange Realization to process
    dest:
        Destination model to add Component Exchange Realizations to
    src:
        Source model to take Component Exchange Realizations from
    base:
        Base model to check Component Exchange Realizations against
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
        LOGGER.fatal(f"[{process.__qualname__}] Element parent was not found in cache, uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

    if (isinstance(destParent, mm.fa.ComponentExchange)
    ):
        targetCollection = destParent.component_exchange_realizations
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Component Exchange Realization parent is not a valid parent, Component Exchange uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    
    matchList = list(filter(lambda y: y.source == mappedSource[0] and y.target == mappedTarget[0], targetCollection)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe

    return recordMatch(matchList, x, destParent, targetCollection, mapping)
