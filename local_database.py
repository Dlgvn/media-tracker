"""Local JSON file database operations for the Media Tracker application."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from models import Book, BookStatus, Movie, MovieStatus


class DatabaseError(Exception):
    """Exception for database errors."""
    pass


class LocalDatabase:
    """JSON file-based local database for media tracking."""

    def __init__(self, data_dir: str = None):
        """Initialize the local database.

        Args:
            data_dir: Directory to store JSON files. Defaults to ~/.media-tracker/
        """
        if data_dir is None:
            data_dir = os.path.join(Path.home(), ".media-tracker")

        self.data_dir = data_dir
        self.movies_file = os.path.join(data_dir, "movies.json")
        self.books_file = os.path.join(data_dir, "books.json")

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Initialize files if they don't exist
        if not os.path.exists(self.movies_file):
            self._save_movies([])
        if not os.path.exists(self.books_file):
            self._save_books([])

    def _load_movies(self) -> List[dict]:
        """Load movies from JSON file."""
        try:
            with open(self.movies_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_movies(self, movies: List[dict]):
        """Save movies to JSON file."""
        with open(self.movies_file, 'w', encoding='utf-8') as f:
            json.dump(movies, f, indent=2, ensure_ascii=False)

    def _load_books(self) -> List[dict]:
        """Load books from JSON file."""
        try:
            with open(self.books_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_books(self, books: List[dict]):
        """Save books to JSON file."""
        with open(self.books_file, 'w', encoding='utf-8') as f:
            json.dump(books, f, indent=2, ensure_ascii=False)

    def _get_next_id(self, items: List[dict]) -> int:
        """Get the next available ID."""
        if not items:
            return 1
        return max(item.get("id", 0) for item in items) + 1

    # Movie operations
    def add_movie(self, movie: Movie) -> int:
        """Add a movie to the database. Returns the movie ID."""
        movies = self._load_movies()
        movie_id = self._get_next_id(movies)

        data = {
            "id": movie_id,
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
            "date_added": datetime.now(timezone.utc).isoformat(),
            "date_completed": movie.date_completed.isoformat() if movie.date_completed else None,
            "is_favorite": getattr(movie, 'is_favorite', False),
        }

        movies.append(data)
        self._save_movies(movies)
        return movie_id

    def get_movie_by_imdb_id(self, imdb_id: str) -> Optional[Movie]:
        """Get a movie by its IMDB ID."""
        movies = self._load_movies()
        for movie_data in movies:
            if movie_data.get("imdb_id") == imdb_id:
                return Movie.from_db_row(movie_data)
        return None

    def get_movies_by_status(self, status: MovieStatus) -> List[Movie]:
        """Get all movies with a specific status."""
        movies = self._load_movies()
        filtered = [m for m in movies if m.get("status") == status.value]
        # Sort by date_added descending
        filtered.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Movie.from_db_row(m) for m in filtered]

    def get_all_movies(self) -> List[Movie]:
        """Get all movies."""
        movies = self._load_movies()
        # Sort by date_added descending
        movies.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Movie.from_db_row(m) for m in movies]

    def update_movie_status(
        self, movie_id: int, status: MovieStatus, user_rating: Optional[int] = None
    ) -> bool:
        """Update movie status and optionally the user rating."""
        movies = self._load_movies()

        for movie in movies:
            if movie.get("id") == movie_id:
                movie["status"] = status.value

                if status == MovieStatus.WATCHED:
                    movie["date_completed"] = datetime.now(timezone.utc).isoformat()
                else:
                    movie["date_completed"] = None

                if user_rating is not None:
                    movie["user_rating"] = user_rating

                self._save_movies(movies)
                return True

        return False

    def delete_movie(self, movie_id: int) -> bool:
        """Delete a movie by ID."""
        movies = self._load_movies()
        original_len = len(movies)
        movies = [m for m in movies if m.get("id") != movie_id]

        if len(movies) < original_len:
            self._save_movies(movies)
            return True
        return False

    def toggle_movie_favorite(self, movie_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status for a movie."""
        movies = self._load_movies()

        for movie in movies:
            if movie.get("id") == movie_id:
                movie["is_favorite"] = is_favorite
                self._save_movies(movies)
                return True
        return False

    def get_favorite_movies(self) -> List[Movie]:
        """Get all favorite movies."""
        movies = self._load_movies()
        filtered = [m for m in movies if m.get("is_favorite", False)]
        filtered.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Movie.from_db_row(m) for m in filtered]

    # Book operations
    def add_book(self, book: Book) -> int:
        """Add a book to the database. Returns the book ID."""
        books = self._load_books()
        book_id = self._get_next_id(books)

        data = {
            "id": book_id,
            "olid": book.olid,
            "title": book.title,
            "author": book.author,
            "subjects": book.subjects,
            "publish_year": book.publish_year,
            "cover_url": book.cover_url,
            "status": book.status.value,
            "user_rating": book.user_rating,
            "date_added": datetime.now(timezone.utc).isoformat(),
            "date_completed": book.date_completed.isoformat() if book.date_completed else None,
            "is_favorite": getattr(book, 'is_favorite', False),
        }

        books.append(data)
        self._save_books(books)
        return book_id

    def get_book_by_olid(self, olid: str) -> Optional[Book]:
        """Get a book by its Open Library ID."""
        books = self._load_books()
        for book_data in books:
            if book_data.get("olid") == olid:
                return Book.from_db_row(book_data)
        return None

    def get_books_by_status(self, status: BookStatus) -> List[Book]:
        """Get all books with a specific status."""
        books = self._load_books()
        filtered = [b for b in books if b.get("status") == status.value]
        filtered.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Book.from_db_row(b) for b in filtered]

    def get_all_books(self) -> List[Book]:
        """Get all books."""
        books = self._load_books()
        books.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Book.from_db_row(b) for b in books]

    def update_book_status(
        self, book_id: int, status: BookStatus, user_rating: Optional[int] = None
    ) -> bool:
        """Update book status and optionally the user rating."""
        books = self._load_books()

        for book in books:
            if book.get("id") == book_id:
                book["status"] = status.value

                if status == BookStatus.READ:
                    book["date_completed"] = datetime.now(timezone.utc).isoformat()
                else:
                    book["date_completed"] = None

                if user_rating is not None:
                    book["user_rating"] = user_rating

                self._save_books(books)
                return True

        return False

    def delete_book(self, book_id: int) -> bool:
        """Delete a book by ID."""
        books = self._load_books()
        original_len = len(books)
        books = [b for b in books if b.get("id") != book_id]

        if len(books) < original_len:
            self._save_books(books)
            return True
        return False

    def toggle_book_favorite(self, book_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status for a book."""
        books = self._load_books()

        for book in books:
            if book.get("id") == book_id:
                book["is_favorite"] = is_favorite
                self._save_books(books)
                return True
        return False

    def get_favorite_books(self) -> List[Book]:
        """Get all favorite books."""
        books = self._load_books()
        filtered = [b for b in books if b.get("is_favorite", False)]
        filtered.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Book.from_db_row(b) for b in filtered]

    # Statistics
    def get_movie_stats(self) -> dict:
        """Get movie statistics."""
        movies = self._load_movies()
        stats = {}

        for status in MovieStatus:
            count = sum(1 for m in movies if m.get("status") == status.value)
            stats[status.value] = count

        # Get average rating
        ratings = [m["user_rating"] for m in movies if m.get("user_rating") is not None]
        if ratings:
            stats["avg_user_rating"] = round(sum(ratings) / len(ratings), 1)
        else:
            stats["avg_user_rating"] = None

        # Get genre counts
        genres = {}
        for movie in movies:
            if movie.get("genre"):
                for g in movie["genre"].split(", "):
                    genres[g] = genres.get(g, 0) + 1
        stats["top_genres"] = sorted(genres.items(), key=lambda x: -x[1])[:5]

        return stats

    def get_book_stats(self) -> dict:
        """Get book statistics."""
        books = self._load_books()
        stats = {}

        for status in BookStatus:
            count = sum(1 for b in books if b.get("status") == status.value)
            stats[status.value] = count

        # Get average rating
        ratings = [b["user_rating"] for b in books if b.get("user_rating") is not None]
        if ratings:
            stats["avg_user_rating"] = round(sum(ratings) / len(ratings), 1)
        else:
            stats["avg_user_rating"] = None

        # Get subject counts
        subjects = {}
        for book in books:
            if book.get("subjects"):
                for s in book["subjects"].split(", ")[:3]:
                    subjects[s] = subjects.get(s, 0) + 1
        stats["top_subjects"] = sorted(subjects.items(), key=lambda x: -x[1])[:5]

        return stats
