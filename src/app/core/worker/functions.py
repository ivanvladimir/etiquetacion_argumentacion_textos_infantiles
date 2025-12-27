import asyncio
import logging
import uvloop
import torch
import uuid
from datetime import datetime
from arq.worker import Worker
from ..config import settings, MLModelsSettings
from ..ml_models import model_cache
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from ...schemas.task import TaskUpdate
from ...models.task import TaskStatus
from meilisearch_python_sdk import AsyncClient
from ...crud.crud_tasks import crud_tasks
from .utils import postprocess_token_classification, create_html_output

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

DATABASE_URI = f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@db:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
DATABASE_PREFIX = settings.POSTGRES_ASYNC_PREFIX
DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"


# -------- background tasks --------
async def sample_background_task(ctx: Worker, name: str) -> str:
    await asyncio.sleep(5)
    return f"Task {name} is complete!"

async def predict_task(ctx: Worker, model_name: str, document_id: str, document_name: str, text: str, task: int, user: int) -> dict:
    """Token classification prediction task"""
    cache = ctx["model_cache"]
   
    try:
        logger.info("Worker starting connection to docsearch")
        docsearch = AsyncClient(f"http://meilisearch:{settings.MEILI_PORT}", settings.MEILI_MASTER_KEY )
        logger.info("Worker starting connection to db")
        async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)
        db_session = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
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
            logits = outputs.logits
        
        predictions = torch.argmax(logits, dim=2)[0].tolist()
        tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
        id2label = model.config.id2label
        spans = postprocess_token_classification(predictions, tokens, id2label)
        html_simple = create_html_output(spans)

        result = {
            "model": model_name,
            "document_id": document_id,
            "document_name": document_name,
            "text_spans": html_simple,
            "status": "success"
        }
        
        logger.info(f"Prediction complete for {model_name}")

        document_id_=uuid.uuid4().hex
        await docsearch.index("documents").add_documents([{
            'id': document_id_,
            'id_original':document_id,
            'id_task':task,
            'text':html_simple,
            'name_document':document_name,
            'type':'labelled',
            'model': model_name,
            'created_by': user,
            'created_at': datetime.now().isoformat()
        }])

        #Update state in db
        values_update = TaskUpdate(**{'status':TaskStatus.FINISHED})
        async with db_session() as db:
            await crud_tasks.update(db=db, object=values_update.model_dump(exclude_unset=True), id=task)

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
