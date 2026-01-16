import capellambse.metamodel as mm
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from .._processor import process

LOGGER = getLogger(__name__)

@process.register
def _(
    x: mm.fa.ComponentFunctionalAllocation,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Function Allocations

    Parameters
    ==========
    x:
        Function Allocation to process
    dest:
        Destination model to add Function Allocations to
    src:
        Source model to take Function Allocations from
    base:
        Base model to check Function Allocations against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        LOGGER.debug(
            f"[{process.__qualname__}] New Function Allocation found, uuid [%s], model name [%s], uuid [%s]",
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # recursively check all direct parents for existence and continue only if parents agree
        modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
        if not process(modelParent, dest, src, base, mapping):
            return False

        # check source and target and postpone processing if both weren't processed
        if not (process(x.source, dest, src, base, mapping) # pyright: ignore[reportOptionalMemberAccess] expect source is there
            and process(x.target, dest, src, base, mapping)): # pyright: ignore[reportOptionalMemberAccess] expect sotargeturce is there
            return False

        destParent = None
        try:
            destParent = mapping[modelParent._model.uuid, modelParent.uuid][0] # pyright: ignore[reportAttributeAccessIssue] expect ModelElement here with valid uuid
        except Exception as ex:
            LOGGER.fatal(f"[{process.__qualname__}] Function Allocation parent was not found in cache, uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s] model name [%s], uuid [%s]",
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

        if (isinstance(destParent, mm.oa.Entity)
            or isinstance(destParent, mm.cs.Component)
            or isinstance(destParent, mm.pa.PhysicalComponent)
            or isinstance(destParent, mm.sa.SystemComponent)
            or isinstance(destParent, mm.la.LogicalComponent)
        ):
            targetCollection = destParent.functional_allocations # pyright: ignore[reportAttributeAccessIssue] expect allocated_functions exists
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Function Allocation parent is not a valid parent, Function uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
        
        matchingFunction = list(filter(lambda y: y.source == mappedSource[0] and x.target == mappedTarget[0], targetCollection)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe

        if (len(matchingFunction) > 0):
            # assume it's same to take first, but theme might be more
            mapping[(x._model.uuid, x.uuid)] = (matchingFunction[0], False)
        else:
            LOGGER.debug(
                f"[{process.__qualname__}] Create new Function Allocation uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

            # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            # Unknown fault creates broken Physical Architecture allocation
            # TODO: fix and eliminate
            if newComp.layer.name == "Physical Architecture":
                return True

            # TODO: fix PVMT
            # .applied_property_value_groups = []
            # .applied_property_values = []
            # .property_value_groups = []
            # .property_values = []
            # .pvmt = 

            # TODO: find a way to copy these properties

            mappedSource = mapping[(x._model.uuid, x.source.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect source is defined
            mappedTarget = mapping[(x._model.uuid, x.target.uuid)] # pyright: ignore[reportOptionalMemberAccess] expect target is defined

            newComp.source = mappedSource[0]
            newComp.target = mappedTarget[0]

            newComp.description = x.description
            newComp.is_visible_in_doc = x.is_visible_in_doc
            newComp.is_visible_in_lm = x.is_visible_in_lm
            newComp.review = x.review
            newComp.sid = x.sid
            newComp.summary = x.summary

            if x.status is not None:
                newComp.status = x.status

            mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedFunctionAllication, fromLibrary) = cachedElement

        errors = {}
        if cachedFunctionAllication.name != x.name:
            errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Function allocation fields does not match known, Component uuid [%s], model name [%s], uuid [%s]",
                x.uuid,
                x._model.name,
                x._model.uuid,
                extra=errors,
            )

    return True
