"""Find and merge Literal Values."""

import sys

import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information.datavalue as dv
import capellambse.model as m

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes, create_element
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Continue,
    Postponed,
    Processed,
    doProcess,
    preprocess,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = dv.BinaryExpression

@preprocess.register
def _(x: T,
    dest: CapellaMergeModel,
    src: CapellaMergeModel,
    base: CapellaMergeModel,
    mapping: MergerElementMappingMap
):
    if doProcess(x.unit, dest, src, base, mapping) == Postponed: # pyright: ignore[reportArgumentType] expect source exists
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

    destParent = getDestParent(x, mapping)

    el = None
    if (isinstance(destParent, (dv.BinaryExpression, dt.NumericType, dt.BooleanType))):
        el =create_element(dest.model, destParent, x)
        el.description = x.description
        el.expression = x.expression
        el.is_abstract = x.is_abstract
        el.is_visible_in_doc = x.is_visible_in_doc
        el.is_visible_in_lm = x.is_visible_in_lm
        el.name = x.name
        el.operator = x.operator
        el.review = x.review
        el.sid = x.sid
        el.summary = x.summary
        el.unparsed_expression = x.unparsed_expression

        if x.unit is not None:
            mappedType = mapping[(x._model.uuid, x.unit.uuid)]
            el.unit = mappedType[0]
    else:
        LOGGER.fatal(
            f"[{process.__qualname__}] Literal Values parent is not a valid parent, Literal Values name [%s], uuid [%s], class [%s], parent name [%s], uuid [%s], class [%s], model name [%s], uuid [%s]",
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

    mapping[(x._model.uuid, x.uuid)] = (el, False)

    return Processed
