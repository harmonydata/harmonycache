import json
import logging
import os
import tempfile
import pickle
import traceback
from hashlib import sha256
from typing import Any

import requests
from azure.functions import HttpResponse, HttpRequest
from azure.storage.blob import ContainerClient

harmony_api = os.getenv("HARMONY_API")

container = ContainerClient.from_connection_string(
    conn_str=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
    container_name="harmonycache",
)

cache = {}

cache_pkl = "cache.pkl"

# While the function is running, the cache file must be temporarily saved in the temp dir
cache_pkl_tmp_file_path = os.path.join(tempfile.gettempdir(), cache_pkl)

# Load cache from Azure blob storage
try:
    logging.info("Loading cache from Azure blob storage")
    cache = pickle.loads(container.download_blob(blob=cache_pkl).readall())
except (Exception,):
    logging.error("Could not download blob, starting with empty cache")
    logging.error(traceback.format_exc())


def main(req: HttpRequest) -> HttpResponse:
    if req.method != "POST":
        return HttpResponse("Method not allowed", status_code=405)

    req_body = req.get_body()
    if req_body:
        files = json.loads(req_body)
        results = []

        # Check if 'files' is a list
        if not isinstance(files, list):
            return HttpResponse("Invalid request", status_code=400)

        # A list of files whose instruments are not cached
        files_with_no_cached_instrument = []

        for file in files:
            # Check if 'content' is present
            if not file.get("content"):
                logging.error(f"File with id '{file.get('file_id')}' has no content")
                continue

            hash_value = get_file_content_hash_value(file)
            if hash_value in cache.keys():
                # If instrument is cached, add it to results
                instrument = cache[hash_value]
                results.append(instrument)
            else:
                # If instrument is not cached, add the file to not_cached_files
                files_with_no_cached_instrument.append(file)

        # Get instruments for files that are not cached
        if files_with_no_cached_instrument:
            response_parse = get_response_parse(
                not_cached_files=files_with_no_cached_instrument
            )
            if response_parse.ok:
                instruments: list = response_parse.json()
                for file_with_no_cached_instrument in files_with_no_cached_instrument:
                    instrument = get_file_instrument(
                        file=file_with_no_cached_instrument, instruments=instruments
                    )
                    if instrument:
                        hash_value = get_file_content_hash_value(
                            file_with_no_cached_instrument
                        )
                        cache[hash_value] = instrument
                        results.append(instrument)
            else:
                error_msg = "Could not get instruments from API"
                logging.error(error_msg)
                return HttpResponse(error_msg, status_code=500)

            # Save cache to storage
            save_cache_to_blob_storage()

        # Return results
        return HttpResponse(
            body=json.dumps(results),
            headers={"Content-Type": "application/json"},
            status_code=200,
        )

    return HttpResponse("Invalid request", status_code=400)


def get_response_parse(not_cached_files: list):
    """Get response parse"""

    return requests.post(
        url=f"{harmony_api}/text/parse",
        data=json.dumps(not_cached_files),
        headers={"Content-Type": "application/json"},
    )


def get_file_content_hash_value(file: Any):
    """Get file content hash value"""

    return sha256(file["content"].encode()).hexdigest()


def get_file_instrument(file: Any, instruments: list):
    """Get file instrument"""

    for instrument in instruments:
        if instrument.get("file_id") == file.get("file_id"):
            return instrument


def save_cache_to_blob_storage():
    """Save cache to blob storage"""

    # Store data
    with open(cache_pkl_tmp_file_path, "wb") as file:
        pickle.dump(cache, file, protocol=pickle.HIGHEST_PROTOCOL)

    # Load data
    with open(cache_pkl_tmp_file_path, "rb") as file:
        data = file.read()

    # Upload cache
    container.upload_blob(name=cache_pkl, data=data, overwrite=True)
