import asyncio
from pydantic_ai import Agent
from pydantic import BaseModel

class MyResult(BaseModel):
    message: str

async def main():
    agent = Agent('openai:gpt-4o', output_type=MyResult)
    # We can't easily run it without a key, but we can inspect the class if we can import it
    # Or we can try to find where AgentRunResult is defined
    
    print("Agent module dir:", dir(agent))

if __name__ == "__main__":
    asyncio.run(main())

