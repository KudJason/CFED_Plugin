"""LangChain components for generating the final Compliance Report."""

from typing import Dict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableSerializable
from langchain_core.language_models.llms import LLM

# Ensure relative import works
from .models import ComplianceReport

# 1. Define the Prompt Template
_reporting_prompt_template = """
Synthesize the provided analysis results into a final compliance report regarding the implementation of control flow protection rules.

Analysis Inputs:

Graph Analysis (JSON):
```json
{graph_json}
```

Protection Determination (JSON):
```json
{protection_determination_json}
```

Rule Verification Results (JSON):
```json
{rule_verification_json}
```

Task:
Generate a final compliance report that includes:
1.  `overall_compliance`: Assess if the rules are met ("FULL", "PARTIAL", "NONE") based on the verification results.
2.  `protection_type_detected`: The type determined in the earlier step.
3.  `summary`: A brief textual summary of the key findings, highlighting major compliance points or deviations.
4.  `rule_verification_results`: The detailed verification results provided as input.
5.  `graph_analysis`: The graph analysis provided as input.

Provide the report strictly in the following JSON format:

{format_instructions}
"""

# 2. Create the Output Parser
_reporting_parser = PydanticOutputParser(pydantic_object=ComplianceReport)

# 3. Create the Prompt
prompt = PromptTemplate(
    template=_reporting_prompt_template,
    input_variables=["graph_json", "protection_determination_json", "rule_verification_json"],
    partial_variables={"format_instructions": _reporting_parser.get_format_instructions()}
)

# 4. Function to create the chain (now an LCEL Runnable)
def create_reporting_runnable(llm: LLM) -> RunnableSerializable[Dict, ComplianceReport]:
    """Creates the LangChain LCEL Runnable for generating the compliance report."""
    return prompt | llm | _reporting_parser 