
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.merger.processors._processor import process, doProcess
import capellambse.metamodel.information as inf
import capellambse.metamodel as mm
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from capellambse import helpers


from arcadiaMergeTool import getLogger

from . import datavalue, datatype, exchange_item, unit

__all__ = [
    "datatype",
    "datavalue",
    "exchange_item",
    "unit",
]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: inf.DataPkg,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Property Value Packages

    Parameters
    ==========
    x:
        Property Value Package to process
    dest:
        Destination model to add Property Value Packages to
    src:
        Source model to take Property Value Packages from
    base:
        Base model to check Property Value Packages against
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

    if isinstance(destParent, mm.cs.BlockArchitecture):
        mapping[(x._model.uuid, x.uuid)] = (destParent.data_pkg, False) # pyright: ignore[reportArgumentType] expect data package is there and valid
        return True
    elif isinstance(destParent, inf.DataPkg):
        targetCollection = destParent.packages
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Property Value Packages parent is not a valid parent, Property Value Packages name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
            f"[{process.__qualname__}] Create new Property Value Packages name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
            description = x.description,
            is_visible_in_doc = x.is_visible_in_doc,
            is_visible_in_lm = x.is_visible_in_lm,
            name = x.name,
            review = x.review,
            sid = x.sid,
            summary = x.summary,
            visibility = x.visibility,
        ) 

        # TODO: fix PVMT
        # .applied_property_value_groups = 
        # .applied_property_values = []
        # .property_value_groups = [0]
        # .property_value_pkgs = []
        # .property_values = []
        # .pvmt = 

        if x.status is not None:
            newComp.status = x.status

        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
