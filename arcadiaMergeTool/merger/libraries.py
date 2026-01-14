import capellambse

from pathlib import PurePosixPath
from arcadiaMergeTool import getLogger
from arcadiaMergeTool.models.capellaModel import CapellaMergeModel
from capellambse.metamodel.libraries import LibraryReference

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

    # assume it's safe to merge libraries into the first ModelInfo extension
    dst_ext: capellambse.model.ModelElement = dest.model.project.extensions[0]

    for ext in dest.model.project.extensions:
        for ref in ext.references:
            if isinstance(ref, LibraryReference):
                try:
                    lib = ref.library
                    if lib:
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

    libs: list[CapellaMergeModel] = []
    libs.extend(src)
    libs.append(base)

    for model in libs:
        proj = model.model.project
        for ext in proj.extensions:
            for ref in ext.references:
                if isinstance(ref, LibraryReference):
                    lib = ref.library
                    if lib and not cache.get(lib.uuid):
                        name = lib.parent.name  # pyright: ignore[reportAttributeAccessIssue] name is a valid attribute here
                        LOGGER.debug(
                            f"[{mergeLibraries.__qualname__}] adding new library [%s]",
                            name,
                        )

                        """in case of library is not loaded, link it"""
                        dest.model._loader._link_library(
                            PurePosixPath("product-configuration")
                        )

                        if not cache.get(lib.uuid):
                            new_lib = dest.model.by_uuid(lib.uuid)
                            dst_ext.references.create(
                                "LibraryReference", library=new_lib
                            )
                            cache[lib.uuid] = True
