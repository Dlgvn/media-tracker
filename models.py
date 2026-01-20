"""Data models for the Media Tracker application."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class MovieStatus(Enum):
    WATCHED = "watched"
    WATCHING = "watching"
    WANT_TO_WATCH = "want_to_watch"


class BookStatus(Enum):
    READ = "read"
    READING = "reading"
    WANT_TO_READ = "want_to_read"


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
        )
