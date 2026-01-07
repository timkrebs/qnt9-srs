import os
import json
import tempfile
import pandas as pd
import numpy as np
import xgboost as xgb
from supabase import create_client, Client
import structlog
from fastapi import HTTPException

from app.core.config import settings
from app.repositories.repos import FeatureRepository, ModelRegistryRepository

logger = structlog.get_logger()

class InferenceService:
    def __init__(self, feature_repo: FeatureRepository, registry_repo: ModelRegistryRepository):
        self.feature_repo = feature_repo
        self.registry_repo = registry_repo
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        self._model_cache = {}

    def _load_model(self, ticker: str):
        """
        Loads model from cache or downloads from Supabase Storage.
        """
        if ticker in self._model_cache:
            return self._model_cache[ticker]

        # 1. Get Metadata
        run = self.registry_repo.get_latest_successful_run(ticker)
        if not run:
            logger.warning("no_model_found", ticker=ticker)
            raise HTTPException(status_code=404, detail=f"No trained model found for {ticker}")

        # 2. Download Artifact
        try:
            # Download file content as bytes
            response = self.supabase.storage.from_(settings.SUPABASE_BUCKET_MODELS).download(run.artifact_path)
            
            # Save to temp file for XGBoost to load (XGBoost often likes file paths)
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                tmp.write(response)
                tmp_path = tmp.name
            
            # Load XGBoost
            model = xgb.XGBClassifier()
            model.load_model(tmp_path)
            os.remove(tmp_path)
            
            self._model_cache[ticker] = model
            logger.info("model_loaded", ticker=ticker, run_id=str(run.id))
            return model
            
        except Exception as e:
            logger.error("model_load_failed", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to load model artifact")

    def predict(self, ticker: str):
        """
        Generates a Buy/Sell/Hold recommendation.
        """
        # 1. Load Model
        model = self._load_model(ticker)
        
        # 2. Get Features
        df = self.feature_repo.get_latest_features(ticker)
        if df is None:
            raise HTTPException(status_code=404, detail=f"No recent market data for {ticker}")
            
        # Select features expected by model (Notebook defined: rsi_14, sma_50, sma_200, macd, macd_signal, volume)
        # IMPORTANT: Order must match!
        feature_cols = ['rsi_14', 'sma_50', 'sma_200', 'macd', 'macd_signal', 'volume']
        X = df[feature_cols]
        
        # 3. Predict PROBABILITY
        probs = model.predict_proba(X)[0] # [prob_sell, prob_hold, prob_buy]
        pred_class = np.argmax(probs)
        
        labels = {0: "SELL", 1: "HOLD", 2: "BUY"}
        recommendation = labels.get(pred_class, "HOLD")
        confidence = float(np.max(probs))
        
        # 4. Generate Reasoning (Simplified rule-based + feature values)
        factors = []
        rsi = X['rsi_14'].iloc[0]
        if rsi > 70: factors.append("RSI indicates Overbought")
        elif rsi < 30: factors.append("RSI indicates Oversold")
        
        if recommendation == "BUY" and confidence > 0.8:
            factors.append("Strong technical buy signal")
            
        return {
            "ticker": ticker,
            "recommendation": recommendation,
            "confidence": round(confidence, 4),
            "factors": factors,
            "features": X.to_dict(orient="records")[0]
        }
