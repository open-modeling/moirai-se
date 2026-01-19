import typing as t
from capellambse.model import ModelElement

type FromLibrary = bool
type ModelUuid = str
type ComponentUuid = str
type MergerElementMappingEntry = tuple[
    ModelElement,  # matching component in destination model
    FromLibrary,  # came from library flag
]


type MergerElementMappingMap = dict[
    tuple[
        ModelUuid,  # model uuid
        ComponentUuid,  # component uuid
    ],
    MergerElementMappingEntry
]

ModelElement_co = t.TypeVar("ModelElement_co", bound=ModelElement, covariant=True)
