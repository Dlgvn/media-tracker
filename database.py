"""Supabase database operations for the Media Tracker application."""

import os
from datetime import datetime, timezone
from typing import List, Optional

from supabase import create_client, Client

from models import Book, BookStatus, Movie, MovieStatus


class DatabaseError(Exception):
    """Exception for database errors."""
    pass


class Database:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise DatabaseError(
                "Supabase credentials not found.\n"
                "Please set SUPABASE_URL and SUPABASE_KEY environment variables."
            )

        self.client: Client = create_client(url, key)

    # Movie operations
    def add_movie(self, movie: Movie) -> int:
        """Add a movie to the database. Returns the movie ID."""
        data = {
            "imdb_id": movie.imdb_id,
            "title": movie.title,
            "year": movie.year,
            "genre": movie.genre,
            "director": movie.director,
            "plot": movie.plot,
            "poster_url": movie.poster_url,
            "imdb_rating": movie.imdb_rating,
            "status": movie.status.value,
            "user_rating": movie.user_rating,
            "date_completed": movie.date_completed.isoformat() if movie.date_completed else None,
            "is_favorite": movie.is_favorite,
        }

        result = self.client.table("movies").insert(data).execute()
        return result.data[0]["id"]

    def get_movie_by_imdb_id(self, imdb_id: str) -> Optional[Movie]:
        """Get a movie by its IMDB ID."""
        result = self.client.table("movies").select("*").eq("imdb_id", imdb_id).execute()
        if result.data:
            return Movie.from_db_row(result.data[0])
        return None

    def get_movies_by_status(self, status: MovieStatus) -> List[Movie]:
        """Get all movies with a specific status."""
        result = (
            self.client.table("movies")
            .select("*")
            .eq("status", status.value)
            .order("date_added", desc=True)
            .execute()
        )
        return [Movie.from_db_row(row) for row in result.data]

    def get_all_movies(self) -> List[Movie]:
        """Get all movies."""
        result = (
            self.client.table("movies")
            .select("*")
            .order("date_added", desc=True)
            .execute()
        )
        return [Movie.from_db_row(row) for row in result.data]

    def update_movie_status(
        self, movie_id: int, status: MovieStatus, user_rating: Optional[int] = None
    ) -> bool:
        """Update movie status and optionally the user rating."""
        data = {"status": status.value}

        if status == MovieStatus.WATCHED:
            data["date_completed"] = datetime.now(timezone.utc).isoformat()
        else:
            data["date_completed"] = None

        if user_rating is not None:
            data["user_rating"] = user_rating

        result = self.client.table("movies").update(data).eq("id", movie_id).execute()
        return len(result.data) > 0

    def delete_movie(self, movie_id: int) -> bool:
        """Delete a movie by ID."""
        result = self.client.table("movies").delete().eq("id", movie_id).execute()
        return len(result.data) > 0

    def toggle_movie_favorite(self, movie_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status for a movie."""
        result = (
            self.client.table("movies")
            .update({"is_favorite": is_favorite})
            .eq("id", movie_id)
            .execute()
        )
        return len(result.data) > 0

    def get_favorite_movies(self) -> List[Movie]:
        """Get all favorite movies."""
        result = (
            self.client.table("movies")
            .select("*")
            .eq("is_favorite", True)
            .order("date_added", desc=True)
            .execute()
        )
        return [Movie.from_db_row(row) for row in result.data]

    # Book operations
    def add_book(self, book: Book) -> int:
        """Add a book to the database. Returns the book ID."""
        data = {
            "olid": book.olid,
            "title": book.title,
            "author": book.author,
            "subjects": book.subjects,
            "publish_year": book.publish_year,
            "cover_url": book.cover_url,
            "status": book.status.value,
            "user_rating": book.user_rating,
            "date_completed": book.date_completed.isoformat() if book.date_completed else None,
            "is_favorite": book.is_favorite,
        }

        result = self.client.table("books").insert(data).execute()
        return result.data[0]["id"]

    def get_book_by_olid(self, olid: str) -> Optional[Book]:
        """Get a book by its Open Library ID."""
        result = self.client.table("books").select("*").eq("olid", olid).execute()
        if result.data:
            return Book.from_db_row(result.data[0])
        return None

    def get_books_by_status(self, status: BookStatus) -> List[Book]:
        """Get all books with a specific status."""
        result = (
            self.client.table("books")
            .select("*")
            .eq("status", status.value)
            .order("date_added", desc=True)
            .execute()
        )
        return [Book.from_db_row(row) for row in result.data]

    def get_all_books(self) -> List[Book]:
        """Get all books."""
        result = (
            self.client.table("books")
            .select("*")
            .order("date_added", desc=True)
            .execute()
        )
        return [Book.from_db_row(row) for row in result.data]

    def update_book_status(
        self, book_id: int, status: BookStatus, user_rating: Optional[int] = None
    ) -> bool:
        """Update book status and optionally the user rating."""
        data = {"status": status.value}

        if status == BookStatus.READ:
            data["date_completed"] = datetime.now(timezone.utc).isoformat()
        else:
            data["date_completed"] = None

        if user_rating is not None:
            data["user_rating"] = user_rating

        result = self.client.table("books").update(data).eq("id", book_id).execute()
        return len(result.data) > 0

    def delete_book(self, book_id: int) -> bool:
        """Delete a book by ID."""
        result = self.client.table("books").delete().eq("id", book_id).execute()
        return len(result.data) > 0

    def toggle_book_favorite(self, book_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status for a book."""
        result = (
            self.client.table("books")
            .update({"is_favorite": is_favorite})
            .eq("id", book_id)
            .execute()
        )
        return len(result.data) > 0

    def get_favorite_books(self) -> List[Book]:
        """Get all favorite books."""
        result = (
            self.client.table("books")
            .select("*")
            .eq("is_favorite", True)
            .order("date_added", desc=True)
            .execute()
        )
        return [Book.from_db_row(row) for row in result.data]

    # Statistics
    def get_movie_stats(self) -> dict:
        """Get movie statistics."""
        stats = {}

        for status in MovieStatus:
            result = (
                self.client.table("movies")
                .select("id", count="exact")
                .eq("status", status.value)
                .execute()
            )
            stats[status.value] = result.count or 0

        # Get average rating
        result = (
            self.client.table("movies")
            .select("user_rating")
            .not_.is_("user_rating", "null")
            .execute()
        )
        if result.data:
            ratings = [r["user_rating"] for r in result.data]
            stats["avg_user_rating"] = round(sum(ratings) / len(ratings), 1)
        else:
            stats["avg_user_rating"] = None

        # Get genre counts
        result = self.client.table("movies").select("genre").not_.is_("genre", "null").execute()
        genres = {}
        for row in result.data:
            if row["genre"]:
                for g in row["genre"].split(", "):
                    genres[g] = genres.get(g, 0) + 1
        stats["top_genres"] = sorted(genres.items(), key=lambda x: -x[1])[:5]

        return stats

    def get_book_stats(self) -> dict:
        """Get book statistics."""
        stats = {}

        for status in BookStatus:
            result = (
                self.client.table("books")
                .select("id", count="exact")
                .eq("status", status.value)
                .execute()
            )
            stats[status.value] = result.count or 0

        # Get average rating
        result = (
            self.client.table("books")
            .select("user_rating")
            .not_.is_("user_rating", "null")
            .execute()
        )
        if result.data:
            ratings = [r["user_rating"] for r in result.data]
            stats["avg_user_rating"] = round(sum(ratings) / len(ratings), 1)
        else:
            stats["avg_user_rating"] = None

        # Get subject counts
        result = self.client.table("books").select("subjects").not_.is_("subjects", "null").execute()
        subjects = {}
        for row in result.data:
            if row["subjects"]:
                for s in row["subjects"].split(", ")[:3]:
                    subjects[s] = subjects.get(s, 0) + 1
        stats["top_subjects"] = sorted(subjects.items(), key=lambda x: -x[1])[:5]

        return stats
