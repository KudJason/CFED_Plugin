# RTL Code Analysis Prompts for Distillation

This directory contains the LangChain prompts, Pydantic models, and associated logic used for analyzing Register Transfer Level (RTL) code (Verilog/VHDL). The primary goal is to generate structured data representing different analysis steps (graph structure, protection type, rule verification), which can be used for knowledge distillation or reporting.

This module assumes the input code provided to the analysis runnables *is* valid RTL, as explicit RTL detection has been removed from the `graph_analysis.py` step for reliability.

## Key Components

*   **`models.py`**: Defines the Pydantic models (`GraphAnalysisOutput`, `ProtectionDeterminationOutput`, `RuleVerificationOutput`, `ComplianceReport`, etc.) that structure the input and output data for each analysis step. This ensures consistent data handling throughout the pipeline and defines the schema for the final distilled knowledge.
*   **`prompt_types.py`**: Defines custom container types like `DistillationPrompt`, used to package LangChain runnables along with their expected output Pydantic models. This helps organize the different stages of the analysis.
*   **`graph_analysis.py`**: Contains the LangChain prompts and parsing logic to analyze RTL code and generate a control/data flow graph representation (`GraphAnalysisOutput`). It takes RTL code as input and outputs a JSON representation of the graph.
*   **`protection_determination.py`**: Includes prompts and logic to determine the type of control flow protection (e.g., CFE, RACFE, NONE) based on the graph analysis output. It outputs a `ProtectionDeterminationOutput`.
*   **`rule_verification.py`**: Provides prompts and logic to verify the implementation of specific protection rules (defined externally, e.g., in `rules.md`) against the code, graph, and determined protection type. It outputs a `RuleVerificationOutput`.
*   **`reporting.py`**: Contains prompts and logic to synthesize the results from the previous steps (graph, protection, verification) into a final compliance summary (`ComplianceReport`).

## Workflow

The typical workflow involves chaining these components, often orchestrated by an external script or notebook:

1.  Input RTL Code -> `graph_analysis.py` -> `GraphAnalysisOutput` (JSON)
2.  `GraphAnalysisOutput` (JSON) -> `protection_determination.py` -> `ProtectionDeterminationOutput`
3.  Input RTL Code, `GraphAnalysisOutput` (JSON), `ProtectionDeterminationOutput`, Rules Text -> `rule_verification.py` -> `RuleVerificationOutput`
4.  `GraphAnalysisOutput` (JSON), `ProtectionDeterminationOutput` (JSON), `RuleVerificationOutput` (JSON) -> `reporting.py` -> `ComplianceReport`

Each step utilizes a corresponding runnable created by functions within these files (e.g., `create_graph_analysis_runnable`), which are packaged within `DistillationPrompt` objects.

## Usage

These modules are designed to be imported and used by higher-level scripts (like `src/analyzer/scripts/distillation_data_prep.py`) or notebooks (like `src/analyzer/distillation_prompts_example.ipynb`) to perform the step-by-step analysis of RTL code.

## Dependencies

This module relies heavily on:
*   `langchain-core`
*   `langchain` (and specific LLM provider packages like `langchain-deepseek`)
*   `pydantic` 