from collections import deque
import stat
from venv import logger

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

    stats: list[int] = []
    stats2: dict[str, int] = {}

    for model in src:
        lst: deque[ModelElement | tuple[ModelElement, int]] = _makeModelElementList(model) # pyright: ignore[reportAssignmentType] TODO: add contravatiant

        logger.info(f"[{mergeElements.__qualname__}] Start merge of source model [%s], uuid [%s] content", model.model.name, model.model.uuid)
        while lst:
            elem = lst.pop()
            counter = 1
            if isinstance(elem, tuple):
                (elem, counter) =elem

            if len(stats) < counter:
                stats.append(1)
            else:
                stats[counter-1] = stats[counter-1]+1
            cls = str(elem.__class__)
            if stats2.get(cls) is None:
                stats2[cls] = 1
            elif counter == 1:
                stats2[cls] = stats2[cls] + 1


            if counter > 25:
                # TODO: make configurable, sometimes it takes up to 20 retries to complete merge
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.fatal(f"[{mergeElements.__qualname__}] Processing retry threshold exceeded [%s], element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s]", counter, elem.name, elem.uuid, elem.__class__, elem._model.name, len(lst)) # type: ignore
                else:
                    LOGGER.fatal(f"[{mergeElements.__qualname__}] Processing retry threshold exceeded [%s], element uuid [%s], class [%s], model [%s]; queue length [%s]", counter, elem.uuid, elem.__class__, elem._model.name, len(lst)) # type: ignore
                exit(str(ExitCodes.MergeFault))

            if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", elem.name, elem.uuid, elem.__class__, elem._model.name, len(lst), counter) # type: ignore
            else:
                LOGGER.debug(f"[{mergeElements.__qualname__}] Process element uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", elem.uuid, elem.__class__, elem._model.name, len(lst), counter) # type: ignore
            res = doProcess(elem, dest, model, base, mapping)
            if not res:
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element name [%s], uuid [%s], class [%s], model [%s] put back to queue", elem.name, elem.uuid, elem.__class__, elem._model.name) # type: ignore
                else:
                    LOGGER.debug(f"[{mergeElements.__qualname__}] element uuid [%s], class [%s], model [%s] put back to queue", elem.uuid, elem.__class__, elem._model.name) # type: ignore
                lst.appendleft((elem, counter+1))

        logger.info(f"[{mergeElements.__qualname__}] Merge of source model [%s], uuid [%s] content completed", model.model.name, model.model.uuid)

    logger.info(f"[{mergeElements.__qualname__}] Elements merge complete, retries [%s], [%s]", stats, stats2)
