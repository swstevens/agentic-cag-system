"""
Analyzer implementations following Strategy Pattern.

Analyzers provide different strategies for deck analysis:
- LLMDeckAnalyzer: Uses LLM (DeckAnalyzerAgent) for context-aware analysis
- LegacyDeckAnalyzer: Uses rule-based logic (deprecated, for backward compatibility)
"""

from .llm_analyzer import LLMDeckAnalyzer

__all__ = [
    "LLMDeckAnalyzer",
]
