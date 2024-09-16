#!/usr/bin/env python3
import os
import re
import shutil
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('media_organizer.log'),
        logging.StreamHandler()
    ]
)

class MediaOrganizer:
    def __init__(self, source_dir, dest_dir, dry_run=False, max_workers=4):
        self.source_dir = source_dir
        self.dest_dir = dest_dir
        self.dry_run = dry_run
        self.max_workers = max_workers
        self.patterns = self.compile_patterns()
        self.processed_files = 0
        self.failed_files = []
        self.dry_run_actions = []  # List to store planned actions during dry run

    def compile_patterns(self):
        """
        Compile regex patterns for performance.
        """
        patterns = [
            # Pattern: League.Event.Date.Title
            re.compile(r'^(?P<league>[A-Z]{2,5})(?:[.\s_-]+(?P<subleague>[^.\s_-]+))?[.\s_-]+(?P<event>.+?)[.\s_-]+(?P<date>\d{4}[.\s_-]\d{2}[.\s_-]\d{2}[a-z]?)', re.IGNORECASE),
            # Pattern: Date - League Event Title
            re.compile(r'^(?P<date>\d{4}[.\s_-]\d{2}[.\s_-]\d{2}[a-z]?)[.\s_-]+(?P<league>[A-Z]{2,5})(?:[.\s_-]+(?P<subleague>[^.\s_-]+))?[.\s_-]+(?P<event>.+)', re.IGNORECASE),
            # Pattern: League.Year.Event
            re.compile(r'^(?P<league>[A-Z]{2,5})(?:[.\s_-]+(?P<subleague>[^.\s_-]+))?[.\s_-]+(?P<year>\d{4})(?:[.\s_-]+(?P<event>.+))?', re.IGNORECASE),
            # Pattern: Date - Event
            re.compile(r'^(?P<date>\d{4}[.\s_-]\d{2}[.\s_-]\d{2}[a-z]?)[.\s_-]+(?P<event>.+)', re.IGNORECASE),
            # Pattern: League.Event
            re.compile(r'^(?P<league>[A-Z]{2,5})(?:[.\s_-]+(?P<subleague>[^.\s_-]+))?[.\s_-]+(?P<event>.+)', re.IGNORECASE),
            # Pattern: Filenames starting with numbers
            re.compile(r'^(?P<number>\d+)[.\s_-]+(?P<date>\d{4}[.\s_-]\d{2}[.\s_-]\d{2})(?:[.\s_-]+(?P<event>.+))?', re.IGNORECASE),
            # Pattern: Event with Date at the End
            re.compile(r'^(?P<league>[A-Z]{2,5})(?:[.\s_-]+(?P<subleague>[^.\s_-]+))?[.\s_-]+(?P<event>.+?)[.\s_-]+(?P<date>\d{4}[.\s_-]\d{2}[.\s_-]\d{2}[a-z]?)$', re.IGNORECASE),
        ]
        return patterns

    def extract_info(self, file_path):
        """
        Extract league, date, event title, and other metadata from the filename.
        """
        filename = os.path.basename(file_path)
        league = ''
        subleague = ''
        event_date = ''
        event_title = ''
        season = ''
        sequence = ''
        number = ''

        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]

        # Attempt to match each pattern
        for pattern in self.patterns:
            match = pattern.match(name_without_ext)
            if match:
                groups = match.groupdict()
                league = groups.get('league', '').strip()
                subleague = groups.get('subleague', '').strip()
                event = groups.get('event', '').strip()
                date = groups.get('date', '').strip()
                year = groups.get('year', '').strip()
                number = groups.get('number', '').strip()

                # Process date
                if date:
                    event_date, season = self.parse_date(date)
                elif year:
                    season = f"Season {year}"
                else:
                    season = self.infer_season(file_path, '')

                # Handle sequence identifiers
                sequence_match = re.search(r'(\d{4}[.\s_-]\d{2}[.\s_-]\d{2})([a-z])', date, re.IGNORECASE)
                if sequence_match:
                    date = sequence_match.group(1)
                    sequence = sequence_match.group(2)
                    event_date, season = self.parse_date(date)
                    sequence = ord(sequence.lower()) - 96  # Convert 'a' to 1, 'b' to 2, etc.

                # Set event title
                event_title = event.replace('.', ' ').replace('_', ' ').strip()

                # Include number in event title if present
                if number:
                    event_title = f"{number} {event_title}"

                # Infer league if missing
                if not league:
                    league = self.infer_league(file_path)
                if subleague:
                    league = f"{league} {subleague}"

                break  # Stop after first successful match

        # Handle outliers
        if not league:
            league = self.infer_league(file_path)
        if not season:
            season = self.infer_season(file_path, event_date)
        if not event_date:
            event_date = self.infer_event_date(season)

        # Clean up league and event title
        league = league.strip().upper()
        event_title = event_title.strip()

        # Construct destination subdirectory
        dest_subdir = league
        if 'WRESTLEMANIA' in league.upper() or 'WRESTLEMANIA' in event_title.upper():
            dest_subdir = 'WWE WrestleMania'
        elif 'ROYAL RUMBLE' in league.upper() or 'ROYAL RUMBLE' in event_title.upper():
            dest_subdir = 'WWE Royal Rumble'
        elif 'SURVIVOR SERIES' in league.upper() or 'SURVIVOR SERIES' in event_title.upper():
            dest_subdir = 'WWE Survivor Series'
        elif 'NJPW VS UWF' in league.upper() or 'NJPW VS UWF' in event_title.upper():
            dest_subdir = 'NJPW Vs UWF'
        elif 'CLASH OF THE CHAMPIONS' in event_title.upper():
            dest_subdir = 'NWA WCW'

        # Reconstruct filename
        new_filename = f"{league}"
        if event_date:
            new_filename += f"-{event_date.replace('-', '.')}"
        if sequence:
            new_filename += f".{str(sequence).zfill(2)}"
        if event_title:
            new_filename += f".{event_title.replace(' ', '-')}"

        # Append file extension
        _, extension = os.path.splitext(file_path)
        new_filename += extension

        logging.debug(f"Extracted Info - League: {league}, Season: {season}, Date: {event_date}, Event: {event_title}")

        return dest_subdir, season, new_filename

    def parse_date(self, date_str):
        """
        Parse date from string and return formatted date and season.
        """
        date_formats = ['%Y.%m.%d', '%Y-%m-%d', '%Y_%m_%d', '%Y%m%d', '%Y %m %d']
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                event_date = dt.strftime('%Y-%m-%d')
                season = f"Season {dt.year}"
                return event_date, season
            except ValueError:
                continue
        logging.warning(f"Failed to parse date: {date_str}")
        return '', ''

    def infer_league(self, file_path):
        """
        Infer league from parent directory or default value.
        """
        parent_dir = Path(file_path).parent
        for part in parent_dir.parts[::-1]:
            if part.isupper() and len(part) <= 10:
                return part
        return 'UNKNOWN'

    def infer_season(self, file_path, event_date):
        """
        Infer season from event date or parent directory.
        """
        if event_date:
            year = event_date[:4]
            return f"Season {year}"
        parent_dir = Path(file_path).parent
        year_match = re.search(r'(19|20)\d{2}', str(parent_dir))
        if year_match:
            return f"Season {year_match.group(0)}"
        return f"Season {datetime.now().year}"

    def infer_event_date(self, season):
        """
        Infer event date from season or default.
        """
        year_match = re.search(r'(19|20)\d{2}', season)
        if year_match:
            return f"{year_match.group(0)}-01-01"
        return '1970-01-01'  # Default date

    def create_folder_structure(self, dest_subdir, season):
        """
        Create the destination folder structure if it doesn't exist.
        """
        dest_folder = os.path.join(self.dest_dir, dest_subdir, season)
        if not self.dry_run:
            os.makedirs(dest_folder, exist_ok=True)
        logging.debug(f"Destination folder: {dest_folder}")
        return dest_folder

    def rename_and_hardlink(self, src, dest_folder, new_filename):
        """
        Hardlink the file to the destination with the new filename.
        """
        dest_path = os.path.join(dest_folder, new_filename)

        # Hardlink the file
        try:
            if not os.path.exists(dest_path):
                if not self.dry_run:
                    os.link(src, dest_path)
                    logging.info(f"Hardlinked: {src} -> {dest_path}")
                else:
                    logging.info(f"Dry Run - Planned Hardlink: {src} -> {dest_path}")
                    # Record the planned action
                    self.dry_run_actions.append((src, dest_path))
                self.processed_files += 1
            else:
                logging.warning(f"File already exists: {dest_path}")
        except Exception as e:
            logging.error(f"Failed to hardlink {src} to {dest_path}: {e}")
            self.failed_files.append(src)

    def process_file(self, file_path):
        """
        Process an individual file.
        """
        dest_subdir, season, new_filename = self.extract_info(file_path)

        dest_folder = self.create_folder_structure(dest_subdir, season)

        self.rename_and_hardlink(file_path, dest_folder, new_filename)

    def scan_directory(self):
        """
        Walk through the source directory and process files.
        """
        files_to_process = []
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                # Ignore hidden files
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    files_to_process.append(file_path)

        # Process files concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.process_file, file): file for file in files_to_process}
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error processing file {file}: {e}")

        logging.info(f"Processing complete. Files processed: {self.processed_files}, Failed files: {len(self.failed_files)}")
        if self.failed_files:
            logging.error(f"Failed files: {self.failed_files}")

        # Write dry run report if applicable
        if self.dry_run:
            self.write_dry_run_report()

    def write_dry_run_report(self):
        """
        Write the planned conversions to a text file during dry run.
        """
        report_file = 'dry_run_report.txt'
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("Dry Run Report - Planned Conversions\n")
                f.write("====================================\n\n")
                for src, dest in self.dry_run_actions:
                    f.write(f"Source: {src}\n")
                    f.write(f"Destination: {dest}\n")
                    f.write("--------------------------------------------------\n")
            logging.info(f"Dry run report written to {report_file}")
        except Exception as e:
            logging.error(f"Failed to write dry run report: {e}")

def get_user_inputs():
    """
    Prompt the user for inputs instead of using command-line arguments.
    """
    print("Welcome to Media Organizer")
    print("--------------------------")
    source_dir = input("Enter the source directory path: ").strip()
    while not os.path.isdir(source_dir):
        print("Invalid source directory. Please try again.")
        source_dir = input("Enter the source directory path: ").strip()

    dest_dir = input("Enter the destination directory path: ").strip()
    while not os.path.isdir(dest_dir):
        try:
            os.makedirs(dest_dir, exist_ok=True)
            break
        except Exception as e:
            print(f"Invalid destination directory. Error: {e}")
            dest_dir = input("Enter the destination directory path: ").strip()

    dry_run_input = input("Perform a dry run? (yes/no): ").strip().lower()
    dry_run = dry_run_input in ['yes', 'y']

    while True:
        workers_input = input("Enter the number of worker threads (default 4): ").strip()
        if not workers_input:
            max_workers = 4
            break
        try:
            max_workers = int(workers_input)
            if max_workers <= 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a valid positive integer.")

    return source_dir, dest_dir, dry_run, max_workers

if __name__ == "__main__":
    source_dir, dest_dir, dry_run, max_workers = get_user_inputs()
    organizer = MediaOrganizer(
        source_dir=source_dir,
        dest_dir=dest_dir,
        dry_run=dry_run,
        max_workers=max_workers
    )
    organizer.scan_directory()