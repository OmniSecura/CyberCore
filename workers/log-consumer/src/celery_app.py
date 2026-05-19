# Intentionally empty.
#
# We don't use Celery for log-consumer — that pattern (one Celery task per
# log line) adds latency and broker overhead we don't need. Instead the
# consumer is a long-running BRPOP loop implemented in `src/consumer.py`.
#
# The file is kept so anyone scanning the codebase for "celery_app.py" in
# every worker doesn't get confused by its absence here.
