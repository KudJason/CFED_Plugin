"""
Pydantic Models for Knowledge Distillation Data Preparation.

These models define the structure for inputs and outputs of the
LangChain prompts used to analyze code against CFE/RACFE rules.
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

# --- Graph Analysis ---

class Edge(BaseModel):
    source: int
    target: int
    condition: Optional[str] = None

class SimplifiedGraph(BaseModel):
    """Represents a simplified control flow graph using edges."""
    edges: List[Edge]
    entry: int
    exit: List[int]
    block_patterns: Dict[str, Literal["SEQUENCE", "BRANCH", "LOOP"]] = Field(default_factory=dict)
    block_ranges: Dict[str, List[int]] = Field(default_factory=dict) # Maps block_id str to [start_line, end_line]

class GraphNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the node (e.g., variable name, block label)")
    type: str = Field(..., description="Type of the node (e.g., 'variable', 'signal', 'register', 'process', 'assignment', 'conditional', 'block')")
    label: str = Field(..., description="Display label for the node")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties (e.g., bit width for a variable)")

class GraphEdge(BaseModel):
    source: str = Field(..., description="ID of the source node")
    target: str = Field(..., description="ID of the target node")
    type: str = Field(..., description="Type of the relationship (e.g., 'reads', 'writes', 'controls', 'next')")
    label: Optional[str] = Field(None, description="Display label for the edge")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties (e.g., condition for a control edge)")

class GraphAnalysisOutput(BaseModel):
    """Structured output for the control/data flow graph analysis."""
    is_rtl: bool = Field(True, description="Flag indicating if the analyzed code was determined to be RTL (Verilog/VHDL).")
    analysis_skipped_reason: Optional[str] = Field(None, description="Reason why analysis was skipped (e.g., 'Input code is not RTL').")
    nodes: List[GraphNode] = Field(default_factory=list, description="List of nodes in the graph")
    edges: List[GraphEdge] = Field(default_factory=list, description="List of edges representing relationships between nodes")
    summary: Optional[str] = Field(None, description="A brief textual summary of the graph's key features or components.")

# --- Protection Determination ---

class ProtectionIndicators(BaseModel):
    cfe: List[str] = Field(default_factory=list)
    racfe: List[str] = Field(default_factory=list)

class ProtectionDeterminationOutput(BaseModel):
    protection_type: Literal["CFE", "RACFE", "BOTH", "NONE"]
    indicators: ProtectionIndicators
    confidence: float = Field(ge=0.0, le=1.0)

# --- Rule Verification ---

class RuleVerificationDetail(BaseModel):
    rule_id: str = Field(description="Identifier for the specific rule from rules.md being checked.")
    is_met: bool = Field(description="Whether the rule is met.")
    evidence: List[str] = Field(description="Code snippets, block IDs, or variable values supporting the finding.")
    deviation_description: Optional[str] = Field(default=None, description="Description of how the code deviates from the rule, if not met.")

class VariableVerification(BaseModel): # Simplified: Combine Variable info + Verification details
    rule_id: str # e.g., "CFE.Var.Check" or "RACFE.S.Init"
    variable_name: str
    check_type: Literal["Initialization", "Update", "Property"] # Type of check (Init, Update, SigProperty, etc.)
    is_met: bool
    evidence: List[str]
    deviation_description: Optional[str] = None
    scope: Optional[str] = None # Optional scope info

class InstructionPatternVerification(BaseModel):
    pattern_name: Literal["SETUP", "BEGIN", "MIDDLE", "END", "INTRA"]
    is_present: bool
    found_instructions: List[str] = Field(default_factory=list)
    missing_instructions: List[str] = Field(default_factory=list)
    extra_instructions: List[str] = Field(default_factory=list)
    evidence_locations: List[str] = Field(description="Block IDs or line ranges where the pattern was expected/found.")

class RuleVerificationOutput(BaseModel):
    variable_verifications: List[VariableVerification] = Field(default_factory=list)
    instruction_pattern_verifications: List[InstructionPatternVerification] = Field(default_factory=list)
    # Add other checks as needed, e.g., value property checks

# --- Final Report ---

class ComplianceReport(BaseModel):
    overall_compliance: Literal["FULL", "PARTIAL", "NONE"]
    protection_type_detected: Literal["CFE", "RACFE", "BOTH", "NONE"]
    summary: str
    rule_verification_results: RuleVerificationOutput
    graph_analysis: SimplifiedGraph 