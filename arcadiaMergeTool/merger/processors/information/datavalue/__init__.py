"""Find and merge Literal Values."""

import capellambse.metamodel.information as inf
import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information.datavalue as dv
import capellambse.model as m
from capellambse import helpers

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes, create_element
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Fault,
    Postponed,
    Processed,
    clone,
    doProcess,
    match,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

from . import (
    binary_expression,
    boolean,
    enumeration,
    numeric_reference,
    opaque_expression,
)

__all__ = [
    "binary_expression",
    "boolean",
    "enumeration",
    "numeric_reference",
    "opaque_expression",
]

LOGGER = getLogger(__name__)

T = dv.LiteralNumericValue | dv.LiteralStringValue

@clone.register
def _(x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    newComp = coll.create(helpers.xtype_of(x._element),
        description = x.description,
        is_abstract = x.is_abstract,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
        name = x.name,
        review = x.review,
        sid = x.sid,
        summary = x.summary,
        value = x.value,
    )

    if x.unit is not None:
        mappedType = mapping[(x._model.uuid, x.unit.uuid)]
        newComp.unit = mappedType[0]

    return newComp

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.unit, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect modelParent is compatible with ModelElement
        return Postponed
    return Continue

@process.register
def _(
    x: T,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    targetCollection = None

    destParent = getDestParent(x, mapping)

    if isinstance(destParent, (dt.Enumeration, dt.BooleanType, dt.NumericType, dt.StringType)):
        targetCollection = destParent.data_values
    elif (isinstance(destParent, (dv.BinaryExpression, inf.ExchangeItemElement))):
        el =create_element(dest.model, destParent, x)

        el.description = x.description
        el.is_abstract = x.is_abstract
        el.is_visible_in_doc = x.is_visible_in_doc
        el.is_visible_in_lm = x.is_visible_in_lm
        el.name = x.name
        el.review = x.review
        el.sid = x.sid
        el.summary = x.summary
        el.value = x.value

        if x.unit is not None:
            mappedType = mapping[(x._model.uuid, x.unit.uuid)]
            el.unit = mappedType[0]

        mapping[(x._model.uuid, x.uuid)] = (el, False)
        return Processed
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    coll: m.ElementList[T],
    _mapping: MergerElementMappingMap
):
    return list(filter(lambda y: y._element.tag == x._element.tag and y.value == x.value, coll))
