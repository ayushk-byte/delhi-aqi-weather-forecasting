"""Scheduled background worker: coordinates periodic data ingestion and real-time inference."""

import argparse
import os
import time
from datetime import datetime, timezone

from src.core.config import get_settings
from src.core.logging import get_logger
from src.pipelines.inference_pipeline import InferencePipeline
from src.pipelines.ingest_pipeline import IngestionPipeline

logger = get_logger("delhi_aqi.worker")


class ScheduledWorker:
    """Runs scheduled ingestion and inference cycles."""

    def __init__(self, interval_minutes: int = 60) -> None:
        self.interval_seconds = interval_minutes * 60
        self.settings = get_settings()

    def run_cycle(self) -> dict:
        """Execute one complete cycle: Ingestion -> Real-time Inference."""
        cycle_start = datetime.now(timezone.utc)
        logger.info(f"--- Starting Scheduled Worker Cycle at {cycle_start.isoformat()} ---")

        # 1. Ingestion
        try:
            ingest_pipeline = IngestionPipeline()
            ingest_summary = ingest_pipeline.run()
            logger.info(f"Ingestion step completed: {ingest_summary}")
        except Exception as exc:
            logger.error(f"Ingestion step failed: {exc}", exc_info=True)
            ingest_summary = {"status": "error", "error": str(exc)}

        # 2. Inference
        try:
            inference_pipeline = InferencePipeline()
            inference_summary = inference_pipeline.run_inference()
            logger.info("Inference step completed successfully.")
        except Exception as exc:
            logger.error(f"Inference step failed: {exc}", exc_info=True)
            inference_summary = {"status": "error", "error": str(exc)}

        duration = (datetime.now(timezone.utc) - cycle_start).total_seconds()
        logger.info(f"--- Completed Worker Cycle in {duration:.2f}s ---")
        return {"ingestion": ingest_summary, "inference": inference_summary}

    def start_loop(self) -> None:
        """Run continuous scheduled loop."""
        logger.info(
            f"Scheduled worker started. Running every {self.interval_seconds // 60} minutes."
        )
        while True:
            try:
                self.run_cycle()
            except Exception as exc:
                logger.error(f"Unhandled error in worker cycle: {exc}", exc_info=True)

            logger.info(f"Sleeping for {self.interval_seconds} seconds until next cycle...")
            time.sleep(self.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delhi AQI Background Worker")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=int(os.getenv("WORKER_INTERVAL_MINUTES", "60")),
        help="Polling interval in minutes",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run single ingestion and inference cycle then exit",
    )
    args = parser.parse_args()

    worker = ScheduledWorker(interval_minutes=args.interval_minutes)
    if args.run_once:
        worker.run_cycle()
    else:
        worker.start_loop()


if __name__ == "__main__":
    main()
