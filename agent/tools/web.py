"""
Web-related tool implementations.

Provides tools for performing live internet searches using a search
API endpoint and for fetching raw content from a URL. These tools
retrieve data using the `requests` library and return text to the
agent.
"""

import os
from typing import Any, Dict, List

import requests

from agent.tools.base import Tool


class WebSearchTool(Tool):
    """
    Perform live internet searches using a configurable search API.

    The search API should accept query parameters such as `q` and
    optionally `num_results`. API authentication can be provided
    via an environment variable.

    Tool input schema:
    {
        "query": "search query string",
        "num_results": 5
    }
    """

    def __init__(self, endpoint: str) -> None:
        super().__init__(
            name="web_search",
            description=(
                "Perform a live web search. Input: {\"query\": str, \"num_results\": int}. "
                "Returns a concise text summary of the top results."
            ),
        )
        self.endpoint = endpoint

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "WebSearchTool":
        endpoint = cfg.get("endpoint") or os.getenv("SEARCH_API_ENDPOINT", "")
        if not endpoint:
            raise RuntimeError(
                "WebSearchTool requires SEARCH_API_ENDPOINT env var or tools.web_search.endpoint in config."
            )
        return cls(endpoint=endpoint)

    def run(self, tool_input: Dict[str, Any]) -> str:
        query = tool_input.get("query", "")
        num_results = int(tool_input.get("num_results", 5))
        if not query:
            return "WebSearchTool: 'query' is required."
        headers: Dict[str, str] = {}
        api_key = os.getenv("SEARCH_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "q": query,
            "num_results": num_results,
        }
        try:
            resp = requests.get(
                self.endpoint,
                params=payload,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return f"WebSearchTool encountered an error while calling the search API: {exc}"
        try:
            data = resp.json()
        except Exception:
            return resp.text[:4000]
        results = data.get("results") or data.get("data") or []
        lines: List[str] = [f"Search results for: {query}"]
        for idx, r in enumerate(results[:num_results], start=1):
            title = r.get("title") or r.get("name") or "Untitled"
            snippet = r.get("snippet") or r.get("description") or ""
            url = r.get("url") or r.get("link") or ""
            lines.append(f"{idx}. {title}")
            if snippet:
                lines.append(f"   {snippet}")
            if url:
                lines.append(f"   URL: {url}")
        return "\n".join(lines)


class WebFetchTool(Tool):
    """
    Fetch raw web content from a given URL using HTTP GET.

    Tool input schema:
    {
        "url": "https://example.com",
        "max_chars": 4000
    }
    """

    def __init__(self) -> None:
        super().__init__(
            name="web_fetch",
            description=(
                "Fetch raw web content from a URL. Input: {\"url\": str, \"max_chars\": int}. "
                "Returns the first N characters of the response."
            ),
        )

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "WebFetchTool":
        # This tool has no specific configuration; return a new instance
        return cls()

    def run(self, tool_input: Dict[str, Any]) -> str:
        url = tool_input.get("url", "")
        max_chars = int(tool_input.get("max_chars", 4000))
        if not url:
            return "WebFetchTool: 'url' is required."
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return f"WebFetchTool encountered an error while fetching URL: {exc}"
        text = resp.text
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]..."
        return text