# Technical Documentation: AI Agent Cost Calculator
**Version:** 1.1.0
**Last Updated:** 2025-11-20
**Currency:** CHF (Swiss Francs)
**Region:** Sweden Central

---

## Table of Contents
1. [Voice Agent Calculations](#1-voice-agent-calculations)
2. [Email Agent Calculations](#2-email-agent-calculations)
3. [Shared Blob Storage](#3-shared-blob-storage)
4. [Free Tier Handling](#4-free-tier-handling)
5. [Real Examples](#5-real-examples)
6. [Validation Checks](#6-validation-checks)
7. [Pricing Reference](#7-pricing-reference)

---

## 1. Voice Agent Calculations

### 1.1 Container Apps Costs

#### Serverless Mode (min_replicas = 0)

**Formula:**
```
Total Container Cost = vCPU Cost + Memory Cost + Request Cost
```

**Step-by-Step:**

1. **Calculate Call Seconds:**
   ```
   call_seconds = calls_per_month × minutes_per_call × 60
   ```

2. **vCPU Cost:**
   ```
   vcpu_seconds = call_seconds

   IF vcpu_seconds > FREE_VCPU_SECONDS (180,000):
       billable_vcpu_seconds = vcpu_seconds - 180,000
       vcpu_cost = billable_vcpu_seconds × 0.5 vCPU × CHF 0.0000192/sec
   ELSE:
       vcpu_cost = 0
   ```

3. **Memory Cost:**
   ```
   gb_seconds = call_seconds × 1.0 GB

   IF gb_seconds > FREE_GB_SECONDS (360,000):
       billable_gb_seconds = gb_seconds - 360,000
       memory_cost = billable_gb_seconds × CHF 0.0000024/GB-sec
   ELSE:
       memory_cost = 0
   ```

4. **Request Cost:**
   ```
   requests = calls_per_month × 2  (connection + messages)

   IF requests > FREE_REQUESTS (2,000,000):
       billable_requests = requests - 2,000,000
       request_cost = (billable_requests ÷ 1,000,000) × CHF 0.319
   ELSE:
       request_cost = 0
   ```

**Example (50 calls/day, 5 min/call):**
```
calls_per_month = 50 × 30 = 1,500
call_seconds = 1,500 × 5 × 60 = 450,000 seconds

vCPU:
  vcpu_seconds = 450,000
  billable = 450,000 - 180,000 = 270,000
  cost = 270,000 × 0.5 × 0.0000192 = CHF 2.592

Memory:
  gb_seconds = 450,000 × 1.0 = 450,000
  billable = 450,000 - 360,000 = 90,000
  cost = 90,000 × 0.0000024 = CHF 0.216

Requests:
  requests = 1,500 × 2 = 3,000
  billable = 3,000 - 2,000,000 = 0 (within free tier)
  cost = CHF 0.00

Total Container Cost = 2.592 + 0.216 + 0.00 = CHF 2.808
```

#### Always-On Mode (min_replicas ≥ 1)

**Formula:**
```
Total Container Cost = Active Cost + Idle Cost + Request Cost
```

**Step-by-Step:**

1. **Calculate Active and Idle Seconds:**
   ```
   monthly_seconds = 2,592,000  (30 days × 24 hours × 60 min × 60 sec)
   active_seconds = calls_per_month × minutes_per_call × 60
   idle_seconds = monthly_seconds - active_seconds
   ```

2. **Active Cost (per replica):**
   ```
   active_cost_per_replica = active_seconds × (
       (0.5 vCPU × CHF 0.0000192/sec) +
       (1.0 GB × CHF 0.0000024/sec)
   )

   total_active_cost = min_replicas × active_cost_per_replica
   ```

3. **Idle Cost (FLAT RATE per replica):**
   ```
   idle_cost_per_replica = idle_seconds × CHF 0.0000024/sec

   total_idle_cost = min_replicas × idle_cost_per_replica

   NOTE: Idle rate (0.0000024) is a FLAT rate for BOTH vCPU + memory combined
   ```

4. **Request Cost:**
   ```
   health_checks_per_month = 30 × 24 × 60 = 43,200
   actual_requests = calls_per_month × 2
   total_requests = health_checks_per_month + actual_requests

   IF total_requests > FREE_REQUESTS (2,000,000):
       billable_requests = total_requests - 2,000,000
       request_cost = (billable_requests ÷ 1,000,000) × CHF 0.319
   ELSE:
       request_cost = 0
   ```

5. **Track Metrics for Free Tier Display:**
   ```
   vcpu_seconds = min_replicas × monthly_seconds
   gb_seconds = min_replicas × monthly_seconds × 1.0 GB
   ```

**Example (50 calls/day, 5 min/call, 1 replica):**
```
calls_per_month = 1,500
active_seconds = 1,500 × 5 × 60 = 450,000
idle_seconds = 2,592,000 - 450,000 = 2,142,000

Active Cost:
  per_replica = 450,000 × ((0.5 × 0.0000192) + (1.0 × 0.0000024))
              = 450,000 × (0.0000096 + 0.0000024)
              = 450,000 × 0.000012
              = CHF 5.40
  total = 1 × 5.40 = CHF 5.40

Idle Cost:
  per_replica = 2,142,000 × 0.0000024 = CHF 5.141
  total = 1 × 5.141 = CHF 5.141

Requests:
  health_checks = 43,200
  actual = 1,500 × 2 = 3,000
  total_requests = 43,200 + 3,000 = 46,200
  billable = 46,200 - 2,000,000 = 0 (within free tier)
  cost = CHF 0.00

Total Container Cost = 5.40 + 5.141 + 0.00 = CHF 10.541
```

### 1.2 Audio Processing Costs

**Formula:**
```
Audio Cost = Input Token Cost + Output Token Cost
```

**Conversion Factor:**
```
Audio: 2,000 tokens per minute
Split: 40% customer (input), 60% AI (output)
```

**Step-by-Step:**

1. **Calculate Total Audio Tokens:**
   ```
   total_minutes = calls_per_month × minutes_per_call
   total_audio_tokens = total_minutes × 2,000
   ```

2. **Split Input/Output:**
   ```
   input_tokens = total_audio_tokens × 0.4
   output_tokens = total_audio_tokens × 0.6
   ```

3. **Apply Model Pricing (per million tokens):**
   ```
   audio_input_cost = (input_tokens ÷ 1,000,000) × model.audio_input_per_m_tokens
   audio_output_cost = (output_tokens ÷ 1,000,000) × model.audio_output_per_m_tokens
   ```

**Example (GPT-realtime-mini, 1,500 calls, 5 min each):**
```
Model Pricing:
  audio_input: CHF 7.96 per 1M tokens
  audio_output: CHF 15.92 per 1M tokens

Calculation:
  total_minutes = 1,500 × 5 = 7,500
  total_audio_tokens = 7,500 × 2,000 = 15,000,000

  input_tokens = 15,000,000 × 0.4 = 6,000,000
  output_tokens = 15,000,000 × 0.6 = 9,000,000

  input_cost = (6,000,000 ÷ 1,000,000) × 7.96 = 6 × 7.96 = CHF 47.76
  output_cost = (9,000,000 ÷ 1,000,000) × 15.92 = 9 × 15.92 = CHF 143.28

Total Audio Cost = 47.76 + 143.28 = CHF 191.04
```

### 1.3 Text Reasoning Costs

**Formula:**
```
Text Cost = Input Token Cost + Output Token Cost
```

**Assumptions:**
```
Text Tokens per Call: 2,000
Split: 70% input, 30% output
```

**Step-by-Step:**

1. **Calculate Token Distribution:**
   ```
   text_tokens_per_call = 2,000
   text_input_tokens_per_call = 2,000 × 0.7 = 1,400
   text_output_tokens_per_call = 2,000 × 0.3 = 600
   ```

2. **Calculate Total Tokens:**
   ```
   total_text_input = calls_per_month × 1,400
   total_text_output = calls_per_month × 600
   ```

3. **Apply Model Pricing:**
   ```
   text_input_cost = (total_text_input ÷ 1,000,000) × model.text_input_per_m_tokens
   text_output_cost = (total_text_output ÷ 1,000,000) × model.text_output_per_m_tokens
   ```

**Example (GPT-realtime-mini, 1,500 calls):**
```
Model Pricing:
  text_input: CHF 0.48 per 1M tokens
  text_output: CHF 1.92 per 1M tokens

Calculation:
  total_input = 1,500 × 1,400 = 2,100,000
  total_output = 1,500 × 600 = 900,000

  input_cost = (2,100,000 ÷ 1,000,000) × 0.48 = 2.1 × 0.48 = CHF 1.008
  output_cost = (900,000 ÷ 1,000,000) × 1.92 = 0.9 × 1.92 = CHF 1.728

Total Text Cost = 1.008 + 1.728 = CHF 2.736
```

### 1.4 ACS (Azure Communication Services) Costs

**Formula:**
```
ACS Cost = Phone Number Cost + Inbound Call Cost
```

**Step-by-Step:**

1. **Phone Number Cost:**
   ```
   phone_cost = num_phone_numbers × CHF 0.80/month
   ```

2. **Inbound Call Cost:**
   ```
   total_minutes = calls_per_month × minutes_per_call
   call_cost = total_minutes × CHF 0.0080/minute
   ```

**Example (1 phone, 1,500 calls, 5 min each):**
```
phone_cost = 1 × 0.80 = CHF 0.80

total_minutes = 1,500 × 5 = 7,500
call_cost = 7,500 × 0.0080 = CHF 60.00

Total ACS Cost = 0.80 + 60.00 = CHF 60.80
```

### 1.5 Voice Agent Total

**Formula:**
```
Total Voice Cost = Phone Cost + ACS Call Cost + Container Cost + Audio Cost + Text Cost
```

**Complete Example (Serverless, GPT-realtime-mini, 50 calls/day, 5 min, 1 phone):**
```
Phone:          CHF 0.80
ACS Calls:      CHF 60.00
Container:      CHF 2.808
Audio:          CHF 191.04
Text:           CHF 2.736

TOTAL:          CHF 257.384
Cost per call:  CHF 257.384 ÷ 1,500 = CHF 0.172
```

---

## 2. Email Agent Calculations

### 2.1 Azure Functions Costs

**Formula:**
```
Functions Cost = Execution Cost + Compute Cost
```

#### Operating Hours Logic

**Business Hours:**
```
hours_per_month = 227.3
  (10.5 hours/day × 5 days/week × 4.33 weeks/month)
  (8:00-18:30, Monday-Friday)
```

**24/7 Hours:**
```
hours_per_month = 720
  (30 days × 24 hours)
```

#### Execution Cost

**Step-by-Step:**

1. **Calculate Checks per Month:**
   ```
   checks_per_month = (hours_per_month × 60) ÷ polling_interval_minutes
   ```

2. **Apply Free Tier:**
   ```
   IF checks_per_month > FREE_EXECUTIONS (1,000,000):
       billable_executions = checks_per_month - 1,000,000
       execution_cost = (billable_executions ÷ 1,000,000) × CHF 0.160
   ELSE:
       execution_cost = 0
   ```

**Example (50 emails/day, 1-min polling, 24/7):**
```
hours_per_month = 720
checks_per_month = (720 × 60) ÷ 1 = 43,200

billable = 43,200 - 1,000,000 = 0 (within free tier)
execution_cost = CHF 0.00
```

#### Compute Cost

**Step-by-Step:**

1. **Calculate GB-Seconds:**
   ```
   execution_seconds = checks_per_month × 3 seconds
   gb_seconds = execution_seconds × 0.5 GB
   ```

2. **Apply Free Tier:**
   ```
   IF gb_seconds > FREE_GB_SECONDS (400,000):
       billable_gb_seconds = gb_seconds - 400,000
       compute_cost = billable_gb_seconds × CHF 0.000013
   ELSE:
       compute_cost = 0
   ```

**Example (43,200 checks):**
```
execution_seconds = 43,200 × 3 = 129,600
gb_seconds = 129,600 × 0.5 = 64,800

billable = 64,800 - 400,000 = 0 (within free tier)
compute_cost = CHF 0.00
```

### 2.2 LLM (Language Model) Costs

**Formula:**
```
LLM Cost = Input Token Cost + Output Token Cost
```

**Token Distribution:**
```
Base Input Tokens: 500
RAG Additional Tokens: 1,500 (if enabled)
Output Tokens: 500
```

**Step-by-Step:**

1. **Calculate Input Tokens per Email:**
   ```
   IF RAG enabled:
       input_tokens_per_email = 500 + 1,500 = 2,000
   ELSE:
       input_tokens_per_email = 500
   ```

2. **Calculate Total Tokens:**
   ```
   emails_per_month = emails_per_day × 30
   total_input_tokens = emails_per_month × input_tokens_per_email
   total_output_tokens = emails_per_month × 500
   ```

3. **Apply Model Pricing (per million tokens):**
   ```
   input_cost = (total_input_tokens ÷ 1,000,000) × model.input_per_m_tokens
   output_cost = (total_output_tokens ÷ 1,000,000) × model.output_per_m_tokens
   ```

**Example (GPT-5-mini, 50 emails/day, RAG enabled):**
```
Model Pricing:
  input: CHF 0.20 per 1M tokens
  output: CHF 1.60 per 1M tokens

Calculation:
  emails_per_month = 50 × 30 = 1,500
  input_tokens_per_email = 500 + 1,500 = 2,000

  total_input = 1,500 × 2,000 = 3,000,000
  total_output = 1,500 × 500 = 750,000

  input_cost = (3,000,000 ÷ 1,000,000) × 0.20 = 3 × 0.20 = CHF 0.60
  output_cost = (750,000 ÷ 1,000,000) × 1.60 = 0.75 × 1.60 = CHF 1.20

Total LLM Cost = 0.60 + 1.20 = CHF 1.80
```

### 2.3 Email Agent Total

**Formula:**
```
Total Email Cost = Functions Cost + LLM Cost + Blob Storage Cost
```

**Complete Example (GPT-5-mini, 50 emails/day, 1-min polling, RAG with 5000 pages):**
```
Functions:      CHF 0.00 (within free tier)
LLM:            CHF 1.80
Blob Storage:   CHF 0.084 (see section 3)

TOTAL:          CHF 1.884
Cost per email: CHF 1.884 ÷ 1,500 = CHF 0.001256
```

---

## 3. Shared Blob Storage

**Formula:**
```
Blob Cost = Storage GB × CHF 0.0147/GB/month
```

**Step-by-Step:**

1. **Calculate Base Storage:**
   ```
   base_storage_mb = num_pages × 0.5 MB/page
   base_storage_gb = base_storage_mb ÷ 1,024
   ```

2. **Apply Index Overhead:**
   ```
   total_storage_gb = base_storage_gb × 1.1
   ```

3. **Calculate Cost:**
   ```
   blob_cost = total_storage_gb × CHF 0.0147
   ```

**Example (5,000 pages):**
```
base_mb = 5,000 × 0.5 = 2,500 MB
base_gb = 2,500 ÷ 1,024 = 2.441 GB

total_gb = 2.441 × 1.1 = 2.685 GB

blob_cost = 2.685 × 0.0147 = CHF 0.0395 ≈ CHF 0.04
```

**NOTE:** This cost is counted ONCE and shared between both agents.

---

## 4. Free Tier Handling

### 4.1 Container Apps Free Tiers

| Resource | Free Tier | Cost When Exceeded |
|----------|-----------|-------------------|
| vCPU-seconds | 180,000/month | CHF 0.0000192 per vCPU-second × 0.5 vCPU |
| GB-seconds | 360,000/month | CHF 0.0000024 per GB-second × 1.0 GB |
| Requests | 2,000,000/month | CHF 0.319 per million requests |

**Free Tier Percentage Calculation:**
```
vcpu_pct = (vcpu_seconds ÷ 180,000) × 100%
memory_pct = (gb_seconds ÷ 360,000) × 100%
request_pct = (requests ÷ 2,000,000) × 100%
```

**Warning Thresholds:**
- 🟢 < 90%: Normal (green)
- 🟡 90-99%: Warning displayed
- 🔴 ≥ 100%: Exceeding free tier (red, costs apply)

### 4.2 Azure Functions Free Tiers

| Resource | Free Tier | Cost When Exceeded |
|----------|-----------|-------------------|
| Executions | 1,000,000/month | CHF 0.160 per million |
| GB-seconds | 400,000/month | CHF 0.000013 per GB-second |

**Free Tier Percentage Calculation:**
```
execution_pct = (checks_per_month ÷ 1,000,000) × 100%
compute_pct = (gb_seconds ÷ 400,000) × 100%
```

**Warning Thresholds:**
- 🟢 < 90%: Normal (green)
- 🟡 90-99%: Warning displayed
- 🔴 ≥ 100%: Exceeding free tier (red, costs apply)

### 4.3 Edge Cases

**Zero Values:**
- If `calls_per_month = 0`: All costs = 0, avoid division by zero for cost_per_call
- If `emails_per_month = 0`: All costs = 0, avoid division by zero for cost_per_email
- If `num_pages = 0` or `RAG disabled`: blob_cost = 0

**Exceeding Free Tiers:**
- Always subtract free tier amount BEFORE applying pricing
- Never charge for usage within free tier
- Show clear warnings when approaching limits

---

## 5. Real Examples

### 5.1 Small Business Preset

**Configuration:**
- Voice: 20 calls/day, 5 min/call, GPT-realtime-mini, 1 phone, serverless
- Email: 30 emails/day, 5-min polling, GPT-5-mini, 2000 pages RAG, 24/7

#### Voice Agent Calculation:

```
Calls: 20 × 30 = 600 calls/month
Minutes: 600 × 5 = 3,000 minutes

Container (Serverless):
  call_seconds = 600 × 5 × 60 = 180,000

  vCPU: 180,000 - 180,000 = 0 (FREE TIER)
  cost = CHF 0.00

  Memory: 180,000 × 1.0 = 180,000 GB-sec
         180,000 - 360,000 = 0 (FREE TIER)
  cost = CHF 0.00

  Requests: 600 × 2 = 1,200
           1,200 - 2,000,000 = 0 (FREE TIER)
  cost = CHF 0.00

  Total Container = CHF 0.00 ✓

Audio (GPT-realtime-mini: 7.96 input, 15.92 output):
  tokens = 3,000 × 2,000 = 6,000,000
  input = 6,000,000 × 0.4 = 2,400,000
  output = 6,000,000 × 0.6 = 3,600,000

  input_cost = (2.4M ÷ 1M) × 7.96 = CHF 19.104
  output_cost = (3.6M ÷ 1M) × 15.92 = CHF 57.312
  Total Audio = CHF 76.416

Text (GPT-realtime-mini: 0.48 input, 1.92 output):
  input = 600 × 1,400 = 840,000
  output = 600 × 600 = 360,000

  input_cost = (0.84M ÷ 1M) × 0.48 = CHF 0.403
  output_cost = (0.36M ÷ 1M) × 1.92 = CHF 0.691
  Total Text = CHF 1.094

ACS:
  phone = 1 × 0.80 = CHF 0.80
  calls = 3,000 × 0.0080 = CHF 24.00
  Total ACS = CHF 24.80

VOICE TOTAL = 0.00 + 76.416 + 1.094 + 24.80 = CHF 102.31
```

#### Email Agent Calculation:

```
Emails: 30 × 30 = 900 emails/month
Polling: (720 × 60) ÷ 5 = 8,640 checks/month

Functions:
  executions = 8,640 - 1,000,000 = 0 (FREE TIER)
  execution_cost = CHF 0.00

  gb_seconds = 8,640 × 3 × 0.5 = 12,960
              12,960 - 400,000 = 0 (FREE TIER)
  compute_cost = CHF 0.00

  Total Functions = CHF 0.00 ✓

LLM (GPT-5-mini: 0.20 input, 1.60 output):
  input = 900 × 2,000 = 1,800,000
  output = 900 × 500 = 450,000

  input_cost = (1.8M ÷ 1M) × 0.20 = CHF 0.36
  output_cost = (0.45M ÷ 1M) × 1.60 = CHF 0.72
  Total LLM = CHF 1.08

Blob Storage (2000 pages):
  gb = (2000 × 0.5 ÷ 1024) × 1.1 = 1.074 GB
  cost = 1.074 × 0.0147 = CHF 0.016

EMAIL TOTAL = 0.00 + 1.08 + 0.016 = CHF 1.096
```

#### Combined Total:
```
Voice:      CHF 102.31
Email:      CHF 1.096
Blob:       (included in email)

TOTAL:      CHF 103.406 ≈ CHF 103.41/month
Avg/interaction: CHF 103.41 ÷ 1,500 = CHF 0.069
```

### 5.2 Medium Business Preset

**Configuration:**
- Voice: 100 calls/day, 7 min/call, GPT-4o Realtime, 2 phones, 1 replica
- Email: 150 emails/day, 1-min polling, GPT-5-mini, 10000 pages RAG, 24/7

#### Voice Agent Calculation:

```
Calls: 100 × 30 = 3,000 calls/month
Minutes: 3,000 × 7 = 21,000 minutes

Container (1 Replica):
  active_seconds = 3,000 × 7 × 60 = 1,260,000
  idle_seconds = 2,592,000 - 1,260,000 = 1,332,000

  active_cost = 1 × 1,260,000 × (0.5 × 0.0000192 + 1.0 × 0.0000024)
              = 1,260,000 × 0.000012
              = CHF 15.12

  idle_cost = 1 × 1,332,000 × 0.0000024
            = CHF 3.197

  requests = 43,200 + (3,000 × 2) = 49,200
            49,200 - 2,000,000 = 0 (FREE TIER)
  request_cost = CHF 0.00

  Total Container = CHF 18.317

Audio (GPT-4o Realtime: 31.8341 input, 63.6680 output):
  tokens = 21,000 × 2,000 = 42,000,000
  input = 42M × 0.4 = 16,800,000
  output = 42M × 0.6 = 25,200,000

  input_cost = (16.8M ÷ 1M) × 31.8341 = CHF 534.813
  output_cost = (25.2M ÷ 1M) × 63.6680 = CHF 1,604.434
  Total Audio = CHF 2,139.247

Text (GPT-4o Realtime: 3.9793 input, 15.9170 output):
  input = 3,000 × 1,400 = 4,200,000
  output = 3,000 × 600 = 1,800,000

  input_cost = (4.2M ÷ 1M) × 3.9793 = CHF 16.713
  output_cost = (1.8M ÷ 1M) × 15.9170 = CHF 28.651
  Total Text = CHF 45.364

ACS:
  phone = 2 × 0.80 = CHF 1.60
  calls = 21,000 × 0.0080 = CHF 168.00
  Total ACS = CHF 169.60

VOICE TOTAL = 18.317 + 2,139.247 + 45.364 + 169.60 = CHF 2,372.53
```

#### Email Agent Calculation:

```
Emails: 150 × 30 = 4,500 emails/month
Polling: (720 × 60) ÷ 1 = 43,200 checks/month

Functions:
  executions = 43,200 - 1,000,000 = 0 (FREE TIER)
  execution_cost = CHF 0.00

  gb_seconds = 43,200 × 3 × 0.5 = 64,800
              64,800 - 400,000 = 0 (FREE TIER)
  compute_cost = CHF 0.00

  Total Functions = CHF 0.00 ✓

LLM (GPT-5-mini: 0.20 input, 1.60 output):
  input = 4,500 × 2,000 = 9,000,000
  output = 4,500 × 500 = 2,250,000

  input_cost = (9M ÷ 1M) × 0.20 = CHF 1.80
  output_cost = (2.25M ÷ 1M) × 1.60 = CHF 3.60
  Total LLM = CHF 5.40

Blob Storage (10000 pages):
  gb = (10000 × 0.5 ÷ 1024) × 1.1 = 5.371 GB
  cost = 5.371 × 0.0147 = CHF 0.079

EMAIL TOTAL = 0.00 + 5.40 + 0.079 = CHF 5.479
```

#### Combined Total:
```
Voice:      CHF 2,372.53
Email:      CHF 5.479
Blob:       (included in email)

TOTAL:      CHF 2,378.01/month
Avg/interaction: CHF 2,378.01 ÷ 7,500 = CHF 0.317
```

### 5.3 Enterprise Preset

**Configuration:**
- Voice: 300 calls/day, 10 min/call, GPT-4o Realtime, 5 phones, 3 replicas
- Email: 500 emails/day, 1-min polling, GPT-5, 30000 pages RAG, 24/7

#### Voice Agent Calculation:

```
Calls: 300 × 30 = 9,000 calls/month
Minutes: 9,000 × 10 = 90,000 minutes

Container (3 Replicas):
  active_seconds = 9,000 × 10 × 60 = 5,400,000
  idle_seconds = 2,592,000 - 1,800,000 = 792,000 per replica

  active_cost = 3 × 1,800,000 × 0.000012 = CHF 64.80
  idle_cost = 3 × 792,000 × 0.0000024 = CHF 5.702

  requests = 43,200 + (9,000 × 2) = 61,200
            61,200 - 2,000,000 = 0 (FREE TIER)
  request_cost = CHF 0.00

  Total Container = CHF 70.502

Audio (GPT-4o Realtime: 31.8341 input, 63.6680 output):
  tokens = 90,000 × 2,000 = 180,000,000
  input = 180M × 0.4 = 72,000,000
  output = 180M × 0.6 = 108,000,000

  input_cost = (72M ÷ 1M) × 31.8341 = CHF 2,292.055
  output_cost = (108M ÷ 1M) × 63.6680 = CHF 6,876.144
  Total Audio = CHF 9,168.199

Text (GPT-4o Realtime: 3.9793 input, 15.9170 output):
  input = 9,000 × 1,400 = 12,600,000
  output = 9,000 × 600 = 5,400,000

  input_cost = (12.6M ÷ 1M) × 3.9793 = CHF 50.139
  output_cost = (5.4M ÷ 1M) × 15.9170 = CHF 85.952
  Total Text = CHF 136.091

ACS:
  phone = 5 × 0.80 = CHF 4.00
  calls = 90,000 × 0.0080 = CHF 720.00
  Total ACS = CHF 724.00

VOICE TOTAL = 70.502 + 9,168.199 + 136.091 + 724.00 = CHF 10,098.79
```

#### Email Agent Calculation:

```
Emails: 500 × 30 = 15,000 emails/month
Polling: (720 × 60) ÷ 1 = 43,200 checks/month

Functions:
  executions = 43,200 - 1,000,000 = 0 (FREE TIER)
  execution_cost = CHF 0.00

  gb_seconds = 43,200 × 3 × 0.5 = 64,800
              64,800 - 400,000 = 0 (FREE TIER)
  compute_cost = CHF 0.00

  Total Functions = CHF 0.00 ✓

LLM (GPT-5: 1.00 input, 7.96 output):
  input = 15,000 × 2,000 = 30,000,000
  output = 15,000 × 500 = 7,500,000

  input_cost = (30M ÷ 1M) × 1.00 = CHF 30.00
  output_cost = (7.5M ÷ 1M) × 7.96 = CHF 59.70
  Total LLM = CHF 89.70

Blob Storage (30000 pages):
  gb = (30000 × 0.5 ÷ 1024) × 1.1 = 16.113 GB
  cost = 16.113 × 0.0147 = CHF 0.237

EMAIL TOTAL = 0.00 + 89.70 + 0.237 = CHF 89.937
```

#### Combined Total:
```
Voice:      CHF 10,098.79
Email:      CHF 89.937
Blob:       (included in email)

TOTAL:      CHF 10,188.73/month
Avg/interaction: CHF 10,188.73 ÷ 24,000 = CHF 0.425
```

---

## 6. Validation Checks

### 6.1 Unit Conversion Verification

| Conversion | Formula | Verification |
|------------|---------|-------------|
| Minutes to Seconds | min × 60 | 5 min × 60 = 300 sec ✓ |
| MB to GB | mb ÷ 1,024 | 2,048 MB ÷ 1,024 = 2 GB ✓ |
| Days to Month | days × 30 | 50 calls/day × 30 = 1,500 calls/month ✓ |
| Tokens to Millions | tokens ÷ 1,000,000 | 3,000,000 ÷ 1M = 3.0 ✓ |

### 6.2 Price Lookup Verification

**Voice Agent Models:**
| Model | Audio Input | Audio Output | Text Input | Text Output |
|-------|-------------|--------------|------------|-------------|
| gpt_realtime | 25.47 | 50.94 | 3.19 | 12.74 |
| gpt_realtime_mini | 7.96 | 15.92 | 0.48 | 1.92 |
| gpt_4o_realtime | 31.8341 | 63.6680 | 3.9793 | 15.9170 |
| gpt_4o_mini_realtime | 7.9586 | 15.9170 | 0.4776 | 1.9100 |

**Email Agent Models:**
| Model | Input | Output | Cached Input |
|-------|-------|--------|--------------|
| gpt_5_mini | 0.20 | 1.60 | 0.02 |
| gpt_5 | 1.00 | 7.96 | 0.10 |
| gpt_4o | 3.9793 | 15.9170 | 1.9897 |
| gpt_4o_mini | 0.4776 | 1.9100 | 0.2388 |

All prices in CHF per million tokens ✓

### 6.3 Edge Case Handling

**Scenario 1: Zero Calls**
```
Input: calls_per_day = 0
Expected: All costs = 0, cost_per_call = 0
Actual: ✓ Handled by checking if calls_per_month > 0 before division
```

**Scenario 2: Exceeding All Free Tiers**
```
Input: 500 calls/day, 30 min/call, 3 replicas
Expected: Billable amounts calculated correctly
Container:
  - vCPU: exceeds 180K
  - Memory: exceeds 360K
  - Requests: exceeds 2M
Actual: ✓ Each free tier subtracted before billing
```

**Scenario 3: Business Hours Polling**
```
Input: business_hours_only = True
Expected: checks = (227.3 × 60) ÷ polling_minutes
Actual: ✓ Correctly uses 227.3 instead of 720
Savings: 68.5% reduction in polling costs
```

**Scenario 4: RAG Disabled**
```
Input: enable_rag = False, num_pages = 5000
Expected: blob_cost = 0, input_tokens = 500 (not 2000)
Actual: ✓ Returns {'cost': 0, 'storage_gb': 0}
```

### 6.4 Rounding and Precision

**Monetary Values:**
- All costs stored as float
- Display rounded to 2 decimal places
- Internal calculations use full precision

**Percentages:**
- Free tier usage displayed to 1 decimal place
- Example: 45.7% not 46% or 45%

**Token Counts:**
- Always integers
- No rounding needed for token calculations

**Example:**
```
Internal: CHF 257.38447891
Display: CHF 257.38
Per-call: CHF 0.17159 → Display as CHF 0.172
```

---

## 7. Pricing Reference

### 7.1 Voice Agent Pricing

**Azure Communication Services:**
- Swiss Geographic Number: CHF 0.80/month
- Inbound Calls: CHF 0.0080/minute
- Outbound Calls: CHF 0.0186/minute (optional)
- Call Recording: CHF 0.0013/minute (optional)
- Audio Streaming: CHF 0.0026/minute (optional)

**Container Apps:**
- vCPU (active): CHF 0.0000192/second × 0.5 vCPU
- Memory (active): CHF 0.0000024/GB-second × 1.0 GB
- Idle: CHF 0.0000024/second (FLAT for both vCPU+memory)
- Requests: CHF 0.319/million
- Free Tier:
  - 180,000 vCPU-seconds/month
  - 360,000 GB-seconds/month
  - 2,000,000 requests/month

**Audio Models (per million tokens):**
- Audio conversion: 2,000 tokens/minute
- Split: 40% input, 60% output

### 7.2 Email Agent Pricing

**Azure Functions:**
- Executions: CHF 0.160/million
- Compute: CHF 0.000013/GB-second
- Memory: 0.5 GB per execution
- Duration: 3 seconds per check
- Free Tier:
  - 1,000,000 executions/month
  - 400,000 GB-seconds/month

**Token Usage:**
- Base Input: 500 tokens
- RAG Additional: 1,500 tokens
- Output: 500 tokens

**Operating Hours:**
- 24/7: 720 hours/month
- Business Hours: 227.3 hours/month (8:00-18:30, Mon-Fri)

### 7.3 Shared Pricing

**Blob Storage (Hot Tier):**
- Cost: CHF 0.0147/GB/month
- Page Size: 0.5 MB per page
- Index Overhead: 1.1× (10% additional)
- Operations: (informational, not calculated)
  - Read: CHF 0.0042/10K operations
  - Write: CHF 0.0518/10K operations
  - Data Retrieval: CHF 0.0/GB

### 7.4 Cost Optimization Decision Tree

```
START: Choose Voice Model
  ├─ Need highest quality? → GPT-4o Realtime (moderate-high cost)
  ├─ Need good balance? → GPT-4o Mini Realtime (low cost)
  ├─ Need absolute best? → GPT-realtime (highest cost)
  └─ Recommended default → GPT-realtime-mini (lowest cost, excellent quality)

Container Configuration:
  ├─ < 50 calls/day? → Serverless (0 replicas)
  ├─ Need zero cold starts? → 1 replica (always-on)
  ├─ Need high availability? → 2-3 replicas
  └─ Very high volume? → Consider load testing

Email Configuration:
  ├─ Routine emails? → GPT-5-mini (recommended)
  ├─ Complex technical? → GPT-5 (highest quality)
  ├─ Instant response needed? → 1-minute polling
  ├─ 5-minute OK? → 5-minute polling (80% less checks)
  ├─ Only business hours? → Enable business hours (68% savings)
  └─ Need RAG? → Enable with minimum pages needed

RAG Configuration:
  ├─ < 5,000 pages? → Very cheap (< CHF 0.05/month)
  ├─ 5,000-20,000 pages? → Cheap (CHF 0.05-0.20/month)
  └─ > 20,000 pages? → Consider document consolidation
```

---

## 8. Troubleshooting

### 8.1 Common Issues

**Issue: Cost seems too high**
```
Check:
1. Are you using the most expensive model? (GPT-realtime or GPT-4o Realtime)
2. Is call volume correct? (calls_per_day × 30 = monthly)
3. Are you using always-on with multiple replicas unnecessarily?
4. Is polling interval too frequent? (1 min vs 5 min)
5. Review optimization recommendations in Combined Tab
```

**Issue: Free tier not applying**
```
Check:
1. Serverless mode: Should see CHF 0.00 for low volumes
2. Verify usage < free tier limits:
   - Container: < 180K vCPU-sec, < 360K GB-sec, < 2M requests
   - Functions: < 1M executions, < 400K GB-seconds
3. Always-on mode uses resources 24/7, may exceed free tier quickly
```

**Issue: Costs different from Azure calculator**
```
Verify:
1. Region: Sweden Central (pricing varies by region)
2. Currency: CHF not USD or EUR
3. All components included: Container + Audio + Text + ACS + Phone
4. Free tiers applied correctly
5. Audio split: 40/60 not 50/50
6. Token conversion: 2,000 tokens/minute
```

### 8.2 Verification Formula

**Complete Voice Agent Verification:**
```
1. Count total minutes: calls × minutes_per_call
2. Calculate audio cost:
   (minutes × 2000 × 0.4 ÷ 1M) × input_rate +
   (minutes × 2000 × 0.6 ÷ 1M) × output_rate
3. Calculate text cost:
   (calls × 1400 ÷ 1M) × text_input_rate +
   (calls × 600 ÷ 1M) × text_output_rate
4. Calculate container (if serverless):
   - Seconds: calls × minutes × 60
   - vCPU: MAX(0, (seconds - 180K) × 0.5 × 0.0000192)
   - Memory: MAX(0, (seconds × 1.0 - 360K) × 0.0000024)
   - Requests: MAX(0, (calls × 2 - 2M) ÷ 1M × 0.319)
5. Calculate ACS:
   - Phone: num_phones × 0.80
   - Calls: minutes × 0.0080
6. Sum all components

Expected Margin of Error: < CHF 0.01 due to rounding
```

---

## 9. Changelog

### Version 1.1.0 (2025-11-20)
- Added container request cost calculations
- Updated audio split to use config values (40/60)
- Added operating hours configuration for email agent
- Corrected all pricing values:
  - Container idle rate: 0.0000096 → 0.0000024
  - Email execution cost: 0.268 → 0.160
  - Email compute cost: 0.0000214 → 0.000013
  - Base email tokens: 1000 → 500
  - GPT-5-mini: 1.9897/7.9586 → 0.20/1.60
  - GPT-5: 6.6313/26.5253 → 1.00/7.96
  - Blob storage: 0.0255 → 0.0147
  - Page size: 2.5 MB → 0.5 MB
  - Index overhead: 1.3 → 1.1
- Added cached input pricing for all models
- Enhanced free tier tracking and display

### Version 1.0.0 (Initial Release)
- Base voice agent calculations
- Base email agent calculations
- Shared blob storage
- Free tier support

---

## 10. References

**Azure Pricing Documentation:**
- Container Apps: https://azure.microsoft.com/pricing/details/container-apps/
- Azure Functions: https://azure.microsoft.com/pricing/details/functions/
- Communication Services: https://azure.microsoft.com/pricing/details/communication-services/
- Blob Storage: https://azure.microsoft.com/pricing/details/storage/blobs/
- OpenAI on Azure: https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/

**Configuration File:**
- All pricing values: `pricing_config.json`
- Version tracking included in config
- Last updated field for audit trail

**Application Code:**
- Voice calculations: `calculate_voice_cost()` in `app.py`
- Email calculations: `calculate_email_cost()` in `app.py`
- Blob calculations: `calculate_blob_storage_cost()` in `app.py`

---

*End of Technical Documentation*
