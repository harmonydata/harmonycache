import json

from azure.functions import HttpResponse, HttpRequest

from .. import constants
from ..utils import helpers

cache_instruments = helpers.get_cache_from_azure(
    cache_file_name=constants.cache_instruments_pkl
)
cache_vectors = helpers.get_cache_from_azure(
    cache_file_name=constants.cache_vectors_pkl
)


def main(req: HttpRequest) -> HttpResponse:
    """
    Endpoint: GET /api/cache
    """

    if req.method != "GET":
        return HttpResponse("Method not allowed", status_code=405)

    # Get cached items
    response = {
        "instruments": [v for k, v in cache_instruments.items()],
        "vectors": [
            {"text": v["text"], "vector": v["vector"]} for k, v in cache_vectors.items()
        ],
    }

    return HttpResponse(
        body=json.dumps(response),
        headers={
            "Content-Type": "application/json",
        },
        status_code=200,
    )
