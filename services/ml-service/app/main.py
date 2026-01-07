from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import structlog

from app.database import get_db, engine, Base
from app.services.inference import InferenceService
from app.repositories.repos import FeatureRepository, ModelRegistryRepository

# Create Tables (for dev)
Base.metadata.create_all(bind=engine)

logger = structlog.get_logger()

app = FastAPI(title="ML Service", version="0.1.0")

class PredictionRequest(BaseModel):
    symbol: str

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ml-service"}

@app.post("/predict")
async def predict(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    feature_repo = FeatureRepository(db)
    registry_repo = ModelRegistryRepository(db)
    service = InferenceService(feature_repo, registry_repo)
    
    try:
        result = service.predict(request.symbol)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error("prediction_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
