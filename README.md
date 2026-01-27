# Testbed - 5G Network Analytics & NWDAF Testing Platform

A comprehensive testbed environment for testing and analyzing 5G network performance, mobility, handover events, and network analytics using **Free5GC**, **UERANSIM**, and **NWDAF** (Network Data Analytics Function).

## Overview

This project provides an integrated testing platform for 5G networks, featuring:

- **Free5GC**: Open-source 5G core network implementation
- **UERANSIM**: 5G RAN simulator for UE (User Equipment) emulation
- **NWDAF**: Network Data Analytics Function for intelligent network insights
- **Prometheus**: Time-series metrics collection and monitoring
- **LLM Integration**: GPT-4 powered natural language interface for network queries and analytics

The testbed is designed for researching 5G network behavior, testing mobility management, analyzing handover procedures, and developing AI-driven network analytics.

## Key Features

- **Real-time Network Metrics**: Track active UEs, registration states, location reports, and destination visits
- **LLM-Powered Analytics**: Query network metrics using natural language with GPT-4o integration
- **NWDAF Integration**: Subscribe/unsubscribe to network analytics events (AMF, SMF)
- **Live Visualization**: Visualize handover and mobility patterns in real-time
- **Prometheus Integration**: Collect and query network metrics via PromQL
- **Comprehensive Dataset**: Includes pre-configured datasets for testing and analysis

## Project Structure

```
.
├── LLM.py                          # Main LLM chatbot interface with function calling
├── LLM1.py                         # Alternative LLM implementation
├── prom_query.py                   # Prometheus query handler and data processing
├── handover_live_visual.py         # Live visualization of handover events
├── mobility_live_visual.py         # Live visualization of UE mobility patterns
├── setup.sh                        # Automated setup script for all dependencies
├── cleanup.sh                      # Cleanup script for testing environment
├── nwdaf.ipynb                     # Jupyter notebook for NWDAF analysis
├── df_2484.csv                     # Sample dataset for testing
├── intent_embeddings.pkl           # Pre-computed LLM embeddings
├── intent_prompts.txt              # Sample prompts for LLM testing
├── test_prompts.txt                # Additional test prompts
├── UERANSIM/                       # UERANSIM 5G RAN simulator
├── free5gc/                        # Free5GC 5G core network
├── prometheus/                     # Prometheus configuration
├── mnc_NWDAF-main/                 # NWDAF implementation
└── core dataset/                   # Network dataset resources
```

## Prerequisites

- **OS**: Ubuntu 20.04 LTS or later
- **Memory**: 8GB+ RAM recommended
- **Storage**: 20GB+ free disk space
- **Python**: Python 3.8+
- **OpenAI API Key**: Required for LLM functionality

## Quick Start

### 1. Automated Setup

Run the setup script to install all dependencies automatically:

```bash
chmod +x setup.sh
./setup.sh
```

This will install:
- Go 1.21.8
- MongoDB 7.0
- Node.js & Yarn
- Prometheus C++ library
- Prometheus v2.41.0
- UERANSIM
- Free5GC
- GTP5G v0.8.7

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
API_KEY=your_openai_api_key_here
PROMETHEUS_URL=http://localhost:9090
NWDAF_URL=http://127.0.0.71:8001
```

### 3. Start the Services

```bash
# Start Prometheus
./prometheus-2.41.0.linux-amd64/prometheus --config.file=prometheus/prometheus.yml

# Start Free5GC
cd free5gc
./webconsole &
./bin/upf &
./bin/smf &
./bin/amf &
./bin/nrf &

# Start UERANSIM
cd UERANSIM
make run

# Start NWDAF service
cd mnc_NWDAF-main
# Follow NWDAF-specific setup instructions
```

### 4. Run the LLM Chatbot

```bash
python LLM.py
```

Then ask natural language questions like:
- "How many active UEs are currently connected?"
- "Show me the registration states of all UEs"
- "Subscribe AMF to NWDAF events"
- "What are the UE location reports?"

## Core Components

### LLM Integration (LLM.py)

The main chatbot interface using OpenAI's GPT-4o model with function calling capabilities:

**Available Functions:**
- `query_prometheus`: Query network metrics using predefined metric names
  - `active_UEs`: Count of currently active UEs
  - `amf_ue_registration_state`: Registration state of each UE
  - `ue_destination_visits_total`: Location visit statistics
  - `UE_location_report`: Current location and cell information

- `nwdaf_subscription_command`: Manage NWDAF event subscriptions
  - Actions: `subscribe` or `unsubscribe`
  - Targets: `amf` or `smf`

### Prometheus Integration (prom_query.py)

Handles queries to Prometheus and data processing:

- `query_prometheus(promql)`: Execute PromQL queries and return structured data
- `get_df_location()`: Retrieve UE location reports
- `get_df_active()`: Get active UE counts over time
- `get_reg()`: Fetch UE registration state changes
- `get_df_destination()`: Query destination visit statistics

### Visualization Tools

- **handover_live_visual.py**: Real-time handover event visualization
- **mobility_live_visual.py**: Live UE mobility pattern visualization with heatmaps and timelines

## Usage Examples

### Query Network Metrics

```bash
python LLM.py
# User input: "How many UEs are currently active?"
# LLM calls: query_prometheus(promql='active_UEs')
# Response: Analytics with active UE count and timeline
```

### Analyze Mobility Patterns

```bash
python handover_live_visual.py
# Displays real-time handover events from Prometheus data
```

### Subscribe to NWDAF Analytics

```bash
python LLM.py
# User input: "Subscribe AMF to NWDAF events"
# LLM calls: nwdaf_subscription_command(action='subscribe', target='amf')
```

## Testing

Use the provided test datasets and prompts:

```bash
# Example test prompts are in test_prompts.txt and intent_prompts.txt
cat test_prompts.txt
```

Run the Jupyter notebook for interactive analysis:

```bash
jupyter notebook nwdaf.ipynb
```

## Cleanup

Remove test data and temporary files:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

## Configuration Files

### Prometheus Configuration
Located in `prometheus/prometheus.yml` - configure scrape intervals, targets, and retention settings.

### Free5GC Configuration
Modify configuration files in `free5gc/config/` for network parameters and service endpoints.

## Known Issues & Manual Steps

⚠️ **Manual Step**: After running setup.sh, manually modify:
```
go/pkg/mod/github.com/free5gc/openapi@v1.0.8/models/model_smf_event.go
```
Add the line: `SmfEvent_PDU_SES_EST SmfEvent = "PDU_SES_EST"`

## Dependencies

- **Python Packages**: `openai`, `pandas`, `prometheus-api-client`, `requests`, `python-dotenv`
- **Go Modules**: `free5gc`, `openapi`
- **System Libraries**: MongoDB, Node.js, Prometheus C++ library

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Chatbot (GPT-4o)                      │
└────────────┬──────────────────────────┬─────────────────────┘
             │                          │
       ┌─────▼──────┐            ┌──────▼──────────┐
       │  Prometheus│            │ NWDAF Commands  │
       │   Queries  │            │  (Subscribe)    │
       └─────┬──────┘            └──────┬──────────┘
             │                          │
       ┌─────▼─────────────────────────▼──────────┐
       │         5G Core Network Stack             │
       │  (Free5GC + UERANSIM + GTP5G)            │
       └─────────────────────────────────────────┘
             │
       ┌─────▼────────────────┐
       │ Network Metrics      │
       │ (Prometheus)         │
       └──────────────────────┘
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

[HenokDanielbfg](https://github.com/HenokDanielbfg)

## Acknowledgments

- Free5GC team for the open-source 5G core implementation
- UERANSIM for the RAN simulator
- Prometheus community for monitoring infrastructure
- OpenAI for GPT-4o API

## Support

For issues and questions, please open an issue on the GitHub repository.

---

**Last Updated**: January 2026
