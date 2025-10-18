import os
from typing import Dict, Any, Tuple
import requests
import json
import config

def perplexity_search(query: str, max_results: int = 5, max_tokens_per_page: int = 512) -> Tuple[str, int]:
    """
    Perform a web search using the Perplexity API.
    
    Args:
        query: The search query string.
        max_results: Maximum number of search results to return (1-20).
        max_tokens_per_page: Maximum tokens to retrieve per page (256-2048).
                            Higher values provide more comprehensive content but increase 
                            processing time and latency. Lower values are faster but may 
                            have less detailed results.
        
    Returns:
        A formatted string containing the search results.
        
    Raises:
        ValueError: If parameters are invalid.
        Exception: If the API request fails.
    """
    # Validate parameters
    if not 1 <= max_results <= 20:
        raise ValueError("max_results must be between 1 and 20")
    
    if not 256 <= max_tokens_per_page <= 2048:
        raise ValueError("max_tokens_per_page must be between 256 and 2048")
    
    # Get API key from environment
    api_key = config.perplexity_api_key
    if not api_key:
        raise ValueError(
            "PERPLEXITY_API_KEY environment variable is not set. "
            "Please set it before using the search tool."
        )
    
    base_url = "https://api.perplexity.ai/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare the request payload
    payload = {
        "query": query,
        "max_results": max_results,
        "max_tokens_per_page": max_tokens_per_page
    }
    
    try:
        # Make the API request
        response = requests.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        
        # Process and return the results
        results = response.json()
        
        # Calculate approximate tokens used (query + results)
        # Rough estimate: 1 token ≈ 4 characters
        tokens_used = len(query) // 4 + max_results * max_tokens_per_page
        
        return _format_results(results)
        
    except requests.exceptions.RequestException as e:
        # Handle API errors
        error_msg = f"Error performing search: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg += f" (Status: {e.response.status_code}, Detail: {error_detail})"
            except:
                error_msg += f" (Status: {e.response.status_code}, Response: {e.response.text[:200]})"
        raise Exception(error_msg)


def _format_results(api_response: Dict[str, Any]) -> str:
    """
    Format the raw API response into a readable string.
    
    Args:
        api_response: The raw response from the Perplexity API.
        
    Returns:
        A formatted string containing the search results.
    """
    if not api_response or "results" not in api_response:
        return "No results found."
    
    results = api_response.get("results", [])
    
    if not results:
        return "No results found."
    
    formatted_output = f"Found {len(results)} search results:\n\n"
    
    for i, result in enumerate(results, 1):
        title = result.get("title", "No title")
        url = result.get("url", "No URL")
        content = result.get("content", "")
        snippet = result.get("snippet", "")
        
        formatted_output += f"Result {i}:\n"
        formatted_output += f"Title: {title}\n"
        formatted_output += f"URL: {url}\n"
        
        # Use snippet if content is empty
        text = content if content else snippet
        if text:
            # Truncate if too long
            if len(text) > 1024:
                text = text[:1024] + "..."
            formatted_output += f"Content: {text}\n"
        
        formatted_output += "\n" + "-" * 80 + "\n\n"
    
    return formatted_output


# Example usage
if __name__ == "__main__":
    # Perform a search
    try:
        results = perplexity_search(
            query="latest developments in AI",
            max_results=3,
            max_tokens_per_page=1024
        )
        print(results)
            
    except Exception as e:
        print(f"Error: {str(e)}")
