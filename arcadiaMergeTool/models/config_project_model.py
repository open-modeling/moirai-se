from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class ConfigProjectModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    name: str
    libs: List[str] = []
    gitModelAttrib: Optional[str] = None
    gitLibAttrib: Optional[str] = None
    projectPath: str
