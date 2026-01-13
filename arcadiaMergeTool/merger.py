from collections import deque
import os
import typing as t

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.models.config_project_model import ConfigProjectModel
from arcadiaMergeTool.models.merger_config_model import MergerConfigModel
from arcadiaMergeTool.models.config_model import ConfigModel
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.merger import mergeExtensions, mergeLibraries
from capellambse.model import ModelElement
import capellambse.model as m
from capellambse import helpers
import capellambse.metamodel as mm
import capellambse.metamodel.re as re
import capellambse.metamodel.capellamodeller as cm
import capellambse.metamodel.libraries as li
from arcadiaMergeTool.processors import process


LOGGER = getLogger(__name__)


def merge(config: ConfigModel):
    extModels = config.models
    targetModel = config.target
    baseModel: ConfigProjectModel = config.base

    mergerConfig = MergerConfigModel(
        basePath=config.project.basePath,
        infoPath=os.path.join(config.project.basePath, "debug/"),
        baseModel=baseModel,
        name=config.project.name,
    )
    os.makedirs(mergerConfig.infoPath, exist_ok=True)

    modelSrc = []
    modelDst = CapellaMergeModel(targetModel, mergerConfig)
    modelBase = CapellaMergeModel(model=baseModel, config=mergerConfig)

    for item in extModels:
        LOGGER.debug(f"[{merge.__name__}] processing external models item ({item})")
        model = CapellaMergeModel(item, config=mergerConfig)

        modelSrc.append(model)

    elementMappingMap: MergerElementMappingMap = {}

    mergeLibraries(modelDst, modelBase, modelSrc)
    mergeExtensions(modelDst, modelBase, modelSrc, elementMappingMap)
    mergeModels(modelDst, modelBase, modelSrc, elementMappingMap)

    modelDst.save()


ModelElement_co = t.TypeVar("ModelElement_co", bound=ModelElement, covariant=True)


def makeModelElementList(
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


# @process.register
# def _(x: mm.capellacommon.Region, dest: CapellaMergeModel, src: CapellaMergeModel, base: CapellaMergeModel, mapping: MergerElementMappingMap) -> bool:
#     return f"Region: name={x.name}, class={x.__class__}"

CAPELLA_NAMES_SYSTEM = "System"
""" Constant to distinct System from other components"""
CAPELLA_NAMES_PHYSICAL_SYSTEM = "Physical System"
""" Constant to distinct Physical System from other components"""
CAPELLA_NAMES_LOGICAL_SYSTEM = "Logical System"
""" Constant to distinct Logical System from other components"""
CAPELLA_NAMES_EPBS_SYSTEM = "System"
""" Constant to distinct EPBS System from other components"""


@process.register
def _(
    x: mm.cs.Component,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
) -> bool:
    """Process SystemComponent

    Parameters
    ==========
    x:
        Component to process
    dest:
        Destination model to add components to
    src:
        Source components to take components from
    base:
        Base model to check components against
    mapping:
        Full mapping of the elements to the corresponding models

    Returns
    =======
    True if element was completely processed, False otherwise
    """

    cachedElement = mapping.get((x._model.uuid, x.uuid))

    if cachedElement is None:
        # for Component - if not found in cache, in general it's a violation of the merging rules
        # at this point all components must come from base library
        LOGGER.debug(
            f"[{process.__qualname__}] New component found, name [%s], uuid [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x._model.name,
            x._model.uuid,
        )

        # recursively check all direct parents for existence and continue only if parents agree
        modelParent = x.parent  # pyright: ignore[reportAttributeAccessIssue] expect parent is there in valid model
        if not process(modelParent, dest, src, base, mapping):
            return False
        
        destParent = mapping[modelParent._model.uuid, modelParent.uuid][0]

        targetCollection = None

        if (isinstance(modelParent, mm.sa.SystemComponentPkg) 
            or isinstance(modelParent, mm.la.LogicalComponentPkg)
            or isinstance(modelParent, mm.pa.PhysicalComponentPkg)
            ) and modelParent.components[0] == x:
            # HACK: assume System is a very first root component
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (modelParent.components[0], False)
        elif isinstance(modelParent, mm.epbs.ConfigurationItemPkg) and modelParent.configuration_items[0] == x:
            # HACK: assume System is a very first root configuratiobn item
            # map system to system and assume it's done
            mapping[(x._model.uuid, x.uuid)] = (modelParent.configuration_items[0], False)
        elif isinstance(destParent, mm.pa.PhysicalComponent):
            targetCollection = destParent.owned_components # pyright: ignore[reportAttributeAccessIssue] owned_components is a valid property in this context
        elif (
            isinstance(destParent, mm.cs.Component)
            or isinstance(destParent, mm.pa.PhysicalComponentPkg)
            or isinstance(destParent, mm.sa.SystemComponentPkg)
            or isinstance(destParent, mm.la.LogicalComponentPkg)
        ):
            targetCollection = destParent.components
        elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
            targetCollection = destParent.configuration_items
        else:
            LOGGER.fatal(
                f"[{process.__qualname__}] Component parent is not a valid parent, Component name [%s], uuid [%s], parent name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                destParent.name,
                destParent.uuid,
                x._model.name,
                x._model.uuid,
            )
            exit(str(ExitCodes.MergeFault))

        if targetCollection is not None:
            # use weak match by name
            # TODO: implement strong match by PVMT properties
            matchingComponent = list(filter(lambda y: y.name == x.name, targetCollection))

            if (len(matchingComponent) > 0):
                LOGGER.error(
                    f"[{process.__qualname__}] Non-library component detected. Component name [%s], uuid [%s], model name [%s], uuid [%s]",
                    x.name,
                    x.uuid,
                    x._model.name,
                    x._model.uuid,
                )
                # assume it's same to take first, but theme might be more
                mapping[(x._model.uuid, x.uuid)] = (matchingComponent[0], False)
            else:
                newComp = targetCollection.create(xtype=helpers.qtype_of(x._element)) 

                # update newly created component and save it for future use
                newComp.name = x.name
                newComp.description = x.description
                # TODO: add other properties, but do not touch linked elements - they are processed by top level iterator
                mapping[(x._model.uuid, x.uuid)] = (newComp, False)

    else:
        (cachedComponent, fromLibrary) = cachedElement

        errors = {}
        if cachedComponent.name != x.name:
            errors["name warn"] = (
                f"known name [{cachedComponent.name}], new name [{x.name}]"
            )
        if cachedComponent.name != x.name:
            errors["description warn"] = "known description does not match processed"

        if len(errors):
            LOGGER.warning(
                f"[{process.__qualname__}] Component fields does not match known, Component name [%s], uuid [%s], model name [%s], uuid [%s]",
                x.name,
                x.uuid,
                x._model.name,
                x._model.uuid,
                extra=errors,
            )

    return True


# @process.register
# def _(x: mm.fa.ComponentPort, dest: CapellaMergeModel, src: CapellaMergeModel, base: CapellaMergeModel, mapping: MergerElementMappingMap) -> bool:
#     return f"ComponentPort: name={x.name}, class={x.__class__}"


def mergeModels(
    dest: CapellaMergeModel,
    base: CapellaMergeModel,
    src: list[CapellaMergeModel],
    elementMappingMap: MergerElementMappingMap,
):
    """Merge models
    Docstring for mergeModels

    :param dest: Description
    :type dest: CapellaMergeModel
    :param base: Description
    :type base: CapellaMergeModel
    :param src: Description
    :type src: list[CapellaMergeModel]
    :param elementMappingMap: Description
    :type elementMappingMap: MergerElementMappingMap
    """

    LOGGER.info(f"[{mergeModels.__name__}] begin merging models into target model")

    for model in src:
        list = makeModelElementList(model)  # ,  mm.capellacommon.Region

        while list:
            elem = list.pop()
            res = process(elem, dest, base, src[0], elementMappingMap)
            if not res:
                list.appendleft(elem)
