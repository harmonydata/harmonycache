import json
import logging
import os
import pickle
import tempfile
import traceback
from hashlib import sha256

import numpy as np
from azure.storage.blob import ContainerClient

from .. import constants
from ..models.question import Question


def get_container_harmonycache() -> ContainerClient:
    """Get container 'harmonycache'"""

    return ContainerClient.from_connection_string(
        conn_str=constants.AZURE_STORAGE_CONNECTION_STRING,
        container_name="harmonycache",
    )


def get_container_mhc() -> ContainerClient:
    """Get container 'mhc'"""

    return ContainerClient.from_connection_string(
        conn_str=constants.AZURE_STORAGE_CONNECTION_STRING,
        container_name="mhc",
    )


def get_cache_from_azure(cache_file_name: str) -> dict:
    """Get cache from Azure Blob Storage"""

    container_harmonycache = get_container_harmonycache()
    cache = {}

    try:
        logging.info(f"Loading blob {cache_file_name} from Azure blob storage")
        cache = pickle.loads(
            container_harmonycache.download_blob(blob=cache_file_name).readall()
        )
    except (Exception,):
        logging.error(f"Could not download blob {cache_file_name}")
        logging.error(traceback.format_exc())

    return cache


def save_cache_to_blob_storage(
    cache_tmp_file_path: str,
    cache_file_name: str,
    cache: dict,
):
    """Save cache to blob storage"""

    container_harmonycache = get_container_harmonycache()

    # Store data
    with open(cache_tmp_file_path, "wb") as file:
        pickle.dump(cache, file, protocol=pickle.HIGHEST_PROTOCOL)

    # Load data
    with open(cache_tmp_file_path, "rb") as file:
        data = file.read()

    # Upload cache
    container_harmonycache.upload_blob(name=cache_file_name, data=data, overwrite=True)


def get_hash_value(text: str) -> str:
    """Get hash value"""

    return sha256(text.encode()).hexdigest()


def get_mhc_embeddings() -> tuple:
    """Get MHC embeddings"""

    mhc_questions = []
    mhc_all_metadata = []
    mhc_embeddings = np.zeros((0, 0))

    container_mhc = get_container_mhc()

    mhc_questions_json = container_mhc.download_blob("mhc_questions.json").readall()
    mhc_all_metadata_json = container_mhc.download_blob(
        "mhc_all_metadatas.json"
    ).readall()
    mhc_embeddings_npy = container_mhc.download_blob("mhc_embeddings.npy").readall()

    try:
        for line in mhc_questions_json.splitlines():
            mhc_question = Question.parse_raw(line)
            mhc_questions.append(mhc_question)

        for line in mhc_all_metadata_json.splitlines():
            mhc_metadata = json.loads(line)
            mhc_all_metadata.append(mhc_metadata)

        mhc_embeddings_npy_tmp_file_path = os.path.join(
            tempfile.gettempdir(), "mhc_embeddings.npy"
        )
        with open(mhc_embeddings_npy_tmp_file_path, "wb") as file:
            file.write(mhc_embeddings_npy)
        mhc_embeddings = np.load(mhc_embeddings_npy_tmp_file_path)
    except (Exception,) as e:
        logging.error(f"Could not load MHC embeddings: {e}")

    return mhc_questions, mhc_all_metadata, mhc_embeddings
