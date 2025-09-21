"""Placeholder worker entrypoint for local development."""

from __future__ import annotations

import logging
import time

logging.basicConfig(level=logging.INFO, format="[worker] %(message)s")


def main() -> None:
    logging.info(
        "Worker service placeholder running. Waiting for future job handlers..."
    )
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Worker service stopping.")


if __name__ == "__main__":
    main()
