"""LangChain components for Protection Determination."""

from typing import Dict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableSerializable
from langchain_core.language_models.llms import LLM

# Ensure relative import works
from .models import ProtectionDeterminationOutput

# 1. Define the Prompt Template
_protection_determination_prompt_template = """
Based on the following control flow graph structure (JSON format), determine if any protection mechanism (CFE, RACFE, or both) is present.

Graph JSON:
```json
{graph_json}
```

Provide indicators based ONLY on the graph structure provided:
1. For CFE: Look for complex branching patterns, potential state update/check structures implied by sequences/branches.
2. For RACFE: Look for patterns suggesting randomization or signature validation, often involving sequential checks or updates.

Return the determination including the type, indicators found, and your confidence (0.0 to 1.0).

{format_instructions}
"""

# 2. Create the Output Parser
_protection_determination_parser = PydanticOutputParser(pydantic_object=ProtectionDeterminationOutput)

# 3. Create the Prompt
prompt = PromptTemplate(
    template=_protection_determination_prompt_template,
    input_variables=["graph_json"],
    partial_variables={"format_instructions": _protection_determination_parser.get_format_instructions()}
)

# 4. Function to create the chain (now an LCEL Runnable)
def create_protection_determination_runnable(llm: LLM) -> RunnableSerializable[Dict, ProtectionDeterminationOutput]:
    """Creates the LangChain LCEL Runnable for protection determination."""
    return prompt | llm | _protection_determination_parser 