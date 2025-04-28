"""LangChain components for Graph Analysis."""

from typing import Dict  # Added typing hint
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.runnables import RunnableSerializable, RunnableLambda
from langchain_core.language_models import BaseLanguageModel

from .models import GraphAnalysisOutput, GraphNode, GraphEdge
from .prompt_types import DistillationPrompt

# 1. Define the Prompt Template
_graph_analysis_prompt_template = """
Analyze the following code to extract its control flow structure using a simplified edge-based representation.

Code:
```
{code}
```

Focus on:
1. Identifying all basic blocks and their line ranges (as strings mapped to lists of ints: "<block_id>": [start_line, end_line])
2. Determining edges between blocks (source -> target, including condition if any)
3. Classifying each block as SEQUENCE, BRANCH, or LOOP (as strings mapped to strings: "<block_id>": "PATTERN")
4. Identifying the entry point (as int) and exit points (as list of ints)

{format_instructions}
"""

# 2. Create the Output Parser
_graph_analysis_parser = PydanticOutputParser(pydantic_object=GraphAnalysisOutput)

# 3. Create the Prompt
prompt = PromptTemplate(
    template=_graph_analysis_prompt_template,
    input_variables=["code"],
    partial_variables={"format_instructions": _graph_analysis_parser.get_format_instructions()}
)

# 4. Function to create the chain (now an LCEL Runnable)
def create_graph_analysis_runnable(llm: BaseLanguageModel) -> RunnableSerializable[Dict, GraphAnalysisOutput]: # Updated type hint
    """Creates the LangChain LCEL Runnable for graph analysis."""
    return prompt | llm | _graph_analysis_parser 

# --- System Prompt Template ---
# Updated prompt to ONLY ask for JSON graph, assuming input is RTL.
SYSTEM_PROMPT_TEMPLATE = """
You are an expert in analyzing hardware description languages (HDLs), specifically Verilog and VHDL.
Your task is to analyze the provided RTL code snippet and generate a simplified control/data flow graph in JSON format, focusing on key operations relevant to control flow protection schemes.

**Instructions:**

1.  **Graph Generation:** Provide **ONLY** a JSON object representing the graph with the following structure:
    `{{"nodes": [{{ "id": "...", "type": "...", "label": "...", "properties": {{...}} }}], "edges": [{{ "source": "...", "target": "...", "type": "...", "label": "..." }}], "summary": "..."}}`
    Ensure the output is **strictly** valid JSON.
    
    *   **Nodes:** Identify key elements:
        *   Signals/Variables/Registers involved in control flow or critical operations.
        *   Assignment operations.
        *   Conditional statements (if, case).
        *   Processes/Always blocks.
        *   Basic blocks or sequences of operations.
        *   Assign unique `id` and descriptive `type` and `label`.
    *   **Edges:** Represent relationships:
        *   Data flow (e.g., `reads`, `writes`).
        *   Control flow (e.g., `controls`, `next`).
        *   Assign `source` and `target` node IDs and a relationship `type`.
    *   **Summary:** Provide a brief textual summary of the graph.

Focus on clarity and relevance to control flow. Omit minor details not pertinent to understanding the core logic flow and dependencies.
"""

HUMAN_PROMPT_TEMPLATE = "Analyze the following code:\n\n```hdl\n{code}\n```"

# --- Output Processing Function ---
def _process_graph_output(output: str) -> GraphAnalysisOutput:
    """Processes the LLM output, attempting to extract and parse a JSON block.
       Returns a default 'error' object on failure, but still sets is_rtl=True.
    """
    logger.debug(f"Raw LLM Output for Graph Analysis:\n{output}") # Log raw output for debugging
    output = output.strip()
    if not output:
        logger.error(f"LLM output was empty.")
        return GraphAnalysisOutput(is_rtl=True, analysis_skipped_reason="LLM output was empty.", nodes=[], edges=[], summary="Error: LLM returned empty output.")
        
    # Attempt to extract JSON block (handles ```json ... ``` markdown)
    json_str = output
    if json_str.startswith("```json"):
        json_str = json_str[7:] # Remove ```json
        if json_str.endswith("```"):
            json_str = json_str[:-3] # Remove trailing ```
        json_str = json_str.strip()
    elif json_str.startswith("{") and json_str.endswith("}"):
        # Assume it's just the JSON object
        pass
    else:
        # Fallback: try to find the first '{' and last '}'
        start_index = json_str.find('{')
        end_index = json_str.rfind('}')
        if start_index != -1 and end_index != -1 and start_index < end_index:
            json_str = json_str[start_index:end_index+1]
        else:
            # Could not find a JSON structure
            logger.error(f"Could not extract JSON block from LLM output.\nOutput:\n{output}")
            return GraphAnalysisOutput(
                is_rtl=True,
                analysis_skipped_reason="Could not extract JSON block from LLM output.",
                nodes=[],
                edges=[],
                summary="Error: Could not extract JSON block from LLM output."
            )

    graph_data = None
    try:
        logger.debug(f"Attempting to parse JSON:\n{json_str}")
        graph_data = json.loads(json_str) # Parse the extracted string
        # Validate and create the Pydantic model, explicitly set is_rtl=True
        return GraphAnalysisOutput(**graph_data, is_rtl=True) 
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode extracted JSON from LLM output: {e}\nExtracted JSON String:\n{json_str}\nOriginal Output:\n{output}")
        return GraphAnalysisOutput(
            is_rtl=True, # Assume it was meant to be RTL even if JSON is bad
            analysis_skipped_reason=f"Failed to parse LLM JSON output: {e}",
            nodes=[],
            edges=[],
            summary="Error: Could not parse the analysis result from the LLM."
        )
    except ValidationError as e:
        # graph_data might be defined or not depending on when validation error occurs
        log_data = graph_data if graph_data is not None else output
        logger.error(f"Failed to validate Pydantic model from LLM JSON: {e}\nData:\n{log_data}")
        return GraphAnalysisOutput(
            is_rtl=True, # Assume it was meant to be RTL if validation fails
            analysis_skipped_reason=f"LLM output failed validation: {e}",
            nodes=[],
            edges=[],
            summary="Error: LLM output did not match the expected format."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred processing graph output: {e}\nOutput:\n{output}")
        # Generic fallback
        return GraphAnalysisOutput(
            is_rtl=True, # Assume it was meant to be RTL
            analysis_skipped_reason=f"Unexpected error during output processing: {e}",
            nodes=[],
            edges=[],
            summary="Error: An unexpected error occurred while processing the LLM response."
        )

# --- Runnable Creation ---
def create_graph_analysis_runnable(llm: BaseLanguageModel) -> DistillationPrompt:
    """Creates the LangChain runnable for the graph analysis step.

    Args:
        llm: The language model instance to use.

    Returns:
        A DistillationPrompt object containing the runnable chain.
    """
    system_prompt = SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT_TEMPLATE)
    human_prompt = HumanMessagePromptTemplate.from_template(HUMAN_PROMPT_TEMPLATE)
    chat_prompt = ChatPromptTemplate.from_messages([system_prompt, human_prompt])

    # Chain definition
    chain = (
        chat_prompt
        | llm
        | StrOutputParser() 
        | RunnableLambda(_process_graph_output) # Use the updated parser
    )

    return DistillationPrompt(runnable=chain, output_model=GraphAnalysisOutput)

# --- Logging Setup ---
# It's better practice to configure logging in the main script
# but we add a basic logger here for potential standalone use/testing
import logging
import json
from pydantic import ValidationError
from langchain_core.language_models import BaseLanguageModel

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO) # Adjust level as needed 