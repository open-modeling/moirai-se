import capellambse.metamodel as mm
import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.capellamodeller as cm
import capellambse.metamodel.information.datavalue as dv
import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information as inf
from capellambse import helpers

from arcadiaMergeTool.helpers import ExitCodes, create_element
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

from . import binary_expression, boolean

__all__ = [
    "binary_expression",
    "boolean",
]

LOGGER = getLogger(__name__)

@process.register
def _(
    x: dv.LiteralNumericValue | dv.LiteralStringValue,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Literal Values

    Parameters
    ==========
    x:
        Literal Value to process
    dest:
        Destination model to add Literal Values to
    src:
        Source model to take Literal Values from
    base:
        Base model to check Literal Values against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    # recursively check all direct parents for existence and continue only if parents agree
    modelParent = x.parent
    if (not doProcess(modelParent, dest, src, base, mapping)):
        # unit is vital property, wait for it
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

    if (isinstance(destParent, dt.Enumeration)):
        targetCollection = destParent.data_values
    elif (isinstance(destParent, dt.BooleanType)):
        targetCollection = destParent.data_values
    elif (isinstance(destParent, dt.NumericType)):
        targetCollection = destParent.data_values
    elif (isinstance(destParent, dt.StringType)):
        targetCollection = destParent.data_values
    elif (isinstance(destParent, dv.BinaryExpression)
        or isinstance(destParent, inf.ExchangeItemElement)
    ):
        el =create_element(dest.model, destParent, x)

        el.description = x.description
        el.is_abstract = x.is_abstract
        el.is_visible_in_doc = x.is_visible_in_doc
        el.is_visible_in_lm = x.is_visible_in_lm
        el.name = x.name
        el.review = x.review
        el.sid = x.sid
        el.summary = x.summary
        el.value = x.value

        if x.status is not None:
            el.status = x.status
        if x.unit is not None:
            mappedType = mapping[(x._model.uuid, x.unit.uuid)]
            el.unit = mappedType[0]

        mapping[(x._model.uuid, x.uuid)] = (el, False)
        return True
    else:
        print(destParent)
        LOGGER.fatal(
            f"[{process.__qualname__}] Literal Values parent is not a valid parent, Literal Values name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
            f"[{process.__qualname__}] Create new Literal Values name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

        newComp = None
        if isinstance(x, dv.LiteralNumericValue):
            newComp = targetCollection.create(xtype=dv.LiteralNumericValue)
        elif isinstance(x, dv.LiteralStringValue):
            newComp = targetCollection.create(xtype=dv.LiteralStringValue)

        newComp = targetCollection.create(xtype=helpers.qtype_of(x._element))
        if isinstance(newComp, dv.LiteralBooleanValue):
            newComp.description = x.description
            # TODO: fix this
            # newComp.is_abstract = x.is_abstract,
            # newComp.is_visible_in_doc = x.is_visible_in_doc,
            # newComp.is_visible_in_lm = x.is_visible_in_lm,
            # newComp.name = x.name,
            # newComp.review = x.review,
            # newComp.sid = x.sid,
            # newComp.summary = x.summary,
            # newComp.value = x.value,
        else:
            newComp.description = x.description, # pyright: ignore[reportAttributeAccessIssue]
            newComp.is_abstract = x.is_abstract, # pyright: ignore[reportAttributeAccessIssue]
            newComp.is_visible_in_doc = x.is_visible_in_doc, # pyright: ignore[reportAttributeAccessIssue]
            newComp.is_visible_in_lm = x.is_visible_in_lm, # pyright: ignore[reportAttributeAccessIssue]
            newComp.name = x.name, # pyright: ignore[reportAttributeAccessIssue]
            newComp.review = x.review, # pyright: ignore[reportAttributeAccessIssue]
            newComp.sid = x.sid, # pyright: ignore[reportAttributeAccessIssue]
            newComp.summary = x.summary, # pyright: ignore[reportAttributeAccessIssue]
            newComp.value = x.value, # pyright: ignore[reportAttributeAccessIssue]


        # TODO: fix PVMT
        # .applied_property_value_groups = 
        # .applied_property_values = []
        # .property_value_groups = [0]
        # .property_value_pkgs = []
        # .property_values = []
        # .pvmt = 

        if x.status is not None:
            newComp.status = x.status
        if x.unit is not None:
            mappedType = mapping[(x._model.uuid, x.unit.uuid)]
            newComp.unit = mappedType[0]


        mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    return True
