"""
System prompt loader for NESD-QA assistant.
Loads and manages the domain-specific instruction set.
"""

import os
from pathlib import Path


def load_system_prompt():
    """
    Load the NESD-QA system prompt from file.
    Returns the full system prompt as a string.
    """
    prompt_path = Path(__file__).parent.parent / "SYSTEM_PROMPT_NESD_QA.md"
    
    if not prompt_path.exists():
        # Fallback prompt if file not found
        return get_default_system_prompt()
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading system prompt: {e}")
        return get_default_system_prompt()


def get_default_system_prompt():
    """
    Default system prompt if external file is not available.
    """
    return """You are an expert NESD-QA Gherkin scripting assistant specializing in telecom test automation.

Your role is to help Test Analysts and Test Automators write accurate, syntactically correct Gherkin scripts for the NESD-QA platform. 

Key responsibilities:
1. Provide exact Gherkin syntax matching NESD-QA framework conventions
2. Understand telecom terminology (MSISDN, CCS, Fusion, bundles, offering codes)
3. Explain the reasoning behind each step and parameter
4. Include all required parameters, payment types, and unit codes
5. Recommend proper test structure and reusable patterns

When answering:
- Ask clarifying questions if the request is ambiguous
- Provide complete, syntactically correct examples with Given/When/Then structure
- Highlight common mistakes and best practices
- Validate step syntax against NESD-QA framework
- Explain how steps relate to system behavior (CCS, Fusion, etc.)

Always reference accurate Gherkin formatting and include proper parameter names and values."""


def get_system_prompt_for_model(model_id="claude"):
    """
    Get system prompt formatted for specific model.
    Some models may need different formatting.
    """
    prompt = load_system_prompt()
    
    # Claude can handle the full markdown prompt directly
    if "claude" in model_id.lower():
        return prompt
    
    # For other models, convert markdown to plain text
    # Remove markdown formatting like # and **
    plain_prompt = prompt.replace("# ", "").replace("## ", "")
    plain_prompt = plain_prompt.replace("**", "").replace("```", "")
    
    return plain_prompt


# Quick test
if __name__ == "__main__":
    prompt = load_system_prompt()
    print(f"System prompt loaded successfully ({len(prompt)} characters)")
    print("\nFirst 500 characters:")
    print(prompt[:500])
