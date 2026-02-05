import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables from .env file
load_dotenv()

def get_llm():
    """
    Returns a configured ChatGroq instance.
    We use temperature=0 because SQL generation needs to be precise, not creative.
    
    Model: llama-3.3-70b-versatile
    - 70B parameters for strong reasoning capability
    - 280 tokens/sec (fast inference)
    - 131K context window
    - Production-grade (stable, won't be deprecated)
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")

    return ChatGroq(
        model="llama-3.3-70b-versatile",  # Latest production Llama 3.3 model
        temperature=0,
        api_key=api_key
    )