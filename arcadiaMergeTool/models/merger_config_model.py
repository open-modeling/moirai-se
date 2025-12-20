from typing import Any, List
from pydantic import BaseModel, ConfigDict, Field, constr

from arcadiaMergeTool.models.config_project_model import ConfigProjectModel

class MergerConfigModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    baseModel: ConfigProjectModel
    basePath: str
    infoPath: str
    

