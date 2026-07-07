"""Pydantic models for glossary extraction validation."""
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
import re

CategoryType = Literal[
    "Character", "Location", "Organization", "Item", "Lore"
]


class AliasCategories(BaseModel):
    titles: list[str] = []
    mis_translations: list[str] = []
    other_names: list[str] = []


class Description(BaseModel):
    en: str = ""
    th: str = ""


class RawGlossaryEntry(BaseModel):
    category: CategoryType
    korean_original: str = Field(min_length=1)
    english_version: Optional[str] = ""
    thai_version: Optional[str] = ""
    aliases: dict | list = Field(default_factory=lambda: {
        "titles": [],
        "mis_translations": [],
        "other_names": [],
    })
    description: Description = Field(default_factory=Description)

    @field_validator("korean_original")
    @classmethod
    def must_contain_korean(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("korean_original must not be empty")
        return v.strip()

    @field_validator("english_version", "thai_version")
    @classmethod
    def clean_strings(cls, v: str | None) -> str:
        if v is None:
            return ""
        return v.strip()


class ChapterExtraction(BaseModel):
    """Validation result for one chapter"""
    chapter_num: int
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    errors: list[str] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Aggregate validation report across all chapters"""
    total_chapters: int = 0
    total_entries: int = 0
    valid_entries: int = 0
    invalid_entries: int = 0
    chapters_with_errors: int = 0
    chapter_details: list[ChapterExtraction] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_entries == 0:
            return 100.0
        return round(self.valid_entries / self.total_entries * 100, 1)
