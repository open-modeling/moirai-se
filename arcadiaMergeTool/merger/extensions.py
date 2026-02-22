import sys

import capellambse.metamodel as mm
from capellambse.metamodel import re

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.helpers.constants import REC_CATALOG_NAME
from arcadiaMergeTool.helpers.types import MergerElementMappingMap
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel

LOGGER = getLogger(__name__)

def mergeExtensions(
    dest: CapellaMergeModel,
    base: CapellaMergeModel,
    src: list[CapellaMergeModel],
    elementsMappingMap: MergerElementMappingMap,
):
    """Merge all extensions into the target model.

    Parameters
    ----------
    param dest
        Target model
    param
        base model to align content against
    param
        src List of the

    Description
    -----------
    Method collects all references extensions into the target model.
    At present only REC Catalog / RPL elements are considered

    Logic behind
    1. all REC elements excluded
    2. all RPLs are copied and linked into the right catalogs
    3. all referenced elements are aligned with target libraries and created empty in target model (to be completed later)
    """
    LOGGER.info(
        f"[{mergeExtensions.__qualname__}] begin merging model catalogs into target model"
    )

    extensionsMap: dict[str, tuple[re.RecCatalog, dict[str, re.CatalogElement]]] = {}
    """ Map of extension type to the extension itself, track catalog only
    key - catalog name
    value - tuple of
      * catalog
      * map of its elements
        * key - catalog element origin uuid
        * value - catalog element from target model
    """
    catalogElementsMap: dict[
        str, tuple[re.CatalogElement, dict[str, re.CatalogElementLink]]
    ] = {}
    """ Map of catalog elements and links
    key - catalog element origin uuid
    value - tuple of
      * element
      * map of links
        * key - origin link id
        * value - link
    """
    prj: mm.capellamodeller.Project = dest.model.project

    for ext in prj.model_root.extensions:
        if isinstance(ext, re.RecCatalog):
            LOGGER.debug(
                f"[{mergeExtensions.__qualname__}] Cache: REC Catalog [%s] found in target model, record contents",
                ext.uuid,
            )

            # cache extension
            extensionsMap[ext.name] = (ext, {})
            extensionElementMap = extensionsMap[ext.name][1]

            for elem in ext.elements:
                if isinstance(elem, re.CatalogElement):
                    elementsMappingMap[(elem._model.uuid, elem.uuid)] = (elem, True)

                    if elem.kind == re.CatalogElementKind.RPL:
                        LOGGER.debug(
                            f"[{mergeExtensions.__qualname__}] Cache: catalog with uuid [%s]",
                            elem.uuid,
                        )
                        # refer to origin uuid, as long as it points to the stable ID in the source library
                        source = elem.origin
                        if source:
                            # cache catalog element
                            extensionElementMap[source.uuid] = source

                            uuid = source.uuid
                            if catalogElementsMap.get(uuid) is None:
                                catalogElementsMap[uuid] = (elem, {})
                            catalogEntry = catalogElementsMap[uuid][1]

                            for link in elem.links:
                                # it's safe to assume model correctness, but broken models must be filtered out on reading
                                origin = link.origin
                                target = link.target
                                if origin is not None and target is not None:
                                    catalogEntry[origin.uuid] = link

                                    cacheOriginKey = (origin.source.uuid, origin.uuid) # pyright: ignore[reportOptionalMemberAccess] expect origin already exists in the model
                                    elementsMappingMap[cacheOriginKey] = (target, True)
                                else:
                                    # stop merge on broken libraries
                                    LOGGER.fatal(
                                        f"[{mergeExtensions.__qualname__}] Cache: catalog link [%s] points to broken entities, origin state is [%s], target state is [%s]",
                                        link.uuid,
                                        origin is None,
                                        target is None,
                                    )
                                    sys.exit(str(ExitCodes.MergeFault))
                        else:
                            LOGGER.warning(
                                f"[{mergeExtensions.__qualname__}] Cache: unknown catalog element [%s] does not have origin",
                                elem.uuid,
                            )
                    else:
                        LOGGER.warning(
                            f"[{mergeExtensions.__qualname__}] Cache: skip merge of catalog element [%s] of kind [%s]",
                            elem.uuid,
                            elem.kind,
                        )
                else:
                    LOGGER.warning(
                        f"[{mergeExtensions.__qualname__}] Cache: unknown catalog element [%s] detacted in target model extension [%s]",
                        elem.uuid,
                        ext.name,
                    )
        else:
            LOGGER.warning(
                f"[{mergeExtensions.__qualname__}] Cache: unknown extension [%s] detacted in target model",
                ext.name,
            )

    destExt = dest.model.project.model_root.extensions

    _model = dest.model

    for model in src:
        LOGGER.debug(
            f"[{mergeExtensions.__qualname__}] Merge: process model [%s], [%s]",
            model.model.name,
            model.model.uuid,
        )

        prj: mm.capellamodeller.Project = model.model.project
        extensions = prj.model_root.extensions
        for ext in extensions:
            if isinstance(ext, re.RecCatalog):
                LOGGER.debug(
                    f"[{mergeExtensions.__qualname__}] Merge: REC Catalog [%s] found in source model [%s], record contents",
                    ext.uuid,
                    model.model.name,
                )

                # create catalog if any found in source models but missing in target
                # feel safe using name based match for catalogs, nobody must override default name
                if extensionsMap.get(ext.name) is None:
                    catalog = destExt.create("RecCatalog", name=REC_CATALOG_NAME)
                    extensionsMap[catalog.name] = (catalog, {})

                (destCatalog, destExtensionsMap) = extensionsMap[ext.name]

                for elem in ext.elements:
                    if isinstance(elem, re.CatalogElement):
                        if elem.kind == re.CatalogElementKind.RPL:
                            # at present only RPLs are considered, other extension types are logged, but ignored
                            # TODO: refactor this code to extract merger into specialized function
                            LOGGER.debug(
                                f"[{mergeExtensions.__qualname__}] Merge: catalog with uuid [%s]",
                                elem.uuid,
                            )

                            # refer to origin uuid, as long as it points to the stable ID in the source library
                            source = elem.origin
                            if source is not None and source.uuid:
                                # if no RPL recorded in target extensions, create one
                                targetElem = destExtensionsMap.get(source.uuid)
                                if targetElem is None:
                                    try:
                                        defaultCompliancy = _model.by_uuid(
                                            str(elem.default_replica_compliancy.uuid)  # pyright: ignore[reportOptionalMemberAccess] expect default_replica_compliancy exists
                                        )
                                        compliancy = _model.by_uuid(
                                            str(elem.current_compliancy.uuid)  # pyright: ignore[reportOptionalMemberAccess] expect current_compliancy exists
                                        )
                                        origin = _model.by_uuid(str(source.uuid))

                                        # new catalog element consists of elements copied into target model
                                        element = destCatalog.elements.create(
                                            "CatalogElement",
                                            name=elem.name,
                                            kind=elem.kind,
                                            current_compliancy=compliancy,
                                            default_replica_compliancy=defaultCompliancy,
                                            origin=origin,
                                            suffix=elem.suffix,
                                        )

                                        elementsMappingMap[(elem._model.uuid, elem.uuid)] = (element, True)

                                        destExtensionsMap[source.uuid] = element
                                        LOGGER.debug(
                                            f"[{mergeExtensions.__qualname__}] Merge: created new extension element [%s] with uuid [%s], origin [%s] with uuid [%s]",
                                            element.name,
                                            element.uuid,
                                            origin.name,
                                            origin.uuid,
                                        )
                                    except Exception as ex:
                                        LOGGER.fatal(
                                            f"[{mergeExtensions.__qualname__}] Merge: can't copy RPL into target model",
                                            ex,
                                        )
                                        sys.exit(str(ExitCodes.MergeFault))
                                else:
                                    elementsMappingMap[(elem._model.uuid, elem.uuid)] = (targetElem, True)
                                    # TODO: implement sanity check to ensure replicas consistency across the models
                                    isSane = True
                                    # isSane = (targetElem.name == elem.name
                                    #     and targetElem.kind == elem.kind
                                    #     and targetElem.current_compliancy == elem.current_compliancy  # pyright: ignore[reportOptionalMemberAccess] expect model elements are correct and sane
                                    #     and targetElem.suffix == elem.suffix
                                    #     )
                                    if not isSane:
                                        LOGGER.error(
                                            (
                                                f"[{mergeExtensions.__qualname__}] Merge: Source and Target RPLs are not the same target [%s], [%s]",
                                                targetElem,
                                                source,
                                            )
                                        )

                                if catalogElementsMap.get(source.uuid) is None:
                                    # access tuple directly, cached entry must already be there
                                    catalogElementsMap[source.uuid] = (
                                        destExtensionsMap[source.uuid],
                                        {},
                                    )

                                # deconstruct tuple to get access to cache and target catalog element
                                (catalogElement, catalogEntry) = catalogElementsMap[
                                    source.uuid
                                ]

                            else:
                                LOGGER.warning(
                                    f"[{mergeExtensions.__qualname__}] Merge: unknown catalog element [%s] does not have origin",
                                    elem.uuid,
                                )
                        else:
                            LOGGER.warning(
                                f"[{mergeExtensions.__qualname__}] Merge: skip merge of catalog element [%s] of kind [%s]",
                                elem.uuid,
                                elem.kind,
                            )
                    else:
                        LOGGER.warning(
                            f"[{mergeExtensions.__qualname__}] Merge: unknown catalog element [%s] detacted in target model extension [%s]",
                            elem.uuid,
                            ext.name,
                        )
            else:
                LOGGER.warning(
                    f"[{mergeExtensions.__qualname__}] Merge: unknown extension [%s] detacted in source model [%s]",
                    ext.name.model.model.name,
                )
