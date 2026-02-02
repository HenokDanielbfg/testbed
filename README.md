# Natural Language Interface for 5G Testbed
This repository implements a **Natural Language Query Interface** for a 5G testbed, enabling users to interact with network analytics and control functions using conversational queries.  
The system translates natural language into analytics queries and network commands, bridging users and 5G monitoring components.

## Components
### LLM1.py — Intent Processing & Orchestration
    • Converts user queries into semantic embeddings
    • Matches queries to predefined 5G analytics and control intents (RAG-style)
    • Dispatches actions to:
        ◦ NWDAF (AMF/SMF subscribe & unsubscribe)
        ◦ Prometheus analytics queries
    • Uses an LLM to interpret and verbalize query results
### prom_query.py — Prometheus Analytics Backend
    • Queries Prometheus for NWDAF-exposed metrics
    • Supported analytics include:
        ◦ Active UE count
        ◦ UE location change reports
        ◦ AMF UE registration state
        ◦ UE destination/visit patterns
    • Cleans, deduplicates, and formats results for LLM consumption
## Supported Capabilities
    • Natural language queries over live 5G network metrics
    • Event-driven analytics via NWDAF subscriptions
    • Unified interface for control-plane events and performance metrics
## Typical Flow
    1. User submits a natural language query
    2. Query is matched to an intent using embeddings
    3. Corresponding NWDAF or Prometheus action is executed
    4. Results are summarized in natural language
