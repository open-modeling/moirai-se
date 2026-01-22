from arcadiaMergeTool.helpers import ExitCodes
from capellambse import helpers
from arcadiaMergeTool.merger.processors._processor import doProcess, process
from capellambse.metamodel import cs
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool import getLogger

LOGGER = getLogger(__name__)

@process.register
def _(
    x: cs.InterfacePkg ,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    LOGGER.debug(
        f"[{process.__qualname__}] processing logical component package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )
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

    package = None
    if isinstance(destParent, cs.BlockArchitecture):
        package = destParent.interface_pkg
        mapping[(x._model.uuid, x.uuid)] = (package, False)  # pyright: ignore[reportArgumentType] expect package is correct
        return True
    elif isinstance(destParent, cs.InterfacePkg):
        targetCollection = destParent.interfaces
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Architecture Realization parent is not a valid parent, Port uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
    matchingInterfacePkg = list(filter(lambda y: y.name == x.name, targetCollection))

    if (len(matchingInterfacePkg) > 0):
        # assume it's same to take first, but theme might be more
        mapping[(x._model.uuid, x.uuid)] = (matchingInterfacePkg[0], False)
    else:
        LOGGER.debug(
            f"[{process.__qualname__}] Create new Interface Package name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
