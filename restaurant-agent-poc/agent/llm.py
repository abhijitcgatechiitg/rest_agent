import os
from langchain_anthropic import ChatAnthropic

def get_claude(temperature: float = 0.2):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    return ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=temperature)
