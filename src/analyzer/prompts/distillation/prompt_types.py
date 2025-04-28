"""
Knowledge Distillation Prompt Types for CFE/RACFE Detection

This module defines the types of prompts used in the knowledge distillation process.
"""

from enum import Enum
from typing import NamedTuple, Type
from langchain_core.runnables import Runnable
from pydantic import BaseModel


class PromptType(Enum):
    """Types of prompts used in the knowledge distillation process."""
    GRAPH_ANALYSIS = "graph_analysis"
    PROTECTION_DETERMINATION = "protection_determination"
    VARIABLE_IDENTIFICATION = "variable_identification"
    CHECK_IDENTIFICATION = "check_identification"
    RANDOMIZATION_ANALYSIS = "randomization_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    BATCH_GROUP_FORMATION = "batch_group_formation"

# Define the missing DistillationPrompt type
class DistillationPrompt(NamedTuple):
    """Simple container for a runnable chain and its expected output model."""
    runnable: Runnable
    output_model: Type[BaseModel]
