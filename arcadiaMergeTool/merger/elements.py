import sys
from collections import deque
from venv import logger

import capellambse.metamodel as mm
import capellambse.metamodel.libraries as li
import capellambse.model as m
from capellambse.metamodel import re
from capellambse.model import ModelElement

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import (
    MergerElementMappingMap,
    ModelElement_co,
)
from arcadiaMergeTool.merger.processors import doProcess
from arcadiaMergeTool.merger.processors._processor import Postponed
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(name=__name__)

def _makeModelElementList(
    model: CapellaMergeModel, clsname: type[ModelElement_co] | None = None
) -> deque[m._obj.ModelElement]:
    """Fetch all model elements from model.

    Parameters
    ----------
    model:
        Source model to fetch all data from
    clsname:
        Type to use as an element hit

    Returns
    -------
    Filtered list of found objects
    """

    # TODO: models can be huge, use generators to iterate through the model
    lst = deque(
        filter(
            lambda x: not isinstance(x, re.CatalogElement)
            and not isinstance(x, re.RecCatalog)
            and not isinstance(x, li.LibraryReference)
            and not isinstance(x, li.ModelInformation),
            model.model.search(ModelElement, below=model.model.project),
        )
    )
    if clsname is not None:
        return deque(filter(lambda x: isinstance(x, clsname), lst))

    return lst

def mergeElements(
    dest: CapellaMergeModel,
    base: CapellaMergeModel,
    src: list[CapellaMergeModel],
    mapping: MergerElementMappingMap,
):
    """Merge models.

    dest: Description
    :type dest: CapellaMergeModel
    :param base: Description
    :type base: CapellaMergeModel
    :param src: Description
    :type src: list[CapellaMergeModel]
    :param elementMappingMap: Description
    :type elementMappingMap: MergerElementMappingMap
    """

    LOGGER.info("[%s] begin merging models into target model", mergeElements.__qualname__)

    stats: list[int] = []
    stats2: dict[str, int] = {}

    for model in src:
        lst: deque[ModelElement | tuple[ModelElement, int]] = _makeModelElementList(model) # pyright: ignore[reportAssignmentType] TODO: add contravatiant

        LOGGER.info("[%s] Start merge of source model [%s], uuid [%s] content", mergeElements.__qualname__, model.model.name, model.model.uuid)
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
                    LOGGER.fatal("[%s] Processing retry threshold exceeded [%s], element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s]", mergeElements.__qualname__, counter, elem.name, elem.uuid, elem.__class__, elem._model.name, len(lst))
                else:
                    LOGGER.fatal("[%s] Processing retry threshold exceeded [%s], element uuid [%s], class [%s], model [%s]; queue length [%s]", mergeElements.__qualname__, counter, elem.uuid, elem.__class__, elem._model.name, len(lst))
                sys.exit(str(ExitCodes.MergeFault))

            if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                LOGGER.debug("[%s] Process element name [%s], uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", mergeElements.__qualname__, elem.name, elem.uuid, elem.__class__, elem._model.name, len(lst), counter)
            else:
                LOGGER.debug("[%s] Process element uuid [%s], class [%s], model [%s]; queue length [%s], try [%s]", mergeElements.__qualname__, elem.uuid, elem.__class__, elem._model.name, len(lst), counter)
            res = doProcess(elem, dest, model, base, mapping)
            if res == Postponed:
                if isinstance(elem, mm.modellingcore.AbstractNamedElement):
                    LOGGER.debug("[%s] element name [%s], uuid [%s], class [%s], model [%s] put back to queue", mergeElements.__qualname__, elem.name, elem.uuid, elem.__class__, elem._model.name)
                else:
                    LOGGER.debug("[%s] element uuid [%s], class [%s], model [%s] put back to queue", mergeElements.__qualname__, elem.uuid, elem.__class__, elem._model.name)
                lst.appendleft((elem, counter+1))

        LOGGER.info("[%s] Merge of source model [%s], uuid [%s] content completed", mergeElements.__qualname__, model.model.name, model.model.uuid)

    LOGGER.info("[%s] Elements merge complete, retries [%s], [%s]", mergeElements.__qualname__, stats, stats2)
