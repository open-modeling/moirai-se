import shortuuid

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import yaml

class ExitCodes(Enum):
    OK = 0,
    Fail = 1,
    CommandLine = 2,
    MergeFault = 3

def loadOrExit (path: str, role: str) -> str:
    """Loads resources"""
    if not Path(path).exists():
        raise Exception(f"Error: {role} file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def _get_timestamp() -> str:
    """Get ISO 8601 timestamp"""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000+00:00')

def _gen_id(prefix: str = "ID", name: str|None = None) -> str:
    """Generate unique identifier"""
    return f"{prefix}_{shortuuid.uuid(name)}"