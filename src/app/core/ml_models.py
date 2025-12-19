import asyncio
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import os
from pathlib import Path
from logging import getLogger

class ModelCache:
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger = getLogger(__name__)
    
    async def load_models(self, model_path: str | Path, model_names: list[str]):
        """Load multiple models asynchronously into cache"""
        model_path = Path(model_path)
        self.logger.info(f"Starting to load {len(model_names)} models from {model_path}")
        
        # Create tasks for loading models concurrently
        tasks = [
            self._load_single_model(model_path, name) 
            for name in model_names
        ]
        
        # Run all loads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for errors
        failed_models = []
        for name, result in zip(model_names, results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to load model '{name}': {result}")
                failed_models.append(name)
            else:
                self.logger.info(f"Successfully loaded model '{name}'")
        
        if failed_models:
            self.logger.warning(f"Failed to load {len(failed_models)} models: {failed_models}")
        else:
            self.logger.info(f"All {len(model_names)} models loaded successfully")
    
    async def _load_single_model(self, model_path: Path, model_name: str):
        """Load a single model in executor to avoid blocking"""
        loop = asyncio.get_event_loop()
        self.logger.debug(f"Starting async load for model '{model_name}'")
        
        try:
            # Run blocking I/O in thread pool executor
            tokenizer, model = await loop.run_in_executor(
                None, 
                self._sync_load_model, 
                model_path, 
                model_name
            )
            
            self.tokenizers[model_name] = tokenizer
            self.models[model_name] = model
            self.logger.debug(f"Model '{model_name}' added to cache")
            
        except Exception as e:
            self.logger.error(f"Exception loading model '{model_name}': {str(e)}", exc_info=True)
            raise RuntimeError(f"Error loading model {model_name}: {str(e)}")
    
    def _sync_load_model(self, model_path: Path, model_name: str):
        """Synchronous model loading (runs in executor)"""
        model_dir = model_path / model_name
        
        cwd = Path.cwd()
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        self.logger.debug(f"Loading tokenizer from {model_dir}")
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        
        self.logger.debug(f"Loading model from {model_dir}")
        model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
        
        self.logger.debug(f"Moving model '{model_name}' to device: {self.device}")
        model.to(self.device)
        model.eval()
        
        return tokenizer, model
    
    def get_model(self, model_name: str):
        """Get model from cache"""
        if model_name not in self.models:
            self.logger.warning(f"Model '{model_name}' not found in cache")
            raise ValueError(f"Model '{model_name}' not found in cache")
        self.logger.debug(f"Retrieved model '{model_name}' from cache")
        return self.models[model_name]
    
    def get_tokenizer(self, model_name: str):
        """Get tokenizer from cache"""
        if model_name not in self.tokenizers:
            self.logger.warning(f"Tokenizer for '{model_name}' not found in cache")
            raise ValueError(f"Tokenizer for '{model_name}' not found in cache")
        self.logger.debug(f"Retrieved tokenizer for '{model_name}' from cache")
        return self.tokenizers[model_name]
    
    def cleanup(self):
        """Clear cache and free memory"""
        self.logger.info(f"Cleaning up {len(self.models)} models from cache")
        self.models.clear()
        self.tokenizers.clear()
        torch.cuda.empty_cache()
        self.logger.info("Cache cleanup completed")
