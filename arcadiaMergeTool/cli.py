"""
JSON to ReqIF Converter - cli
"""

import json
import sys

import pydantic

from arcadiaMergeTool import logger
from arcadiaMergeTool.helpers import ExitCodes, loadOrExit
from arcadiaMergeTool.models.config_model import ConfigModel
from arcadiaMergeTool.merger import merge

def cli():
    """Main entry point"""

    if len(sys.argv) < 1:
        print("Usage: python capellaMergeTool <config.json>")
        print()
        print("Arguments:")
        print("  config.yaml   - merger configuration")
        return ExitCodes.CommandLine

    try:
        json_path = sys.argv[1]

        config = pydantic.TypeAdapter(ConfigModel).validate_python(loadOrExit(json_path,   "Input"))

        merge(config)
        
        return ExitCodes.OK

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return ExitCodes.Fail
