"""
Entry point: python start_worker.py
Starts the log-consumer BRPOP loop. Identical to `python -m src.consumer`.
"""
from src.consumer import main

if __name__ == "__main__":
    main()
