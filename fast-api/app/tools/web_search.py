"""Web search tool backed by the Tavily API."""
import json

import httpx

from tavily import TavilyClient

from app.core.config import settings


tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

async def web_search(query: str) -> str:
    """Search the web for current information using the Tavily API."""
    response = tavily_client.search(query=query)
    results = response.get("results", [])[:3]
    return json.dumps([
        {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")[:200]}
        for r in results
    ])


WEB_SEARCH_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
}
