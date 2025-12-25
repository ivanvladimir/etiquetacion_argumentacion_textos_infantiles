import asyncio
import logging
import uvloop
import torch
from arq.worker import Worker
from ..config import settings, MLModelsSettings
from ..ml_models import model_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


# -------- background tasks --------
async def sample_background_task(ctx: Worker, name: str) -> str:
    await asyncio.sleep(5)
    return f"Task {name} is complete!"

async def predict_task(ctx: Worker, model_name: str, document_id: str, document_name: str, text: str) -> dict:
    """Token classification prediction task"""
    cache = ctx["model_cache"]
    
    try:
        logger.info(f"Starting prediction with {model_name}")
        
        model = cache.get_model(model_name)
        tokenizer = cache.get_tokenizer(model_name)
        
        # Tokenize
        inputs = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True
        ).to(cache.device)
        
        # Predict
        with torch.no_grad():
            outputs = model(**inputs)
        
        predictions = outputs.logits.argmax(dim=-1)
        tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        result = {
            "model": model_name,
            "document_id": document_id,
            "document_name": document_name,
            "tokens": tokens,
            "predictions": predictions[0].tolist(),
            "status": "success"
        }
        
        logger.info(f"Prediction complete for {model_name}")
        return result
    
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        return {
            "model": model_name,
            "document_id": document_id,
            "document_name": document_name,
            "status": "error",
            "error": str(e)
        }


# -------- base functions --------
async def startup(ctx: Worker) -> None:
    logging.info("Worker Started")
    logger.info("Worker starting (models loaded by FastAPI)")
    if isinstance(settings, MLModelsSettings):
        await model_cache.load_models(model_path=settings.ML_MODELS_DIRPATH, model_names=settings.ML_MODELS_NAMES)
    ctx["model_cache"] = model_cache

async def shutdown(ctx: Worker) -> None:
    logging.info("Worker end")
