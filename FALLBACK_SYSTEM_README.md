# Model Fallback System - Implementation Summary

## What Was Implemented

A complete **model fallback and rotation system** that automatically switches to alternative free models when one hits OpenRouter's rate limits.

## Key Components

### 1. **Model Fallback Manager** ([openrouter_app/model_fallback.py](openrouter_app/model_fallback.py))
   - Tracks which models are available
   - Monitors rate-limited models with cooldown timer
   - Rotates through available free models
   - Can be monitored and controlled programmatically

### 2. **Chat Module Updates** ([openrouter_app/chat.py](openrouter_app/chat.py))
   - `RateLimitError` exception for detecting rate limits
   - `invoke_model_with_fallback()` function that:
     - Catches 429 (rate limit) errors
     - Automatically marks model as rate-limited
     - Retries with next available model
     - Preserves conversation context
   - `chat_stream()` now uses fallback-enabled streaming

### 3. **RAG Integration** ([openrouter_app/rag.py](openrouter_app/rag.py))
   - `answer_with_context_stream()` updated to use fallback system
   - Works seamlessly in "Conversational Mode or RAG"

### 4. **Optimized RAG Integration** ([openrouter_app/optimized_rag.py](openrouter_app/optimized_rag.py))
   - Streaming responses use fallback system
   - Works in "Intelligent Document Querying Mode"

## Available Free Models (Auto-Rotated)

1. **Meta Llama 3.3 70B** - High quality, good for complex tasks
2. **GPT-OSS 120B** - Large model, good reasoning
3. **Arcee Trinity Large** - Specialized model
4. **Mistral Small 3.1** - Fast, efficient
5. **Gemini 2.0 Flash** - Experimental, very fast
6. **Step 3.5 Flash** - Alternative model
7. **DeepSeek R1** - Reasoning-focused

## How It Works

```
User sends message
    ↓
System tries primary model (or gets next available)
    ↓
Model responds successfully → User sees response
    ↓ (if rate limited)
Catches 429 error
    ↓
Marks model as rate-limited (60 second cooldown)
    ↓
Gets next available model
    ↓
Retries request with new model
    ↓
After 60 seconds, model becomes available again
```

## Usage Examples

### Basic Usage (Automatic)
```python
from openrouter_app.chat import chat_stream

# Automatically uses fallback if needed
for token in chat_stream("meta-llama/llama-3.3-70b-instruct:free", "Hello!"):
    print(token, end='', flush=True)
```

### Monitoring Model Status
```python
from openrouter_app.model_fallback import get_fallback_manager

manager = get_fallback_manager()
status = manager.get_model_status()

print("Available:", status['available'])
print("Rate-limited:", status['rate_limited'])
```

### Manual Control (for testing)
```python
manager = get_fallback_manager()

# Mark a model as rate-limited
manager.mark_rate_limited("model-id", cooldown_seconds=120)

# Reset all cooldowns
manager.reset_cooldowns()

# Get next model in rotation
next_model = manager.get_next_model()
```

## Console Output Example

When fallback activates:
```
[ATTEMPT 1] Using model: Llama 3.3 70B
[RATE LIMIT] Llama 3.3 70B (meta-llama/llama-3.3-70b-instruct:free)
[RATE LIMIT] Llama 3.3 70B rate-limited until Thu Feb 27 10:05:30 2026
[ATTEMPT 2] Using model: GPT-OSS 120B
[Response successfully received...]
```

## Features

✅ **Automatic Detection** - 429 errors caught automatically
✅ **Transparent Switching** - User sees continuous response
✅ **Context Preservation** - Conversation history maintained across switches
✅ **Cooldown Tracking** - Models unavailable for 60s after rate limit
✅ **Full Coverage** - Works in all chat modes:
  - Conversational Mode
  - Conversational Mode with RAG (documents/images)
  - Document Querying Mode

## Error Handling

- **All models rate-limited**: Shows friendly message, waits for cooldowns
- **Model failure**: Automatically tries next model
- **All attempts exhausted**: User is notified with helpful message

## Future Enhancements

1. Configurable cooldown duration
2. Per-user rate limit tracking
3. Model performance metrics
4. Cost optimization (switch to cheaper models)
5. Cached responses during full rate limiting
6. User-selectable model preferences

## Testing the Fallback

To test manually:
```python
from openrouter_app.model_fallback import get_fallback_manager

manager = get_fallback_manager()

# Simulate rate limit on all models
for model in manager.available_models:
    manager.mark_rate_limited(model['id'], cooldown_seconds=5)

# After 5 seconds, they'll auto-recover
# Or manually reset:
manager.reset_cooldowns()
```

## Troubleshooting

**Models keep rate limiting?**
- OpenRouter has strict rate limits on free models
- Consider spacing out requests more
- Or set up account with credits for paid models

**Want to see detailed logs?**
- All fallback attempts are printed to console with timestamps
- Look for `[ATTEMPT n]`, `[RATE LIMIT]`, `[ERROR]` messages

**Need to prefer a specific model?**
- Pass its model_id as first parameter to chat_stream
- System will try that one first before rotating
