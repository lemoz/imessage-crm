"""OpenAI configuration and client setup."""
import os
from typing import Optional

from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OpenAIConfig:
    """Configuration for OpenAI client."""
    
    DEFAULT_MODEL = "gpt-4"
    DEFAULT_TEMPERATURE = 0.7
    MAX_RETRIES = 3
    TIMEOUT = 30.0
    
    @staticmethod
    def get_client(api_key: Optional[str] = None) -> OpenAI:
        """
        Get OpenAI client instance.
        
        Args:
            api_key: Optional API key. If not provided, will try to get from environment.
            
        Returns:
            OpenAI client instance
        
        Raises:
            ValueError: If no API key is found
        """
        # Try environment first, then fallback to provided key
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            
        return OpenAI(
            api_key=api_key,
            timeout=OpenAIConfig.TIMEOUT,
            max_retries=OpenAIConfig.MAX_RETRIES
        )
