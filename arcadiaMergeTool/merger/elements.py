from collections import deque
import os
import typing as t

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap, ModelElement_co
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.model import ModelElement
import capellambse.model as m
import capellambse.metamodel as mm
import capellambse.metamodel.re as re
import capellambse.metamodel.capellamodeller as cm
import capellambse.metamodel.libraries as li
from arcadiaMergeTool.merger.processors import process

LOGGER = getLogger(name=__name__)

def _makeModelElementList(
    model: CapellaMergeModel, clsname: type[ModelElement_co] | None = None
) -> deque[m._obj.ModelElement]:
    """Fetch all model elements from model

    Parameters
    ==========
    model:
        Source model to fetch all data from

    Returns
    =======
    Filtered list of found objects
    """

    # print (list(model.model.search(mm.fa.ComponentFunctionalAllocation, below=model.model.project)),)
    # exit()

    # TODO: models can be huge, use generators to iterate through the model
    lst = deque(
        filter(
            lambda x: not isinstance(x, re.CatalogElement)
            and not isinstance(x, re.CatalogElementLink)
            and not isinstance(x, re.RecCatalog)
            and not isinstance(x, mm.capellacommon.TransfoLink)
            and not isinstance(x, li.LibraryReference)
            and not isinstance(x, li.ModelInformation),
            model.model.search(ModelElement, below=model.model.project),
            # model.model.search(mm.fa.ComponentFunctionalAllocation, below=model.model.project)
        )
    )
    if clsname is not None:
        return deque(filter(lambda x: isinstance(x, clsname), lst))
    else:
        return lst

def mergeElements(
    dest: CapellaMergeModel,
    base: CapellaMergeModel,
    src: list[CapellaMergeModel],
    mapping: MergerElementMappingMap,
):
    """Merge models

    dest: Description
    :type dest: CapellaMergeModel
    :param base: Description
    :type base: CapellaMergeModel
    :param src: Description
    :type src: list[CapellaMergeModel]
    :param elementMappingMap: Description
    :type elementMappingMap: MergerElementMappingMap
    """

    LOGGER.info(f"[{mergeElements.__qualname__}] begin merging models into target model")

    for model in src:
        list = _makeModelElementList(model)  # ,  mm.capellacommon.Region

        while list:
            elem = list.pop()
            if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s]", elem.name, elem.uuid, elem.__class__, elem._model.name, len(list)) # type: ignore
            else:
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element uuid [%s], class [%s], model [%s]; queue length [%s]", elem.uuid, elem.__class__, elem._model.name, len(list)) # type: ignore
            res = __doProcess(elem, dest, model, base, mapping)
            if not res:
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element name [%s], uuid [%s], class [%s], model [%s] put back to queue", elem.name, elem.uuid, elem.__class__, elem._model.name) # type: ignore
                else:
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element uuid [%s], class [%s], model [%s] put back to queue", elem.uuid, elem.__class__, elem._model.name) # type: ignore
                list.appendleft(elem)

def __doProcess (
    x: ModelElement,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:

    if x == x._model.project:
        # edge case, root node reached
        mapping[(x._model.uuid, x.uuid)] = (x, False)

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        if isinstance(x, mm.capellacore.NamedElement):
            LOGGER.debug(
                f"[{process.__qualname__}] Add new element to model name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )
        else:
            LOGGER.debug(
                f"[{process.__qualname__}] Add new element to model uuid [%s], class [%s], model name [%s], uuid [%s]",
                x.uuid,
                x.__class__,
                x._model.name,
                x._model.uuid,
            )

        return process(x, dest, src, base, mapping)

    else:
        (cachedFunction, fromLibrary) = cachedElement

        errors = []
        # if cachedFunction.name != x.name:
        #     errors["name warn"] = (
        #         f"known name [{cachedFunction.name}], new name [{x.name}]"
        #     )
        # if cachedFunction.description != x.description:
        #     errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Fields does not match recorded, element uuid [%s], model name [%s], uuid [%s], warnings [%s]",
                x.uuid,
                x._model.name,
                x._model.uuid,
                errors,
            )

    return True
