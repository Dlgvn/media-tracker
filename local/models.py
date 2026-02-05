"""Data models for the Media Tracker application."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class MovieStatus(Enum):
    WATCHED = "watched"
    WATCHING = "watching"
    WANT_TO_WATCH = "want_to_watch"


class BookStatus(Enum):
    READ = "read"
    READING = "reading"
    WANT_TO_READ = "want_to_read"


class SeriesStatus(Enum):
    WATCHING = "watching"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"
    WANT_TO_WATCH = "want_to_watch"


@dataclass
class Movie:
    id: Optional[int]
    imdb_id: str
    title: str
    year: Optional[str]
    genre: Optional[str]
    director: Optional[str]
    plot: Optional[str]
    poster_url: Optional[str]
    imdb_rating: Optional[str]
    status: MovieStatus
    user_rating: Optional[int] = None
    date_added: Optional[datetime] = None
    date_completed: Optional[datetime] = None
    is_favorite: bool = False
    notes: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Movie":
        """Create a Movie instance from a database row."""
        date_added = row.get("date_added")
        date_completed = row.get("date_completed")
        return cls(
            id=row.get("id"),
            imdb_id=row["imdb_id"],
            title=row["title"],
            year=row.get("year"),
            genre=row.get("genre"),
            director=row.get("director"),
            plot=row.get("plot"),
            poster_url=row.get("poster_url"),
            imdb_rating=row.get("imdb_rating"),
            status=MovieStatus(row["status"]),
            user_rating=row.get("user_rating"),
            date_added=datetime.fromisoformat(date_added.replace("Z", "+00:00")) if date_added else None,
            date_completed=datetime.fromisoformat(date_completed.replace("Z", "+00:00")) if date_completed else None,
            is_favorite=row.get("is_favorite", False),
            notes=row.get("notes"),
        )


@dataclass
class Book:
    id: Optional[int]
    olid: str
    title: str
    author: Optional[str]
    subjects: Optional[str]
    publish_year: Optional[int]
    cover_url: Optional[str]
    status: BookStatus
    user_rating: Optional[int] = None
    date_added: Optional[datetime] = None
    date_completed: Optional[datetime] = None
    is_favorite: bool = False
    notes: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Book":
        """Create a Book instance from a database row."""
        date_added = row.get("date_added")
        date_completed = row.get("date_completed")
        return cls(
            id=row.get("id"),
            olid=row["olid"],
            title=row["title"],
            author=row.get("author"),
            subjects=row.get("subjects"),
            publish_year=row.get("publish_year"),
            cover_url=row.get("cover_url"),
            status=BookStatus(row["status"]),
            user_rating=row.get("user_rating"),
            date_added=datetime.fromisoformat(date_added.replace("Z", "+00:00")) if date_added else None,
            date_completed=datetime.fromisoformat(date_completed.replace("Z", "+00:00")) if date_completed else None,
            is_favorite=row.get("is_favorite", False),
            notes=row.get("notes"),
        )


@dataclass
class Series:
    id: Optional[int]
    imdb_id: str
    title: str
    year: Optional[str]
    genre: Optional[str]
    plot: Optional[str]
    poster_url: Optional[str]
    imdb_rating: Optional[str]
    total_seasons: int
    status: SeriesStatus
    user_rating: Optional[int] = None
    date_added: Optional[datetime] = None
    is_favorite: bool = False
    notes: Optional[str] = None
    current_season: int = 1
    current_episode: int = 1
    episodes_watched: List[dict] = field(default_factory=list)

    @classmethod
    def from_db_row(cls, row: dict) -> "Series":
        """Create a Series instance from a database row."""
        date_added = row.get("date_added")
        return cls(
            id=row.get("id"),
            imdb_id=row["imdb_id"],
            title=row["title"],
            year=row.get("year"),
            genre=row.get("genre"),
            plot=row.get("plot"),
            poster_url=row.get("poster_url"),
            imdb_rating=row.get("imdb_rating"),
            total_seasons=row.get("total_seasons", 1),
            status=SeriesStatus(row["status"]),
            user_rating=row.get("user_rating"),
            date_added=datetime.fromisoformat(date_added.replace("Z", "+00:00")) if date_added else None,
            is_favorite=row.get("is_favorite", False),
            notes=row.get("notes"),
            current_season=row.get("current_season", 1),
            current_episode=row.get("current_episode", 1),
            episodes_watched=row.get("episodes_watched", []),
        )
