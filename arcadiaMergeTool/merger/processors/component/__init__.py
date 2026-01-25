import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

import capellambse.model as m
from arcadiaMergeTool.merger.processors._processor import clone, process, doProcess, recordMatch

from . import exchange, port, physical, realization

__all__ = [
    "exchange",
    "port",
    "physical",
    "realization",
]

LOGGER = getLogger(__name__)

T = mm.cs.Component

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap): # pyright: ignore[reportInvalidTypeArguments]
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_abstract = x.is_abstract,
        is_actor = x.is_actor,
        is_human = x.is_human,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    ) 

    # TODO: fix PVMT
    # .property_value_groups = []
    # .property_values = []
    # .pvmt = 

    # TODO: find a way to copy these properties
    # if not isinstance(newComp, mm.epbs.ConfigurationItem):
    #     newComp.super = x.super

    if x.status is not None: # pyright: ignore[reportAttributeAccessIssue] expect status is valid attribute
        newComp.status = x.status # pyright: ignore[reportAttributeAccessIssue] expect status is valid attribute
        
    if not isinstance(newComp, mm.la.LogicalComponent):
        newComp.kind = x.kind
        newComp.nature = x.nature

    return newComp

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Components

    Parameters
    ==========
    x:
        Component to process
    dest:
        Destination model to add components to
    src:
        Source model to take components from
    base:
        Base model to check components against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent # pyright: ignore[reportAttributeAccessIssue] expect parent is there
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

    if (isinstance(destParent, mm.sa.SystemComponentPkg) 
        or isinstance(destParent, mm.la.LogicalComponentPkg)
        or isinstance(destParent, mm.pa.PhysicalComponentPkg)
        ) and x.parent.components[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect components are there
        # HACK: assume System is a very first root component
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.components[0], False)
        return True
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg) and x.parent.configuration_items[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect configuration items are there
        # HACK: assume System is a very first root configuratiobn item
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items[0], False)
        return True
    elif isinstance(destParent, mm.pa.PhysicalComponent):
        targetCollection = destParent.owned_components # pyright: ignore[reportAttributeAccessIssue] owned_components is a valid property in this context
    elif (
        isinstance(destParent, mm.cs.Component)
        or isinstance(destParent, mm.pa.PhysicalComponentPkg)
        or isinstance(destParent, mm.sa.SystemComponentPkg)
        or isinstance(destParent, mm.la.LogicalComponentPkg)
    ):
        targetCollection = destParent.components
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
        targetCollection = destParent.configuration_items
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Component parent is not a valid parent, Component name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
