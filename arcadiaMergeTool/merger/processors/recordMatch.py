from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import LOGGER, T, clone


import capellambse.metamodel as mm
import capellambse.model as m


def recordMatch(matchColl: list[T], x: T, destParent: T, destColl: m.ElementList[T], mapping: MergerElementMappingMap) -> bool:
    """Record match in cache or fail.

    Parameters
    ==========
    matchColl:
        Collection of Elements to record in cache
    x:
        Source element to make cache key from
    destParent:
        Potential parent element
    mapping:
        Cache to put element in

    Returns
    =======
    True for success, False otherwise
    """

    destEl = None
    fromLibrary = False

    if len(matchColl) > 0:
        # assume it's same to take first, but theme might be more
        destEl = matchColl[0]

        mappedTargetPart = mapping.get((destEl._model.uuid, destEl.uuid))
        fromLibrary = mappedTargetPart[1] if mappedTargetPart is not None else False

    else:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{recordMatch.__qualname__}] Create new model element name [%s], uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
        else:
            LOGGER.debug(
                f"[{recordMatch.__qualname__}] Create new model element uuid [%s], parent name [%s], uuid [%s], class [%s], dest parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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
        destEl = clone(x, destColl, mapping)

    mapping[(x._model.uuid, x.uuid)] = (destEl, fromLibrary)

    return True
