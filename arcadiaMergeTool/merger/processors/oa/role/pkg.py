"""Find and merge RolePkg."""

import capellambse.model as m
from capellambse import helpers
from capellambse.metamodel import oa

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    Processed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = oa.RolePkg

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    # use weak match by name
    # TODO: implement strong match by PVMT properties
    return list(filter(lambda y: y.name == x.name, coll))

@clone.register
def _ (x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
    )


@process.register
def _(
    x: T,
    _dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    destParent = getDestParent(x, mapping);

    if isinstance(destParent, oa.OperationalAnalysis):
        package = destParent.interface_pkg
        mapping[(x._model.uuid, x.uuid)] = (package, False)  # pyright: ignore[reportArgumentType] expect package is correct
        return Processed

    if isinstance(destParent, T):
        targetCollection = destParent.packages
    else:
        return Fault

    return targetCollection
