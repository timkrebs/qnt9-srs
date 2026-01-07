import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Float, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TrainingRun(Base):
    """
    Model Registry Table.
    Tracks training experiments executed in Colab/Notebooks.
    """
    __tablename__ = "training_runs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(String, index=True)
    model_type: Mapped[str] = mapped_column(String)  # e.g., 'XGBoost', 'LSTM'
    
    # Experiment Metadata
    hyperparameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    metrics: Mapped[Dict[str, float]] = mapped_column(JSONB, default={})
    
    # Artifact Location in Supabase Storage
    artifact_path: Mapped[str] = mapped_column(String) # e.g., "AAPL/v1_uuid.json"
    
    status: Mapped[str] = mapped_column(String, default="completed") # processing, completed, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
