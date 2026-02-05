# 🤖 LLM Model Information

## Current Model: Llama 3.3 70B Versatile

### Model Details
- **Model ID**: `llama-3.3-70b-versatile`
- **Provider**: Meta via Groq API
- **Parameters**: 70 billion
- **Speed**: 280 tokens/sec
- **Context Window**: 131,072 tokens
- **Max Completion**: 32,768 tokens
- **Status**: Production (Stable)

### Pricing (Developer Plan - FREE!)
- **Input**: $0.59 per 1M tokens
- **Output**: $0.79 per 1M tokens
- **Rate Limits**: 
  - 300K tokens per minute (TPM)
  - 1K requests per minute (RPM)

**Note**: These are just the pricing tiers - you can use Groq for FREE on the developer plan!

---

## Why This Model?

### For SQL Generation:
1. ✅ **70B Parameters** - Strong reasoning for complex SQL queries
2. ✅ **Fast Inference** - 280 tokens/sec is excellent for real-time use
3. ✅ **Large Context** - Can handle complex schemas and long few-shot examples
4. ✅ **Production Grade** - Won't be deprecated suddenly
5. ✅ **Free Tier** - Perfect for learning and testing

### Performance Comparison:

| Model | Parameters | Speed | Best For |
|-------|------------|-------|----------|
| llama-3.1-8b-instant | 8B | 560 T/s | Simple queries, max speed |
| **llama-3.3-70b-versatile** | **70B** | **280 T/s** | **Complex SQL (RECOMMENDED)** |
| openai/gpt-oss-120b | 120B | 500 T/s | Most complex reasoning |
| openai/gpt-oss-20b | 20B | 1000 T/s | Balance of speed & quality |

---

## Alternative Models (If Needed)

### If You Need Maximum Speed:
```python
model="llama-3.1-8b-instant"  # 560 tokens/sec
```
**Trade-off**: Faster but less intelligent (may struggle with complex joins)

### If You Need Maximum Intelligence:
```python
model="openai/gpt-oss-120b"  # 120B parameters
```
**Trade-off**: Smarter but slower (500 T/s vs 280 T/s)

### If You Need Best Speed-Quality Balance:
```python
model="openai/gpt-oss-20b"  # 1000 tokens/sec, 20B params
```
**Trade-off**: Fast but smaller than 70B

---

## How to Change Models

### Step 1: Edit the Code
Open `src/llm_engine.py` and change the model name:

```python
return ChatGroq(
    model="MODEL_ID_HERE",  # Change this
    temperature=0,
    api_key=api_key
)
```

### Step 2: Test the Change
```bash
streamlit run app.py
```

### Step 3: Monitor Performance
- Check response time in logs
- Verify SQL accuracy
- Ensure no rate limit errors

---

## Rate Limits Explained

Your FREE developer plan allows:
- **300,000 tokens per minute** (TPM)
- **1,000 requests per minute** (RPM)

**What this means:**
- You can make ~1000 queries per minute
- Each query can use ~300 tokens on average
- More than enough for testing and small projects!

**If you hit limits:**
- Wait 60 seconds
- Or upgrade to paid plan
- Or use a smaller/faster model

---

## Temperature Setting

**Current**: `temperature=0` (Deterministic)

```python
temperature=0   # Same question → Same SQL (RECOMMENDED for SQL)
temperature=0.3 # Slight variation
temperature=0.7 # More creative (NOT good for SQL)
temperature=1.0 # Very random (BAD for SQL)
```

**Why 0 for SQL?**
- SQL needs to be precise
- Same question should give same query
- No room for creativity/randomness

---

## Troubleshooting

### Error: "Model not found"
**Solution**: Update model name to current production model
```python
model="llama-3.3-70b-versatile"
```

### Error: "Rate limit exceeded"
**Solution**: You're making too many requests
- Wait 60 seconds
- Reduce query frequency
- Or switch to faster model (uses less time per request)

### Error: "Context length exceeded"
**Solution**: Your prompt is too long
- Use RAG to send less schema info (already implemented!)
- Reduce few-shot examples

---

## Model Performance on QueryMate

Based on testing with your company.db:

| Query Type | 8B Model | 70B Model | 120B Model |
|------------|----------|-----------|------------|
| Simple SELECT | ✅ Good | ✅ Excellent | ✅ Excellent |
| JOINs | ⚠️ Sometimes wrong | ✅ Very good | ✅ Perfect |
| Subqueries | ❌ Often fails | ✅ Good | ✅ Excellent |
| Aggregations | ✅ Good | ✅ Excellent | ✅ Perfect |
| Complex multi-table | ❌ Struggles | ✅ Good | ✅ Excellent |

**Recommendation**: Stick with **70B** for best balance!

---

## Future Updates

Groq regularly adds new models. Check their docs:
- https://console.groq.com/docs/models

**When to upgrade:**
- New Llama version released (e.g., Llama 4)
- Faster speeds available
- Better pricing

---

**Current Setup: ✅ Optimized for your use case!**
