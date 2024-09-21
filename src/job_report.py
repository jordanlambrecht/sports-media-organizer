# src/job_report.py

from pathlib import Path
from typing import Dict, Any
from src.custom_logger import log
import json


class JobReport:
    """
    Generates and manages job reports for processed media files.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initializes the JobReport with configuration.

        Args:
            config (Dict[str, Any]): The global configuration dictionary.
        """
        self.report = []
        self.report_file = (
            Path(config.get("report_directory", "reports")) / "job_report.json"
        )
        self.report_file.parent.mkdir(parents=True, exist_ok=True)

    def log_file_processing(
        self, file: Path, success: bool, metadata: Dict[str, Any]
    ) -> None:
        """
        Logs the processing result of a single file.

        Args:
            file (Path): The media file path.
            success (bool): Whether the processing was successful.
            metadata (Dict[str, Any]): Extracted metadata.
        """
        entry = {"file": str(file), "success": success, "metadata": metadata}
        self.report.append(entry)
        log.debug(f"Logged processing result for {file}: {entry}")

    def generate_report(self) -> None:
        """
        Generates the job report by writing the logged data to a JSON file.
        """
        try:
            with self.report_file.open("w", encoding="utf-8") as f:
                json.dump(self.report, f, indent=4)
            log.info(f"Job report generated at {self.report_file}")
        except Exception as e:
            log.error(f"Failed to generate job report: {e}")
