import sys
import time
import logging
import threading
from pathlib import Path
from concurrent import futures

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))

import catalog_pb2
import catalog_pb2_grpc
import db
import security

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PORT = 9000
POLL_INTERVAL_SECONDS = 2


class CatalogServicer(catalog_pb2_grpc.CatalogServiceServicer):

    def GetMovie(self, request, context):
        try:
            security.validate_movie_id(request.movie_id)
        except ValueError as e:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

        movie = db.fetch_movie(request.movie_id)
        if movie is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"No movie with id {request.movie_id}")

        log.info("GetMovie -> id=%s title=%s", movie["id"], movie["title"])
        return catalog_pb2.MovieResponse(
            id=movie["id"],
            title=security.sanitize_output(movie["title"]),
            release_year=movie["release_year"],
            runtime_minutes=movie["runtime_minutes"],
            director=security.sanitize_output(movie["director"]),
            synopsis=security.sanitize_output(movie["synopsis"]),
            genres=[security.sanitize_output(g) for g in movie["genres"]],
        )

    def LiveReviewFeed(self, request_iterator, context):
        subscribed_ids: set[int] = set()
        last_review_id = db.fetch_latest_review_id()

        def consume_requests():
            try:
                for req in request_iterator:
                    try:
                        security.validate_movie_id(req.movie_id)
                        subscribed_ids.add(req.movie_id)
                        log.info("Subscribed to movie_id=%s", req.movie_id)
                    except ValueError as e:
                        log.warning("Invalid subscribe request: %s", e)
            except Exception as exc:
                log.warning("Request stream ended: %s", exc)

        threading.Thread(target=consume_requests, daemon=True).start()

        while context.is_active():
            if subscribed_ids:
                new_reviews = db.fetch_new_reviews_for_movies(
                    list(subscribed_ids), last_review_id
                )
                for r in new_reviews:
                    last_review_id = max(last_review_id, r["review_id"])
                    yield catalog_pb2.ReviewUpdate(
                        review_id=r["review_id"],
                        movie_id=r["movie_id"],
                        movie_title=security.sanitize_output(r["movie_title"]),
                        rating=r["rating"],
                        comment=security.sanitize_output(r["comment"]),
                        created_at=r["created_at"],
                    )
            time.sleep(POLL_INTERVAL_SECONDS)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    catalog_pb2_grpc.add_CatalogServiceServicer_to_server(CatalogServicer(), server)
    server.add_insecure_port(f"[::]:{PORT}")
    server.start()
    log.info("gRPC server listening on port %d", PORT)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
