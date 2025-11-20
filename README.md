# Azure AI Agent Cost Calculator

A comprehensive Streamlit web application that calculates and visualizes the monthly costs of Azure-based Voice and Email AI agents for customer support systems.

## Features

### 3-Tab Interface
- **Voice Agent Tab**: Configure and analyze voice call support costs
- **Email Agent Tab**: Configure and analyze email support costs
- **Combined Total Tab**: View overall costs, optimization recommendations, and export configuration

### Voice Agent Features
- Real-time cost calculations for Azure Communication Services
- 4 GPT Realtime audio models with side-by-side comparison
- Serverless vs Always-on infrastructure analysis
- Free tier support (180K vCPU-seconds, 360K GiB-seconds/month)
- Cold start impact visualization

### Email Agent Features
- Azure Functions serverless email polling cost analysis
- 3 GPT-5 models for email processing
- RAG (Retrieval Augmented Generation) document search capability
- Business hours vs 24/7 polling comparison
- Free tier tracking (1M executions, 400K GiB-seconds/month)

### Shared Features
- Shared blob storage (Hot tier) for both agents
- Preset scenarios (Small Business, Medium Business, Enterprise)
- Cost optimization recommendations
- Interactive Plotly visualizations
- JSON configuration export

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Setup

1. Clone or download this repository:
```bash
git clone <your-repo-url>
cd Cost_Analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Start the Streamlit server:
```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Architecture

### Voice Agent Infrastructure
- **Azure Communication Services**: Phone number leasing + inbound call charges
- **Container Apps**: WebSocket server for real-time voice processing
  - Serverless (0 replicas): Cold starts, pay only during calls
  - Always-on (1+ replicas): No cold starts, 24/7 availability
- **GPT Realtime Models**: Audio processing + text reasoning
- **Shared Blob Storage**: Access to repair manuals and documentation

### Email Agent Infrastructure
- **Azure Functions**: Serverless email polling (configurable frequency)
- **Microsoft Graph API**: Email access (assumed, not included in costs)
- **GPT-5 Models**: Text processing for email understanding and generation
- **Shared Blob Storage**: RAG document search across manuals

### Pricing Configuration
All pricing is loaded from `pricing_config.json` with no hardcoded values in the application code. This allows for easy updates as Azure pricing changes.

## Configuration Options

### Voice Agent
- **Call Volume**: 1-500 calls per day
- **Call Duration**: 1-30 minutes per call
- **AI Models**:
  - GPT-realtime (Best quality, highest cost)
  - GPT-realtime-mini (Fast, lowest cost)
  - GPT-4o Realtime (Good quality, moderate-high cost)
  - GPT-4o Mini Realtime (Fast, low cost)
- **Phone Numbers**: 1-20 Swiss geographic numbers (CHF 0.80/month each)
- **Infrastructure**: 0-10 container replicas

### Email Agent
- **Email Volume**: 1-1000 emails per day
- **Polling Frequency**: 1, 2, 5, 10, 15, 30, or 60 minutes
- **Operating Hours**: 24/7 or Business hours only (8:00-18:30, Mon-Fri)
- **AI Models**:
  - GPT-5-mini (Fast, economical)
  - GPT-5 (Best quality)
  - GPT-4o (Good balance)
- **RAG**: Enable/disable document search with 0-50,000 manual pages

## Preset Scenarios

### Small Business
- **Voice**: 20 calls/day, 5 min/call, GPT-realtime-mini, 1 phone, serverless
- **Email**: 30 emails/day, 5min polling, GPT-5-mini, 2000 pages RAG, 24/7
- **Expected Cost**: ~CHF 150-250/month

### Medium Business
- **Voice**: 100 calls/day, 7min/call, GPT-4o Realtime, 2 phones, 1 replica
- **Email**: 150 emails/day, 1min polling, GPT-5-mini, 10000 pages RAG, 24/7
- **Expected Cost**: ~CHF 600-900/month

### Enterprise
- **Voice**: 300 calls/day, 10min/call, GPT-4o Realtime, 5 phones, 3 replicas
- **Email**: 500 emails/day, 1min polling, GPT-5, 30000 pages RAG, 24/7
- **Expected Cost**: ~CHF 3,000-4,500/month

## Dashboard Features

### Voice Agent Tab
1. **Key Metrics**: Total cost, cost per call, monthly calls, total minutes
2. **Cost Distribution**: Pie chart showing service breakdown
3. **Detailed Breakdown**: Table with per-service costs and percentages
4. **Model Comparison**: All 4 models at current volume
5. **Serverless vs Always-On**: Infrastructure cost comparison

### Email Agent Tab
1. **Key Metrics**: Total cost, cost per email, monthly emails, manual pages
2. **Cost Distribution**: LLM, Azure Functions, Blob Storage breakdown
3. **Free Tier Status**: Visual tracking of free tier consumption
4. **Model Comparison**: All 3 models at current volume
5. **Polling Frequency Impact**: How frequency affects costs

### Combined Total Tab
1. **Overview Metrics**: Total cost, voice/email split, average cost per interaction
2. **Cost Distribution Bar Chart**: Stacked visualization by channel
3. **Channel Comparison Table**: Side-by-side metrics
4. **Combined Cost Breakdown**: All services in single pie chart
5. **Optimization Recommendations**: Actionable cost-saving suggestions
6. **Cost Alerts**: Color-coded warnings for high costs
7. **Export Configuration**: Download full configuration as JSON

## Cost Assumptions

### Deployment Region
- All services and models deployed in **Sweden Central**

### Voice Agent
- **Audio Processing**: 2000 tokens per minute
- **Audio Split**: 40% customer talking, 60% AI responding
- **Text Reasoning**: 2000 tokens per call (tool usage, context management)
- **Container**: 0.5 vCPU, 1 GB memory per replica
- **Free Tier**: 180,000 vCPU-seconds + 360,000 GiB-seconds per month

### Email Agent
- **Base Email**: 1000 tokens (reading and understanding)
- **RAG Context**: 1500 additional tokens (~1125 words ≈ 2-3 pages of manual text)
- **Response**: 500 tokens
- **Function**: 0.5 GB memory, 3 seconds per email check
- **Free Tier**: 1,000,000 executions + 400,000 GiB-seconds per month

### Shared Resources
- **Blob Storage**: Hot tier, CHF 0.0255 per GB/month
- **Manual Pages**: 2.5 MB per page average
- **Index Overhead**: 30% additional storage for embeddings and metadata

### Business Hours
- **Schedule**: 8:00-18:30, Monday-Friday
- **Monthly Hours**: ~227 hours (vs 720 for 24/7)

### Prompt Caching
- **Not Included**: Cost estimates are conservative (prompt caching would reduce costs further)

## Optimization Recommendations

The application automatically suggests cost optimizations based on your configuration:

1. **Voice Agent**:
   - Switch to lower-cost models when quality difference is minimal
   - Reduce replica count if over-provisioned
   - Consider serverless for low call volumes

2. **Email Agent**:
   - Increase polling interval if instant response not required
   - Switch to GPT-5-mini for routine email responses
   - Enable business hours only if 24/7 coverage not needed
   - Optimize RAG document count

3. **Combined**:
   - Color-coded alerts for high monthly costs (>CHF 5000)
   - Moderate cost warnings (>CHF 1000)
   - Confirmation for economical configurations

## Technical Details

### Files
- `app.py`: Main Streamlit application (1029 lines)
- `pricing_config.json`: All Azure service pricing (no hardcoded values)
- `requirements.txt`: Python dependencies
- `README.md`: This documentation

### Dependencies
- `streamlit>=1.28.0`: Web application framework
- `plotly>=5.14.0`: Interactive visualizations
- `pandas>=2.0.0`: Data manipulation and tables

### Pricing Updates
To update pricing, edit `pricing_config.json` only. The application automatically loads all values from this file, ensuring consistency and easy maintenance.

## Export Configuration

Click "Download Configuration (JSON)" in the Combined Total tab to export:
- Voice agent settings and costs
- Email agent settings and costs
- Shared resource costs
- Combined totals and percentages
- Timestamp and pricing version

## Development

### Adding New Models
1. Add model pricing to `pricing_config.json` under appropriate section
2. Application automatically detects and displays new models

### Modifying Assumptions
1. Update values in `pricing_config.json`
2. Application recalculates automatically
3. Assumptions display updates in sidebar

### Custom Scenarios
Modify preset buttons in `app.py` lines 246-292 to add custom quick-load configurations.

## Troubleshooting

### Application won't start
- Ensure Python 3.10+ is installed
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check `pricing_config.json` is valid JSON

### Costs seem incorrect
- Verify `pricing_config.json` has latest Azure pricing
- Check calculation assumptions in sidebar expander
- Compare with Azure pricing calculator

### Preset scenarios not working
- Try clicking preset button again
- Check browser console for errors
- Restart Streamlit server

## License

This calculator is provided as-is for cost estimation purposes. Actual Azure costs may vary based on region, consumption patterns, and Azure pricing changes.

## Support

For issues or questions:
1. Check this README for configuration details
2. Verify `pricing_config.json` matches current Azure pricing
3. Review calculation assumptions in the sidebar

## Version History

- **v1.0.0** (2025-11-20): Initial release with Voice + Email dual-agent calculator
  - 3-tab interface
  - 4 Voice models, 3 Email models
  - Free tier support
  - Preset scenarios
  - Optimization recommendations
  - JSON export
