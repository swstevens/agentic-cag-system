import asyncio
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

class SimpleOutput(BaseModel):
    message: str

async def main():
    agent = Agent('openai:gpt-4o-mini', output_type=SimpleOutput)
    result = await agent.run("Say hello")
    
    print("Result type:", type(result))
    print("Result attributes:", [attr for attr in dir(result) if not attr.startswith('_')])
    print("\nTrying different access patterns:")
    
    # Try different ways to access the data
    if hasattr(result, 'data'):
        print("result.data:", result.data)
    if hasattr(result, 'output'):
        print("result.output:", result.output)
    if hasattr(result, 'result'):
        print("result.result:", result.result)
    
    # Just print the result directly
    print("\nDirect result:", result)

if __name__ == "__main__":
    asyncio.run(main())
