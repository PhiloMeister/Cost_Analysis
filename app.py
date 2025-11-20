import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json

# Page configuration
st.set_page_config(
    page_title="Voice Agent Cost Calculator",
    page_icon="📞",
    layout="wide"
)

# Title and description
st.title("📞 Azure Voice Agent Cost Calculator")
st.markdown("Calculate your monthly costs for an AI-powered voice support system")

# ==============================================================================
# SIDEBAR: INPUT WIDGETS
# ==============================================================================

st.sidebar.header("📞 Call Configuration")

minutes_per_call = st.sidebar.slider(
    "Average minutes per call",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
    help="How long does an average customer call last?"
)

calls_per_day = st.sidebar.slider(
    "Number of calls per day",
    min_value=1,
    max_value=500,
    value=50,
    step=5,
    help="Average daily call volume"
)

# AI Model Selection
st.sidebar.header("🤖 AI Model Configuration")

model_options = [
    "GPT-realtime (Best quality, highest cost)",
    "GPT-realtime-mini (Fast, lowest cost)",
    "GPT-4o Realtime (Good quality, moderate-high cost)",
    "GPT-4o Mini Realtime (Fast, low cost)"
]

model_option = st.sidebar.radio(
    "Select Voice AI Model",
    options=model_options,
    index=2,  # GPT-4o Realtime default
    help="Choose the AI model for voice processing"
)

# Show warning for GPT-realtime
if "GPT-realtime (Best" in model_option:
    st.sidebar.warning("⚠️ Not available in Switzerland North region. Requires North Europe or Sweden Central deployment.")

# Infrastructure Configuration
st.sidebar.header("🏗️ Infrastructure Configuration")

num_phone_numbers = st.sidebar.number_input(
    "Number of Swiss phone numbers",
    min_value=1,
    max_value=20,
    value=1,
    step=1,
    help="Each phone number costs CHF 0.80/month"
)

min_replicas = st.sidebar.slider(
    "Minimum container replicas",
    min_value=0,
    max_value=10,
    value=0,
    step=1,
    help="0 = Serverless (cold starts, pay only when active)\n1+ = Always-on (no cold starts, higher cost)"
)

# Show info based on selection
if min_replicas == 0:
    st.sidebar.info("💡 Serverless mode: 5-15 second cold start on first call. Pay only when handling calls.")
else:
    st.sidebar.info(f"⚡ Always-on mode: {min_replicas} replica(s) running 24/7. No cold starts. ~CHF {min_replicas * 31.10:.2f}/month base cost.")

# ==============================================================================
# COST CALCULATIONS
# ==============================================================================

# Step 1: Calculate call volume
calls_per_month = calls_per_day * 30
total_minutes_per_month = calls_per_month * minutes_per_call

# Step 2: Fixed costs
phone_number_cost = num_phone_numbers * 0.80  # CHF 0.80 per Swiss geographic number
storage_cost = 0.10
fixed_costs = phone_number_cost + storage_cost

# Step 3: Container costs
if min_replicas == 0:
    # Serverless: Only pay during calls
    container_seconds_per_call = (minutes_per_call * 60) + 30  # Call duration + 30s overhead
    total_container_seconds = calls_per_month * container_seconds_per_call

    vcpu_cost = total_container_seconds * 0.5 * 0.0000192  # CHF 0.0000192 per vCPU-second
    memory_cost = total_container_seconds * 1.0 * 0.0000024  # CHF 0.0000024 per GiB-second
    container_cost = vcpu_cost + memory_cost
else:
    # Always-on: Pay 24/7
    seconds_per_month = 30 * 24 * 60 * 60  # 2,592,000
    container_cost = min_replicas * (
        (seconds_per_month * 0.5 * 0.0000192) +  # vCPU
        (seconds_per_month * 1.0 * 0.0000024)    # Memory
    )

# Step 4: ACS call costs
acs_cost = total_minutes_per_month * 0.0080

# Step 5: AI model costs (audio only - speech-to-speech)
# Prices converted from per-1M-tokens to per-minute (using 2000 tokens/minute)
if "GPT-realtime (Best" in model_option:
    # GPT-realtime: 25.47 input, 50.94 output (per 1M tokens)
    audio_input_rate = 0.05094
    audio_output_rate = 0.10188
elif "GPT-realtime-mini" in model_option:
    # GPT-realtime-mini: 7.96 input, 15.92 output (per 1M tokens)
    audio_input_rate = 0.01592
    audio_output_rate = 0.03184
elif "GPT-4o Realtime" in model_option:
    # GPT-4o Realtime: 31.8341 input, 63.6680 output (per 1M tokens)
    audio_input_rate = 0.0636682
    audio_output_rate = 0.127336
else:  # GPT-4o Mini Realtime
    # GPT-4o Mini Realtime: 7.9586 input, 15.9170 output (per 1M tokens)
    audio_input_rate = 0.0159172
    audio_output_rate = 0.031834

# Audio costs (50/50 split - customer talks 50%, AI responds 50%)
audio_input_cost = total_minutes_per_month * 0.5 * audio_input_rate
audio_output_cost = total_minutes_per_month * 0.5 * audio_output_rate

ai_cost = audio_input_cost + audio_output_cost

# Step 6: Total
total_monthly_cost = fixed_costs + container_cost + acs_cost + ai_cost
cost_per_call = total_monthly_cost / calls_per_month if calls_per_month > 0 else 0

# ==============================================================================
# MAIN DASHBOARD
# ==============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Total Monthly Cost",
        value=f"CHF {total_monthly_cost:,.2f}"
    )

with col2:
    st.metric(
        label="📞 Cost per Call",
        value=f"CHF {cost_per_call:.2f}"
    )

with col3:
    st.metric(
        label="📊 Monthly Calls",
        value=f"{calls_per_month:,}"
    )

with col4:
    st.metric(
        label="⏱️ Total Minutes",
        value=f"{total_minutes_per_month:,}"
    )

st.markdown("---")

# ==============================================================================
# VISUALIZATIONS
# ==============================================================================

# 1. Cost Breakdown Pie Chart
st.subheader("📊 Cost Distribution")

cost_components = {
    "AI Model (Audio)": audio_input_cost + audio_output_cost,
    "Azure Communication Services": acs_cost,
    "Container Apps": container_cost,
    "Phone Numbers": phone_number_cost,
    "Storage": storage_cost
}

labels = []
values = []
for label, value in cost_components.items():
    if value > 0:
        labels.append(label)
        values.append(value)

fig_pie = go.Figure(data=[go.Pie(
    labels=labels,
    values=values,
    hole=0.3,
    textinfo='label+percent',
    hovertemplate='%{label}<br>CHF %{value:.2f}<br>%{percent}<extra></extra>'
)])

fig_pie.update_layout(
    title="Cost Distribution",
    height=500
)

st.plotly_chart(fig_pie, use_container_width=True)

# 2. Detailed Cost Table
st.subheader("💵 Detailed Cost Breakdown")

breakdown_data = {
    "Service": [],
    "Monthly Cost (CHF)": [],
    "% of Total": [],
    "Cost per Call (CHF)": []
}

for service, cost in cost_components.items():
    breakdown_data["Service"].append(service)
    breakdown_data["Monthly Cost (CHF)"].append(f"{cost:.2f}")
    breakdown_data["% of Total"].append(f"{(cost/total_monthly_cost*100):.1f}%")
    breakdown_data["Cost per Call (CHF)"].append(f"{(cost/calls_per_month):.4f}")

# Add total row
breakdown_data["Service"].append("TOTAL")
breakdown_data["Monthly Cost (CHF)"].append(f"{total_monthly_cost:.2f}")
breakdown_data["% of Total"].append("100.0%")
breakdown_data["Cost per Call (CHF)"].append(f"{cost_per_call:.4f}")

df = pd.DataFrame(breakdown_data)
st.dataframe(df, use_container_width=True, hide_index=True)

# 3. AI Model Comparison
st.subheader("🤖 AI Model Comparison")

# Calculate costs for all 4 models at current volume (audio only)
# GPT-realtime
gpt_realtime_audio = (total_minutes_per_month * 0.5 * 0.05094) + (total_minutes_per_month * 0.5 * 0.10188)
gpt_realtime_total = gpt_realtime_audio + fixed_costs + container_cost + acs_cost

# GPT-realtime-mini
gpt_realtime_mini_audio = (total_minutes_per_month * 0.5 * 0.01592) + (total_minutes_per_month * 0.5 * 0.03184)
gpt_realtime_mini_total = gpt_realtime_mini_audio + fixed_costs + container_cost + acs_cost

# GPT-4o Realtime
gpt4o_audio = (total_minutes_per_month * 0.5 * 0.0636682) + (total_minutes_per_month * 0.5 * 0.127336)
gpt4o_total = gpt4o_audio + fixed_costs + container_cost + acs_cost

# GPT-4o Mini Realtime
gpt4o_mini_audio = (total_minutes_per_month * 0.5 * 0.0159172) + (total_minutes_per_month * 0.5 * 0.031834)
gpt4o_mini_total = gpt4o_mini_audio + fixed_costs + container_cost + acs_cost

models_comparison = {
    "Model": ["GPT-realtime", "GPT-realtime-mini", "GPT-4o Realtime", "GPT-4o Mini Realtime"],
    "Audio Cost/min": ["CHF 0.076", "CHF 0.024", "CHF 0.096", "CHF 0.024"],
    "Monthly Cost (current volume)": [f"CHF {gpt_realtime_total:.2f}",
                                       f"CHF {gpt_realtime_mini_total:.2f}",
                                       f"CHF {gpt4o_total:.2f}",
                                       f"CHF {gpt4o_mini_total:.2f}"],
    "Best For": [
        "Highest quality, complex interactions",
        "Fast, lowest cost",
        "Good balance, moderate-high cost",
        "Fast, low cost"
    ]
}

df_models = pd.DataFrame(models_comparison)
st.dataframe(df_models, use_container_width=True, hide_index=True)

# 5. Serverless vs Always-On Comparison
st.subheader("⚡ Serverless vs Always-On Comparison")

replica_options = [0, 1, 2, 3]
replica_costs = []
replica_config_names = []

for replicas in replica_options:
    # Calculate container cost
    if replicas == 0:
        container_secs = calls_per_month * ((minutes_per_call * 60) + 30)
        rep_container_cost = container_secs * 0.5 * 0.000024 + container_secs * 1.0 * 0.000004
        config_name = "Serverless (0 replicas)"
    else:
        secs_month = 30 * 24 * 60 * 60
        rep_container_cost = replicas * ((secs_month * 0.5 * 0.000024) + (secs_month * 1.0 * 0.000004))
        config_name = f"Always-on ({replicas} replica{'s' if replicas > 1 else ''})"

    rep_total = fixed_costs + rep_container_cost + acs_cost + ai_cost
    replica_costs.append(rep_total)
    replica_config_names.append(config_name)

comparison_df = pd.DataFrame({
    "Configuration": replica_config_names,
    "Monthly Cost": [f"CHF {c:.2f}" for c in replica_costs],
    "Cold Start": ["5-15 sec", "None", "None", "None"],
    "Availability": ["99%", "99.95%", "99.99%", "99.99%"]
})

st.dataframe(comparison_df, use_container_width=True, hide_index=True)

# Highlight current selection
st.info(f"💡 You selected: {replica_config_names[min_replicas]}")

# ==============================================================================
# EXPORT CONFIGURATION
# ==============================================================================

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Export Configuration")

config = {
    "minutes_per_call": minutes_per_call,
    "calls_per_day": calls_per_day,
    "calls_per_month": calls_per_month,
    "model": model_option,
    "num_phone_numbers": num_phone_numbers,
    "min_replicas": min_replicas,
    "calculated_monthly_cost": round(total_monthly_cost, 2),
    "cost_per_call": round(cost_per_call, 2),
    "cost_breakdown": {
        "fixed_costs": round(fixed_costs, 2),
        "container_cost": round(container_cost, 2),
        "acs_cost": round(acs_cost, 2),
        "ai_audio_cost": round(audio_input_cost + audio_output_cost, 2)
    }
}

config_json = json.dumps(config, indent=2)

st.sidebar.download_button(
    label="📥 Download JSON",
    data=config_json,
    file_name="voice_agent_config.json",
    mime="application/json",
    use_container_width=True
)

# Footer
st.markdown("---")
st.markdown("""
### 📋 Cost Assumptions:
- **Container**: 0.5 vCPU, 1 GB memory per replica
- **Cold start overhead**: 30 seconds per call (serverless mode)
- **Audio split**: 50% input (customer talking), 50% output (AI responding)
- **Speech-to-speech**: Direct audio processing, no separate text LLM costs
- **Billing**: 30 days per month, 2,592,000 seconds per month
""")
