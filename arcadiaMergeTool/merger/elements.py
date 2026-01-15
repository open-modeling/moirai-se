from collections import deque
import os
import typing as t

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap, ModelElement_co
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.model import ModelElement
import capellambse.model as m
import capellambse.metamodel.re as re
import capellambse.metamodel.capellamodeller as cm
import capellambse.metamodel.libraries as li
from arcadiaMergeTool.merger.processors import process

LOGGER = getLogger(name=__name__)

def _makeModelElementList(
    model: CapellaMergeModel, clsname: type[ModelElement_co] | None = None
) -> deque[m._obj.ModelObject]:
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
            and not isinstance(x, cm.SystemEngineering)
            and not isinstance(x, cm.Project)
            and not isinstance(x, li.LibraryReference)
            and not isinstance(x, li.ModelInformation),
            model.model.search(ModelElement, below=model.model.project),
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
    elementMappingMap: MergerElementMappingMap,
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
            res = process(elem, dest, base, src[0], elementMappingMap)
            if not res:
                LOGGER.debug(f"[{mergeElements.__qualname__}] element [%s], uuid [%s] put back to queue", elem.name, elem.uuid)
                list.appendleft(elem)
