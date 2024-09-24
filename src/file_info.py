# src/file_info.py

from dataclasses import dataclass
from .custom_logger import log


@dataclass
class FileInfo:
    original_filename: str
    original_filepath: str
    modified_filename: str
    modified_filepath: str

    def update_filename(self, new_filename: str) -> None:
        self.modified_filename = new_filename
        log.debug(f"Updated filename to {new_filename}", style="cyan")

    def update_filepath(self, new_filepath: str) -> None:
        self.modified_filepath = new_filepath
        log.debug(f"Updated filepath to {new_filepath}", style="cyan")

    def remove_from_filename(self, text: str) -> None:
        self.modified_filename = self.modified_filename.replace(text, "")
        log.debug(
            f"Removed {text} from filename. New filename is {self.modified_filename}",
            style="cyan",
        )

    def remove_from_filepath(self, text: str) -> None:
        self.modified_filepath = self.modified_filepath.replace(text, "")
        log.debug(
            f"Removed {text} from filepath. New filepath is {self.modified_filepath}",
            style="cyan",
        )
