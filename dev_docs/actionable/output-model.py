"""
Pydantic models for RTL protection analysis outputs
"""

from typing import List, Dict, Union, Optional, Literal
from pydantic import BaseModel, Field


# CFG Models
class Successor(BaseModel):
    id: int = Field(..., description="ID of the successor block")
    condition: str = Field(..., description="Condition for this transition")


class BasicBlock(BaseModel):
    id: int = Field(..., description="Unique block identifier")
    range: List[int] = Field(..., description="[start_line, end_line]")
    pattern: Literal["SEQUENCE", "BRANCH", "LOOP"] = Field(
        ..., description="Block structure pattern"
    )
    successors: List[Successor] = Field(
        default_factory=list, description="Successor blocks"
    )


class CFG(BaseModel):
    blocks: List[BasicBlock] = Field(..., description="All basic blocks")
    entry: int = Field(..., description="Entry block ID")
    exit: List[int] = Field(..., description="Exit block IDs")


# Pattern Models
class ProtectionPattern(BaseModel):
    type: str = Field(..., description="Pattern identifier")
    template: str = Field(..., description="Mathematical formula template")
    blocks: List[int] = Field(..., description="Block IDs using this pattern")
    parameters: Dict[str, str] = Field(
        ..., description="Parameters customizing the template"
    )


class PatternCollection(BaseModel):
    protection_type: Literal["CFE", "RACFE", "BOTH"] = Field(
        ..., description="Overall protection type"
    )
    patterns: List[ProtectionPattern] = Field(..., description="Detected patterns")


# Protection Models
class VariableUpdate(BaseModel):
    expression: str = Field(..., description="Default update expression")
    conditions: Dict[str, str] = Field(
        default_factory=dict, description="Conditional expressions"
    )


class ProtectionVariable(BaseModel):
    name: str = Field(..., description="Variable name")
    init: str = Field(..., description="Initialization expression")
    updates: Dict[str, VariableUpdate] = Field(
        ..., description="Updates by block ID"
    )


class CheckPoint(BaseModel):
    block_id: int = Field(..., description="Block where check occurs")
    location: Literal["BEGIN", "END", "MIDDLE"] = Field(
        ..., description="Position within block"
    )
    expression: str = Field(..., description="Check expression")


class ProtectionSchema(BaseModel):
    variables: List[ProtectionVariable] = Field(
        ..., description="Protection variables"
    )
    checks: List[CheckPoint] = Field(..., description="Validation checks")
    randomization: Optional[Dict[str, Union[str, Dict]]] = Field(
        None, description="RACFE randomization elements"
    )


# Randomization Models (for RACFE)
class RandomElement(BaseModel):
    name: str = Field(..., description="Element name (e.g., #Sig, #SubRanPrevVal)")
    scope: Literal["GLOBAL", "BLOCK", "INSTRUCTION"] = Field(
        ..., description="Scope of this random element"
    )
    properties: List[Literal["UNIQUE", "RANDOM"]] = Field(
        ..., description="Properties of this element"
    )


class RandomizationSchema(BaseModel):
    elements: List[RandomElement] = Field(..., description="Random elements used")
    state_updates: Dict[str, Dict[str, str]] = Field(
        ..., description="State updates by location"
    )
    signatures: Dict[int, str] = Field(
        ..., description="Block-specific signatures"
    )


# Complete Analysis Model
class ProtectionAnalysis(BaseModel):
    """完整的保护分析结果模型
    整合了所有分析阶段的结果，包括：
    1. 元数据：分析的文件信息和保护类型
    2. 核心分析组件：控制流图、保护模式和机制
    3. RACFE特定组件：随机化模式（如果使用）

    示例数据展示了典型的CFE保护实现，包括：
    - 基本块结构（如分支块）
    - 变量检查模式
    - 保护变量的初始化和更新规则
    - 检查点位置和表达式
    """

    # Metadata
    files: Dict[str, str] = Field(
        ..., description="Paths to the analyzed files"
    )
    protection_type: Literal["CFE", "RACFE", "BOTH"] = Field(
        ..., description="Detected protection type"
    )

    # Core analysis components
    cfg: CFG = Field(..., description="Control flow graph")
    patterns: List[ProtectionPattern] = Field(..., description="Protection patterns")
    protection: ProtectionSchema = Field(..., description="Protection mechanisms")

    # RACFE-specific components (optional)
    randomization: Optional[RandomizationSchema] = Field(
        None, description="Randomization schema (for RACFE)"
    )

    class Config:
        """Example configuration with sample data"""

        schema_extra = {
            "example": {
                "files": {
                    "protected": "protected_rtl.v",
                    "unprotected": "unprotected_rtl.v"
                },
                "protection_type": "CFE",
                "cfg": {
                    "blocks": [
                        {
                            "id": 1,
                            "range": [10, 25],
                            "pattern": "BRANCH",
                            "successors": [
                                {"id": 2, "condition": "x > 0"},
                                {"id": 3, "condition": "default"}
                            ]
                        }
                    ],
                    "entry": 1,
                    "exit": [3]
                },
                "patterns": [
                    {
                        "type": "VARIABLE_CHECK",
                        "template": "$V_{out} = V_{in} + BB_{id} - Succ_{id}$",
                        "blocks": [1, 4, 7],
                        "parameters": {"variable": "S", "check_location": "BEGIN"}
                    }
                ],
                "protection": {
                    "variables": [
                        {
                            "name": "S",
                            "init": "BB_ID[1]",
                            "updates": {
                                "1": {
                                    "expression": "S + BB_ID[1] - BB_ID[next]",
                                    "conditions": {
                                        "true": "S + BB_ID[1] - BB_ID[2]",
                                        "false": "S + BB_ID[1] - BB_ID[3]"
                                    }
                                }
                            }
                        }
                    ],
                    "checks": [
                        {
                            "block_id": 1,
                            "location": "BEGIN",
                            "expression": "S == BB_ID[1]"
                        }
                    ]
                }
            }
        }


# Results from individual stages
class CFGResult(BaseModel):
    """Result from the CFG extraction stage"""
    cfg: CFG


class PatternResult(BaseModel):
    """Result from the pattern detection stage"""
    protection_type: Literal["CFE", "RACFE", "BOTH"]
    patterns: List[ProtectionPattern]


class ProtectionResult(BaseModel):
    """Result from the protection schema stage"""
    variables: List[ProtectionVariable]
    checks: List[CheckPoint]
    randomization: Optional[Dict[str, Union[str, Dict]]] = None
