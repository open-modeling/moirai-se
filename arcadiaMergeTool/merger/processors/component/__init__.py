"""Find and merge Components."""

import sys

import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
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

T = mm.cs.Component

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

    if (isinstance(destParent, (mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg, mm.pa.PhysicalComponentPkg))
        ) and x.parent.components[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect components are there
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.components.filter(lambda y: not y.is_abstract and not y.is_actor and not y.is_human)[0], False)
        return Processed
    if isinstance(destParent, mm.epbs.ConfigurationItemPkg) and x.parent.configuration_items[0] == x: # pyright: ignore[reportAttributeAccessIssue] expect configuration items are there
        # map system to system and assume it's done
        mapping[(x._model.uuid, x.uuid)] = (destParent.configuration_items.filter(lambda y: y.name == x.name)[0], False)
        return Processed
    if isinstance(destParent, mm.pa.PhysicalComponent):
        targetCollection = destParent.owned_components # pyright: ignore[reportAttributeAccessIssue] owned_components is a valid property in this context
    elif isinstance(destParent, (mm.cs.Component, mm.pa.PhysicalComponentPkg, mm.sa.SystemComponentPkg, mm.la.LogicalComponentPkg)):
        targetCollection = destParent.components
    elif isinstance(destParent, mm.epbs.ConfigurationItemPkg):
        targetCollection = destParent.configuration_items
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Component parent is not a valid parent, Component name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
            x.name,
            x.uuid,
            x.__class__,
            destParent.name,
            destParent.uuid,
            destParent.__class__,
            x._model.name,
            x._model.uuid,
        )
        sys.exit(str(ExitCodes.MergeFault))

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
