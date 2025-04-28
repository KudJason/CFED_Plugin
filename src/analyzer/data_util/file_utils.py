"""Utility functions for file operations."""

def load_rules(filepath: str) -> str:
    """Loads the content of the rules file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Rules file not found at {filepath}")
        # Depending on requirements, might want to raise an exception
        # raise FileNotFoundError(f"Rules file not found: {filepath}")
        return "" # Or return empty string/None
    except Exception as e:
        print(f"Error reading rules file {filepath}: {e}")
        # raise e
        return "" 