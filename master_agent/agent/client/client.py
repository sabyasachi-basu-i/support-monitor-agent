
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import Any,List
import os,json
import asyncio
from mcp_use import MCPAgent, MCPClient
from agent.server.api.jobs import create_audit_logs
from langchain import messages
from mcp.shared.exceptions import McpError


load_dotenv()

LLM_MODEL = os.getenv("MODEL")

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("Missing GROQ_API_KEY in .env")

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

def read_instructions():
    base_path = os.path.dirname(__file__)
    file_path = os.path.abspath( os.path.join(base_path,"config/SOP.txt"))
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

instructions = read_instructions()

async def setup_agent(message,job_id): 
    
    base_dir = os.path.dirname(__file__)
    server_path = os.path.abspath(os.path.join(base_dir, "../server/server.py"))

    config = {
        "mcpServers": {
            "server": {
                "command": "python",
                "args": [server_path],
                "transport": "stdio",  # keep stdio but remove prints in server.py
            }
        }
    }

    client = MCPClient(config=config)
    llm =  ChatGroq(model=LLM_MODEL)
    agent = MCPAgent(
        llm=llm,
        client=client,
        system_prompt=instructions, 
        max_steps=30)

    result = await agent.run(message)
    audits: List[dict] = []
    history = agent.get_conversation_history()
    for msg in history:
        audits.append({
            "jobType": msg.type,                # Use type as the jobType
            "jobId": job_id,       # Use id if available
            "actor": msg.name or "unknown",     # Name of the message sender
            # "message": msg.content
        })
    # await create_audit_logs(audits)
    agent.close()
    return result
