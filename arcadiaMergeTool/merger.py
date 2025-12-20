from dbm.ndbm import library
from logging import config
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import capellambse
import capellambse.metamodel

from arcadiaMergeTool import logger
from arcadiaMergeTool.models.config_project_model import ConfigProjectModel
from arcadiaMergeTool.models.merger_config_model import MergerConfigModel
from arcadiaMergeTool.models.config_model import ConfigModel
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from capellambse.metamodel.libraries import (
    LibraryReference
)

def merge(config: ConfigModel):

    extModels = config.models
    targetModel = config.target
    baseModel: ConfigProjectModel = config.base

    mergerConfig = MergerConfigModel(basePath=config.basePath, infoPath=os.path.join(config.basePath, 'debug/'), baseModel=baseModel)
    os.makedirs(mergerConfig.infoPath, exist_ok=True)

    modelSrc = []
    summaryFromAll = []

    modelDst = CapellaMergeModel(targetModel, mergerConfig)

    modelBase = CapellaMergeModel(model=baseModel, config=mergerConfig)

    # print(modelBase.model.sa.all_components)        
    # # print(modelBase.model.sa)
    # print(modelBase.model.project)

    # print(modelDst.model.sa.all_components)        
    # print(modelDst.model.project)

    for item in extModels:
        logger.debug(f"{merge} processing external models item ({item})")
        model = CapellaMergeModel(item, config=mergerConfig);
        
        modelSrc.append(model)
        # summaryFromAll.append(model.export())

        # print(model.model.sa.all_components)        
        # print(model.model)
        # print(model.model.project)
        # # print(model.model.project.libraries)
        # print(model.model.project.extensions[0])
        # print(model.model.project.extensions[0].references[0])
        # print(model.model.project.extensions[0].references[0].library)

        # update base objects
        # modelDst.FillBaseObjects(model)

    '''Does not work at the moment, capellambse does not support libraries load and use'''
    mergeLibraries(modelDst, modelBase, modelSrc)

    # импорт данных из списка словарей (summaryFromAll) в целевую модель (modelDst)
    # modelDst.importData(summaryFromAll)

    # modelDst.importInfo("Subsystem.report")
    # summaryAll = modelDst.export()
    # modelDst.traceSummary(summaryAll, "Subsystem.summary")

    modelDst.save()
# capellambse.metamodel.interaction.Scenario


def mergeLibraries(dest: CapellaMergeModel, base: CapellaMergeModel, src: List[CapellaMergeModel]):
    '''
    Collect libraries into the first reference of destination model.
    Assume destination model has only first and empty set of referwnces
    
    :param dest: Target model to add libraries to
    :type dest: CapellaMergeModel
    :param base: Base Library to aligh all models with
    :type base: CapellaMergeModel
    :param src: Source models to take other libraries from
    :type src: List[CapellaMergeModel]
    '''
    cache: Dict[str, bool] = {}

    logger.info(f"[{mergeLibraries.__name__}] begin merging libraries into target model")

    '''assume it's safe operation'''
    dst_ext: capellambse.model.ModelElement = dest.model.project.extensions[0]

    for ext in dest.model.project.extensions:
        for ref in ext.references:
            if isinstance(ref, LibraryReference):
                try: 
                    lib = ref.library
                    if lib:
                        cache[lib.uuid] = True
                    else:
                        ext.references.remove(ref)    
                except Exception as e:
                    logger.warning(f"{mergeLibraries.__name__} library for refererence [%s] is not initialized, remove from model [%r]", ref.uuid, e)
                    ext.references.remove(ref)

    l: List[CapellaMergeModel] = []
    l.extend(src)
    l.append(base)

    for model in l:
        proj = model.model.project
        for ext in proj.extensions:
            for ref in ext.references:
                if isinstance(ref, LibraryReference):
                    lib = ref.library
                    if lib and not cache.get(lib.uuid):
                        logger.debug(f"[{mergeLibraries}] adding new library {ref}")
                        
                        frag = model.model._loader.find_fragment(lib.parent._element).parent
                        '''in case of library is not loaded, link it'''
                        dest.model._loader._link_library(frag)

                        if not cache.get(lib.uuid):
                            new_lib = dest.model.by_uuid(lib.uuid)
                            dst_ext.references.create("LibraryReference", library=new_lib)
                            cache[lib.uuid] = True

