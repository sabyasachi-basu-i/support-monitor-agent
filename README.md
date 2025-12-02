# Bot Monitoring AI Agent – Technical Overview

An intelligent monitoring system that observes bot executions in real-time, detects failures, performs AI-driven Root Cause Analysis (RCA), restarts processes when possible, and communicates with developers via email.

🚀 Key Features

Real-time WebSocket monitoring of bot executions

Automatic log ingestion and MongoDB storage

AI-powered RCA using LLM (Groq Llama3)

Auto-restart of failed jobs (self-healing)

Email-based developer feedback loop (SMTP/IMAP)

Live monitoring dashboard (HTML UI)

Complete audit logging and traceability

📁 High-Level Project Structure
master_agent/              # AI Brain – LLM, MCP Tools, RCA logic
monitoring_controller/     # System Engine – WebSocket, DB, Email, Scheduler, UI
│── utils/
│── scheduler/
│── api/
│── view.html              # Live dashboard

⚙️ Configuration (.env File)

Create a .env file in the project root:

# WebSocket
WS_URL=wss://us01governor.futuredge.com/api/myhub

# AI / LLM
GROQ_API_KEY=gsk_your_api_key_here
MODEL=llama3-70b-8192

# Database
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=automation_logs_db

# SMTP - Sending Emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_bot_email@gmail.com
SENDER_PASSWORD=your_app_specific_password
RECEIVER_EMAIL=developer_email@gmail.com

# IMAP - Receiving Emails
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your_bot_email@gmail.com
IMAP_PASSWORD=your_app_specific_password


# Local Setup Guide – Bot Monitoring AI Agent
🐍 Python Version Requirement

This project is tested and verified on:

Python 3.11+


To check your Python version:
---
  ``python --version``

🧪 1. Create & Activate Virtual Environment
Windows
---
 ``python -m venv venv``

``venv\Scripts\activate``


📦 2. Install Project Dependencies
--
Run this inside the activated virtual environment:

 ``pip install -r requirements.txt``

🔌 3. Internal Component Ports
Component	Port Master Agent API	8000 
Monitoring Controller API	8001
--
⚠️ Mandatory Startup Order
--
Before running the system, the Master Agent must always be started first.
The Monitoring Controller depends on the Master Agent’s API for RCA, decisions, and MCP tool actions.

--
▶️ 4. Start the Master Agent (AI Brain)
Navigate to Master Agent folder:
--
``cd master_agent``


Run the service:

``uvicorn main:app --reload --port 8000``

▶️ 5. Start the Monitoring Controller (System Engine)
Navigate to Monitoring Controller folder:
--
``cd monitoring_controller``

Run the service:

``uvicorn main:app --reload --port 8001``

📊 6. Open Dashboard (UI)
--
Open this file directly in your browser:

``monitoring_controller/utils/view.html``


🔄 System Workflow (Simplified Flow)
flowchart LR
--
    WS[WebSocket Listener] --> DB[(MongoDB)]
    DB --> FaultMonitor[Fault Monitor (Scheduler)]
    FaultMonitor --> AgentTrigger[(POST /v1/event?jobid)]
    AgentTrigger --> LLM[AI Analysis & RCA]
    LLM --> Tools{MCP Tools}
    Tools --> Restart[Auto Restart]
    Tools --> Email[Send Email to Developer]
    Email --> ReplyMonitor[IMAP Reply Monitor]
    ReplyMonitor --> AgentResponse[Resume AI Processing]
    DB --> Dashboard[Live UI Dashboard]

💡 Component Responsibilities
Component	Description
WebSocket Client	Receives bot execution and log data in real-time
MongoDB	Stores jobs, logs, executions, and audit data
Fault Monitor	Detects failures and triggers AI
Master Agent (LLM)	Performs RCA and decision-making
MCP Tools	Restart actions, email sending, audit logging
SMTP/IMAP	Sends developer notifications and receives replies
HTML Dashboard	Displays real-time job status and RCA results
📝 MongoDB Collections Overview
Collection	Purpose
jobs	Job status, timestamps, email thread tracking
executions	Raw execution metadata
logs	Detailed process log lines
rca	RCA outputs from the AI
auditlogs	All AI decisions and tool actions
📬 Email Communication Loop
Step	Description
1	AI decides whether developer involvement is needed
2	Email sent with unique threadId
3	IMAP worker retrieves replies
4	Reply mapped to correct job via threadId
5	AI continues action based on developer input
📌 Key Benefits

✔ Autonomous fault monitoring

✔ Intelligent LLM-driven analytics

✔ Automated RCA and job recovery

✔ Human-in-loop approval flow

✔ Fully transparent with auditing and dashboards

📄 Licensing & Contribution

Feel free to extend, customize, or integrate with your automation systems.
Contributions and pull requests are welcome.