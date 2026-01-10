import os


from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.models.config_project_model import ConfigProjectModel
from arcadiaMergeTool.models.merger_config_model import MergerConfigModel
from arcadiaMergeTool.models.config_model import ConfigModel
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.merger import mergeExtensions, mergeLibraries



LOGGER = getLogger(__name__)

def merge(config: ConfigModel):

    extModels = config.models
    targetModel = config.target
    baseModel: ConfigProjectModel = config.base

    mergerConfig = MergerConfigModel(basePath=config.project.basePath, infoPath=os.path.join(config.project.basePath, 'debug/'), baseModel=baseModel, name=config.project.name)
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

    modelDst.save()


def mergeModels(dest: CapellaMergeModel, base: CapellaMergeModel, src: list[CapellaMergeModel]):
    LOGGER.info(f"[{mergeModels.__name__}] begin merging models into target model")

