Bot Monitoring AI Agent

An intelligent system that monitors bot executions in real-time, detects failures, performs AI-driven Root Cause Analysis (RCA), restarts processes when possible, and communicates with developers via email.

🚀 Features

Real-time WebSocket monitoring of bot executions

Automatic log ingestion & database storage (MongoDB)

AI-powered RCA using LLM (Groq Llama3)

Auto-restart of failed executions (self-healing)

Email-based developer communication loop (SMTP/IMAP)

Live Monitoring Dashboard (HTML UI)

Transparent audit logs & job tracking

📁 Project Structure (High Level)
master_agent/          # AI Brain: LLM, MCP Tools, RCA logic
monitoring_controller/ # System Body: WebSocket, DB, Email, Scheduler, UI
│── utils/
│── scheduler/
│── api/
│── view.html

⚙️ Configuration

Create a .env file in the root directory:

# WebSocket Service
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

🧵 Internal Ports
Component	Port
Monitoring Controller API	8001
Master Agent API	8000
▶️ How to Run

Open two terminals:

🧠 Terminal 1 – Master Agent (AI Brain)
cd master_agent
uvicorn main:app --reload --port 8000

🛠 Terminal 2 – Monitoring Controller (System Engine)
cd monitoring_controller
uvicorn main:app --reload --port 8001

📊 Open Dashboard

Open the UI file directly in your browser:

monitoring_controller/utils/view.html

🔄 System Overview (Simplified Flow)
flowchart LR
    WS[WebSocket Listener] --> DB[(MongoDB)]
    DB --> FaultMonitor[Fault Monitor (Scheduler)]
    FaultMonitor --> AgentTrigger[(POST /v1/event?jobid)]
    AgentTrigger --> LLM[AI Analysis & RCA]
    LLM --> Tools{MCP Tools}
    Tools --> Restart[Auto Restart]
    Tools --> Email[Send Email to Developer]
    Email --> ReplyMonitor[IMAP Reply Monitor]
    ReplyMonitor --> AgentResponse[Agent Continues Processing]
    DB --> Dashboard[Live UI Dashboard]

💡 Components Overview
Component	Responsibility
WebSocket Client	Receives execution + log data
MongoDB	Stores jobs, logs, executions, audit logs
Fault Monitor	Detects and triggers AI for faulted jobs
Master Agent	AI decision-making using Groq LLM
MCP Tools	RCA, email, restart, audit logging
SMTP/IMAP	Email sending and response handling
HTML Dashboard	Visual job tracking & live updates
📝 Included Collections (MongoDB)
Collection	Purpose
jobs	Tracks job status & email/thread state
executions	Raw execution metadata
logs	Detailed process log lines
rca	Stored Root Cause data
auditlogs	AI reasoning and actions
📬 Communication Loop (Email Automation)
Step	Description
1	AI decides escalation to developer
2	Sends email with unique threadId
3	IMAP service captures reply
4	Finds matching job via threadId
5	AI resumes processing based on response
📌 Key Benefits

✔ Fully autonomous monitoring
✔ Intelligent analytics (LLM-based)
✔ Automated RCA and action execution
✔ Human-in-loop approval via email
✔ Transparent & traceable dashboards

📄 Licensing & Contribution

Feel free to customize, extend, or integrate with your own automation platforms. Contributions are welcome