import json
import logging
import os
import tempfile
import uuid
from collections import Counter

import numpy as np
import requests
from azure.functions import HttpResponse, HttpRequest

from utils import helpers
from utils.negator import negate

harmony_api = os.getenv("HARMONY_API")

cache_match_pkl = "cache_match.pkl"

cache = helpers.get_cache_from_azure(cache_file_name=cache_match_pkl)

# While the function is running, the cache file must be temporarily saved in the temp dir
cache_match_pkl_tmp_file_path = os.path.join(tempfile.gettempdir(), cache_match_pkl)


def main(req: HttpRequest) -> HttpResponse:
    """
    Endpoint: '/api/match'

    Pieces of codes below were copied from Harmony API
    """

    if req.method != "POST":
        return HttpResponse(body="Method not allowed", status_code=405)

    req_body = req.get_body()
    if req_body:
        req_body_json = json.loads(req_body)
        instruments = req_body_json.get("instruments")
        query = req_body_json.get("query")

        # Assign any missing IDs
        for instrument in instruments:
            if instrument.get("file_id") is None:
                instrument["file_id"] = uuid.uuid4().hex
            if instrument.get("instrument_id") is None:
                instrument["instrument_id"] = uuid.uuid4().hex

        texts = []
        negated_texts = []
        instrument_ids = []
        question_indices = []
        all_questions = []
        for instrument in instruments:
            for question_idx, question in enumerate(instrument.get("questions")) or []:
                instrument_id = instrument.get("instrument_id")
                question_text = question.get("question_text")
                question["instrument_id"] = instrument_id
                all_questions.append(question)
                texts.append(question_text)
                negated = negate(question_text, instrument.get("language"))
                negated_texts.append(negated)
                instrument_ids.append(instrument_id)
                question_indices.append(question_idx)

        all_texts = texts + negated_texts
        if query:
            all_texts.append(query)

        all_vectors: list[list[float]] = []

        # A list of texts whose vectors aren't cached yet
        texts_with_no_cached_vector: list[str] = []

        for text in all_texts:
            hash_value = helpers.get_hash_value(text)
            if hash_value in cache.keys():
                # If the vector of the text is cached, add it to all_vectors
                vector = cache[hash_value]
                all_vectors.append(vector)
            else:
                # If the vector of the text is not cached
                texts_with_no_cached_vector.append(text)

        # Get vectors that aren't cached yet and cache them
        if texts_with_no_cached_vector:
            response_vectors = get_response_vectors(texts_with_no_cached_vector)
            if response_vectors.ok:
                vectors: list[list[float]] = response_vectors.json()
                text_vectors = zip(texts_with_no_cached_vector, vectors)
                for text, vector in text_vectors:
                    hash_value = helpers.get_hash_value(text)
                    cache[hash_value] = vector
                    all_vectors.append(vector)
            else:
                error_msg = "Could not get vectors from API"
                logging.error(error_msg)
                return HttpResponse(body=error_msg, status_code=500)

            # Save cache to storage
            helpers.save_cache_to_blob_storage(
                cache_tmp_file_path=cache_match_pkl_tmp_file_path,
                cache_file_name=cache_match_pkl,
                cache=cache,
            )

        all_questions, similarity_with_polarity, query_similarity = get_similarity_data(
            texts=texts,
            all_questions=all_questions,
            query=query,
            all_vectors=all_vectors,
        )

        response = {
            "questions": all_questions,
            "matches": similarity_with_polarity,
            "query_similarity": query_similarity,
        }

        return HttpResponse(
            body=json.dumps(response),
            headers={"Content-Type": "application/json"},
            status_code=200,
        )

    return HttpResponse(body="Invalid request", status_code=400)


def get_response_vectors(texts: list[str]) -> requests.Response:
    """Get response vectors"""

    return requests.post(
        url=f"{harmony_api}/text/vectors",
        data=json.dumps(texts),
        headers={"Content-Type": "application/json"},
    )


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> np.ndarray:
    """
    Cosine similarity

    This function was copied from Harmony API
    """

    dp = np.dot(vec1, vec2.T)
    m1 = np.mat(np.linalg.norm(vec1, axis=1))
    m2 = np.mat(np.linalg.norm(vec2.T, axis=0))

    return np.asarray(dp / np.matmul(m1.T, m2))


def get_similarity_data(
    texts: list[str], all_questions: list, query: str, all_vectors: list[list[float]]
):
    """
    Get similarity data

    Pieces of codes below were copied from Harmony API
    """

    all_vectors = np.array(all_vectors)

    vectors_pos = all_vectors[: len(texts), :]
    vectors_neg = all_vectors[len(texts) : len(texts) * 2, :]

    if query:
        vector_query = np.array(all_vectors[-1:, :])
        query_similarity = cosine_similarity(vectors_pos, vector_query)[:, 0]
    else:
        query_similarity = None

    pairwise_similarity = cosine_similarity(vectors_pos, vectors_pos)
    pairwise_similarity_neg1 = cosine_similarity(vectors_neg, vectors_pos)
    pairwise_similarity_neg2 = cosine_similarity(vectors_pos, vectors_neg)

    pairwise_similarity_neg_mean = np.mean(
        [pairwise_similarity_neg1, pairwise_similarity_neg2], axis=0
    )

    similarity_difference = pairwise_similarity - pairwise_similarity_neg_mean
    similarity_polarity = np.sign(similarity_difference)

    # Make sure that any 0's in polarity are converted to 1's
    where_0 = np.where(np.abs(similarity_difference) < 0.001)
    similarity_polarity[where_0] = 1

    similarity_max = np.max([pairwise_similarity, pairwise_similarity_neg_mean], axis=0)
    similarity_with_polarity = similarity_max * similarity_polarity

    # Get MHC embeddings
    mhc_questions, mhc_all_metadata, mhc_embeddings = helpers.get_mhc_embeddings()

    # Work out similarity with MHC
    if len(mhc_embeddings) > 0:
        similarities_mhc = cosine_similarity(vectors_pos, mhc_embeddings)

        ctrs = {}
        for idx, a in enumerate(np.argmax(similarities_mhc, axis=1)):
            if all_questions[idx].get("instrument_id") not in ctrs:
                ctrs[all_questions[idx].get("instrument_id")] = Counter()
            for topic in mhc_all_metadata[a]["topics"]:
                ctrs[all_questions[idx].get("instrument_id")][topic] += 1
            all_questions[idx]["nearest_match_from_mhc_auto"] = mhc_questions[a].dict()

        instrument_to_category = {}
        for instrument_id, counts in ctrs.items():
            instrument_to_category[instrument_id] = []
            max_count = max(counts.values())
            for topic, topic_count in counts.items():
                if topic_count > max_count / 2:
                    instrument_to_category[instrument_id].append(topic)

        for question in all_questions:
            question["topics_auto"] = instrument_to_category[
                question.get("instrument_id")
            ]

    return all_questions, similarity_with_polarity.tolist(), query_similarity.tolist()
