from pydantic import BaseModel, ConfigDict

class ConfigProject(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    name: str
    author: str
    basePath: str