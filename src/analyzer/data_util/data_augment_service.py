from typing import List, Dict, Set, Tuple
from collections import defaultdict # Added for insertions dictionary
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

from ..model.augmented_data_model import AugmentType, AugmentedPluginFile, AugmentedDataModel
from ..model.data_model import DataModel
from ..service.llm_service import ask_deepseek
import logging
import re # Added for parsing line specifiers

# --- Pydantic Models for Structured Output ---
class CodeEditInstruction(BaseModel):
    line_specifier: str = Field(description="The 1-based line number (e.g., '6') or line range (e.g., '6-10') in the original code to modify.")
    new_content: str = Field(description="The new content to insert before the specified line/range. The specified lines/range will be deleted.")

class CodeChanges(BaseModel):
    changes: List[CodeEditInstruction] = Field(description="A list of edit instructions to apply to the code.")

# --- Helper Function to Apply Changes ---
def parse_line_specifier(specifier: str, max_lines: int) -> Tuple[int | None, int | None]:
    """Parses 'N' or 'N-M' into 1-based start and end lines, returns None if invalid."""
    specifier = specifier.strip()
    if '-' in specifier:
        parts = specifier.split('-')
        if len(parts) == 2:
            try:
                start_line = int(parts[0].strip())
                end_line = int(parts[1].strip())
                if 1 <= start_line <= end_line <= max_lines:
                    return start_line, end_line
            except ValueError:
                pass # Invalid number format
    else:
        try:
            line_num = int(specifier)
            if 1 <= line_num <= max_lines:
                return line_num, line_num # Single line is a range of 1
        except ValueError:
            pass # Invalid number format
    logging.warning(f"Invalid line specifier: '{specifier}'. Max lines: {max_lines}")
    return None, None

def apply_code_changes(original_code: str, code_changes: CodeChanges) -> str:
    """Applies the specified edit instructions (insertions/deletions) to the original code string."""
    lines = original_code.splitlines()
    max_lines = len(lines)
    
    insertions = defaultdict(list) # Key: 0-based index to insert *before*
    deletions = set()              # Set of 0-based indices to delete
    
    # Sort changes by start line number for potentially more predictable (though still complex) application
    # We need to parse first to sort correctly
    parsed_instructions = []
    for change in code_changes.changes:
        start_line, end_line = parse_line_specifier(change.line_specifier, max_lines)
        if start_line is not None and end_line is not None:
            parsed_instructions.append({
                "start_line": start_line,
                "end_line": end_line,
                "content": change.new_content
            })
        else:
             logging.warning(f"Skipping invalid change instruction: {change}")
             
    # Sort by start line
    parsed_instructions.sort(key=lambda x: x["start_line"])

    # Populate insertions and deletions based on sorted instructions
    for instruction in parsed_instructions:
        start_idx = instruction["start_line"] - 1
        end_idx = instruction["end_line"] - 1
        
        insertions[start_idx].append(instruction["content"])
        for i in range(start_idx, end_idx + 1):
             # Check again just in case (should be valid if parsed correctly)
             if 0 <= i < max_lines:
                 deletions.add(i)
             else: 
                 # This case should ideally not happen due to parse_line_specifier checks
                 logging.error(f"Internal inconsistency: Invalid index {i} during deletion marking.")
                 
    # Build the new code string
    new_lines = []
    for i, line in enumerate(lines):
        # Apply insertions before the current line
        if i in insertions:
            new_lines.extend(insertions[i])
            
        # Add the original line only if it's not marked for deletion
        if i not in deletions:
            new_lines.append(line)
            
    # Check if any insertions were meant for *after* the last line (unlikely use case for now)
    # if max_lines in insertions:
    #    new_lines.extend(insertions[max_lines])

    if not insertions and not deletions:
         logging.warning("LLM provided changes, but none were valid or applicable. Returning original code.")
         return original_code
         
    return "\n".join(new_lines)

# --- Service Class ---
class DataAugmentService:
    def __init__(self):
        self.system_prompt = """You are an expert in code analysis and modification. 
        Your task is to modify code according to specific augmentation strategies using the provided format.
        You MUST specify the exact line or line range to be replaced and provide the new content to insert before that line/range."""
        # Initialize the output parser with the updated Pydantic model
        self.parser = PydanticOutputParser(pydantic_object=CodeChanges)
    
    def _get_augment_prompt(self, code: str, augment_type: AugmentType) -> str:
        """Constructs the prompt for the LLM, including format instructions."""
        lines_with_numbers = []
        for i, line in enumerate(code.splitlines(), 1):
            lines_with_numbers.append(f"{i}: {line}")
        numbered_code = "\n".join(lines_with_numbers)
        
        format_instructions = self.parser.get_format_instructions()
        
        # Add examples to the prompt for clarity
        prompt_template = f"""Please modify the following code (shown with line numbers) according to this augmentation strategy: {augment_type.value}

{format_instructions}

Example for single line deletion and insertion before:
```json
{{
  "changes": [
    {{
      "line_specifier": "5",
      "new_content": "// New comment or code to insert before line 5"
    }}
  ]
}}
```

Example for multi-line range deletion and insertion before:
```json
{{
  "changes": [
    {{
      "line_specifier": "10-15",
      "new_content": "insertedFunctionCall(); // Replaces lines 10-15"
    }}
  ]
}}
```

Original code:
```
{numbered_code}
```
"""
        return prompt_template
    
    def augment_code(self, code: str, augment_type: AugmentType) -> str | None:
        """Augments code using LLM with structured output parsing and application."""
        prompt = self._get_augment_prompt(code, augment_type)
        llm_response = None # Initialize for error logging
        try:
            logging.debug(f"""Sending prompt to LLM for type {augment_type.value}:
{prompt[:1000]}...""") # Log more of the prompt
            llm_response = ask_deepseek(prompt, self.system_prompt)
            if not llm_response:
                logging.error("LLM returned empty response.")
                return None 
                
            logging.debug(f"LLM Response received: {llm_response}")
            
            parsed_changes: CodeChanges = self.parser.parse(llm_response)
            logging.debug(f"Parsed changes: {parsed_changes}")
            
            modified_code = apply_code_changes(code, parsed_changes)
            return modified_code
            
        except OutputParserException as e:
            # Log the specific parsing error and the raw response
            logging.error(f"Failed to parse LLM output. Error: {e}. Raw response: ```{llm_response}```")
            return None 
        except Exception as e:
            logging.error(f"An unexpected error occurred during augmentation: {e}", exc_info=True)
            return None 
    
    def create_augmented_data_model(self, data_model: DataModel, augment_types: List[AugmentType]) -> AugmentedDataModel:
        """Create an augmented version of the data model with modified code according to specified augmentation types"""
        augmented_files = []
        
        for file_path, plugin_file in data_model.plugin_files.items():
            for augment_type in augment_types:
                augmented_content = self.augment_code(plugin_file.content, augment_type)
                if augmented_content is not None:
                    # ---> START Indented Block <---
                    augmented_file = AugmentedPluginFile(
                        content=augmented_content,
                        function_name=plugin_file.function_name,
                        doc_name=plugin_file.doc_name,
                        augment_type=augment_type
                    )
                    augmented_files.append(augmented_file)
                    # ---> END Indented Block <---
                else:
                    # ---> START Indented Block <---
                    logging.warning(f"Skipping augmentation for {file_path} with type {augment_type.value} due to error.")
                            # ---> END Indented Block <---

        return AugmentedDataModel.from_data_model(data_model, augmented_files)