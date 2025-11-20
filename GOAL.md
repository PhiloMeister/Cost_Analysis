Prompt for AI Coder: Update Code for New Pricing Data
CRITICAL UPDATE REQUIRED: The pricing_config.json has been updated with correct prices AND new data fields. You must update your entire codebase to use these new fields.

## WHAT CHANGED IN pricing_config.json

### 1. NEW DATA ADDED

**Voice Agent - New Fields:**
- ✅ `requests_per_million`: 0.319 (Container Apps request pricing)
- ✅ `free_requests_per_month`: 2000000 (Free tier for requests)
- ✅ `input_split`: 0.4 (Customer talking percentage)
- ✅ `output_split`: 0.6 (AI talking percentage)
- ✅ `text_cached_input_per_m_tokens` (for all 4 models)
- ✅ `audio_cached_input_per_m_tokens` (for all 4 models)
- ✅ `outbound_per_minute`: 0.0186 (optional ACS service)
- ✅ `call_recording_per_minute`: 0.0013 (optional ACS service)
- ✅ `audio_streaming_per_minute`: 0.0026 (optional ACS service)

**Email Agent - New Fields:**
- ✅ `cached_input_per_m_tokens` (for all 4 models)
- ✅ `operating_hours` section with:
  - `full_time_hours_per_month`: 720
  - `business_hours_per_month`: 227.3
  - `business_hours_definition`: "8:00-18:30, Monday-Friday"
- ✅ `microsoft_365` section with:
  - `business_basic_per_month`: 5.25

**Shared - New Fields:**
- ✅ `read_operations_per_10k`: 0.0042
- ✅ `write_operations_per_10k`: 0.0518
- ✅ `data_retrieval_per_gb`: 0.0

### 2. CORRECTED PRICES

**Voice Agent:**
- ❌ OLD: `idle_per_second`: 0.0000096 → ✅ NEW: 0.0000024
- ❌ OLD: All text model prices fabricated → ✅ NEW: Real prices (e.g., gpt_realtime: 3.19/12.74)

**Email Agent:**
- ❌ OLD: `execution_cost_per_million`: 0.268 → ✅ NEW: 0.160
- ❌ OLD: `compute_cost_per_gb_second`: 0.0000214 → ✅ NEW: 0.000013
- ❌ OLD: `base_input_tokens`: 1000 → ✅ NEW: 500
- ❌ OLD: GPT-5-mini: 1.9897/7.9586 → ✅ NEW: 0.20/1.60
- ❌ OLD: GPT-5: 6.6313/26.5253 → ✅ NEW: 1.00/7.96

**Shared:**
- ❌ OLD: `hot_tier_per_gb_month`: 0.0255 → ✅ NEW: 0.0147
- ❌ OLD: `mb_per_page`: 2.5 → ✅ NEW: 0.5
- ❌ OLD: `index_overhead_multiplier`: 1.3 → ✅ NEW: 1.1

## REQUIRED CODE CHANGES

### CHANGE 1: Add Container Request Cost Calculation

**WHERE:** In `calculate_voice_cost()` function

**ADD THIS CODE** after calculating vCPU and memory costs:
```python
# Container request cost (NEW)
container_config = pricing['voice_agent']['container_apps']

if min_replicas == 0:
    # Serverless: each call generates ~2 requests (connection + messages)
    requests = calls_per_month * 2
else:
    # Always-on: health checks + actual requests
    # Azure does ~1 health check per minute
    health_checks_per_month = 30 * 24 * 60  # 43,200/month
    actual_requests = calls_per_month * 2
    requests = health_checks_per_month + actual_requests

# Apply free tier (NEW field: free_requests_per_month)
if requests > container_config['free_requests_per_month']:
    request_cost = ((requests - container_config['free_requests_per_month']) / 1_000_000) * container_config['requests_per_million']
else:
    request_cost = 0

# Update container cost to include requests
container_cost = vcpu_cost + memory_cost + request_cost
```

**UPDATE RETURN DICT** to include request cost:
```python
return {
    # ... existing fields ...
    'breakdown': {
        # ... existing breakdown ...
        'container_vcpu': vcpu_cost,
        'container_memory': memory_cost,
        'container_requests': request_cost,  # NEW
    }
}
```

### CHANGE 2: Use Audio Split from Config

**WHERE:** In `calculate_voice_cost()` function, audio cost calculation

**FIND:**
```python
# OLD CODE (hardcoded 50/50)
input_tokens = total_audio_tokens * 0.5
output_tokens = total_audio_tokens * 0.5
```

**REPLACE WITH:**
```python
# NEW CODE (from config)
audio_conversion = pricing['voice_agent']['audio_conversion']
input_tokens = total_audio_tokens * audio_conversion['input_split']
output_tokens = total_audio_tokens * audio_conversion['output_split']
```

**RESULT:** Changes from 50/50 split to 40/60 split (customer/AI)

### CHANGE 3: Add Business Hours Support

**WHERE:** In `calculate_email_cost()` function

**FIND:**
```python
# OLD CODE (always 720 hours)
checks_per_month = (30 * 24 * 60) / polling_minutes
```

**REPLACE WITH:**
```python
# NEW CODE (configurable hours)
operating_hours = pricing['email_agent']['operating_hours']

if business_hours_only:
    hours_per_month = operating_hours['business_hours_per_month']
else:
    hours_per_month = operating_hours['full_time_hours_per_month']

checks_per_month = (hours_per_month * 60) / polling_minutes
```

**ENSURE** the `business_hours_only` parameter is passed from the UI checkbox.

### CHANGE 4: Update Blob Storage Calculation

**WHERE:** In `calculate_blob_storage_cost()` function

**VERIFY** it uses correct config values:
```python
blob_config = pricing['shared']['blob_storage']

# These values changed:
# mb_per_page: 2.5 → 0.5 (now in config)
# index_overhead_multiplier: 1.3 → 1.1 (now in config)

storage_gb = (num_pages * blob_config['mb_per_page'] / 1024) * blob_config['index_overhead_multiplier']
blob_cost = storage_gb * blob_config['hot_tier_per_gb_month']
```

**The calculation itself doesn't change, but the VALUES from config changed significantly.**

### CHANGE 5: Add RAG Context Info Tooltip

**WHERE:** In email agent sidebar, where RAG is enabled

**ADD THIS** after the num_pages input:
```python
if email_enable_rag:
    email_num_pages = st.sidebar.number_input(...)
    
    # Show storage estimate
    blob_config = pricing['shared']['blob_storage']
    storage_gb = (email_num_pages * blob_config['mb_per_page'] / 1024) * blob_config['index_overhead_multiplier']
    st.sidebar.caption(f"≈ {storage_gb:.2f} GB storage needed")
    
    # NEW: Show RAG context explanation
    rag_tokens = pricing['email_agent']['tokens']['rag_additional_tokens']
    rag_words = int(rag_tokens * 0.75)
    st.sidebar.info(f"💡 RAG adds {rag_tokens} tokens context (~{rag_words} words ≈ 2-3 pages of manual text per email)")
```

### CHANGE 6: Update Assumptions Display

**WHERE:** In sidebar expander "📋 Calculation Assumptions"

**UPDATE** to reflect new data:
```python
with st.sidebar.expander("📋 Calculation Assumptions"):
    st.markdown(f"""
    **Deployment Region:**
    - All models: Sweden Central
    
    **Voice Agent:**
    - Audio: {pricing['voice_agent']['audio_conversion']['tokens_per_minute_audio']} tokens per minute
    - Split: {int(pricing['voice_agent']['audio_conversion']['input_split']*100)}% customer, {int(pricing['voice_agent']['audio_conversion']['output_split']*100)}% AI
    - Text reasoning: {pricing['voice_agent']['models']['gpt_realtime_mini']['tokens_per_call']} tokens per call
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
```

### CHANGE 7: Add Container Request Cost to Breakdown

**WHERE:** In TAB 1 (Voice Agent), detailed breakdown table

**UPDATE** the voice_breakdown dict to include request cost:
```python
voice_breakdown = {
    "AI Audio Processing": voice_results['ai_audio'],
    "AI Text Reasoning": voice_results['ai_text'],
    "Phone Calls (ACS)": voice_results['acs'],
    "Container - Compute": voice_results['breakdown']['container_vcpu'] + voice_results['breakdown']['container_memory'],
    "Container - Requests": voice_results['breakdown']['container_requests'],  # NEW
    "Phone Numbers": voice_results['phone']
}
```

**OR** if you want more detail:
```python
voice_breakdown = {
    "AI Audio Processing": voice_results['ai_audio'],
    "AI Text Reasoning": voice_results['ai_text'],
    "Phone Calls (ACS)": voice_results['acs'],
    "Container - vCPU": voice_results['breakdown']['container_vcpu'],
    "Container - Memory": voice_results['breakdown']['container_memory'],
    "Container - Requests": voice_results['breakdown']['container_requests'],  # NEW
    "Phone Numbers": voice_results['phone']
}
```

### CHANGE 8: Update Business Hours Info Display

**WHERE:** In TAB 2 (Email Agent), after main metrics

**ADD THIS** to show when business hours are enabled:
```python
# Operating hours info
if email_results['business_hours']:
    hours_def = pricing['email_agent']['operating_hours']['business_hours_definition']
    hours_saved = pricing['email_agent']['operating_hours']['full_time_hours_per_month'] - pricing['email_agent']['operating_hours']['business_hours_per_month']
    st.info(f"⏰ Email agent operates during business hours only ({hours_def}) - Saves {hours_saved:.1f} hours/month vs 24/7")
```

### CHANGE 9: Verify Container Idle Cost Uses Correct Rate

**WHERE:** In `calculate_voice_cost()`, always-on container calculation

**VERIFY** your code uses the FLAT idle rate:
```python
# Always-on: pay 24/7
if min_replicas > 0:
    # Active time costs
    active_seconds = calls_per_month * (minutes_per_call * 60)
    active_cost = min_replicas * active_seconds * (
        (container_config['vcpu_per_replica'] * container_config['vcpu_active_per_second']) +
        (container_config['memory_gb_per_replica'] * container_config['memory_gb_active_per_second'])
    )
    
    # Idle time costs (FLAT RATE for both vCPU + memory)
    idle_seconds = container_config['seconds_per_month'] - active_seconds
    idle_cost = min_replicas * idle_seconds * container_config['idle_per_second']  # This is 0.0000024 (flat rate)
    
    container_cost = active_cost + idle_cost
```

**CRITICAL:** `idle_per_second` = 0.0000024 is a FLAT rate for BOTH vCPU and memory combined when idle, NOT per component.

### CHANGE 10: Add Free Tier Display for Container Requests

**WHERE:** In TAB 1 (Voice Agent), after cost breakdown

**ADD THIS** section to show free tier usage:
```python
# Free tier usage
st.subheader("🎁 Container Apps Free Tier Status")

container_config = pricing['voice_agent']['container_apps']
col1, col2, col3 = st.columns(3)

with col1:
    vcpu_seconds = voice_results.get('vcpu_seconds', 0)  # You'll need to return this from calculate_voice_cost
    vcpu_pct = (vcpu_seconds / container_config['free_vcpu_seconds_per_month']) * 100
    st.metric(
        "vCPU Usage",
        f"{vcpu_pct:.1f}%",
        delta=f"{vcpu_seconds:,.0f} / {container_config['free_vcpu_seconds_per_month']:,} free"
    )

with col2:
    gb_seconds = voice_results.get('gb_seconds', 0)  # You'll need to return this
    gb_pct = (gb_seconds / container_config['free_gb_seconds_per_month']) * 100
    st.metric(
        "Memory Usage",
        f"{gb_pct:.1f}%",
        delta=f"{gb_seconds:,.0f} / {container_config['free_gb_seconds_per_month']:,} free"
    )

with col3:
    requests = voice_results.get('requests', 0)  # NEW - you'll need to return this
    requests_pct = (requests / container_config['free_requests_per_month']) * 100
    st.metric(
        "Request Usage",
        f"{requests_pct:.1f}%",
        delta=f"{requests:,.0f} / {container_config['free_requests_per_month']:,} free"
    )
```

**UPDATE** `calculate_voice_cost()` to return these values:
```python
return {
    # ... existing fields ...
    'vcpu_seconds': vcpu_seconds,
    'gb_seconds': gb_seconds,
    'requests': requests,  # NEW
}
```

## SUMMARY OF NEW DATA FIELDS TO USE

### Voice Agent - NEW fields you must use:
1. ✅ `requests_per_million` - Container request pricing
2. ✅ `free_requests_per_month` - Free tier for requests
3. ✅ `input_split` - Audio input percentage (0.4)
4. ✅ `output_split` - Audio output percentage (0.6)
5. ✅ `text_cached_input_per_m_tokens` - All 4 models (future use)
6. ✅ `audio_cached_input_per_m_tokens` - All 4 models (future use)

### Email Agent - NEW fields you must use:
1. ✅ `operating_hours.business_hours_per_month` - 227.3 hours
2. ✅ `operating_hours.full_time_hours_per_month` - 720 hours
3. ✅ `operating_hours.business_hours_definition` - Display string
4. ✅ `cached_input_per_m_tokens` - All 4 models (future use)

### Shared - NEW fields (informational only, don't need to calculate):
1. ✅ `read_operations_per_10k` - For reference
2. ✅ `write_operations_per_10k` - For reference
3. ✅ `data_retrieval_per_gb` - For reference
