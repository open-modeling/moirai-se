from pydantic import BaseModel, ConfigDict

from arcadiaMergeTool.models.config_project_model import ConfigProjectModel

class MergerConfigModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    baseModel: ConfigProjectModel
    basePath: str
    infoPath: str
    name: str
    

