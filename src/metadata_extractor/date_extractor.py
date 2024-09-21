# src/metadata_extractor/date_extractor.py

import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from .base_extractor import BaseExtractor
from src.custom_logger import log


class DateExtractor(BaseExtractor):
    """
    Extracts the air date (year, month, day) and part number from the filename and directory structure.
    """

    def extract(self, filename: str, file_path: Path) -> Dict[str, Any]:
        """
        Orchestrates date extraction from the filename or directory.

        Args:
            filename (str): The media filename.
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Extracted date components, part number, and their confidence scores.
        """
        # Initialize the date information dictionary with default values
        date_info = {
            "year": "Unknown",
            "year_confidence": 0,
            "month": "Unknown",
            "month_confidence": 0,
            "day": "Unknown",
            "day_confidence": 0,
            "part_number": "",
            "part_number_confidence": 0,
        }

        # Step 1: Extract the Date from the String
        extracted_date = self.date_extract_date_from_string(filename)
        if extracted_date["year"]:
            log.info(
                f"Date extracted from string: {extracted_date['year']}-{extracted_date['month']}-{extracted_date['day']}, "
                f"Part: {extracted_date['part_number']} with confidence {extracted_date['year_confidence']}%"
            )
            date_info.update(extracted_date)
            return date_info

        # Step 2: Handle Incomplete Dates (e.g., 87.04.22A -> 1987, Part A)
        extracted_date = self.date_handle_incomplete_date(filename)
        if extracted_date["year"]:
            log.info(
                f"Handled incomplete date format: {extracted_date['year']}-{extracted_date['month']}-{extracted_date['day']}, "
                f"Part: {extracted_date['part_number']} with confidence {extracted_date['year_confidence']}%"
            )
            date_info.update(extracted_date)
            return date_info

        # Step 3: Infer Year from Directory Structure
        inferred_date = self.date_infer_year_from_directory(file_path)
        if inferred_date["year"] != "Unknown":
            log.info(
                f"Date inferred from directory structure: Year {inferred_date['year']} with confidence {inferred_date['year_confidence']}%"
            )
            date_info.update(inferred_date)
            return date_info

        # Step 4: Fallback to Unknown
        log.warning(
            f"Date could not be inferred for '{file_path}'. Defaulting to 'Unknown'."
        )
        return date_info

    def date_extract_date_from_string(self, date_str: str) -> Dict[str, Any]:
        """
        Extracts the date and part number from a string using known formats.
        Handles 2-digit years and part numbers.

        Args:
            date_str (str): The date string extracted from the filename.

        Returns:
            Dict[str, Any]: Extracted date components and confidence scores.
        """
        date_info = {
            "year": "",
            "year_confidence": 0,
            "month": "",
            "month_confidence": 0,
            "day": "",
            "day_confidence": 0,
            "part_number": "",
            "part_number_confidence": 0,
        }

        if not date_str:
            return date_info

        # Regex to extract part number (e.g., 87.04.22A -> 1987.04.22, Part A)
        part_number_match = re.search(
            r"(\d{2,4}[\.\-_]\d{2}[\.\-_]\d{2})([A-Za-z]?)", date_str
        )
        if part_number_match:
            date_str = part_number_match.group(1)
            part_number = (
                part_number_match.group(2).upper() if part_number_match.group(2) else ""
            )
            date_info["part_number"] = part_number
            date_info["part_number_confidence"] = (
                80  # Confidence for part number extraction
            )

        # List of known date formats
        date_formats = [
            "%Y.%m.%d",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d-%m-%Y",
            "%Y_%m_%d",
            "%d%m%Y",
            "%y.%m.%d",
            "%d.%m.%y",
            "%d-%m-%y",  # 2-digit years (e.g., 87.04.22)
        ]

        # Try parsing the date
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)

                # Handle 2-digit years (e.g., 87 -> 1987 or 2087)
                air_year = str(dt.year)
                if len(air_year) == 2:
                    air_year = (
                        f"20{air_year}" if int(air_year) < 50 else f"19{air_year}"
                    )

                air_month = f"{dt.month:02d}" if dt.month else ""
                air_day = f"{dt.day:02d}" if dt.day else ""

                date_info["year"] = air_year
                date_info["year_confidence"] = 90  # High confidence
                date_info["month"] = air_month
                date_info["month_confidence"] = 90
                date_info["day"] = air_day
                date_info["day_confidence"] = 90

                return date_info
            except ValueError:
                continue

        return date_info

    def date_handle_incomplete_date(self, filename: str) -> Dict[str, Any]:
        """
        Handles incomplete date formats (e.g., 87.04.22A -> Part A).
        Handles 2-digit year formats and returns (year, month, day, part_number).

        Args:
            filename (str): The media filename.

        Returns:
            Dict[str, Any]: Extracted date components and part number with confidence scores.
        """
        date_info = {
            "year": "",
            "year_confidence": 0,
            "month": "",
            "month_confidence": 0,
            "day": "",
            "day_confidence": 0,
            "part_number": "",
            "part_number_confidence": 0,
        }

        # Regex to match incomplete date formats (e.g., 87.04.22A)
        match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})([A-Za-z]?)", filename)
        if match:
            # Handle 2-digit year (e.g., 87 -> 1987 or 2087)
            year_prefix = "19" if int(match.group(1)) > 50 else "20"
            air_year = year_prefix + match.group(1)
            air_month = match.group(2)
            air_day = match.group(3)
            part_number = match.group(4).upper() if match.group(4) else ""

            date_info["year"] = air_year
            date_info["year_confidence"] = (
                70  # Confidence for handling incomplete dates
            )
            date_info["month"] = air_month
            date_info["month_confidence"] = 70
            date_info["day"] = air_day
            date_info["day_confidence"] = 70
            date_info["part_number"] = part_number
            date_info["part_number_confidence"] = 70

            return date_info

        return date_info

    def date_infer_year_from_directory(self, file_path: Path) -> Dict[str, Any]:
        """
        Infers the year from the directory structure (e.g., parent folder names).

        Args:
            file_path (Path): The full path to the media file.

        Returns:
            Dict[str, Any]: Inferred year and confidence score.
        """
        inferred_date = {
            "year": "Unknown",
            "year_confidence": 0,
            "month": "",
            "month_confidence": 0,
            "day": "",
            "day_confidence": 0,
            "part_number": "",
            "part_number_confidence": 0,
        }

        for directory in file_path.parents:
            try:
                year_match = re.search(r"(19|20)\d{2}", str(directory))
                if year_match:
                    air_year = year_match.group(0)
                    inferred_date["year"] = air_year
                    inferred_date["year_confidence"] = (
                        50  # Confidence for directory-based inference
                    )
                    return inferred_date
            except re.error as e:
                log.error(
                    f"DateExtractor: Regex error during directory inference - {e}"
                )
                continue
            except Exception as e:
                log.error(
                    f"DateExtractor: Unexpected error during directory inference - {e}"
                )
                continue

        return inferred_date
