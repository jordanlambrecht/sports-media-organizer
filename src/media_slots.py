# src/media_slots.py

from dataclasses import asdict, dataclass, fields, field
from typing import Optional, Dict, Any
from .custom_logger import log


@dataclass
class SlotInfo:
    value: Optional[str] = None
    confidence: float = 0.0
    is_filled: bool = False
    # TODO: load confidence thresholds from config into slot dataclass
    # confidence_threshold: int = 0


@dataclass
class MediaSlots:
    league_name: SlotInfo = field(default_factory=SlotInfo)
    event_name: SlotInfo = field(default_factory=SlotInfo)
    air_year: SlotInfo = field(default_factory=SlotInfo)
    air_month: SlotInfo = field(default_factory=SlotInfo)
    air_day: SlotInfo = field(default_factory=SlotInfo)
    season_name: SlotInfo = field(default_factory=SlotInfo)
    episode_title: SlotInfo = field(default_factory=SlotInfo)
    episode_part: SlotInfo = field(default_factory=SlotInfo)
    codec: SlotInfo = field(default_factory=SlotInfo)
    fps: SlotInfo = field(default_factory=SlotInfo)
    resolution: SlotInfo = field(default_factory=SlotInfo)
    release_format: SlotInfo = field(default_factory=SlotInfo)
    release_type: SlotInfo = field(default_factory=SlotInfo)
    release_group: SlotInfo = field(default_factory=SlotInfo)
    extension: SlotInfo = field(default_factory=SlotInfo)

    def fill_slot(
        self, slot_name: str, value: str, confidence: float, config: Dict[str, Any]
    ) -> None:
        """
        Fill a slot with the extracted value based on confidence.

        Args:
            slot_name (str): Name of the slot to fill.
            value (str): Extracted value.
            confidence (float): Confidence level of the extraction.
            config (Dict[str, Any]): Configuration settings.
        """

        if not hasattr(self, slot_name):
            log.error(f"Attempted to fill an invalid slot: {slot_name}")
            raise AttributeError(f"MediaSlots has no slot named '{slot_name}'.")

        confidence_threshold = config.get("confidence_threshold", 0.5)
        weight = config.get("confidence_weights", {}).get(slot_name, 1.0)
        required_confidence = confidence_threshold * weight

        slot = getattr(self, slot_name)
        if confidence >= required_confidence:
            slot.value = value
            slot.confidence = confidence
            slot.is_filled = True
        else:
            slot.value = None
            slot.confidence = 0.0
            slot.is_filled = False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the MediaSlots instance to a dictionary, excluding unfilled slots.
        """
        return {
            slot_name: slot_info.value
            for slot_name, slot_info in asdict(self).items()
            if slot_info["is_filled"] and slot_info["value"] is not None
        }

    def get_confidence(self, slot_name: str) -> float:
        """
        Get the confidence score for a specific slot.

        Args:
            slot_name (str): Name of the slot.

        Returns:
            float: Confidence score of the slot.
        """
        return getattr(self, slot_name).confidence

    def is_slot_filled(self, slot_name: str) -> bool:
        """
        Check if a slot has been filled.

        Args:
            slot_name (str): Name of the slot to check.

        Returns:
            bool: True if the slot is filled, False otherwise.
        """
        slot = getattr(self, slot_name, None)
        if slot is None:
            raise ValueError(f"Invalid slot name: {slot_name}")
        return slot.is_filled
