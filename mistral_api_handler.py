import requests
import time
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MistralAPIHandler:
    """Enhanced Mistral API handler with robust error handling, retry logic, and fallback analysis."""

    BASE_URL = "https://api.mistral.ai/v1/chat/completions"

    def __init__(self, api_key: str):
        """Initialize the API handler with authentication and settings."""
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })

        # Configuration settings
        self.timeout = 90
        self.max_retries = 3
        self.base_wait_time = 5
        self.max_tokens_limit = 4096

        # Keywords for fallback analysis
        self.KEYWORDS = {
            "urban_planning": [
                "city development", "zoning", "infrastructure", "urban design",
                "land use", "planning policy", "sustainable development"
            ],
            "transportation": [
                "public transit", "traffic management", "sustainable mobility",
                "transport infrastructure", "pedestrian", "cycling"
            ],
            "geography": [
                "spatial analysis", "land use", "environmental factors",
                "geographic information", "mapping", "spatial planning"
            ],
            "technical": [
                "methodology", "analysis", "data", "research",
                "survey", "statistics", "assessment"
            ],
            "policy": [
                "regulation", "policy", "guidelines", "standards",
                "requirements", "legislation", "compliance"
            ]
        }

    def run_command(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.1, model: str = "mistral-medium-latest") -> str:
        """
        Execute a command through the Mistral API with improved formatting.

        UPDATED: Using mistral-medium-latest for comprehensive document analysis.
        The fine-tuned model was trained only on Q&A, writing style, analytical frameworks,
        and comparison analyses, so base model provides better results for full document processing.
        """
        # Add formatting instructions to the prompt
        formatted_prompt = f"""
        Please provide your response in the following format, without using markdown symbols or hashtags:

        For main sections:
        Title
        ===========

        For subsections:
        Subsection: Your text here

        For example:
        Key Points
        ===========

        Diverse Sources: The document includes a wide range of sources...

        Geographical Scope: The references span multiple regions...

        Your response:
        {prompt}
        """

        if not self.api_key:
            return "Error: API key not configured"

        if not prompt or not isinstance(prompt, str):
            return "Error: Invalid prompt"

        # Ensure max_tokens is within limits
        max_tokens = min(max_tokens, self.max_tokens_limit)

        # Prepare request data
        data = {
            "model": model,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        # Retry loop
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Sending request to Mistral API - Attempt {attempt + 1}/{self.max_retries}")

                # Make the API call
                response = self.session.post(
                    self.BASE_URL,
                    json=data,
                    timeout=self.timeout
                )

                # Handle different response scenarios
                if response.status_code == 200:
                    content = response.json()['choices'][0]['message']['content'].strip()
                    logger.info("Successfully received response")
                    return content

                elif response.status_code == 429:
                    # Rate limit hit - wait longer before retry
                    wait_time = self.base_wait_time * (attempt + 1) * 2
                    logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                elif response.status_code == 401:
                    logger.error("Authentication failed - invalid API key")
                    return "Error: Invalid API key or authentication failed"

                elif response.status_code >= 500:
                    wait_time = self.base_wait_time * (attempt + 1)
                    logger.warning(f"Server error {response.status_code}. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                else:
                    error_detail = self.extract_error_detail(response)
                    return f"Error: API request failed - {error_detail}"

            except requests.exceptions.Timeout:
                wait_time = self.base_wait_time * (attempt + 1)
                logger.warning(f"Request timed out. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                if attempt == self.max_retries - 1:
                    return "Error: All requests timed out. Please try again later."

            except requests.exceptions.ConnectionError:
                wait_time = self.base_wait_time * (attempt + 1)
                logger.warning(f"Connection error. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                if attempt == self.max_retries - 1:
                    return "Error: Unable to connect to Mistral API. Please check your internet connection."

            except json.JSONDecodeError:
                logger.error("Failed to parse API response")
                return "Error: Invalid response from API"

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                return f"Error: {str(e)}"

        return "Error: Maximum retry attempts reached. Please try again later."

    def fallback_analysis(self, content: str) -> str:
        """
        Perform fallback analysis when API is unavailable.

        Args:
            content (str): The text content to analyze

        Returns:
            str: Basic keyword-based analysis
        """
        logger.info("Performing fallback analysis")
        content = content.lower()
        analysis_results = []

        # Check each category
        for category, keywords in self.KEYWORDS.items():
            matches = [keyword for keyword in keywords if keyword in content]
            if matches or category in content:
                relevance = len(matches) / len(keywords) if matches else 0.1
                analysis_results.append((category, matches, relevance))

        # Generate response
        if not analysis_results:
            return "Unable to determine specific categories for this document."

        # Sort by relevance
        analysis_results.sort(key=lambda x: x[2], reverse=True)

        # Format response
        response = ["Document Analysis (Fallback):"]
        for category, matches, relevance in analysis_results:
            category_name = category.replace('_', ' ').title()
            response.append(f"\n{category_name} (Relevance: {relevance:.1%})")
            if matches:
                response.append(f"Found concepts: {', '.join(matches)}")

        response.append("\nNote: This is a basic keyword-based analysis due to API unavailability.")
        return '\n'.join(response)

    def validate_connection(self) -> bool:
        """Test the API connection with a simple request."""
        test_prompt = "Test connection"
        response = self.run_command(test_prompt, max_tokens=10)
        return not response.startswith("Error:")

    def extract_error_detail(self, response) -> str:
        """Extract detailed error information from API response."""
        try:
            error_data = response.json()
            if 'error' in error_data:
                return error_data['error'].get('message', str(error_data['error']))
            return str(error_data)
        except Exception:
            return f"Status code: {response.status_code}"

    def get_token_count(self, text: str) -> int:
        """Estimate token count for input text."""
        # Rough approximation: ~4 characters per token
        return len(text) // 4

    def close(self) -> None:
        """Clean up resources by closing the session."""
        try:
            self.session.close()
            logger.info("API session closed successfully")
        except Exception as e:
            logger.error(f"Error closing session: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

# Utility function to help with model migration
def get_updated_model_name(deprecated_model: str) -> str:
    """
    Map deprecated model names to their recommended replacements.

    Args:
        deprecated_model (str): The deprecated model name

    Returns:
        str: The recommended replacement model name
    """
    model_mapping = {
        "mistral-medium-2312": "mistral-medium-latest",
        "codestral-2405": "codestral-latest",
        "mistral-large-2402": "mistral-medium-latest",
        "mistral-small-2402": "mistral-small-latest"
    }

    return model_mapping.get(deprecated_model, deprecated_model)

if __name__ == "__main__":
    # Example usage with updated model
    API_KEY = "your-api-key"

    with MistralAPIHandler(API_KEY) as handler:
        if handler.validate_connection():
            # You can now use different models based on your needs
            response = handler.run_command("Hello, how are you?", model="mistral-medium-latest")
            print(f"Response: {response}")

            # For coding tasks, you might want to use codestral
            # response = handler.run_command("Write a Python function to sort a list", model="codestral-latest")

        else:
            print("Failed to connect to Mistral API")
