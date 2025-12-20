from typing import List
from pydantic import BaseModel, ConfigDict

from arcadiaMergeTool.models.config_project_model import ConfigProjectModel

class ConfigModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    basePath: str
    base: ConfigProjectModel
    target: ConfigProjectModel
    models: List[ConfigProjectModel]
