from langchain_deepseek.chat_models import ChatDeepSeek
from langchain.schema import SystemMessage, HumanMessage
import os

# Initialize DeepSeek model
def get_deepseek_chat():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

    return ChatDeepSeek(
    model="deepseek-chat",
        max_tokens=8192,
        temperature=0
    )

# Function to directly get the LangChain compatible model instance
def get_langchain_llm():
    """Returns the initialized ChatDeepSeek model instance for use with LangChain."""
    # The API key check happens within get_deepseek_chat()
    return get_deepseek_chat()

class LLMService:
    """Service for interacting with DeepSeek LLM"""
    
    def __init__(self):
        self.chat_model = get_deepseek_chat()
    
    def ask(self, question, system_prompt="You are an expert in code augmentation and transformation. Your task is to modify code according to specific augmentation types while maintaining syntactic validity."):
        """Ask the LLM a question with the given system prompt"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        response = self.chat_model(messages)
        
        try:
            return response.content
        except:
            try:
                return response.message.content
            except:
                if isinstance(response, str):
                    return response
                else:
                    return str(response)

# Simple function wrapper around the service
def ask_deepseek(question, system_prompt="You are an expert in code augmentation and transformation. Your task is to modify code according to specific augmentation types while maintaining syntactic validity."):
    """Use DeepSeek model to answer a question"""
    # Check if we're in test mode
    if os.environ.get("TESTING") == "True":
        # Use a mock response in testing
        from analyzer.service.mock_llm_service import MockLLMService
        mock_service = MockLLMService()
        return mock_service.ask(question, system_prompt)
    
    # Otherwise, use the real service
    service = LLMService()
    return service.ask(question, system_prompt)

# Test example
if __name__ == "__main__":
    question = "Please briefly introduce the history of artificial intelligence"
    answer = ask_deepseek(question)
    print(answer)