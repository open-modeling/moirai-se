import typing as t
from typing import Callable
import capellambse.model as m
import capellambse.metamodel as mm

from arcadiaMergeTool import getLogger
from arcadiaMergeTool.helpers.types import MergerElementMappingMap, ModelElement_co, ModelElement_contra
from arcadiaMergeTool.merger.processors._processor import clone


LOGGER = getLogger(__name__)

