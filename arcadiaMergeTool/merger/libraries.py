import capellambse

from pathlib import PurePosixPath
from arcadiaMergeTool import getLogger
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.metamodel.libraries import LibraryReference
from capellambse.model import ModelElement

LOGGER = getLogger(name=__name__)

def mergeLibraries(
    dest: CapellaMergeModel, base: CapellaMergeModel, src: list[CapellaMergeModel]
):
    """Collect Libraries into destination model

    Parameters
    ==========
    dest:
        Target model to add libraries to
    base:
        Base Library to aligh all models with
    src:
        Source models to take other libraries from

    Description
    ===========
    Collect libraries into the first reference of destination model.
    Assume destination model has only first and empty set of referwnces

    """
    cache: dict[str, bool] = {}

    LOGGER.info(
        f"[{mergeLibraries.__qualname__}] begin merging libraries into target model"
    )

    def linkLibrary (lib, model, cache):
        # assume it's safe to merge libraries into the first ModelInfo extension
        dst_ext: capellambse.model.ModelElement = model.project.extensions[0]

        lib_id: str = lib.extensions[0].uuid 
        if lib and not cache.get(lib_id):
            name = lib.name
            LOGGER.debug(
                f"[{linkLibrary.__qualname__}] adding new library [%s]",
                name,
            )

            #in case of library is not loaded, link it
            model._loader.link_library(
                PurePosixPath(name)
            )

            if not cache.get(lib_id):
                dst_ext.references.create(
                    "LibraryReference", library=dest.model.by_uuid(lib_id)
                )
                cache[lib_id] = True



    for ext in dest.model.project.extensions:
        for ref in ext.references:
            if isinstance(ref, LibraryReference):
                try:
                    lib: ModelElement = ref.library.parent # pyright: ignore[reportAssignmentType, reportOptionalMemberAccess] expect parent exists and it's ModelElement
                    if lib is not None:
                        cache[lib.uuid] = True
                    else:
                        ext.references.remove(ref)
                except Exception as e:
                    LOGGER.warning(
                        f"[{mergeLibraries.__qualname__}] library for refererence [%s] is not initialized, remove from model [%r]",
                        ref.uuid,
                        e,
                    )
                    ext.references.remove(ref)

    linkLibrary(base.model.project, dest.model, cache)

    for model in src:
        proj = model.model.project
        for ext in proj.extensions:
            for ref in ext.references:
                if isinstance(ref, LibraryReference):
                    ext = ref.library
                    if ext is not None:
                        linkLibrary(ext.parent, dest.model, cache)
