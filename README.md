# Azure Voice Agent Cost Calculator

A comprehensive Streamlit web application that calculates and visualizes the monthly costs of an Azure-based voice agent system.

## Features

- **Interactive Cost Calculator**: Adjust call volume, AI models, and infrastructure settings
- **Real-time Visualizations**:
  - Cost breakdown pie chart
  - Volume scaling analysis
  - AI model comparison
  - Serverless vs Always-on comparison
- **Preset Scenarios**: Quick configurations for Small, Medium, and Enterprise deployments
- **Export Functionality**: Download configuration as JSON

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Cost Components

### Fixed Monthly Costs
- Azure Communication Services Phone Number: CHF 1.00/month per number
- Storage Account: CHF 0.10/month

### Variable Costs
- **Container Apps**: Based on vCPU and memory usage
  - Serverless (0 replicas): Pay only during calls, 5-15s cold start
  - Always-on (1+ replicas): ~CHF 31.10/replica/month, no cold starts
- **Azure Communication Services**: CHF 0.0080 per minute (inbound calls)
- **AI Models**: Choose from GPT-4, GPT-4o, or GPT-4o-mini Realtime Audio
- **Text LLM**: For reasoning/tool calls during conversations

## Preset Scenarios

### Small Business
- 20 calls/day, 5 min/call
- GPT-4o-mini model
- 1 phone number, serverless (0 replicas)
- Expected: ~CHF 50-80/month

### Medium Business
- 100 calls/day, 7 min/call
- GPT-4o model
- 2 phone numbers, 1 replica (always-on)
- Expected: ~CHF 400-600/month

### Enterprise
- 300 calls/day, 10 min/call
- GPT-4 Realtime model
- 5 phone numbers, 3 replicas (high availability)
- Expected: ~CHF 2,500-3,500/month

## Configuration Options

### Call Configuration
- Average minutes per call (1-30 minutes)
- Number of calls per day (1-500 calls)

### AI Model Configuration
- **GPT-4 Realtime**: Best quality, highest cost
- **GPT-4o Realtime**: Good balance (default)
- **GPT-4o-mini Realtime**: Fast, lowest cost

### Infrastructure Configuration
- Number of phone numbers (1-20)
- Minimum container replicas (0-10)

## Understanding the Dashboard

### Metrics
- **Total Monthly Cost**: Complete cost for your configuration
- **Cost per Call**: Average cost per customer call
- **Monthly Calls**: Total expected calls per month
- **Total Minutes**: Total conversation minutes per month

### Visualizations
1. **Cost Distribution**: See which services consume the most budget
2. **Volume Scaling**: Understand how costs change with call volume
3. **Model Comparison**: Compare AI models at your current volume
4. **Serverless vs Always-On**: Evaluate infrastructure trade-offs

## Export Configuration

Click "Download JSON" in the sidebar to export your current configuration and calculated costs for documentation or comparison purposes.

## Technical Notes

- Built with Streamlit 1.28+
- Uses Plotly for interactive visualizations
- All costs in Swiss Francs (CHF)
- Assumes 30 days per month (2,592,000 seconds)
- Audio split: 50% input (customer), 50% output (AI)
- Text usage: 2,000 tokens per call (70% input, 30% output)
