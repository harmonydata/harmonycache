import json
import logging
import os
import tempfile
from typing import Any
import uuid

import requests
from azure.functions import HttpResponse, HttpRequest

from ..utils import helpers

harmony_api = os.getenv("HARMONY_API")

container = helpers.get_container_harmonycache()

cache_parse_pkl = "cache_parse.pkl"

cache = helpers.get_cache_from_azure(cache_file_name=cache_parse_pkl)

# While the function is running, the cache file must be temporarily saved in the temp dir
cache_parse_pkl_tmp_file_path = os.path.join(tempfile.gettempdir(), cache_parse_pkl)


def main(req: HttpRequest) -> HttpResponse:
    """
    Endpoint: /api/parse
    """

    if req.method != "POST":
        return HttpResponse("Method not allowed", status_code=405)

    req_body = req.get_body()
    if req_body:
        req_body_json = json.loads(req_body)
        files = req_body_json

        response = []

        # Check if 'files' is a list
        if not isinstance(files, list):
            return HttpResponse(body="Invalid request", status_code=400)

        # A list of files whose instruments are not cached
        files_with_no_cached_instrument = []

        for file in files:
            # Assign any missing IDs
            if file.get("file_id") is None:
                file["file_id"] = uuid.uuid4().hex

            # Check if 'content' is present
            if not file.get("content"):
                logging.error(f"File with id '{file.get('file_id')}' has no content")
                continue

            hash_value = helpers.get_hash_value(file["content"])
            if hash_value in cache.keys():
                # If instrument is cached
                instrument = cache[hash_value]
                response.append(instrument)
            else:
                # If instrument is not cached
                files_with_no_cached_instrument.append(file)

        # Get instruments that aren't cached yet and cache them
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
                        hash_value = helpers.get_hash_value(
                            file_with_no_cached_instrument["content"]
                        )
                        cache[hash_value] = instrument
                        response.append(instrument)
            else:
                error_msg = "Could not get instruments from Harmony API"
                logging.error(error_msg)
                return HttpResponse(body=error_msg, status_code=500)

            # Save cache to storage
            helpers.save_cache_to_blob_storage(
                cache_tmp_file_path=cache_parse_pkl_tmp_file_path,
                cache_file_name=cache_parse_pkl,
                cache=cache,
            )

        # Return results
        return HttpResponse(
            body=json.dumps(response),
            headers={"Content-Type": "application/json"},
            status_code=200,
        )

    return HttpResponse(body="Invalid request", status_code=400)


def get_response_parse(not_cached_files: list) -> requests.Response:
    """Get response parse"""

    return requests.post(
        url=f"{harmony_api}/text/parse",
        data=json.dumps(not_cached_files),
        headers={"Content-Type": "application/json"},
    )


def get_file_instrument(file: Any, instruments: list):
    """Get file instrument"""

    for instrument in instruments:
        if instrument.get("file_id") == file.get("file_id"):
            return instrument
