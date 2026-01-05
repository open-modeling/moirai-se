from typing import List
from pydantic import BaseModel, ConfigDict

from arcadiaMergeTool.models.config_project import ConfigProject
from arcadiaMergeTool.models.config_project_model import ConfigProjectModel

class ConfigModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    project: ConfigProject
    base: ConfigProjectModel
    target: ConfigProjectModel
    models: List[ConfigProjectModel]
