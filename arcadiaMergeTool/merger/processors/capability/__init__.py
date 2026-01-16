import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from .._processor import process

# from . import allocation, port, realization

# __all__ = [
#     "allocation",
#     "port",
#     "realization"
# ]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.sa.Capability | mm.oa.OperationalCapability,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Capabilities

    Parameters
    ==========
    x:
        Capability to process
    dest:
        Destination model to add Capabilities to
    src:
        Source model to take Capabilities from
    base:
        Base model to check Capabilities against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        LOGGER.debug(
            f"[{process.__qualname__}] New Capability found, name [%s], uuid [%s], model name [%s], uuid [%s]",
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
            LOGGER.fatal(f"[{process.__qualname__}] Capability parent was not found in cache, name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

        if (isinstance(modelParent, mm.sa.CapabilityPkg) 
            ) and modelParent.capabilities[0] == x:
            # HACK: assume Root Capability is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.capabilities, False)
            return True
        elif isinstance(modelParent, mm.oa.OperationalCapabilityPkg) and modelParent.capabilities[0] == x:
            # HACK: assume Root Activity is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (destParent.capabilities[0], False)
            return True
        elif (isinstance(destParent, mm.oa.OperationalCapabilityPkg)
            or isinstance(destParent, mm.sa.CapabilityPkg)
        ):
            targetCollection = destParent.capabilities
        # elif isinstance(destParent, mm.oa.)
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Capability parent is not a valid parent, Capability name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.__class__,
                destParent.name,
                destParent.uuid,
                destParent.__class__,
                x._model.name,
                x._model.uuid,
            )
            print(modelParent, destParent)
            exit(str(ExitCodes.MergeFault))

        # use weak match by name
        # TODO: implement strong match by PVMT properties
        matchingCapability = list(filter(lambda y: y.name == x.name, targetCollection))

        if (len(matchingCapability) > 0):
            # assume it's same to take first, but theme might be more
            mapping[(x._model.uuid, x.uuid)] = (matchingCapability[0], False)
        else:
            LOGGER.debug(
                f"[{process.__qualname__}] Create new Capability name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
            # .applied_property_value_groups = 
            # .applied_property_values = []
            # .property_value_groups = [0]
            # .property_value_pkgs = []
            # .property_values = []
            # .pvmt = 

            newComp.description = x.description
            newComp.is_visible_in_doc = x.is_visible_in_doc
            newComp.is_visible_in_lm = x.is_visible_in_lm
            newComp.name = x.name
            newComp.review = x.review
            newComp.sid = x.sid
            newComp.summary = x.summary

            if x.status is not None:
                newComp.status = x.status
            if x.postcondition is not None:
                newComp.postcondition = x.postcondition
            if x.precondition is not None:
                newComp.precondition = x.precondition

            mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedCapability, fromLibrary) = cachedElement

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
