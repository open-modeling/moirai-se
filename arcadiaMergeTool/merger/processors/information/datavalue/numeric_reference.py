import capellambse.metamodel.information.datavalue as dv
import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information as inf

from arcadiaMergeTool.helpers import ExitCodes, create_element
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

from arcadiaMergeTool.merger.processors._processor import process, doProcess

LOGGER = getLogger(__name__)

T = dv.NumericReference

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Find and merge Numeric References

    Parameters
    ==========
    x:
        Numeric Reference to process
    dest:
        Destination model to add Numeric References to
    src:
        Source model to take Numeric References from
    base:
        Base model to check Numeric References against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """
    if mapping.get((x._model.uuid, x.uuid)) is not None:
        return True

    modelParent = x.parent
    if (not doProcess(modelParent, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect modelParent is of type ModelElement
        or not doProcess(x.property, dest, src, base, mapping) # pyright: ignore[reportArgumentType] expect property is there
    ):
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

    el = None
    if (isinstance(destParent, inf.ExchangeItemElement)
    ):
        el = create_element(dest.model, destParent, x)
        el.description = x.description
        el.is_abstract = x.is_abstract
        el.is_visible_in_doc = x.is_visible_in_doc
        el.is_visible_in_lm = x.is_visible_in_lm
        el.name = x.name
        el.review = x.review
        el.sid = x.sid
        el.summary = x.summary

        if x.property is not None:
            el.property = x.property
        if x.status is not None:
            el.status = x.status
        if x.unit is not None:
            mappedType = mapping[(x._model.uuid, x.unit.uuid)]
            el.unit = mappedType[0]
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Numeric References parent is not a valid parent, Numeric References name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    mapping[(x._model.uuid, x.uuid)] = (el, False)
    
    return True
