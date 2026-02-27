"""
Model Fallback System for OpenRouter
Handles rate limiting by rotating through available free models
"""

import time
from typing import List, Dict, Optional
from .openrouter_models import OPENROUTER_MODELS


class ModelFallbackManager:
    """
    Manages model rotation when rate limits are hit.
    Tracks rate-limited models and their cooldown periods.
    """
    
    def __init__(self):
        """Initialize the fallback manager with available free models"""
        self.available_models = OPENROUTER_MODELS.get("chat", [])
        self.rate_limited_models = {}  # {model_id: timestamp_when_available}
        self.current_model_idx = 0
        
    def get_available_models(self) -> List[Dict]:
        """Get list of models not currently rate-limited"""
        current_time = time.time()
        available = []
        
        for model in self.available_models:
            model_id = model["id"]
            # Check if model is rate-limited and if cooldown has expired
            if model_id in self.rate_limited_models:
                if current_time < self.rate_limited_models[model_id]:
                    continue  # Still rate-limited
                else:
                    # Cooldown expired, remove from rate-limited
                    del self.rate_limited_models[model_id]
            
            available.append(model)
        
        return available
    
    def get_next_model(self, current_model_id: Optional[str] = None) -> Dict:
        """
        Get next available model, or rotate to next if current is rate-limited.
        
        Args:
            current_model_id: The model that might be rate-limited (optional)
            
        Returns:
            Next available model dict
        """
        available = self.get_available_models()
        
        if not available:
            # All models rate-limited, reset and start fresh
            print("[WARN] All models rate-limited! Resetting cooldowns...")
            self.rate_limited_models.clear()
            available = self.available_models
        
        # If current model is specified and available, use it
        if current_model_id:
            for model in available:
                if model["id"] == current_model_id:
                    return model
        
        # Otherwise return next in rotation
        model = available[self.current_model_idx % len(available)]
        self.current_model_idx += 1
        return model
    
    def mark_rate_limited(self, model_id: str, cooldown_seconds: int = 60):
        """
        Mark a model as rate-limited with a cooldown period.
        
        Args:
            model_id: The model to mark as rate-limited
            cooldown_seconds: How long to wait before retrying (default 60 seconds)
        """
        available_when = time.time() + cooldown_seconds
        self.rate_limited_models[model_id] = available_when
        print(f"[RATE LIMIT] {model_id} rate-limited until {time.ctime(available_when)}")
    
    def get_model_status(self) -> Dict:
        """Get status of all models"""
        current_time = time.time()
        status = {
            "available": [],
            "rate_limited": []
        }
        
        for model in self.available_models:
            model_id = model["id"]
            model_info = {
                "id": model_id,
                "name": model.get("name", "Unknown"),
                "provider": model.get("provider", "Unknown")
            }
            
            if model_id in self.rate_limited_models:
                time_remaining = self.rate_limited_models[model_id] - current_time
                if time_remaining > 0:
                    model_info["time_remaining"] = f"{time_remaining:.1f}s"
                    status["rate_limited"].append(model_info)
                else:
                    status["available"].append(model_info)
            else:
                status["available"].append(model_info)
        
        return status
    
    def reset_cooldowns(self):
        """Reset all rate-limit cooldowns (useful for debugging)"""
        self.rate_limited_models.clear()
        print("[INFO] All model cooldowns reset")


# Global instance
_fallback_manager = None

def get_fallback_manager() -> ModelFallbackManager:
    """Get or create global fallback manager instance"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = ModelFallbackManager()
    return _fallback_manager
