"""
Knowledge Distillation Models for CFE/RACFE Detection

This module provides data structures for knowledge distillation that reduces
API calls and tokens when using models like GPT-4o for RTL protection analysis.
Based on the unified schema design described in knowledge-distillation-cfe-racfe.md.
Simplified to use edges instead of complete CFG.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field


class ProtectionType(Enum):
    """Type of protection mechanism detected."""
    CFE = "CFE"
    RACFE = "RACFE"
    BOTH = "BOTH"


class BlockPattern(Enum):
    """Pattern types for basic blocks."""
    SEQUENCE = "SEQUENCE"
    BRANCH = "BRANCH"
    LOOP = "LOOP"


class CheckLocation(Enum):
    """Location for protection checks within a block."""
    BEGIN = "BEGIN"
    END = "END"


@dataclass
class Edge:
    """Represents an edge between two blocks in the simplified graph."""
    source: int
    target: int
    condition: Optional[str] = None


@dataclass
class SimplifiedGraph:
    """Represents a simplified control flow graph using edges."""
    edges: List[Edge]
    entry: int
    exit: List[int]
    block_patterns: Dict[int, BlockPattern] = field(default_factory=dict)
    block_ranges: Dict[int, List[int]] = field(default_factory=dict)  # Maps block_id to [start_line, end_line]


@dataclass
class VariableUpdate:
    """Represents a protection variable update rule."""
    pattern: str
    blocks: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass
class ProtectionVariable:
    """Represents a protection variable."""
    name: str
    scope: str
    init: str
    updates: VariableUpdate = field(default_factory=VariableUpdate)


@dataclass
class CheckExpression:
    """Represents a protection check expression."""
    block_id: int
    location: CheckLocation
    expression: str
    handling: str = "ABORT"


@dataclass
class RandomizationProperty:
    """Represents randomization properties for RACFE."""
    block_id: int
    signature: str
    properties: List[str] = field(default_factory=list)
    state_updates: Dict[str, str] = field(default_factory=dict)


@dataclass
class Protection:
    """Represents the protection scheme applied to a program."""
    variables: List[ProtectionVariable] = field(default_factory=list)
    checks: List[CheckExpression] = field(default_factory=list)
    randomization: List[RandomizationProperty] = field(default_factory=list)


@dataclass
class Metadata:
    """Metadata for the protection analysis."""
    id: str
    files: Dict[str, str]
    protection_type: ProtectionType


@dataclass
class PatternTemplate:
    """Template for protection patterns."""
    structure: str
    protection_template: Dict[str, str]


@dataclass
class PatternCatalog:
    """Catalog of known protection patterns."""
    patterns: Dict[str, PatternTemplate] = field(default_factory=dict)


@dataclass
class BatchGroup:
    """Group of blocks that share a similar protection pattern."""
    pattern: str
    blocks: List[int]
    template: str
    parameters: Dict[str, Any]


@dataclass
class KnowledgeDistillation:
    """Main class for knowledge distillation schema."""
    metadata: Metadata
    graph: SimplifiedGraph
    protection: Protection
    pattern_catalog: PatternCatalog = field(default_factory=PatternCatalog)
    batch_groups: List[BatchGroup] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary representation."""
        return {
            "metadata": {
                "id": self.metadata.id,
                "files": self.metadata.files,
                "protection_type": self.metadata.protection_type.value
            },
            "graph": {
                "edges": [
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "condition": edge.condition
                    }
                    for edge in self.graph.edges
                ],
                "entry": self.graph.entry,
                "exit": self.graph.exit,
                "block_patterns": {
                    str(block_id): pattern.value
                    for block_id, pattern in self.graph.block_patterns.items()
                },
                "block_ranges": {
                    str(block_id): block_range
                    for block_id, block_range in self.graph.block_ranges.items()
                }
            },
            "protection": {
                "variables": [
                    {
                        "name": var.name,
                        "scope": var.scope,
                        "init": var.init,
                        "updates": {
                            "pattern": var.updates.pattern,
                            "blocks": var.updates.blocks
                        }
                    }
                    for var in self.protection.variables
                ],
                "checks": [
                    {
                        "block_id": check.block_id,
                        "location": check.location.value,
                        "expression": check.expression,
                        "handling": check.handling
                    }
                    for check in self.protection.checks
                ],
                "randomization": [
                    {
                        "block_id": rand.block_id,
                        "signature": rand.signature,
                        "properties": rand.properties,
                        "state_updates": rand.state_updates
                    }
                    for rand in self.protection.randomization
                ]
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeDistillation':
        """Create a KnowledgeDistillation instance from a dictionary."""
        metadata = Metadata(
            id=data["metadata"]["id"],
            files=data["metadata"]["files"],
            protection_type=ProtectionType(data["metadata"]["protection_type"])
        )
        
        edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                condition=edge.get("condition")
            )
            for edge in data["graph"]["edges"]
        ]
        
        block_patterns = {
            int(block_id): BlockPattern(pattern)
            for block_id, pattern in data["graph"]["block_patterns"].items()
        }
        
        block_ranges = {
            int(block_id): block_range
            for block_id, block_range in data["graph"]["block_ranges"].items()
        }
        
        graph = SimplifiedGraph(
            edges=edges,
            entry=data["graph"]["entry"],
            exit=data["graph"]["exit"],
            block_patterns=block_patterns,
            block_ranges=block_ranges
        )
        
        variables = [
            ProtectionVariable(
                name=var["name"],
                scope=var["scope"],
                init=var["init"],
                updates=VariableUpdate(
                    pattern=var["updates"]["pattern"],
                    blocks=var["updates"]["blocks"]
                )
            )
            for var in data["protection"]["variables"]
        ]
        
        checks = [
            CheckExpression(
                block_id=check["block_id"],
                location=CheckLocation(check["location"]),
                expression=check["expression"],
                handling=check.get("handling", "ABORT")
            )
            for check in data["protection"]["checks"]
        ]
        
        randomization = [
            RandomizationProperty(
                block_id=rand["block_id"],
                signature=rand["signature"],
                properties=rand.get("properties", []),
                state_updates=rand.get("state_updates", {})
            )
            for rand in data["protection"]["randomization"]
        ]
        
        protection = Protection(
            variables=variables,
            checks=checks,
            randomization=randomization
        )
        
        return cls(
            metadata=metadata,
            graph=graph,
            protection=protection
        )

    # Helper methods for the simplified graph
    def get_successors(self, block_id: int) -> List[Tuple[int, Optional[str]]]:
        """Get the successors of a block in the simplified graph."""
        return [(edge.target, edge.condition) 
                for edge in self.graph.edges 
                if edge.source == block_id]
    
    def get_predecessors(self, block_id: int) -> List[Tuple[int, Optional[str]]]:
        """Get the predecessors of a block in the simplified graph."""
        return [(edge.source, edge.condition) 
                for edge in self.graph.edges 
                if edge.target == block_id]
    
    def get_block_pattern(self, block_id: int) -> BlockPattern:
        """Get the pattern of a block."""
        return self.graph.block_patterns.get(block_id, BlockPattern.SEQUENCE)
    
    def get_block_range(self, block_id: int) -> List[int]:
        """Get the range of a block."""
        return self.graph.block_ranges.get(block_id, [0, 0])


class DistillationTaskType(Enum):
    """Types of distillation tasks."""
    ANALYZE_GRAPH = "analyze_graph"
    DETERMINE_PROTECTION = "determine_protection"
    APPLY_TEMPLATE = "apply_template"


@dataclass
class DistillationTask:
    """Represents a task in the distillation workflow."""
    task: DistillationTaskType
    input: Dict[str, Any]
    output: str


# Example of creating a batch processing strategy for similar blocks
def create_batch_group(pattern_type: str, block_ids: List[int], 
                       template: str, parameters: Dict[str, Any]) -> BatchGroup:
    """Create a batch group for similar blocks."""
    return BatchGroup(
        pattern=pattern_type,
        blocks=block_ids,
        template=template,
        parameters=parameters
    )


# Example of formula representation for state updates
# These could be actual implementation of formula parsing/execution
def cfe_variable_update(v_in: str, source_id: int, target_id: int) -> str:
    """Calculate the CFE variable update: V_out = V_in + Source_id - Target_id."""
    return f"{v_in} + {source_id} - {target_id}"


def racfe_signature_validation(s_prev: str, sig_k: str, intra_vals: List[str], sig_next: str) -> str:
    """Calculate the RACFE signature validation: S_k = S_{k-1} + (Sig_k + sum(IntraVal_i)) - Sig_{k+1}."""
    intra_sum = " + ".join(intra_vals) if intra_vals else "0"
    return f"{s_prev} + ({sig_k} + {intra_sum}) - {sig_next}"


# Functions to convert between the old and new representations if needed
def create_simplified_graph_from_cfg(cfg) -> SimplifiedGraph:
    """Convert a ControlFlowGraph to a SimplifiedGraph."""
    edges = []
    block_patterns = {}
    block_ranges = {}
    
    for block in cfg.blocks:
        block_patterns[block.id] = block.pattern
        block_ranges[block.id] = block.range
        
        for successor in block.successors:
            edges.append(Edge(
                source=block.id,
                target=successor.id,
                condition=successor.condition
            ))
    
    return SimplifiedGraph(
        edges=edges,
        entry=cfg.entry,
        exit=cfg.exit,
        block_patterns=block_patterns,
        block_ranges=block_ranges
    )