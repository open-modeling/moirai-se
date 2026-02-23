"""Find and merge CapellaTypesFolder."""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.extensions.reqif import capellarequirements

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = capellarequirements.CapellaTypesFolder

@clone.register
def _ (x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        description = x.description,
        identifier = x.identifier,
        long_name = x.long_name,
        sid = x.sid,
    )

@process.register
def _(
    x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    destParent = getDestParent(x, mapping)

    if isinstance(destParent, (mm.cs.BlockArchitecture, capellarequirements.CapellaModule)):
        targetCollection = destParent.requirement_types_folders
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    # use weak match by name
    # TODO: implement strong match by PVMT properties
    return list(filter(lambda y: y.long_name == x.long_name, coll))
