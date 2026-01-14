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
        Source functions to take functions from
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
        # for Function - if not found in cache, in general it's a violation of the merging rules
        # at this point all function must come from base library
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
            mapping[(x._model.uuid, x.uuid)] = (modelParent.functions[0], False)
        elif isinstance(modelParent, mm.oa.OperationalActivityPkg) and modelParent.activities[0] == x:
            # HACK: assume Root Activity is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (modelParent.activities[0], False)
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

        if targetCollection is not None:
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
    
                # update newly created component and save it for future use
                newComp.name = x.name
                newComp.description = x.description
                # TODO: add other properties, but do not touch linked elements - they are processed by top level iterator
                mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedFunction, fromLibrary) = cachedElement

        errors = {}
        if cachedFunction.name != x.name:
            errors["name warn"] = (
                f"known name [{cachedFunction.name}], new name [{x.name}]"
            )
        if cachedFunction.name != x.name:
            errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Component fields does not match known, Component name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                extra=errors,
            )

    return True
