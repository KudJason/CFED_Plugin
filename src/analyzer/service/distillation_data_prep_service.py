"""
Service to prepare data for knowledge distillation by analyzing code against rules.
"""

import json
from typing import Dict, Any
from langchain_core.runnables import RunnableSerializable  # Use Runnable
from langchain_core.language_models.llms import LLM

# Assuming llm_service can provide a LangChain LLM instance
# from .llm_service import get_langchain_llm

from ..prompts.distillation.models import (
    GraphAnalysisOutput,
    ProtectionDeterminationOutput,
    RuleVerificationOutput,
    ComplianceReport
)
# Import the new runnable creation functions
from ..prompts.distillation.graph_analysis import create_graph_analysis_runnable
from ..prompts.distillation.protection_determination import create_protection_determination_runnable
from ..prompts.distillation.rule_verification import create_rule_verification_runnable
from ..prompts.distillation.reporting import create_reporting_runnable


class DistillationDataPrepService:
    """Orchestrates code analysis using LangChain for distillation data preparation."""

    def __init__(self, llm: LLM):
        """Initializes the service with a LangChain LLM instance."""
        if not llm:
            raise ValueError("A LangChain LLM instance is required.")
        self.llm = llm
        self._initialize_chains()

    def _initialize_chains(self):
        """Creates and stores the necessary LangChain LCEL Runnables."""
        # Use the new function names and update type hints
        self.graph_runnable: RunnableSerializable[Dict, GraphAnalysisOutput] = create_graph_analysis_runnable(self.llm)
        self.protection_runnable: RunnableSerializable[Dict, ProtectionDeterminationOutput] = create_protection_determination_runnable(self.llm)
        self.verification_runnable: RunnableSerializable[Dict, RuleVerificationOutput] = create_rule_verification_runnable(self.llm)
        self.reporting_runnable: RunnableSerializable[Dict, ComplianceReport] = create_reporting_runnable(self.llm)

    def prepare_distillation_data(self, code: str, rules_text: str) -> ComplianceReport:
        """
        Runs the full analysis pipeline on the given code against the rules.

        Args:
            code: The source code to analyze.
            rules_text: The content of the rules.md file.

        Returns:
            A ComplianceReport object containing the structured analysis.

        Raises:
            ValueError: If input code or rules_text is empty.
            Exception: If any chain execution fails.
        """
        if not code or not rules_text:
            raise ValueError("Input code and rules_text cannot be empty.")

        try:
            # Step 1: Graph Analysis
            print("Running Graph Analysis...")
            # Use the runnable attribute names
            graph_result: GraphAnalysisOutput = self.graph_runnable.invoke({"code": code})
            # Use model_dump_json() for Pydantic v2+
            graph_json = graph_result.model_dump_json() if hasattr(graph_result, 'model_dump_json') else graph_result.json()
            print("Graph Analysis Complete.")

            # Step 2: Protection Determination
            print("Running Protection Determination...")
            protection_result: ProtectionDeterminationOutput = self.protection_runnable.invoke(
                {"graph_json": graph_json}
            )
            protection_json = protection_result.model_dump_json() if hasattr(protection_result, 'model_dump_json') else protection_result.json()
            print(f"Protection Determined: {protection_result.protection_type}")

            # Step 3: Rule Verification
            print("Running Rule Verification...")
            verification_result: RuleVerificationOutput = self.verification_runnable.invoke({
                "protection_type": protection_result.protection_type,
                "code": code,
                "graph_json": graph_json,
                "rules_text": rules_text
            })
            verification_json = verification_result.model_dump_json() if hasattr(verification_result, 'model_dump_json') else verification_result.json()
            print("Rule Verification Complete.")

            # Step 4: Reporting
            print("Generating Final Report...")
            final_report: ComplianceReport = self.reporting_runnable.invoke({
                "graph_json": graph_json,
                "protection_determination_json": protection_json,
                "rule_verification_json": verification_json
            })
            print("Report Generation Complete.")

            # Ensure the nested objects are included correctly
            # The reporting runnable's output parser should handle this

            return final_report

        except Exception as e:
            print(f"Error during analysis pipeline: {e}")
            # Consider more specific error handling or logging
            raise # Re-raise the exception after logging 