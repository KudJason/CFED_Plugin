from dataclasses import dataclass
from typing import Dict, List
from .data_model import DataModel, PluginFile
from enum import Enum

# enum for augment_type for change some RTL code to make RTL protection wrong for training data
class AugmentType(Enum):
    INVERT_LOGIC = "Invert the logic of conditional statements to create unexpected behavior."
    REMOVE_CONDITIONALS = "Remove conditional statements to force execution through all paths, leading to potential errors."
    ALTER_VARIABLES = "Change the values of key variables to unexpected states, causing incorrect flow."
    REORDER_INSTRUCTIONS = "Reorder instructions within a block to disrupt the intended execution sequence."
    ADD_NO_OPS = "Insert no-operation instructions to create delays and confuse the control flow."
    MODIFY_JUMP_TARGETS = "Change the targets of jump instructions to redirect execution to unintended blocks."
    DUPLICATE_BLOCKS = "Duplicate existing blocks to create ambiguity in the control flow."
    REMOVE_EXIT_POINTS = "Eliminate exit points from loops or functions to create infinite loops."
    CHANGE_DATA_TYPES = "Alter the data types of variables to introduce type errors during execution."
    INSERT_FAULTY_FUNCTIONS = "Add calls to functions that are known to fail or produce errors."

@dataclass
class AugmentedPluginFile(PluginFile):
    augment_type: AugmentType
    
@dataclass
class AugmentedDataModel(DataModel):
    augmented_plugin_files: List[AugmentedPluginFile]

    @classmethod
    def from_data_model(cls, data_model: DataModel, augmented_plugin_files: List[AugmentedPluginFile]) -> 'AugmentedDataModel':
        return cls(
            id=data_model.id,
            algorithm_name=data_model.algorithm_name,
            algorithm_path=data_model.algorithm_path,
            technique=data_model.technique,
            technique_type=data_model.technique_type,
            selective_level=data_model.selective_level,
            archive_timestamp=data_model.archive_timestamp,
            plugin_files=data_model.plugin_files,
            augmented_plugin_files=augmented_plugin_files
        ) 