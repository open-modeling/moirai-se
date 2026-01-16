
import uuid
import capellambse.metamodel as mm
from capellambse import helpers

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

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        # for Part - if not found in cache, in general it's a violation of the merging rules
        # at this point all parts must come from base library
        LOGGER.debug(
            f"[{process.__qualname__}] New part found, name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # recursively check all direct parents for existence and continue only if parents agree
        modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
        if not process(modelParent, dest, src, base, mapping):
            return False
        
        destParent = None
        try:
            destParent = mapping[modelParent._model.uuid, modelParent.uuid][0] # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
        except Exception as ex:
            LOGGER.fatal(f"[{process.__qualname__}] Part parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.__class__,
                modelParent.name, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                modelParent.uuid, # pyright: ignore[reportAttributeAccessIssue] expect parent is already there
                modelParent.__class__,
                x._model.name,
                x._model.uuid,
                exc_info=ex
            )
            exit(str(ExitCodes.MergeFault))

        targetCollection = None

        if (isinstance(modelParent, mm.sa.SystemComponentPkg) 
            or isinstance(modelParent, mm.la.LogicalComponentPkg)
            or isinstance(modelParent, mm.pa.PhysicalComponentPkg)
            ) and modelParent.parts[0] == x:
            # HACK: assume System is a very first root part
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.parts[0], False)
        elif isinstance(modelParent, mm.epbs.ConfigurationItemPkg) and modelParent.configuration_items[0] == x:
            # HACK: assume System is a very first root configuratiobn item
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items[0], False)
        elif isinstance(destParent, mm.pa.PhysicalComponentPkg):
            targetCollection = destParent.owned_parts
        elif (
            isinstance(destParent, mm.cs.Component)
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

                newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

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
                # if not isinstance(newComp, mm.epbs.ConfigurationItem):
                    # newComp.status = x.status

                newComp.type = mapping[(x._model.uuid, x.type.uuid)][0] # pyright: ignore[reportOptionalMemberAccess] expect type exists and uuid is valid
                newComp.name = x.name
                newComp.description = x.description
                newComp.description = x.description
                newComp.is_abstract = x.is_abstract
                newComp.is_derived = x.is_derived
                newComp.is_final = x.is_final
                newComp.is_max_inclusive = x.is_max_inclusive
                newComp.is_min_inclusive = x.is_min_inclusive
                newComp.is_ordered = x.is_ordered
                newComp.is_part_of_key = x.is_part_of_key
                newComp.is_read_only = x.is_read_only
                newComp.is_static = x.is_static
                newComp.is_unique = x.is_unique
                newComp.is_visible_in_doc = x.is_visible_in_doc
                newComp.is_visible_in_lm = x.is_visible_in_lm
                newComp.name = x.name
                newComp.review = x.review
                newComp.sid = x.sid
                newComp.summary = x.summary
                newComp.visibility = x.visibility

                # TODO: add other properties, but do not touch linked elements - they are processed by top level iterator
                mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedPart, fromLibrary) = cachedElement

        errors = {}
        if cachedPart.name != x.name:
            errors["name warn"] = (
                f"known name [{cachedPart.name}], new name [{x.name}]"
            )
        if cachedPart.name != x.name:
            errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Part fields does not match known, Part name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                extra=errors,
            )

    return True
