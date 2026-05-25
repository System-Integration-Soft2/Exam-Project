"""
Simple test client for the gRPC catalog service.

Usage:
  python client.py get 1            # unary: fetch movie with id 1
  python client.py feed 1 2 3       # streaming: subscribe to reviews for movies 1, 2, 3
"""

import sys
import time
from pathlib import Path

import grpc

sys.path.insert(0, str(Path(__file__).resolve().parent / "generated"))

import catalog_pb2
import catalog_pb2_grpc

SERVER = "localhost:9000"


def call_get_movie(movie_id: int) -> None:
    with grpc.insecure_channel(SERVER) as channel:
        stub = catalog_pb2_grpc.CatalogServiceStub(channel)
        try:
            response = stub.GetMovie(catalog_pb2.MovieRequest(movie_id=movie_id))
            print("── Movie ──────────────────────────────")
            print(f"  ID:       {response.id}")
            print(f"  Title:    {response.title}")
            print(f"  Year:     {response.release_year}")
            print(f"  Runtime:  {response.runtime_minutes} min")
            print(f"  Director: {response.director}")
            print(f"  Genres:   {', '.join(response.genres)}")
            print(f"  Synopsis: {response.synopsis}")
        except grpc.RpcError as e:
            print(f"Error: {e.code().name} — {e.details()}")


def call_live_review_feed(movie_ids: list[int]) -> None:
    def request_generator():
        for mid in movie_ids:
            print(f"→ Subscribing to movie_id={mid}")
            yield catalog_pb2.ReviewSubscribeRequest(movie_id=mid)
            time.sleep(0.2)

    with grpc.insecure_channel(SERVER) as channel:
        stub = catalog_pb2_grpc.CatalogServiceStub(channel)
        print(f"Listening for new reviews on movies {movie_ids}. Ctrl-C to stop.")
        try:
            for update in stub.LiveReviewFeed(request_generator()):
                print(
                    f"← New review: [{update.movie_title}] "
                    f"rating={update.rating}/10  '{update.comment}'  ({update.created_at})"
                )
        except grpc.RpcError as e:
            print(f"Error: {e.code().name} — {e.details()}")
        except KeyboardInterrupt:
            print("\nStopped.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    if cmd == "get" and len(args) == 1:
        call_get_movie(int(args[0]))
    elif cmd == "feed" and args:
        call_live_review_feed([int(a) for a in args])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()