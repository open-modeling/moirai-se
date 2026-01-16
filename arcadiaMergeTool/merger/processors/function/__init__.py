import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from .._processor import process

from . import allocation, port, realization

__all__ = [
    "allocation",
    "port",
    "realization"
]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.fa.AbstractFunction,
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

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        LOGGER.debug(
            f"[{process.__qualname__}] New function found, name [%s], uuid [%s], model name [%s], uuid [%s]",
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
            LOGGER.fatal(f"[{process.__qualname__}] Function parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

        if (isinstance(modelParent, mm.sa.SystemFunctionPkg) 
            or isinstance(modelParent, mm.la.LogicalFunctionPkg)
            or isinstance(modelParent, mm.pa.PhysicalFunctionPkg)
            ) and modelParent.functions[0] == x:
            # HACK: assume Root Function is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.functions[0], False)
            return True
        elif isinstance(modelParent, mm.oa.OperationalActivityPkg) and modelParent.activities[0] == x:
            # HACK: assume Root Activity is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.activities[0], False)
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
        matchingFunction = list(filter(lambda y: y.name == x.name, targetCollection))

        if (len(matchingFunction) > 0):
            # assume it's same to take first, but theme might be more
            mapping[(x._model.uuid, x.uuid)] = (matchingFunction[0], False)
        else:
            LOGGER.debug(
                f"[{process.__qualname__}] Create new function name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.name,
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

            newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

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
            # newComp.type = x.type

            newComp.aggregation_kind = x.aggregation_kind
            newComp.condition = x.condition
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
            newComp.kind = x.kind
            newComp.name = x.name
            newComp.review = x.review
            newComp.sid = x.sid
            newComp.summary = x.summary
            newComp.visibility = x.visibility

            if x.status is not None:
                newComp.status = x.status

            mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedFunction, fromLibrary) = cachedElement

        errors = {}
        # if cachedFunction.name != x.name:
        #     errors["name warn"] = (
        #         f"known name [{cachedFunction.name}], new name [{x.name}]"
        #     )
        # if cachedFunction.description != x.description:
        #     errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Fields does not match recorded, element uuid [%s], model name [%s], uuid [%s], warnings [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                errors,
            )

    return True
