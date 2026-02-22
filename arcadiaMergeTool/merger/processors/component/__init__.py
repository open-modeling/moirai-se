"""Find and merge Components."""

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

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

from . import exchange, physical, port, realization

__all__ = [
    "exchange",
    "physical",
    "port",
    "realization",
]

LOGGER = getLogger(__name__)

T = mm.la.LogicalComponent | mm.sa.SystemComponent | mm.oa.Entity | mm.epbs.ConfigurationItem

@clone.register
def _(x: T, coll: m.ElementList[T], _mapping: MergerElementMappingMap): # pyright: ignore[reportInvalidTypeArguments]
    return coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_abstract = x.is_abstract,
        is_actor = x.is_actor,
        is_human = x.is_human,
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
    targetCollection = None

    destParent = getDestParent(x, mapping)

    if (isinstance(destParent, (mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg))
        ) and x.parent.components[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect components are there
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.components.filter(lambda y: not y.is_abstract and not y.is_actor and not y.is_human)[0], False)
        return Processed
    if isinstance(destParent, mm.epbs.ConfigurationItemPkg) and x.parent.configuration_items[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect configuration items are there
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items.filter(lambda y: y.name == x.name)[0], False)
        return Processed
    if isinstance(destParent, (mm.cs.Component, mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg)):
        targetCollection = destParent.components
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
        targetCollection = destParent.configuration_items
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T], # pyright: ignore[reportInvalidTypeArguments] expect component is correct collection element
    _mapping: MergerElementMappingMap
):
    # use weak match by name
    # TODO: implement strong match by PVMT properties
    return list(filter(lambda y: y.name == x.name, coll))
