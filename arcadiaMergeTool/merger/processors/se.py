import capellambse.metamodel as mm
import capellambse.model as m
from capellambse import helpers
from capellambse.metamodel import capellamodeller as ca

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.merger.processors._processor import (
    Fault,
    Postponed,
    Processed,
    clone,
    match,
    process,
)
from arcadiaMergeTool.merger.processors.helpers import getDestParent
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

@process.register
def _(
    x: ca.SystemEngineering,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = None
        if isinstance(x, ca.SystemEngineering):
            package = dest.model.project.model_root

        mapping[(x._model.uuid, x.uuid)] = (package, False) # pyright: ignore[reportArgumentType] expect root is exists and correct element

    return Processed

@process.register
def _(
    x: ca.Project,
    dest: CapellaMergeModel,
    _src: CapellaMergeModel,
    _base: CapellaMergeModel,
    mapping: MergerElementMappingMap,
):
    LOGGER.debug(
        f"[{process.__qualname__}] create root entry for package [%s], class [%s], uuid [%s], model name [%s], uuid [%s]",
        x.name,
        x.__class__,
        x.uuid,
        x._model.name,
        x._model.uuid,
    )

    if mapping.get((x._model.uuid, x.uuid)) is None:
        package = None
        if isinstance(x, ca.Project):
            package = dest.model.project

        mapping[(x._model.uuid, x.uuid)] = (package, False)

    return Processed

T = mm.epbs.PhysicalArchitectureRealization | mm.pa.LogicalArchitectureRealization | mm.la.SystemAnalysisRealization | mm.sa.OperationalAnalysisRealization

@clone.register
def _ (x: T, coll: m.ElementList[T], mapping: MergerElementMappingMap):
    return coll.create(helpers.xtype_of(x._element),
        source = mapping.get((x._model.uuid, x.source.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect source is already there
        target = mapping.get((x._model.uuid, x.target.uuid))[0], # pyright: ignore[reportOptionalMemberAccess, reportOptionalSubscript] expect target is already there
        description = x.description,
        is_visible_in_doc = x.is_visible_in_doc,
        is_visible_in_lm = x.is_visible_in_lm,
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

    if isinstance(destParent, mm.epbs.EPBSArchitecture):
        targetCollection = destParent.physical_architecture_realizations
    elif isinstance(destParent, mm.pa.PhysicalArchitecture):
        targetCollection = destParent.logical_architecture_realizations
    elif isinstance(destParent, mm.la.LogicalArchitecture):
        targetCollection = destParent.system_analysis_realizations
    elif isinstance(destParent, mm.sa.SystemAnalysis):
        targetCollection = destParent.operational_analysis_realizations
    else:
        return Fault

    return targetCollection

@match.register
def _(x: T,
    _destParent: m.ModelElement,
    targetCollection: m.ElementList[T],
    mapping: MergerElementMappingMap
):
    mappedSource = mapping.get((x._model.uuid, x.source.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect source is already there
    mappedTarget = mapping.get((x._model.uuid, x.target.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect target is already there
    if mappedSource is None or mappedTarget is None:
        # if source or target is not mapped, postpone allocation processing
        return Postponed

    return list(filter(lambda y: y.source == mappedSource[0] and y.target == mappedTarget[0], targetCollection)) # pyright: ignore[reportOptionalSubscript] check for none is above, mappedSource and mappedTarget are safe
