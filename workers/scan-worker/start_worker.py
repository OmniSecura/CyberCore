"""
Entry point: python start_worker.py
Starts a Celery worker consuming the 'sast' queue.
"""
from src.celery_app import celery_app

if __name__ == "__main__":
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=INFO",
            "--queues=sast",
            "--concurrency=2",
            "--hostname=scan-worker@%h",
        ]
    )
