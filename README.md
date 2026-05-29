# SentinelFly

SentinelFly is an AI-powered Drone Security Analyst Agent.

This repository currently contains a clean project foundation with a minimal Streamlit dashboard and placeholder modules for future simulation, event parsing, alerting, memory, and agent workflows.

## Project Structure

```text
SentinelFly/
├── app.py
├── requirements.txt
├── README.md
├── data/
├── docs/
├── src/
│   ├── agent.py
│   ├── alert_engine.py
│   ├── database.py
│   ├── event_parser.py
│   ├── indexer.py
│   ├── memory.py
│   ├── simulator.py
│   └── summarizer.py
└── tests/
```

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the dashboard:

```bash
streamlit run app.py
```
