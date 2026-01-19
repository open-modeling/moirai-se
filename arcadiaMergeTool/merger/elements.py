from collections import deque

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap, ModelElement_co
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.model import ModelElement
import capellambse.model as m
import capellambse.metamodel as mm
import capellambse.metamodel.re as re
import capellambse.metamodel.libraries as li
from arcadiaMergeTool.merger.processors import doProcess

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
        list: deque[ModelElement | tuple[ModelElement, int]] = _makeModelElementList(model) # pyright: ignore[reportAssignmentType] TODO: add contravatiant

        while list:
            elem = list.pop()
            counter = 1
            if isinstance(elem, tuple):
                (elem, counter) =elem

            if counter > 50:
                # TODO: make configurable, sometimes it takes up to 20 retries to complete merge
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.fatal(f"[{mergeElements.__qualname__}] Processing retry threshold exceeded [%s], element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s]", counter, elem.name, elem.uuid, elem.__class__, elem._model.name, len(list)) # type: ignore
                else:
                    LOGGER.fatal(f"[{mergeElements.__qualname__}] Processing retry threshold exceeded [%s], element uuid [%s], class [%s], model [%s]; queue length [%s]", counter, elem.uuid, elem.__class__, elem._model.name, len(list)) # type: ignore
                exit(str(ExitCodes.MergeFault))

            if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", elem.name, elem.uuid, elem.__class__, elem._model.name, len(list), counter) # type: ignore
            else:
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", elem.uuid, elem.__class__, elem._model.name, len(list), counter) # type: ignore
            res = doProcess(elem, dest, model, base, mapping)
            if not res:
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element name [%s], uuid [%s], class [%s], model [%s] put back to queue", elem.name, elem.uuid, elem.__class__, elem._model.name) # type: ignore
                else:
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element uuid [%s], class [%s], model [%s] put back to queue", elem.uuid, elem.__class__, elem._model.name) # type: ignore
                list.appendleft((elem, counter+1))

