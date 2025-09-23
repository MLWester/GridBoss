# GridBoss Worker Service

The worker service runs asynchronous jobs using [Dramatiq](https://dramatiq.io/) with Redis as the queue broker.

## Local development

1. Ensure Redis is available (Docker Compose stack provides it by default).
2. Install worker dependencies:
   ```powershell
   pip install -r worker/requirements.txt
   ```
3. Start the worker:
   ```powershell
   python -m worker.main
   ```

The worker will connect to `REDIS_URL` (defaults to `redis://localhost:6379/0`).

## Environment variables

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `WORKER_THREADS` | Number of worker threads | `8` |
| `WORKER_NAME` | Identifier for the worker process | `gridboss-worker` |
| `WORKER_RETRY_MAX_RETRIES` | Maximum retry attempts for jobs | `5` |
| `WORKER_RETRY_MIN_BACKOFF_MS` | Minimum delay between retries (ms) | `1000` |
| `WORKER_RETRY_MAX_BACKOFF_MS` | Maximum delay between retries (ms) | `300000` |

## Sample job

`worker.jobs.heartbeat` logs a heartbeat message so you can verify jobs are executed:

```python
from worker.jobs import heartbeat

heartbeat.send(message="ping")
```

Logs appear in the worker output confirming the job ran.
