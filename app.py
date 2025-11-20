import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
from datetime import datetime

# ==============================================================================
# LOAD PRICING CONFIGURATION
# ==============================================================================

@st.cache_data(ttl=60)  # Cache expires after 60 seconds to pick up pricing updates
def load_pricing():
    """Load pricing configuration from JSON file"""
    with open('pricing_config.json', 'r') as f:
        return json.load(f)

pricing = load_pricing()

# ==============================================================================
# CALCULATION FUNCTIONS
# ==============================================================================

def calculate_blob_storage_cost(num_pages, enable_rag):
    """Calculate shared blob storage cost"""
    if not enable_rag or num_pages == 0:
        return {'cost': 0, 'storage_gb': 0}

    blob_config = pricing['shared']['blob_storage']

    # Document storage
    storage_gb = (num_pages * blob_config['mb_per_page'] / 1024) * blob_config['index_overhead_multiplier']

    # Cost
    blob_cost = storage_gb * blob_config['hot_tier_per_gb_month']

    return {
        'cost': blob_cost,
        'storage_gb': storage_gb
    }


def calculate_voice_cost(minutes_per_call, calls_per_day, model_key, num_phones, min_replicas, business_hours_only=False):
    """Calculate voice agent monthly costs"""

    # Load pricing
    acs_pricing = pricing['voice_agent']['acs']
    container_config = pricing['voice_agent']['container_apps']
    model = pricing['voice_agent']['models'][model_key]
    audio_conversion = pricing['voice_agent']['audio_conversion']
    operating_hours_config = pricing['email_agent']['operating_hours']

    # Volume calculations
    calls_per_month = calls_per_day * 30
    total_minutes = calls_per_month * minutes_per_call

    # ACS costs
    phone_cost = num_phones * acs_pricing['phone_number_per_month']
    acs_call_cost = total_minutes * acs_pricing['inbound_per_minute']

    # Container costs
    if min_replicas == 0:
        # Serverless: only pay during calls
        call_seconds = calls_per_month * (minutes_per_call * 60)

        # vCPU cost
        vcpu_seconds = call_seconds
        if vcpu_seconds > container_config['free_vcpu_seconds_per_month']:
            vcpu_cost = (vcpu_seconds - container_config['free_vcpu_seconds_per_month']) * container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']
        else:
            vcpu_cost = 0

        # Memory cost
        gb_seconds = call_seconds * container_config['memory_gb_per_replica']
        if gb_seconds > container_config['free_gb_seconds_per_month']:
            memory_cost = (gb_seconds - container_config['free_gb_seconds_per_month']) * container_config['memory_gb_active_per_second']
        else:
            memory_cost = 0

        # Request cost (NEW)
        # Serverless: each call generates ~2 requests (connection + messages)
        requests = calls_per_month * 2
        if requests > container_config['free_requests_per_month']:
            request_cost = ((requests - container_config['free_requests_per_month']) / 1_000_000) * container_config['requests_per_million']
        else:
            request_cost = 0

        container_cost = vcpu_cost + memory_cost + request_cost

    else:
        # Always-on: pay for operating hours (business hours or 24/7)
        if business_hours_only:
            # Business hours: ~227.3 hours/month
            operating_hours = operating_hours_config['business_hours_per_month']
        else:
            # Full time: 720 hours/month (30 days × 24 hours)
            operating_hours = operating_hours_config['full_time_hours_per_month']

        monthly_seconds = operating_hours * 3600  # Convert hours to seconds

        # Active time: during calls
        active_seconds = calls_per_month * (minutes_per_call * 60)
        idle_seconds = monthly_seconds - active_seconds

        # Active costs (separate vCPU and memory for breakdown)
        active_vcpu_cost = min_replicas * active_seconds * container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']
        active_memory_cost = min_replicas * active_seconds * container_config['memory_gb_per_replica'] * container_config['memory_gb_active_per_second']
        active_cost = active_vcpu_cost + active_memory_cost

        # Idle costs (flat rate for both vCPU + memory combined)
        idle_cost = min_replicas * idle_seconds * container_config['idle_per_second']

        # Calculate separate vcpu and memory costs for breakdown
        # For idle, we split the flat rate proportionally based on active rates
        total_active_rate = (container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']) + \
                           (container_config['memory_gb_per_replica'] * container_config['memory_gb_active_per_second'])
        vcpu_active_rate = container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']
        memory_active_rate = container_config['memory_gb_per_replica'] * container_config['memory_gb_active_per_second']

        vcpu_idle_portion = (vcpu_active_rate / total_active_rate) if total_active_rate > 0 else 0.5
        memory_idle_portion = (memory_active_rate / total_active_rate) if total_active_rate > 0 else 0.5

        idle_vcpu_cost = idle_cost * vcpu_idle_portion
        idle_memory_cost = idle_cost * memory_idle_portion

        vcpu_cost = active_vcpu_cost + idle_vcpu_cost
        memory_cost = active_memory_cost + idle_memory_cost

        # vCPU and Memory seconds for always-on
        vcpu_seconds = min_replicas * monthly_seconds
        gb_seconds = min_replicas * monthly_seconds * container_config['memory_gb_per_replica']

        # Request cost (NEW)
        # Always-on: health checks + actual requests
        # Azure does ~1 health check per minute
        if business_hours_only:
            health_checks_per_month = operating_hours * 60  # 1 per minute during operating hours
        else:
            health_checks_per_month = 30 * 24 * 60  # 43,200/month for 24/7

        actual_requests = calls_per_month * 2
        requests = health_checks_per_month + actual_requests
        if requests > container_config['free_requests_per_month']:
            request_cost = ((requests - container_config['free_requests_per_month']) / 1_000_000) * container_config['requests_per_million']
        else:
            request_cost = 0

        container_cost = active_cost + idle_cost + request_cost

    # AI Audio costs (per million tokens, convert to per-minute)
    tokens_per_minute = audio_conversion['tokens_per_minute_audio']
    total_audio_tokens = total_minutes * tokens_per_minute

    # Split: use config values (40% customer input, 60% AI output)
    input_tokens = total_audio_tokens * audio_conversion['input_split']
    output_tokens = total_audio_tokens * audio_conversion['output_split']

    audio_input_cost = (input_tokens / 1_000_000) * model['audio_input_per_m_tokens']
    audio_output_cost = (output_tokens / 1_000_000) * model['audio_output_per_m_tokens']

    # Text reasoning costs (2000 tokens per call)
    text_tokens = model['tokens_per_call']
    text_input_tokens = text_tokens * 0.7
    text_output_tokens = text_tokens * 0.3

    text_input_cost = calls_per_month * (text_input_tokens / 1_000_000) * model['text_input_per_m_tokens']
    text_output_cost = calls_per_month * (text_output_tokens / 1_000_000) * model['text_output_per_m_tokens']

    # Total AI cost
    ai_cost = audio_input_cost + audio_output_cost + text_input_cost + text_output_cost

    # Total
    total_cost = phone_cost + acs_call_cost + container_cost + ai_cost

    return {
        'total': total_cost,
        'phone': phone_cost,
        'acs': acs_call_cost,
        'container': container_cost,
        'ai_audio': audio_input_cost + audio_output_cost,
        'ai_text': text_input_cost + text_output_cost,
        'ai_total': ai_cost,
        'calls': calls_per_month,
        'minutes': total_minutes,
        'cost_per_call': total_cost / calls_per_month,
        'vcpu_seconds': vcpu_seconds,  # NEW
        'gb_seconds': gb_seconds,  # NEW
        'requests': requests,  # NEW
        'business_hours': business_hours_only,  # NEW
        'breakdown': {
            'phone_cost': phone_cost,
            'acs_cost': acs_call_cost,
            'container_cost': container_cost,
            'container_vcpu': vcpu_cost,  # NEW
            'container_memory': memory_cost,  # NEW
            'container_requests': request_cost,  # NEW
            'audio_input': audio_input_cost,
            'audio_output': audio_output_cost,
            'text_input': text_input_cost,
            'text_output': text_output_cost
        }
    }


def calculate_email_cost(emails_per_day, polling_minutes, model_key, enable_rag, num_pages, business_hours_only):
    """Calculate email agent monthly costs"""

    # Load pricing
    functions_config = pricing['email_agent']['azure_functions']
    model = pricing['email_agent']['models'][model_key]
    token_config = pricing['email_agent']['tokens']
    operating_hours = pricing['email_agent']['operating_hours']

    # Volume
    emails_per_month = emails_per_day * 30

    # Adjust checks for business hours (use config values)
    if business_hours_only:
        hours_per_month = operating_hours['business_hours_per_month']
    else:
        hours_per_month = operating_hours['full_time_hours_per_month']

    checks_per_month = (hours_per_month * 60) / polling_minutes

    # Azure Functions cost
    # Execution cost
    if checks_per_month > functions_config['free_executions_per_month']:
        execution_cost = ((checks_per_month - functions_config['free_executions_per_month']) / 1_000_000) * functions_config['execution_cost_per_million']
    else:
        execution_cost = 0

    # Compute cost (3 seconds per check, 0.5 GB memory)
    execution_seconds = checks_per_month * functions_config['seconds_per_execution']
    gb_seconds = execution_seconds * functions_config['memory_gb']

    if gb_seconds > functions_config['free_gb_seconds_per_month']:
        compute_cost = (gb_seconds - functions_config['free_gb_seconds_per_month']) * functions_config['compute_cost_per_gb_second']
    else:
        compute_cost = 0

    functions_cost = execution_cost + compute_cost

    # LLM costs (per million tokens, NOT per 1K)
    if enable_rag:
        input_tokens_per_email = token_config['base_input_tokens'] + token_config['rag_additional_tokens']
    else:
        input_tokens_per_email = token_config['base_input_tokens']

    output_tokens_per_email = token_config['output_tokens']

    total_input_tokens = emails_per_month * input_tokens_per_email
    total_output_tokens = emails_per_month * output_tokens_per_email

    llm_input_cost = (total_input_tokens / 1_000_000) * model['input_per_m_tokens']
    llm_output_cost = (total_output_tokens / 1_000_000) * model['output_per_m_tokens']
    llm_cost = llm_input_cost + llm_output_cost

    # Total (blob storage calculated separately as shared resource)
    total_cost = functions_cost + llm_cost

    return {
        'total': total_cost,
        'functions': functions_cost,
        'llm': llm_cost,
        'emails': emails_per_month,
        'checks': checks_per_month,
        'cost_per_email': total_cost / emails_per_month if emails_per_month > 0 else 0,
        'gb_seconds': gb_seconds,
        'execution_cost': execution_cost,
        'compute_cost': compute_cost,
        'llm_input': llm_input_cost,
        'llm_output': llm_output_cost,
        'business_hours': business_hours_only
    }

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="Voice + Email Agent Cost Calculator",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Agent Cost Calculator")
st.markdown("Calculate monthly costs for Voice and Email AI support agents")

# Display pricing version info
col1, col2, col3 = st.columns([2, 1, 1])
with col3:
    with st.expander("ℹ️ Pricing Info"):
        st.caption(f"**Version:** {pricing['version']}")
        st.caption(f"**Currency:** {pricing['currency']}")
        st.caption(f"**Updated:** {pricing['last_updated']}")
        st.caption("💡 Prices from `pricing_config.json`")

# ==============================================================================
# ==============================================================================
# SIDEBAR: VOICE AGENT CONFIGURATION
# ==============================================================================

st.sidebar.header("📞 Voice Agent Configuration")

voice_minutes_per_call = st.sidebar.slider(
    "Average minutes per call",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
    help="How long does an average customer call last?"
)

voice_calls_per_day = st.sidebar.slider(
    "Number of calls per day",
    min_value=1,
    max_value=500,
    value=50,
    step=5,
    help="Average daily call volume"
)

# AI Model Selection
voice_model_options = list(pricing['voice_agent']['models'].keys())
voice_model_names = {k: v['name'] for k, v in pricing['voice_agent']['models'].items()}

default_voice_model = 'gpt_realtime_mini'
voice_model_index = voice_model_options.index(default_voice_model) if default_voice_model in voice_model_options else 1

voice_model_key = st.sidebar.radio(
    "Voice AI Model",
    options=voice_model_options,
    format_func=lambda x: voice_model_names[x],
    index=voice_model_index,
    help="AI model for voice processing"
)

# Infrastructure
voice_num_phones = st.sidebar.number_input(
    "Number of Swiss phone numbers",
    min_value=1,
    max_value=20,
    value=1,
    step=1,
    help="Each phone number costs CHF 0.80/month"
)

voice_min_replicas = st.sidebar.slider(
    "Minimum container replicas",
    min_value=0,
    max_value=10,
    value=0,
    step=1,
    help="0 = Serverless (cold starts, pay only when active)\n1+ = Always-on (no cold starts, higher cost)"
)

if voice_min_replicas == 0:
    st.sidebar.info("💡 Serverless: 5-15 sec cold start on first call. Pay only when handling calls.")
else:
    # Calculate always-on cost estimate
    container_config = pricing['voice_agent']['container_apps']
    monthly_cost = voice_min_replicas * (
        (container_config['seconds_per_month'] * container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']) +
        (container_config['seconds_per_month'] * container_config['memory_gb_per_replica'] * container_config['memory_gb_active_per_second'])
    )
    st.sidebar.info(f"⚡ Always-on: {voice_min_replicas} replica(s) running 24/7. Base cost ~CHF {monthly_cost:.2f}/month + usage costs.")

# Operating Hours
voice_operating_hours = st.sidebar.checkbox(
    "Business hours only (8h-18h30, Mon-Fri)",
    value=False,
    help="Run voice agent only during business hours to reduce costs (mainly affects always-on mode)"
)

if voice_operating_hours:
    operating_hours = pricing['email_agent']['operating_hours']
    st.sidebar.caption(f"💡 Voice agent active during business hours (~{operating_hours['business_hours_per_month']:.1f} hours/month vs 720 for 24/7)")

# ==============================================================================
# SIDEBAR: EMAIL AGENT CONFIGURATION
# ==============================================================================

st.sidebar.header("📧 Email Agent Configuration")

# Email Volume
email_emails_per_day = st.sidebar.slider(
    "Average emails per day",
    min_value=1,
    max_value=1000,
    value=50,
    step=5,
    help="Number of customer emails received daily"
)

# Polling Interval
email_polling_interval = st.sidebar.select_slider(
    "Email check frequency (minutes)",
    options=[1, 2, 5, 10, 15, 30, 60],
    value=1,
    help="How often to check for new emails"
)

email_checks_per_month = (30 * 24 * 60) / email_polling_interval
st.sidebar.caption(f"= {email_checks_per_month:,.0f} checks/month")

if email_polling_interval == 1 and email_emails_per_day > 200:
    st.sidebar.warning("⚠️ High frequency + volume may exceed free tier")

# Operating Hours
email_operating_hours = st.sidebar.checkbox(
    "Business hours only (8h-18h30, Mon-Fri)",
    value=False,
    help="Reduce polling to business hours to save costs"
)

if email_operating_hours:
    # Business hours: 8:00-18:30 = 10.5 hours/day, 5 days/week
    # = 52.5 hours/week = 227.3 hours/month
    hours_per_month = 227.3
    st.sidebar.caption(f"💡 Polling only during business hours (~227 hours/month vs 720 for 24/7)")
else:
    hours_per_month = 720  # 30 days × 24 hours

# AI Model Selection
email_model_options = list(pricing['email_agent']['models'].keys())
email_model_names = {k: v['name'] for k, v in pricing['email_agent']['models'].items()}

default_email_model = 'gpt_5_mini'
email_model_index = email_model_options.index(default_email_model) if default_email_model in email_model_options else 0

email_model_key = st.sidebar.radio(
    "Email AI Model",
    options=email_model_options,
    format_func=lambda x: email_model_names[x],
    index=email_model_index,
    help="Model for reading emails and generating responses"
)

# Document Knowledge Base (RAG)
email_enable_rag = st.sidebar.checkbox(
    "Enable PDF document search (RAG)",
    value=True,
    help="Allow agent to search repair manuals/documentation"
)

if email_enable_rag:
    email_num_pages = st.sidebar.number_input(
        "Number of manual pages",
        min_value=0,
        max_value=50000,
        value=5000,
        step=100,
        help="Total pages across all repair manuals and guides"
    )

    # Show storage estimate
    blob_config = pricing['shared']['blob_storage']
    storage_gb = (email_num_pages * blob_config['mb_per_page'] / 1024) * blob_config['index_overhead_multiplier']
    st.sidebar.caption(f"≈ {storage_gb:.2f} GB storage needed")

    # Info about RAG context
    rag_tokens = pricing['email_agent']['tokens']['rag_additional_tokens']
    st.sidebar.info(f"💡 RAG adds {rag_tokens} tokens context (~{int(rag_tokens * 0.75)} words ≈ 2-3 pages of manual text per email)")
else:
    email_num_pages = 0

# ==============================================================================
# TABS
# ==============================================================================

tab1, tab2, tab3 = st.tabs(["📞 Voice Agent", "📧 Email Agent", "💰 Combined Total"])

# ==============================================================================
# TAB 1: VOICE AGENT
# ==============================================================================

with tab1:
    st.header("📞 Voice Agent Costs")

    # Calculate costs
    voice_results = calculate_voice_cost(
        voice_minutes_per_call,
        voice_calls_per_day,
        voice_model_key,
        voice_num_phones,
        voice_min_replicas,
        voice_operating_hours
    )

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Monthly Cost", f"CHF {voice_results['total']:,.2f}")
    with col2:
        st.metric("📞 Cost per Call", f"CHF {voice_results['cost_per_call']:.2f}")
    with col3:
        st.metric("📊 Monthly Calls", f"{voice_results['calls']:,}")
    with col4:
        st.metric("⏱️ Total Minutes", f"{voice_results['minutes']:,}")

    # Operating hours info
    if voice_results['business_hours'] and voice_min_replicas > 0:
        operating_hours_config = pricing['email_agent']['operating_hours']
        hours_def = operating_hours_config['business_hours_definition']
        hours_saved = operating_hours_config['full_time_hours_per_month'] - operating_hours_config['business_hours_per_month']
        st.info(f"⏰ Voice agent operates during business hours only ({hours_def}) - Saves {hours_saved:.1f} hours/month vs 24/7 (applies to always-on mode)")

    # Cost breakdown pie chart
    st.subheader("📊 Cost Distribution")

    voice_breakdown = {
        "AI Audio Processing": voice_results['ai_audio'],
        "AI Text Reasoning": voice_results['ai_text'],
        "Phone Calls (ACS)": voice_results['acs'],
        "Container - Compute": voice_results['breakdown']['container_vcpu'] + voice_results['breakdown']['container_memory'],
        "Container - Requests": voice_results['breakdown']['container_requests'],
        "Phone Numbers": voice_results['phone']
    }

    # Remove zero values
    voice_breakdown = {k: v for k, v in voice_breakdown.items() if v > 0}

    fig = go.Figure(data=[go.Pie(
        labels=list(voice_breakdown.keys()),
        values=list(voice_breakdown.values()),
        hole=0.3,
        textinfo='label+percent',
        texttemplate='%{label}<br>%{percent}<br>CHF %{value:.2f}'
    )])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Detailed breakdown table
    st.subheader("📋 Detailed Breakdown")
    breakdown_data = []
    for service, cost in voice_breakdown.items():
        breakdown_data.append({
            "Service": service,
            "Monthly Cost": f"CHF {cost:.2f}",
            "% of Total": f"{(cost/voice_results['total']*100):.1f}%",
            "Cost per Call": f"CHF {(cost/voice_results['calls']):.4f}"
        })

    df = pd.DataFrame(breakdown_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Model comparison
    st.subheader("🔄 Model Comparison at Current Volume")

    model_comparison = []
    for model_key_temp, model_data in pricing['voice_agent']['models'].items():
        temp_results = calculate_voice_cost(
            voice_minutes_per_call,
            voice_calls_per_day,
            model_key_temp,
            voice_num_phones,
            voice_min_replicas,
            voice_operating_hours
        )
        model_comparison.append({
            "Model": model_data['name'],
            "Monthly Cost": f"CHF {temp_results['total']:,.2f}",
            "Cost per Call": f"CHF {temp_results['cost_per_call']:.2f}",
            "AI Cost": f"CHF {temp_results['ai_total']:.2f}"
        })

    df_models = pd.DataFrame(model_comparison)
    st.dataframe(df_models, use_container_width=True, hide_index=True)

    # Free tier usage
    st.subheader("🎁 Container Apps Free Tier Status")

    container_config = pricing['voice_agent']['container_apps']
    col1, col2, col3 = st.columns(3)

    with col1:
        vcpu_seconds = voice_results.get('vcpu_seconds', 0)
        vcpu_pct = (vcpu_seconds / container_config['free_vcpu_seconds_per_month']) * 100
        vcpu_color = "normal" if vcpu_pct < 100 else "inverse"
        st.metric(
            "vCPU Usage",
            f"{vcpu_pct:.1f}%",
            delta=f"{vcpu_seconds:,.0f} / {container_config['free_vcpu_seconds_per_month']:,} free",
            delta_color=vcpu_color
        )
        if vcpu_pct >= 90:
            st.warning("⚠️ Approaching vCPU limit")

    with col2:
        gb_seconds = voice_results.get('gb_seconds', 0)
        gb_pct = (gb_seconds / container_config['free_gb_seconds_per_month']) * 100
        gb_color = "normal" if gb_pct < 100 else "inverse"
        st.metric(
            "Memory Usage",
            f"{gb_pct:.1f}%",
            delta=f"{gb_seconds:,.0f} / {container_config['free_gb_seconds_per_month']:,} free",
            delta_color=gb_color
        )
        if gb_pct >= 90:
            st.warning("⚠️ Approaching memory limit")

    with col3:
        requests = voice_results.get('requests', 0)
        requests_pct = (requests / container_config['free_requests_per_month']) * 100
        requests_color = "normal" if requests_pct < 100 else "inverse"
        st.metric(
            "Request Usage",
            f"{requests_pct:.1f}%",
            delta=f"{requests:,.0f} / {container_config['free_requests_per_month']:,} free",
            delta_color=requests_color
        )
        if requests_pct >= 90:
            st.warning("⚠️ Approaching request limit")

    # Serverless vs Always-on comparison
    st.subheader("⚡ Serverless vs Always-On Comparison")

    replica_comparison = []
    for replicas in [0, 1, 2, 3]:
        temp_results = calculate_voice_cost(
            voice_minutes_per_call,
            voice_calls_per_day,
            voice_model_key,
            voice_num_phones,
            replicas,
            voice_operating_hours
        )

        config_name = "Serverless (0 replicas)" if replicas == 0 else f"Always-on ({replicas} replica{'s' if replicas > 1 else ''})"
        cold_start = "5-15 sec" if replicas == 0 else "None"

        replica_comparison.append({
            "Configuration": config_name,
            "Monthly Cost": f"CHF {temp_results['total']:.2f}",
            "Container Cost": f"CHF {temp_results['container']:.2f}",
            "Cold Start": cold_start
        })

    df_replicas = pd.DataFrame(replica_comparison)
    st.dataframe(df_replicas, use_container_width=True, hide_index=True)

    # Highlight current selection
    current_config = "Serverless (0 replicas)" if voice_min_replicas == 0 else f"Always-on ({voice_min_replicas} replica{'s' if voice_min_replicas > 1 else ''})"
    st.info(f"💡 Current selection: **{current_config}**")

# ==============================================================================
# TAB 2: EMAIL AGENT
# ==============================================================================

with tab2:
    st.header("📧 Email Agent Costs")

    # Calculate costs
    email_results = calculate_email_cost(
        email_emails_per_day,
        email_polling_interval,
        email_model_key,
        email_enable_rag,
        email_num_pages,
        email_operating_hours
    )

    # Calculate shared blob storage
    blob_results = calculate_blob_storage_cost(email_num_pages, email_enable_rag)

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_with_storage = email_results['total'] + blob_results['cost']
        st.metric("💰 Monthly Cost", f"CHF {total_with_storage:,.2f}")
    with col2:
        st.metric("📧 Cost per Email", f"CHF {email_results['cost_per_email']:.4f}")
    with col3:
        st.metric("📊 Monthly Emails", f"{email_results['emails']:,}")
    with col4:
        if email_enable_rag:
            st.metric("📚 Manual Pages", f"{email_num_pages:,}")
        else:
            st.metric("📚 RAG", "Disabled")

    # Operating hours info
    if email_results['business_hours']:
        hours_def = pricing['email_agent']['operating_hours']['business_hours_definition']
        hours_saved = pricing['email_agent']['operating_hours']['full_time_hours_per_month'] - pricing['email_agent']['operating_hours']['business_hours_per_month']
        st.info(f"⏰ Email agent operates during business hours only ({hours_def}) - Saves {hours_saved:.1f} hours/month vs 24/7")

    # Cost breakdown pie chart
    st.subheader("📊 Cost Distribution")

    email_breakdown = {
        "AI Model (LLM)": email_results['llm'],
        "Azure Functions": email_results['functions'],
        "Blob Storage": blob_results['cost']
    }

    email_breakdown = {k: v for k, v in email_breakdown.items() if v > 0}

    fig = go.Figure(data=[go.Pie(
        labels=list(email_breakdown.keys()),
        values=list(email_breakdown.values()),
        hole=0.3,
        textinfo='label+percent',
        texttemplate='%{label}<br>%{percent}<br>CHF %{value:.2f}'
    )])
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Detailed breakdown
    st.subheader("📋 Detailed Breakdown")
    breakdown_data = []
    for service, cost in email_breakdown.items():
        breakdown_data.append({
            "Service": service,
            "Monthly Cost": f"CHF {cost:.2f}",
            "% of Total": f"{(cost/total_with_storage*100):.1f}%",
            "Cost per Email": f"CHF {(cost/email_results['emails']):.6f}"
        })

    df = pd.DataFrame(breakdown_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Free tier usage
    st.subheader("🎁 Azure Functions Free Tier Status")

    functions_config = pricing['email_agent']['azure_functions']

    col1, col2 = st.columns(2)
    with col1:
        exec_pct = (email_results['checks'] / functions_config['free_executions_per_month']) * 100
        exec_color = "normal" if exec_pct < 100 else "inverse"
        st.metric(
            "Execution Usage",
            f"{exec_pct:.1f}%",
            delta=f"{email_results['checks']:,.0f} / {functions_config['free_executions_per_month']:,} free",
            delta_color=exec_color
        )
        if exec_pct >= 90:
            st.warning("⚠️ Approaching execution limit")

    with col2:
        gb_pct = (email_results['gb_seconds'] / functions_config['free_gb_seconds_per_month']) * 100
        gb_color = "normal" if gb_pct < 100 else "inverse"
        st.metric(
            "Compute Usage",
            f"{gb_pct:.1f}%",
            delta=f"{email_results['gb_seconds']:,.0f} / {functions_config['free_gb_seconds_per_month']:,} free",
            delta_color=gb_color
        )
        if gb_pct >= 90:
            st.warning("⚠️ Approaching compute limit")

    # Model comparison
    st.subheader("🔄 Model Comparison at Current Volume")

    model_comparison = []
    for model_key_temp, model_data in pricing['email_agent']['models'].items():
        temp_results = calculate_email_cost(
            email_emails_per_day,
            email_polling_interval,
            model_key_temp,
            email_enable_rag,
            email_num_pages,
            email_operating_hours
        )
        model_comparison.append({
            "Model": model_data['name'],
            "Monthly Cost": f"CHF {temp_results['total']:.2f}",
            "Cost per Email": f"CHF {temp_results['cost_per_email']:.4f}",
            "LLM Cost": f"CHF {temp_results['llm']:.2f}"
        })

    df_models = pd.DataFrame(model_comparison)
    st.dataframe(df_models, use_container_width=True, hide_index=True)

    # Polling frequency comparison
    st.subheader("⏱️ Polling Frequency Impact")

    polling_comparison = []
    for poll_min in [1, 5, 10, 30, 60]:
        temp_results = calculate_email_cost(
            email_emails_per_day,
            poll_min,
            email_model_key,
            email_enable_rag,
            email_num_pages,
            email_operating_hours
        )
        polling_comparison.append({
            "Check Frequency": f"Every {poll_min} min",
            "Checks/Month": f"{temp_results['checks']:,.0f}",
            "Functions Cost": f"CHF {temp_results['functions']:.2f}",
            "Total Cost": f"CHF {temp_results['total']:.2f}"
        })

    df_polling = pd.DataFrame(polling_comparison)
    st.dataframe(df_polling, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 3: COMBINED TOTAL
# ==============================================================================

with tab3:
    st.header("💰 Combined Monthly Costs")

    # Calculate all costs
    voice_results = calculate_voice_cost(
        voice_minutes_per_call, voice_calls_per_day,
        voice_model_key, voice_num_phones, voice_min_replicas,
        voice_operating_hours
    )

    email_results = calculate_email_cost(
        email_emails_per_day, email_polling_interval,
        email_model_key, email_enable_rag, email_num_pages,
        email_operating_hours
    )

    blob_results = calculate_blob_storage_cost(email_num_pages, email_enable_rag)

    # Totals
    voice_total = voice_results['total']
    email_total = email_results['total']
    blob_total = blob_results['cost']
    combined_total = voice_total + email_total + blob_total

    total_interactions = voice_results['calls'] + email_results['emails']
    avg_cost = combined_total / total_interactions if total_interactions > 0 else 0

    voice_pct = (voice_total / combined_total * 100) if combined_total > 0 else 0
    email_pct = (email_total / combined_total * 100) if combined_total > 0 else 0
    blob_pct = (blob_total / combined_total * 100) if combined_total > 0 else 0

    # Main dashboard
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Total Cost", f"CHF {combined_total:,.2f}")
    with col2:
        st.metric("📞 Voice Agent", f"CHF {voice_total:,.2f}",
                 delta=f"{voice_pct:.0f}% of total")
    with col3:
        st.metric("📧 Email Agent", f"CHF {email_total:,.2f}",
                 delta=f"{email_pct:.0f}% of total")
    with col4:
        st.metric("📊 Avg Cost/Interaction", f"CHF {avg_cost:.3f}")

    # Channel comparison bar chart
    st.subheader("📊 Cost Distribution by Channel")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Voice Agent',
        x=['Voice', 'Email', 'Shared', 'Total'],
        y=[voice_total, 0, 0, voice_total],
        marker_color='#2962ff'
    ))
    fig.add_trace(go.Bar(
        name='Email Agent',
        x=['Voice', 'Email', 'Shared', 'Total'],
        y=[0, email_total, 0, email_total],
        marker_color='#00bfa5'
    ))
    fig.add_trace(go.Bar(
        name='Shared (Blob Storage)',
        x=['Voice', 'Email', 'Shared', 'Total'],
        y=[0, 0, blob_total, blob_total],
        marker_color='#ff6f00'
    ))
    fig.update_layout(
        barmode='stack',
        height=400,
        yaxis_title="Monthly Cost (CHF)",
        xaxis_title="Channel"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Comparison table
    st.subheader("📋 Channel Comparison")

    comparison = pd.DataFrame({
        "Channel": ["Voice Call", "Email", "Shared Storage"],
        "Monthly Volume": [
            f"{voice_results['calls']:,} calls",
            f"{email_results['emails']:,} emails",
            f"{email_num_pages:,} pages" if email_enable_rag else "N/A"
        ],
        "Cost per Interaction": [
            f"CHF {voice_results['cost_per_call']:.2f}",
            f"CHF {email_results['cost_per_email']:.4f}",
            "N/A"
        ],
        "Monthly Cost": [
            f"CHF {voice_total:.2f}",
            f"CHF {email_total:.2f}",
            f"CHF {blob_total:.2f}"
        ],
        "% of Total": [
            f"{voice_pct:.1f}%",
            f"{email_pct:.1f}%",
            f"{blob_pct:.1f}%"
        ]
    })
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    # Combined breakdown pie
    st.subheader("🥧 Combined Cost Breakdown")

    all_costs = {
        "Voice - AI Audio": voice_results['ai_audio'],
        "Voice - AI Text": voice_results['ai_text'],
        "Voice - Phone Calls": voice_results['acs'],
        "Voice - Container": voice_results['container'],
        "Voice - Phone Numbers": voice_results['phone'],
        "Email - AI Model": email_results['llm'],
        "Email - Functions": email_results['functions'],
        "Shared - Blob Storage": blob_total
    }

    all_costs = {k: v for k, v in all_costs.items() if v > 0}

    fig = go.Figure(data=[go.Pie(
        labels=list(all_costs.keys()),
        values=list(all_costs.values()),
        hole=0.4,
        textinfo='label+percent',
        texttemplate='%{label}<br>%{percent}'
    )])
    fig.update_layout(title="All Services Combined", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Cost optimization recommendations
    st.subheader("💡 Cost Optimization Recommendations")

    recommendations = []

    # Voice recommendations
    if voice_model_key == 'gpt_realtime':
        savings = voice_results['ai_total'] * 0.68  # Approximate savings
        recommendations.append({
            "Channel": "Voice",
            "Suggestion": "Switch to GPT-Realtime-mini",
            "Savings": f"CHF {savings:.2f}/month",
            "Impact": "Slightly lower quality, excellent for most calls"
        })

    if voice_min_replicas >= 2:
        temp_results = calculate_voice_cost(
            voice_minutes_per_call, voice_calls_per_day,
            voice_model_key, voice_num_phones, 1,
            voice_operating_hours
        )
        savings = voice_results['total'] - temp_results['total']
        recommendations.append({
            "Channel": "Voice",
            "Suggestion": f"Reduce to 1 replica (from {voice_min_replicas})",
            "Savings": f"CHF {savings:.2f}/month",
            "Impact": "Still no cold starts, maintain availability"
        })

    # Email recommendations
    if email_model_key in ['gpt_5', 'gpt_4o'] and email_results['emails'] > 100:
        temp_results = calculate_email_cost(
            email_emails_per_day, email_polling_interval,
            'gpt_5_mini', email_enable_rag, email_num_pages,
            email_operating_hours
        )
        savings = email_results['total'] - temp_results['total']
        recommendations.append({
            "Channel": "Email",
            "Suggestion": "Switch to GPT-5-mini",
            "Savings": f"CHF {savings:.2f}/month",
            "Impact": "Minimal quality loss for email responses"
        })

    if email_polling_interval == 1 and email_results['emails'] < 1000:
        temp_results = calculate_email_cost(
            email_emails_per_day, 5,
            email_model_key, email_enable_rag, email_num_pages,
            email_operating_hours
        )
        savings = email_results['functions'] - temp_results['functions']
        recommendations.append({
            "Channel": "Email",
            "Suggestion": "Increase polling to 5 minutes",
            "Savings": f"CHF {savings:.2f}/month",
            "Impact": "5-min delay acceptable for email (vs instant)"
        })

    if not email_operating_hours and email_emails_per_day < 100:
        temp_results = calculate_email_cost(
            email_emails_per_day, email_polling_interval,
            email_model_key, email_enable_rag, email_num_pages,
            True
        )
        savings = email_results['functions'] - temp_results['functions']
        recommendations.append({
            "Channel": "Email",
            "Suggestion": "Enable business hours only",
            "Savings": f"CHF {savings:.2f}/month",
            "Impact": "No email processing nights/weekends"
        })

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            with st.expander(f"💰 Recommendation {i}: {rec['Suggestion']}"):
                st.write(f"**Channel:** {rec['Channel']}")
                st.write(f"**Potential Savings:** {rec['Savings']}")
                st.write(f"**Impact:** {rec['Impact']}")
    else:
        st.success("✅ Your configuration is well-optimized!")

    # Cost alerts
    if combined_total > 5000:
        st.error(f"⚠️ Very high monthly cost: CHF {combined_total:,.2f}")
        st.write("Consider implementing optimization recommendations above")
    elif combined_total > 1000:
        st.warning(f"💡 Moderate monthly cost: CHF {combined_total:,.2f}")
        st.write("Review recommendations for potential savings")
    else:
        st.success(f"✅ Economical configuration: CHF {combined_total:,.2f}/month")

    # Export configuration
    st.subheader("📥 Export Configuration")

    config_export = {
        "version": pricing['version'],
        "generated_date": datetime.now().isoformat(),
        "voice_agent": {
            "calls_per_day": voice_calls_per_day,
            "minutes_per_call": voice_minutes_per_call,
            "model": voice_model_names[voice_model_key],
            "phone_numbers": voice_num_phones,
            "min_replicas": voice_min_replicas,
            "monthly_cost": float(voice_total)
        },
        "email_agent": {
            "emails_per_day": email_emails_per_day,
            "polling_minutes": email_polling_interval,
            "business_hours_only": email_operating_hours,
            "model": email_model_names[email_model_key],
            "manual_pages": email_num_pages if email_enable_rag else 0,
            "rag_enabled": email_enable_rag,
            "monthly_cost": float(email_total)
        },
        "shared": {
            "blob_storage_cost": float(blob_total),
            "blob_storage_gb": float(blob_results['storage_gb']) if email_enable_rag else 0
        },
        "totals": {
            "combined_cost": float(combined_total),
            "voice_percentage": float(voice_pct),
            "email_percentage": float(email_pct),
            "total_interactions": int(total_interactions),
            "avg_cost_per_interaction": float(avg_cost)
        }
    }

    st.download_button(
        label="📄 Download Configuration (JSON)",
        data=json.dumps(config_export, indent=2),
        file_name=f"ai_agent_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )

# ==============================================================================
# SIDEBAR: ASSUMPTIONS
# ==============================================================================

st.sidebar.markdown("---")
with st.sidebar.expander("📋 Calculation Assumptions"):
    st.markdown(f"""
    **Deployment Region:**
    - All models: Sweden Central

    **Voice Agent:**
    - Audio: {pricing['voice_agent']['audio_conversion']['tokens_per_minute_audio']} tokens per minute
    - Split: {int(pricing['voice_agent']['audio_conversion']['input_split']*100)}% customer, {int(pricing['voice_agent']['audio_conversion']['output_split']*100)}% AI
    - Text reasoning: {pricing['voice_agent']['models'][voice_model_key]['tokens_per_call']} tokens per call (tool usage)
    - Container: {pricing['voice_agent']['container_apps']['memory_gb_per_replica']} GB memory, {pricing['voice_agent']['container_apps']['vcpu_per_replica']} vCPU per replica
    - Requests: ~2 per call (serverless) or +{30*24*60:,} health checks/month (always-on)

    **Email Agent:**
    - Base email: {pricing['email_agent']['tokens']['base_input_tokens']} tokens
    - RAG context: {pricing['email_agent']['tokens']['rag_additional_tokens']} tokens (~{int(pricing['email_agent']['tokens']['rag_additional_tokens']*0.75)} words ≈ 2-3 pages)
    - Response: {pricing['email_agent']['tokens']['output_tokens']} tokens
    - Function: {pricing['email_agent']['azure_functions']['memory_gb']} GB memory, {pricing['email_agent']['azure_functions']['seconds_per_execution']} sec per check
    - Business hours: {pricing['email_agent']['operating_hours']['business_hours_definition']}

    **Shared Resources:**
    - Blob storage (Hot tier): CHF {pricing['shared']['blob_storage']['hot_tier_per_gb_month']}/GB/month
    - Page size: {pricing['shared']['blob_storage']['mb_per_page']} MB per page
    - Index overhead: {int((pricing['shared']['blob_storage']['index_overhead_multiplier']-1)*100)}% additional storage

    **Prompt Caching:**
    - Not included in calculations (conservative estimates)
    - Available: Voice models have cached_input rates, Email models have cached_input rates
    """)
