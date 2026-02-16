"""Find and merge Opaque Expression."""

import sys

import capellambse.metamodel.capellacore as cc
import capellambse.metamodel.information.datatype as dt
import capellambse.metamodel.information.datavalue as dv
import capellambse.model as m

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes, create_element
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Processed,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

T = dv.OpaqueExpression

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
    if (isinstance(destParent, (dv.BinaryExpression, dt.NumericType, dt.BooleanType, cc.Constraint))):
        el =create_element(dest.model, destParent, x)

        el.bodies = x.bodies
        el.languages = x.languages
        el.description = x.description
        el.is_visible_in_doc = x.is_visible_in_doc
        el.is_visible_in_lm = x.is_visible_in_lm
        el.name = x.name
        el.review = x.review
        el.sid = x.sid
        el.summary = x.summary

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
