"""
Metrics collector utility for tracking performance metrics
"""

import json
import logging
import time
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Utility class for collecting and storing performance metrics
    """

    def __init__(self, metrics_file: Optional[Union[str, Path]] = None):
        """
        Initialize the metrics collector

        Args:
            metrics_file: File path to store metrics (optional)
        """
        self.metrics = {}
        self.metrics_file = Path(metrics_file) if metrics_file else None
        self.lock = Lock()

        # Load existing metrics if file exists
        if self.metrics_file and self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.error(f"Error loading metrics file: {str(e)}")
                self.metrics = {}

        # Initialize metric categories if they don't exist
        for category in [
            "document_generation",
            "report_generation",
            "report_generation_error",
            "system_startup",
        ]:
            if category not in self.metrics:
                self.metrics[category] = []

    def add_metric(self, category: str, data: Dict[str, Any]) -> None:
        """
        Add a new metric to the specified category

        Args:
            category: The metric category (e.g., "document_generation")
            data: The metric data to store
        """
        with self.lock:
            # Initialize category if it doesn't exist
            if category not in self.metrics:
                self.metrics[category] = []

            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = time.time()

            # Add the metric
            self.metrics[category].append(data)

            # Save to file if specified
            self._save_metrics()

    def get_metrics(
        self, category: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve metrics for the specified category

        Args:
            category: The metric category to retrieve
            limit: Maximum number of metrics to return (most recent first)

        Returns:
            List of metric data dictionaries
        """
        with self.lock:
            if category not in self.metrics:
                return []

            # Sort by timestamp (newest first) and return requested number
            metrics = sorted(
                self.metrics[category],
                key=lambda x: x.get("timestamp", 0),
                reverse=True,
            )

            return metrics[:limit] if limit else metrics

    def clear_metrics(self, category: Optional[str] = None) -> None:
        """
        Clear metrics for the specified category or all metrics if no category provided

        Args:
            category: The metric category to clear, or None to clear all
        """
        with self.lock:
            if category:
                if category in self.metrics:
                    self.metrics[category] = []
            else:
                self.metrics = {}

            self._save_metrics()

    def _save_metrics(self) -> None:
        """
        Save metrics to the file if a file path is specified
        """
        if not self.metrics_file:
            return

        try:
            # Create parent directory if it doesn't exist
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

            # Save metrics to file
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics to file: {str(e)}")
