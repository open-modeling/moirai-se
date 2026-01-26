export LOG_LEVEL=INFO
#each module has own logger, slashes in path are treated as underscores
#export LOG_LEVEL_ARCADIAMERGETOOL_MERGER_ELEMENTS=DEBUG
#export LOG_LEVEL_ARCADIAMERGETOOL_MERGER_PROCESSORS_FUNCTION=DEBUG 
export PYTHONPATH=$PYTHONPATH:..
python -m arcadiaMergeTool example_config.yaml 
