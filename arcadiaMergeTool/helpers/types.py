import typing as t
from capellambse.model import ModelElement

type FromLibrary = bool
type ModelUuid = str
type ComponentUuid = str

type MergerElementMappingMap = dict[
    tuple[
        ModelUuid,  # model uuid
        ComponentUuid,  # component uuid
    ],
    tuple[
        ModelElement,  # matching component in destination model
        FromLibrary,  # came from library flag
    ],
]

ModelElement_co = t.TypeVar("ModelElement_co", bound=ModelElement, covariant=True)
