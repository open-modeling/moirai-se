import os

import capellambse
import capellambse.model as m

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers import ExitCodes
from arcadiaMergeTool.models.config_project_model import ConfigProjectModel
from arcadiaMergeTool.models.merger_config_model import MergerConfigModel
from arcadiaMergeTool.models.config_model import ConfigModel
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from arcadiaMergeTool.helpers.merger import mergeLibraries
from capellambse.model import ModelElement
import capellambse.metamodel.re as re
import capellambse.metamodel.capellamodeller



LOGGER = getLogger(__name__)


type MergerElementMappingMap = dict[tuple[str, str], ModelElement]


def merge(config: ConfigModel):

    extModels = config.models
    targetModel = config.target
    baseModel: ConfigProjectModel = config.base

    mergerConfig = MergerConfigModel(basePath=config.project.basePath, infoPath=os.path.join(config.project.basePath, 'debug/'), baseModel=baseModel, name=config.project.name)
    os.makedirs(mergerConfig.infoPath, exist_ok=True)

    modelSrc = []
    modelDst = CapellaMergeModel(targetModel, mergerConfig)
    modelBase = CapellaMergeModel(model=baseModel, config=mergerConfig)

    for item in extModels:
        LOGGER.debug(f"[{merge.__name__}] processing external models item ({item})")
        model = CapellaMergeModel(item, config=mergerConfig)
        
        modelSrc.append(model)

    elementMappingMap: MergerElementMappingMap = {}

    mergeLibraries(modelDst, modelBase, modelSrc)
    mergeExtensions(modelDst, modelBase, modelSrc, elementMappingMap)

    modelDst.save()


def mergeModels(dest: CapellaMergeModel, base: CapellaMergeModel, src: list[CapellaMergeModel]):
    LOGGER.info(f"[{mergeModels.__name__}] begin merging models into target model")

REC_CATALOG_NAME = "REC Catalog"

def mergeExtensions(dest: CapellaMergeModel, base: CapellaMergeModel, src: list[CapellaMergeModel], elementsMappingMap: MergerElementMappingMap):

    """Merge all extensions into the target model
    
    Parameters
    ==========

    param dest
        Target model
    param 
        base model to align content against
    param 
        src List of the 

    Description
    ===========
    Method collects all references extensions into the target model.
    At present only REC Catalog / RPL elements are considered

    Logic behind
    1. all REC elements excluded
    2. all RPLs are copied and linked into the right catalogs
    3. all referenced elements are aligned with target libraries and created empty in target model (to be completed later)
    """
    LOGGER.info(f"[{mergeExtensions.__name__}] begin merging model catalogs into target model")

    extensionsMap: dict[str, tuple[re.RecCatalog, dict[str, re.CatalogElement]]] = {}
    """ Map of extension type to the extension itself, track catalog only
    key - catalog name
    value - tuple of
      * catalog
      * map of its elements
        * key - catalog element origin uuid
        * value - catalog element from target model
    """
    catalogElementsMap: dict[str, tuple[re.CatalogElement, dict[str, re.CatalogElementLink]]] = {}
    """ Map of catalog elements and links
    key - catalog element origin uuid
    value - tuple of
      * element
      * map of links
        * key - origin link id
        * value - link
    """

    for ext in dest.model.project.model_root.extensions:
        if isinstance(ext, re.RecCatalog):
            LOGGER.debug(f"[{mergeExtensions.__name__}] Cache: REC Catalog [%s] found in target model, record contents", ext.uuid)

            # cache extension
            extensionsMap[ext.name] = (ext, {})
            extensionElementMap = extensionsMap[ext.name][1]

            for elem in ext.elements:
                if isinstance(elem, re.CatalogElement):
                    if elem.kind == re.CatalogElementKind.RPL:
                        LOGGER.debug(f"[{mergeExtensions.__name__}] Cache: catalog with uuid [%s]", elem.uuid)
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

                                    cacheOriginKey = (origin._model.uuid, origin.uuid)
                                    elementsMappingMap[cacheOriginKey] = target
                                else:
                                    # stop merge on broken libraries
                                    LOGGER.fatal(f"[{mergeExtensions.__name__}] Cache: catalog link [%s] points to broken entities, origin state is [%s], target state is [%s]", link.uuid, origin is None, target is None)
                                    exit(str(ExitCodes.MergeFault))
                        else:
                            LOGGER.warning(f"[{mergeExtensions.__name__}] Cache: unknown catalog element [%s] does not have origin", elem.uuid)
                    else:
                        LOGGER.warning(f"[{mergeExtensions.__name__}] Cache: skip merge of catalog element [%s] of kind [%s]", elem.uuid, elem.kind)
                else:
                   LOGGER.warning(f"[{mergeExtensions.__name__}] Cache: unknown catalog element [%s] detacted in target model extension [%s]", elem.uuid, ext.name)
        else:
            LOGGER.warning(f"[{mergeExtensions.__name__}] Cache: unknown extension [%s] detacted in target model", ext.name)

    destExt = dest.model.project.model_root.extensions

    _model = dest.model

    for model in src:
        LOGGER.debug(f"[{mergeExtensions.__name__}] Merge: process model [%s], [%s]", model.model.name, model.model.uuid)
        extensions = model.model.project.model_root.extensions
        for ext in extensions:
            if isinstance(ext, re.RecCatalog):
                LOGGER.debug(f"[{mergeExtensions.__name__}] Merge: REC Catalog [%s] found in source model [%s], record contents", ext.uuid, model.model.name)

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
                            LOGGER.debug(f"[{mergeExtensions.__name__}] Merge: catalog with uuid [%s]", elem.uuid)

                            # refer to origin uuid, as long as it points to the stable ID in the source library
                            source = elem.origin
                            if source and source.uuid:

                                # if no RPL recorded in target extensions, create one
                                targetElem = destExtensionsMap.get(source.uuid)
                                if targetElem is None:
                                    try:
                                        defaultCompliancy = _model.by_uuid(str(elem.default_replica_compliancy.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect default_replica_compliancy exists
                                        compliancy = _model.by_uuid(str(elem.current_compliancy.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect current_compliancy exists
                                        origin = _model.by_uuid(str(source.uuid))
                                        
                                        # new catalog element consists of elements copied into target model
                                        element = destCatalog.elements.create("CatalogElement", 
                                            name = elem.name,
                                            kind = elem.kind, 
                                            current_compliancy = compliancy,
                                            default_replica_compliancy = defaultCompliancy,
                                            origin = origin,
                                            suffix = elem.suffix,
                                        )
                                        destExtensionsMap[source.uuid] = element
                                        LOGGER.debug(f"[{mergeExtensions.__name__}] Merge: created new extension element [%s] with uuid [%s], origin [%s] with uuid [%s]", element.name, element.uuid, origin.name, origin.uuid)
                                    except Exception as ex:
                                        LOGGER.fatal(f"[{mergeExtensions.__name__}] Merge: can't copy RPL into target model", ex)
                                        exit(str(ExitCodes.MergeFault))
                                else:
                                    # TODO: implement sanity check to ensure replicas consistency across the models
                                    isSane = True
                                    # isSane = (targetElem.name == elem.name 
                                    #     and targetElem.kind == elem.kind
                                    #     and targetElem.current_compliancy == elem.current_compliancy  # pyright: ignore[reportOptionalMemberAccess] expect model elements are correct and sane
                                    #     and targetElem.suffix == elem.suffix
                                    #     )
                                    if not isSane:
                                        LOGGER.error((f"[{mergeExtensions.__name__}] Merge: Source and Target RPLs are not the same target [%s], [%s]", targetElem, source))

                                if catalogElementsMap.get(source.uuid) is None:
                                    # access tuple directly, cached entry must already be there
                                    catalogElementsMap[source.uuid] = (destExtensionsMap[source.uuid], {})

                                # deconstruct tuple to get access to cache and target catalog element
                                (catalogElement, catalogEntry) = catalogElementsMap[source.uuid]

                                for link in elem.links:
                                    LOGGER.debug(f"[{mergeExtensions.__name__}] Merge: Processing catalog element link [%s]", link.uuid)

                                    # assume all missing cache does not really exists and it's safe to add more links
                                    if catalogEntry.get(link.origin.uuid) is None:  # pyright: ignore[reportOptionalMemberAccess] expect origin must be there, model parsing fails on missing origin
                                        # source = _model.by_uuid(str(link.source.uuid))
                                        # take catalogElement as granted, assume no links can point outside catalog
                                        source = catalogElement

                                        # target elements must be re-constructed by copying relevant properties and elements inside target model
                                        # this adds certain degree of confidence that resulting model contains correctly copied elements
                                        # target = _model.by_uuid(str(link.target.uuid))
                                        target = mergeRplElement(link.target, link.origin, dest, base, elementsMappingMap) # pyright: ignore[reportArgumentType, reportOptionalMemberAccess] expect target already exists in the model
                                        origin = _model.by_uuid(str(link.origin.uuid)) # pyright: ignore[reportOptionalMemberAccess] expect origin exists
                                        newLink = catalogElement.links.create("CatalogElementLink",
                                            source = source,
                                            origin = origin,
                                            target = target)
                                        catalogEntry[origin.uuid] = newLink

                            else:
                                LOGGER.warning(f"[{mergeExtensions.__name__}] Merge: unknown catalog element [%s] does not have origin", elem.uuid)
                        else:
                            LOGGER.warning(f"[{mergeExtensions.__name__}] Merge: skip merge of catalog element [%s] of kind [%s]", elem.uuid, elem.kind)
                    else:
                        LOGGER.warning(f"[{mergeExtensions.__name__}] Merge: unknown catalog element [%s] detacted in target model extension [%s]", elem.uuid, ext.name)
            else:
                LOGGER.warning(f"[{mergeExtensions.__name__}] Merge: unknown extension [%s] detacted in source model [%s]", ext.name. model.model.name)

        # exit(1)

def mergeRplElement(sourceElement: ModelElement, origin: re.CatalogElementLink, dest: CapellaMergeModel, base: CapellaMergeModel, elementsMappingMap: MergerElementMappingMap) -> ModelElement:
    """ Starting point for recursive merge of the model elements
    
    Parameters
    ==========

    sourceElement:
        element of source model to merge into the target model
    origin:
        link to a library to check element against
    dest:
        destination model to merge element into
    base:
        base library to check all elements against
    elementsMappingMap
        global cache of mapped elements
    return:
        element created in destination model

    Description
    ===========

    From this point start recursive merge of every element into destination model
    """

    # create key for cache matches
    cacheKey = (sourceElement._model.uuid, sourceElement.uuid)
    cacheOriginKey = (origin._model.uuid, origin.uuid)

    if elementsMappingMap.get(cacheKey) is not None:
        # immediate cached match, at the moment there's no need for a deep merge
        return elementsMappingMap[cacheKey]
    elif elementsMappingMap.get(cacheOriginKey) is not None:
        # immediate cached match, at the moment there's no need for a deep merge
        return elementsMappingMap[cacheOriginKey]

    # first level of elements will be brought right to their direct parents counterparts
    # in destination model, all others will be delivered based on the components internal structure
    prj: capellambse.metamodel.capellamodeller.Project = dest.model.project

    # use nearest match by name, it is more or less safe in case of the replicas, usually nobody takes care to rename imported elements
    nearestMatch = list(filter(lambda x: x.name == sourceElement.name and x.parent.name == sourceElement.parent.name, dest.model.search(sourceElement.__class__, below = prj.model_root))) # pyright: ignore[reportAttributeAccessIssue] name is a legal attribute in this context

    if len(nearestMatch) == 0:
        LOGGER.debug(f"[{mergeRplElement.__name__}] no matching element found for [%s] uuid [%s] class [%s], append to the model", sourceElement.name, sourceElement.uuid, sourceElement.__class__)
    
        # assume it's safe to search for the nearest match by class and find only one root using two step lookup - by layer and then by parent
        nearestDestLayer = dest.model.search(sourceElement.layer.__class__, below = prj.model_root).pop()
        nearestDestParents = dest.model.search(sourceElement.parent.__class__, below = nearestDestLayer)
        nearestDestParent = None
        if len(nearestDestParents) == 1:
            nearestDestParent = nearestDestParents.pop()
        elif len(nearestDestParents) > 1:
            nearestDestParent = list(filter(lambda x: x.name == sourceElement.parent.name and x.parent.name == sourceElement.parent.parent.name, nearestDestParents)).pop() # pyright: ignore[reportAttributeAccessIssue] name is a legal attribute in this context
        else:
            LOGGER.fatal(f"[{mergeRplElement.__name__}] impossible case, no nearest parent found for [%s] uuid [%s] class [%s], append to the model", sourceElement.name, sourceElement.uuid, sourceElement.__class__)
            exit(str(ExitCodes.MergeFault))

        # note limited use of low level api, it must be used to create immediate structure in simplest possible way
        # for everything else higher level api must be used with appropriate mapping mathods
        lowLevelParent = nearestDestParent._element
        lowLevelSourceElement = sourceElement._element
        with dest.model._loader.new_uuid(lowLevelParent) as uuid:
            attrib = lowLevelSourceElement.attrib
            lowLevelDestElement = lowLevelParent.makeelement(lowLevelSourceElement.tag, attrib=attrib, nsmap=lowLevelSourceElement.nsmap)
            lowLevelDestElement.set('id', uuid)
            lowLevelParent.append(lowLevelDestElement)
            dest.model._loader.idcache_index(lowLevelDestElement)

            # HACK: due to low level model deficiency, following attributes must be recursively processed, otherwise model renders broken due to wrong ids supplied
            if attrib.get("source") is not None:
                sel = sourceElement.source
                rel = mergeRplElement(sel, origin, dest, base, elementsMappingMap)
                lowLevelDestElement.set("source", f"#{rel.uuid}")
            if attrib.get("target") is not None:
                sel = sourceElement.target
                rel = mergeRplElement(sel, origin, dest, base, elementsMappingMap)
                lowLevelDestElement.set("target", f"#{rel.uuid}")
            if attrib.get("abstractType"):
                sel = sourceElement.type
                rel = mergeRplElement(sel, origin, dest, base, elementsMappingMap)
                lowLevelDestElement.set("abstractType", f"#{rel.uuid}")

        destElement = m.wrap_xml(dest.model,lowLevelDestElement)

        elementsMappingMap[cacheKey] = destElement
        elementsMappingMap[cacheOriginKey] = destElement
        return destElement
    else:
        destElement = nearestMatch.pop()
        LOGGER.debug(f"[{mergeRplElement.__name__}] nearest matching element found in target model [%s] uuid [%s] class [%s]; total elements found [%s]",sourceElement.name, sourceElement.uuid, sourceElement.__class__, len(nearestMatch))
        elementsMappingMap[cacheKey] = destElement
        elementsMappingMap[cacheOriginKey] = destElement
        return destElement
    