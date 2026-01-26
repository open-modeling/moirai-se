import os
from typing import Any
import capellambse

from arcadiaMergeTool.models.config_project_model import ConfigProjectModel
from arcadiaMergeTool.models.merger_config_model import MergerConfigModel

from arcadiaMergeTool import logger

class CapellaMergeModel:
    config: MergerConfigModel

    def __init__(self, model: ConfigProjectModel, config: MergerConfigModel):
        logger.info(f"[CapellaMergeModel.__init__] add model {model.name}")
        self.config = config
        self.path = os.path.join(config.basePath, model.projectPath)

        resources = {}

        for lib in model.libs:
            logger.debug(f"[CapellaMergeModel.__init__] adding model {model.name} resource {lib}")
            resources[lib.name] = {'path': os.path.join(config.basePath, lib.path)}

        path = os.path.join(self.path)

        if model.gitLibAttrib is not None:
            resources['revision'] = model.gitLibAttrib

        modelRefs: dict[str, Any] = {'revision': model.gitModelAttrib} if model.gitModelAttrib is not None else {}

        print ("!!!", path, config.basePath)
        print(resources)
        self.model = capellambse.MelodyModel(path=path, resources=resources, **modelRefs)

    def save(self):
        self.model.name = self.config.name
        self.model.project.model_root.name = self.config.name

        self.model._loader.update_namespaces()
        self.model._loader.idcache_rebuild()
        self.model.save()
