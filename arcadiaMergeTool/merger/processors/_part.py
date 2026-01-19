
import capellambse.metamodel as mm
from capellambse import helpers
from capellambse.model import ModelElement

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from ._processor import process

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.cs.Part,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Parts

    Parameters
    ==========
    x:
        Part to process
    dest:
        Destination model to add parts to
    src:
        Source model to take parts from
    base:
        Base model to check parts against
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

    if (isinstance(destParent, mm.sa.SystemComponentPkg) 
        or isinstance(destParent, mm.la.LogicalComponentPkg)
        or isinstance(destParent, mm.pa.PhysicalComponentPkg)
        ) and destParent.parts[0] == x:
        # HACK: assume System is a very first root part
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.parts[0], False)
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg) and destParent.configuration_items[0] == x:
        # HACK: assume System is a very first root configuratiobn item
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items[0], False)
    elif (isinstance(destParent, mm.cs.Component)
        or isinstance(destParent, mm.pa.PhysicalComponentPkg)
        or isinstance(destParent, mm.sa.SystemComponentPkg)
        or isinstance(destParent, mm.la.LogicalComponentPkg)
    ):
        targetCollection = destParent.owned_parts # pyright: ignore[reportAttributeAccessIssue] expect owned_parts exists in this context
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
        targetCollection = destParent.configuration_items
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Part parent is not a valid parent, Part name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    if targetCollection is not None:
        # use weak match by name
        # TODO: implement strong match by PVMT properties
        matchingPart = list(filter(lambda y: y.name == x.name, targetCollection))

        if (len(matchingPart) > 0):
            # coming here means that part was added in a project, not taken from the library

            targetPart = matchingPart[0]
            mappedTargetPart = mapping.get((targetPart._model.uuid, targetPart.uuid))
            fromLibrary = mappedTargetPart[1] if mappedTargetPart is not None else False
            if not fromLibrary:
                LOGGER.error(
                    f"[{process.__qualname__}] Non-library part detected. Part name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                    x.name,
                    x.uuid,
                    destParent.name,
                    destParent.uuid,
                    x._model.name,
                    x._model.uuid,
                )

            # assume it's same to take first, but theme might be more
            mapping[(x._model.uuid, x.uuid)] = (matchingPart[0], fromLibrary)
        else:
            LOGGER.debug(
                f"[{process.__qualname__}] Create a non-library part name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
            )

            if not process(x.type, dest, src, base, mapping):
                # part is merely a link to a component, check if component can be references
                # if not, stop processing to retry later
                return False

            newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
                type = mapping[(x._model.uuid, x.type.uuid)][0], # pyright: ignore[reportOptionalMemberAccess] expect type exists and uuid is valid
                name = x.name,
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
                review = x.review,
                sid = x.sid,
                summary = x.summary,
                visibility = x.visibility,
            ) 

            # TODO: track PVMT
            # .applied_property_value_groups = []
            # .applied_property_values = []
            # .property_value_groups = []
            # .property_values = []

            # TODO: check how to copy these values
            # newComp.default_value = x.default_value
            # newComp.max_card = x.max_card
            # newComp.max_length = x.max_length
            # newComp.max_value = x.max_value
            # newComp.min_card = x.min_card
            # newComp.min_length = x.min_length
            # newComp.min_value = x.min_value
            # newComp.null_value = x.null_value
            # newComp.owned_type = x.owned_type

            if x.status is not None:
                newComp.status = x.status  # pyright: ignore[reportAttributeAccessIssue] assume status is already there

            # TODO: add other properties, but do not touch linked elements - they are processed by top level iterator
            mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
