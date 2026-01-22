from capellambse import MelodyModel
import capellambse.model as m

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

def create_element(model: MelodyModel, parent, source):
    pel = parent._element
    el = source._element
    
    # hacks to remove keys of the foreign attributes
    attrib = {}
    for k, i in el.attrib.items():
        if k in ["id", "appliedPropertyValues", "appliedPropertyValueGroups"]:
            continue
        attrib[k] = i

    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(el.attrib)
    print(attrib)
    if el.attrib["id"] == "a6dd668c-1079-4b99-9560-771a42349471":
        exit()

    with model._loader.new_uuid(pel) as obj_id:
        child = pel.makeelement(el.tag, nsmap=el.nsmap, attrib=attrib)
        child.set("id", obj_id)
        pel.append(child)
        model._loader.update_namespaces()
        model._loader.idcache_index(child)
    return m.wrap_xml(model, child)
