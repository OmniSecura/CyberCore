import os

# Redis — must match log-service so we pop from the same list.
REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/2")
LOG_QUEUE_KEY = os.getenv("LOG_QUEUE_KEY", "cyberlog:queue")

# Tuning knobs for the worker loop.
# How long BRPOP blocks waiting for a single entry (seconds). 0 = forever.
BRPOP_TIMEOUT = int(os.getenv("BRPOP_TIMEOUT", "5"))

# How many entries we attempt to bundle into one DB transaction.
BATCH_SIZE   = int(os.getenv("CONSUMER_BATCH_SIZE", "100"))

# Max time (seconds) we wait while filling a partial batch before flushing.
BATCH_TIMEOUT = float(os.getenv("CONSUMER_BATCH_TIMEOUT", "1.0"))
