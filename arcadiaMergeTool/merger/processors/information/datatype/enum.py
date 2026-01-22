import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.information as inf
import capellambse.metamodel.information.datatype as dt
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

LOGGER = getLogger(__name__)

@process.register
def _(
    x: dt.Enumeration,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Property Value Groups

    Parameters
    ==========
    x:
        Property Value Group to process
    dest:
        Destination model to add Property Value Groups to
    src:
        Source model to take Property Value Groups from
    base:
        Base model to check Property Value Groups against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
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

    if (isinstance(destParent, inf.DataPkg)
    ):
        targetCollection = destParent.data_types
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Property Value Groups parent is not a valid parent, Property Value Groups name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    matchingPropertyValuePackages = list(filter(lambda y: y.name == x.name, targetCollection))

    if (len(matchingPropertyValuePackages) > 0):
        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingPropertyValuePackages[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create new Property Value Groups name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element),
        ) 
        newComp.description = x.description
        newComp.is_abstract = x.is_abstract
        newComp.is_discrete = x.is_discrete
        newComp.is_final = x.is_final
        newComp.is_max_inclusive = x.is_max_inclusive
        newComp.is_min_inclusive = x.is_min_inclusive
        newComp.is_visible_in_doc = x.is_visible_in_doc
        newComp.is_visible_in_lm = x.is_visible_in_lm
        newComp.name = x.name
        newComp.pattern = x.pattern
        newComp.review = x.review
        newComp.sid = x.sid
        newComp.summary = x.summary
        newComp.visibility = x.visibility

        # newComp.null_value = x.null_value
        # newComp.max_value = x.max_value
        # newComp.min_value = x.min_value
        # newComp.domain_type = x.domain_type
        # newComp.default_value = x.default_value

        if x.super is not None:
            newComp.super = x.super
        if x.status is not None:
            newComp.status = x.status

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
