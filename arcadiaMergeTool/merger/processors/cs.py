from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors._processor import process
from capellambse.metamodel import cs
from capellambse import helpers
from capellambse.model import ModelElement
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: cs.PhysicalLink,
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

    if isinstance(destParent, cs.Component):
        targetCollection = destParent.physical_links # pyright: ignore[reportAttributeAccessIssue] except physical links exitst
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
    matchingComponent = list(filter(lambda y: y.name == x.name, targetCollection))

    if (len(matchingComponent) > 0):
        # coming here means that component was added in a project, not taken from the library
        LOGGER.error(
            f"[{process.__qualname__}] Non-library component detected. Component name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            destParent.name,
            destParent.uuid,
            x._model.name,
            x._model.uuid,
        )

        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingComponent[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create a non-library component name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        print(x)
        exit()

        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
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

        .source = <PhysicalPort 'PP 2' (d1d4466a-54cf-46bd-bac9-7af09d1df728)>
        .target = <PhysicalPort 'PP 4' (9f81ba5d-3041-44f4-8f1d-554273b433df)>

        # TODO: fix PVMT
        # .applied_property_value_groups = []
        # .applied_property_values = []
        # .property_value_groups = []
        # .property_values = []
        # .pvmt = 

        # TODO: find a way to copy these properties
        # if not isinstance(newComp, mm.epbs.ConfigurationItem):
        #     newComp.super = x.super

        if x.status is not None: # pyright: ignore[reportAttributeAccessIssue] expect status is valid attribute
            newComp.status = x.status # pyright: ignore[reportAttributeAccessIssue] expect status is valid attribute

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
