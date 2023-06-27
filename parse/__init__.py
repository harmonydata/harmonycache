import logging
import operator
import os
import traceback

import azure.functions as func
from azure.storage.blob import ContainerClient

container = ContainerClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"), "harmonycache")

import json
import re
import pickle as pkl

cache = {}

try:
    logging.info("Loading cache from Azure blob storage")
    cache = pkl.loads(container.download_blob("cache.pkl").readall())
except:
    logging.error("Couldn't download blob")
    logging.error(traceback.format_exc())


def main(req: func.HttpRequest) -> func.HttpResponse:
    data = req.params.get('data')
    if not data:
        try:
            req_body = req.get_json()
            data = req_body.get('data')
        except ValueError:
            pass

    if data:
        data = json.loads(data)
        return func.HttpResponse(json.dumps(data))
    else:
        return func.HttpResponse(
            "Sorry. There was an error.",
            status_code=200
        )
