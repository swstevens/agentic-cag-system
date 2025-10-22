from typing import Dict, Any, List, Optional
import json
import os
import re
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse


class SchedulingAgent(BaseAgent):
    """Agent responsible for planning and scheduling multi-step workflows"""

    def __init__(self, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.SCHEDULING, model_name)

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        # Create Pydantic AI agent
        self._pydantic_agent = Agent(
            model_name,
            system_prompt="""You are a scheduling agent for an MTG deck-building assistant.
            Your role is to analyze queries and determine the best processing path.

            For each query, determine:
            1. Query Type:
               - "deck_building" for queries about building/improving decks
               - "card_info" for queries about specific cards or mechanics
            
            2. For deck building queries, extract:
               - Format (Standard, Modern, etc.)
               - Colors (Red, Blue, etc.)
               - Strategy (Aggro, Control, Midrange, etc.)
               - Budget constraints if mentioned

            3. For card info queries:
               - Specific cards mentioned
               - Mechanics or interactions being asked about

            Return your analysis in this format:
            {
                "query_type": "deck_building" or "card_info",
                "format": "format_name",
                "colors": ["color1", "color2"],
                "strategy": "strategy_name",
                "cards": ["card1", "card2"],
                "next_steps": ["step1", "step2"]
            }"""
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Process query and create execution plan"""
        self.update_state("processing", "Creating execution plan")

        query = input_data.get("query", "")
        context = input_data.get("context", {})

        try:
            # Use Pydantic AI agent to analyze query
            result = await self._pydantic_agent.run(
                f"Analyze this MTG query and provide structured response:\n{query}\nContext: {json.dumps(context)}"
            )

            # Parse the response
            response_text = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Extract the JSON part from the response
            try:
                # Find JSON-like structure between curly braces
                json_match = re.search(r'\{[^{}]*\}', response_text)
                if json_match:
                    # Clean up the JSON string
                    json_str = json_match.group(0)
                    # Replace single quotes with double quotes (but not inside already quoted strings)
                    json_str = json_str.replace("'", '"')
                    # Add quotes around unquoted property names (only if not already quoted)
                    # This regex looks for word characters followed by : that are NOT already quoted
                    json_str = re.sub(r'(?<!")(\w+)(?!"):', r'"\1":', json_str)
                    response_data = json.loads(json_str)
                else:
                    # Fallback to simpler parsing
                    # Smart fallback that extracts format and other details
                    query_lower = query.lower()
                    format_matches = {
                        "standard": "Standard",
                        "modern": "Modern",
                        "legacy": "Legacy",
                        "vintage": "Vintage",
                        "commander": "Commander",
                        "edh": "Commander",
                        "pioneer": "Pioneer"
                    }
                    detected_format = next((format_matches[fmt] for fmt in format_matches if fmt in query_lower), "Standard")
                    
                    # Detect colors from query (using database single-letter codes: W, U, B, R, G)
                    detected_colors = []
                    color_keywords = {
                        "white": "White",
                        "blue": "Blue",
                        "black": "Black",
                        "red": "Red",
                        "green": "Green"
                    }

                    # Also detect guild names (two-color pairs)
                    guild_names = {
                        "azorius": ["White", "Blue"],
                        "dimir": ["Blue", "Black"],
                        "rakdos": ["Black", "Red"],
                        "gruul": ["Red", "Green"],
                        "selesnya": ["Green", "White"],
                        "orzhov": ["White", "Black"],
                        "izzet": ["Blue", "Red"],
                        "golgari": ["Black", "Green"],
                        "boros": ["Red", "White"],
                        "simic": ["Green", "Blue"]
                    }

                    # Check for guild names first
                    for guild, colors in guild_names.items():
                        if guild in query_lower:
                            detected_colors.extend(colors)
                            break  # Only match one guild

                    # If no guild found, check individual colors
                    if not detected_colors:
                        for keyword, color_name in color_keywords.items():
                            if keyword in query_lower:
                                detected_colors.append(color_name)

                    response_data = {
                        "query_type": "deck_building" if any(term in query_lower for term in ["build", "create", "make"]) else "card_info",
                        "format": detected_format,
                        "colors": detected_colors,
                        "strategy": "aggro" if "aggro" in query_lower else "midrange",
                        "next_steps": ["Process query based on type"]
                    }
            except Exception as parse_error:
                print(f"Error parsing response: {parse_error}")
                # Smarter fallback based on query content
                query_lower = query.lower()
                format_matches = {
                    "standard": "Standard",
                    "modern": "Modern",
                    "legacy": "Legacy",
                    "vintage": "Vintage",
                    "commander": "Commander",
                    "edh": "Commander",
                    "pioneer": "Pioneer"
                }
                detected_format = next((format_matches[fmt] for fmt in format_matches if fmt in query_lower), "Standard")

                # Detect colors from query (fallback case)
                detected_colors = []
                color_keywords = {
                    "white": "White",
                    "blue": "Blue",
                    "black": "Black",
                    "red": "Red",
                    "green": "Green"
                }

                # Also detect guild names (two-color pairs)
                guild_names = {
                    "azorius": ["White", "Blue"],
                    "dimir": ["Blue", "Black"],
                    "rakdos": ["Black", "Red"],
                    "gruul": ["Red", "Green"],
                    "selesnya": ["Green", "White"],
                    "orzhov": ["White", "Black"],
                    "izzet": ["Blue", "Red"],
                    "golgari": ["Black", "Green"],
                    "boros": ["Red", "White"],
                    "simic": ["Green", "Blue"]
                }

                # Check for guild names first
                for guild, colors in guild_names.items():
                    if guild in query_lower:
                        detected_colors.extend(colors)
                        break  # Only match one guild

                # If no guild found, check individual colors
                if not detected_colors:
                    for keyword, color_name in color_keywords.items():
                        if keyword in query_lower:
                            detected_colors.append(color_name)

                response_data = {
                    "query_type": "deck_building" if any(term in query_lower for term in ["build", "create", "make"]) else "card_info",
                    "format": detected_format,
                    "colors": detected_colors,
                    "strategy": "aggro" if "aggro" in query_lower else "midrange",
                    "next_steps": ["Process query with default handling"]
                }

            # Return structured response
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data=response_data,
                confidence=1.0,
                reasoning_trace=[
                    f"Identified query type: {response_data.get('query_type', 'unknown')}",
                    "Created processing plan"
                ]
            )

        except Exception as e:
            self.update_state("error")
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=False,
                data={},
                confidence=0.0,
                error=str(e)
            )