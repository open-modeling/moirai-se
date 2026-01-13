from capellambse.model import ModelElement

type MergerElementMappingMap = dict[
    tuple[
        str,  # model uuid
        str,  # component uuid
    ],
    tuple[
        ModelElement,  # matching component in destination model
        bool,  # came from library flag
    ],
]
