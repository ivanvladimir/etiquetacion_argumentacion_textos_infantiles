import typer
import asyncio
import logging
import uuid
import re
import os
import sys
import time
import hashlib
import dateparser
import dateparser
from rich.progress import track
from datetime import UTC, datetime

from meilisearch_python_sdk import AsyncClient
from dotenv import load_dotenv
from collections import Counter

import json
from typing import List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(pretty_exceptions_show_locals=False)

def transform_jsonl_to_html(input_file: str) -> List[dict]:
    """
    Transform JSONL file with Doccano TextLabel annotations to HTML format.
    
    Args:
        input_file: Path to input JSONL file
    
    Returns:
        List of transformed documents with HTML labels
    """
    results = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                doc = json.loads(line)
                transformed = transform_document(doc)
                results.append((doc["text"],transformed))
    
    return results


def transform_document(doc: dict) -> dict:
    """
    Transform a single document by converting labels to HTML spans.
    
    Args:
        doc: Document with 'id', 'text', and 'labels' fields
    
    Returns:
        Document with 'html_text' field containing annotated text
    """
    text = doc['text']
    labels = doc.get('labels', [])
    
    # Sort labels by start position in reverse order to avoid index shifting
    sorted_labels = sorted(labels, key=lambda x: x[0], reverse=True)
    
    # Apply labels from end to beginning
    html_text = text
    for start, end, label_type in sorted_labels:
        tagged_text = f'<span class="labeled-span" label_type="{label_type}">{text[start:end]}</span>'
        html_text = html_text[:start] + tagged_text + html_text[end:]
    
    return html_text


async def add_documents_(filename:str, collection_name:str, index: str):
    """ Adds filter for the database async

    Parameters:

    filter(str) Column of the database to allow to look for.

    Returns:

    None"""
    load_dotenv()

    htmls=transform_jsonl_to_html(filename)

    documents=[]
    for i,(doc,html) in enumerate(htmls):
        document_id=uuid.uuid4().hex
        document_id_=uuid.uuid4().hex
        documents.append({
            'id': document_id,
            'id_labelled':document_id_,
            'text':doc,
            'name_document':f"{i}",
            'type':'original',
            'model': collection_name,
            'created_at': datetime.now().isoformat()
        })
        documents.append({
            'id': document_id_,
            'id_original':document_id,
            'text':html,
            'name_document':f"{i}",
            'type':'manual',
            'model': collection_name,
            'created_at': datetime.now().isoformat()
        })

    async with AsyncClient('http://localhost:7700', os.getenv("MEILI_MASTER_KEY")) as client:
        index = client.index(index)
        await index.update_documents(documents, primary_key = "id")


@app.command()
def add_documents(filename:str, collection_name: str, index: str = "documents"):
    """ Adds filter for the database

    Parameters:

    Returns:

    None"""
 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(add_documents_(filename, collection_name, index))




async def add_filter_(filter:str, index: str):
    """ Adds filter for the database async

    Parameters:

    filter(str) Column of the database to allow to look for.

    Returns:

    None"""
    load_dotenv()

    async with AsyncClient('http://localhost:7700', os.getenv("MEILI_MASTER_KEY")) as client:
        index = client.index(index)
        results=await index.get_filterable_attributes()
        if results:
            await index.update_filterable_attributes(results+filter.split(","))
        else:
            await index.update_filterable_attributes(filter.split(","))


@app.command()
def add_filter(filter:str, index: str = "documents"):
    """ Adds filter for the database

    Parameters:

    filter(str) Column of the database to allow to look for.

    Returns:

    None"""
 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(add_filter_(filter, index))

async def add_sortable_(sortable:str, index_name: str = "documents"):
    """ Adds _sortable_ for the database async

    Parameters:

    sortable(str) Column of the database to allow to look for.

    Returns:

    None"""
    load_dotenv()

    async with AsyncClient('http://localhost:7700', os.getenv("MEILI_MASTER_KEY")) as client:
        index = client.index(index_name)
        results=await index.get_sortable_attributes()
        await index.update_sortable_attributes(results+sortable.split(","))

@app.command()
def add_sortable(sortable:str, index: str = "documents"):
    """ Adds _sortable_ for the database

    Parameters:

    sortable(str) Column of the database to allow to look for.

    Returns:

    None"""
 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(add_sortable_(sortable, index))


async def show_info_(index:str):
    """ Show filter for the database async

    Parameters:

    filter(str) Column of the database to allow to look for.

    Returns:

    None"""
    load_dotenv()

    async with AsyncClient('http://localhost:7700', os.getenv("MEILI_MASTER_KEY")) as client:
        index = client.index(index)
        results=await index.get_filterable_attributes()
        print(f"Attibutos filterable: {", ".join(results)}")
        results=await index.get_sortable_attributes()
        print(f"Attibutos sortable: {", ".join(results)}")


@app.command()
def show_info(index: str = "documents"):
    """ Shows filter for the database

    Parameters:

    filter(str) Column of the database to allow to look for.

    Returns:

    None"""
 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(show_info_(index))

async def delete_all_(index_name: str):
    """ Delete all the documents

    Parameters:

    Returns:

    None"""
    load_dotenv()

    async with AsyncClient('http://localhost:7700', os.getenv("MEILI_MASTER_KEY")) as client:
        index = client.index(index_name)
        task =  await index.delete_all_documents()

@app.command()
def delete_all(index: str = "documents"):
    """ Delete all the documents

    Parameters:

    Returns:

    None"""
 
    loop = asyncio.get_event_loop()
    loop.run_until_complete(delete_all_(index))


if __name__ == "__main__":
   app()


    

