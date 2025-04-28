"""LangChain components for Rule Verification against rules.md."""

from typing import Dict
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableSerializable
from langchain_core.language_models.llms import LLM

# Ensure relative import works
from .models import RuleVerificationOutput

# 1. Define the Prompt Template
_rule_verification_prompt_template = """
Analyze the provided code and its control flow graph (CFG) to verify the implementation of the specified control flow protection rules.

Protection Type Determined: {protection_type} # CFE, RACFE, BOTH, or NONE

Code:
```
{code}
```

Graph JSON:
```json
{graph_json}
```

Verification Rules (from rules.md):
```
{rules_text}
```

Task:
Based *only* on the {protection_type} rules provided above, perform the following verification steps:

1.  **Variable Verification:**
    *   Identify the primary state variable(s) (e.g., 'Var' for CFE, 'S' for RACFE).
    *   For each variable, check its initialization against the corresponding rule (`#initial_value` range for CFE, `#initVal` formula for RACFE). Report `rule_id` (e.g., "CFE.Var.Init"), `variable_name`, `check_type`="Initialization", `is_met`, `evidence`, `deviation_description`, `scope`.
    *   For representative blocks (entry, typical sequence, conditional branch), check variable updates against the `BEGIN` and `END` rules (e.g., `Var += #random_val`, `Var -= #update_val_true`, `S -= #SubRanPrevVal`, `S += #AdjustVal_True`). Report `rule_id` (e.g., "RACFE.S.Update.EndTrue"), `variable_name`, `check_type`="Update", `is_met`, `evidence`, `deviation_description`.
    *   For RACFE, check `#Sig` properties (uniqueness, randomness if possible from context) and `#SubRanPrevVal` randomness. Report `rule_id` (e.g., "RACFE.Sig.Unique"), `variable_name`="Sig", `check_type`="Property", `is_met`, `evidence`, `deviation_description`.

2.  **Instruction Pattern Verification:**
    *   Identify code sections corresponding to the `SETUP`, `BEGIN`, `MIDDLE`, `END`, and `INTRA` instruction patterns defined for {protection_type} in the rules.
    *   Map these patterns to block IDs or line ranges in the code.
    *   For each pattern (`pattern_name`), report `is_present`, `found_instructions`, `missing_instructions`, `extra_instructions`, and `evidence_locations`.

Provide the results strictly in the following JSON format:

{format_instructions}
"""

# 2. Create the Output Parser
_rule_verification_parser = PydanticOutputParser(pydantic_object=RuleVerificationOutput)

# 3. Create the Prompt
prompt = PromptTemplate(
    template=_rule_verification_prompt_template,
    input_variables=["protection_type", "code", "graph_json", "rules_text"],
    partial_variables={"format_instructions": _rule_verification_parser.get_format_instructions()}
)

# 4. Function to create the chain (now an LCEL Runnable)
def create_rule_verification_runnable(llm: LLM) -> RunnableSerializable[Dict, RuleVerificationOutput]:
    """Creates the LangChain LCEL Runnable for rule verification."""
    return prompt | llm | _rule_verification_parser 