"""Placeholder Discord bot entrypoint for local development."""

from __future__ import annotations

import logging
import time

logging.basicConfig(level=logging.INFO, format="[bot] %(message)s")


def main() -> None:
    logging.info("Discord bot placeholder running. Waiting for future integration...")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Discord bot stopping.")


if __name__ == "__main__":
    main()
