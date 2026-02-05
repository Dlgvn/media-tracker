"""Local JSON file database operations for the Media Tracker application."""

import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from models import Book, BookStatus, Movie, MovieStatus, Series, SeriesStatus


class DatabaseError(Exception):
    """Exception for database errors."""
    pass


class Database:
    """JSON file-based local database for media tracking."""

    def __init__(self, data_dir: str = None):
        """Initialize the local database.

        Args:
            data_dir: Directory to store JSON files. Defaults to data/ in project folder.
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "data")

        self.data_dir = data_dir
        self.movies_file = os.path.join(data_dir, "movies.json")
        self.books_file = os.path.join(data_dir, "books.json")
        self.series_file = os.path.join(data_dir, "series.json")
        self.search_history_file = os.path.join(data_dir, "search_history.json")

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Initialize files if they don't exist
        if not os.path.exists(self.movies_file):
            self._save_movies([])
        if not os.path.exists(self.books_file):
            self._save_books([])
        if not os.path.exists(self.series_file):
            self._save_series([])
        if not os.path.exists(self.search_history_file):
            self._save_search_history({"movies": [], "books": [], "series": []})

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

    def _load_series(self) -> List[dict]:
        """Load series from JSON file."""
        try:
            with open(self.series_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_series(self, series: List[dict]):
        """Save series to JSON file."""
        with open(self.series_file, 'w', encoding='utf-8') as f:
            json.dump(series, f, indent=2, ensure_ascii=False)

    def _load_search_history(self) -> dict:
        """Load search history from JSON file."""
        try:
            with open(self.search_history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"movies": [], "books": [], "series": []}

    def _save_search_history(self, history: dict):
        """Save search history to JSON file."""
        with open(self.search_history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

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
            "notes": getattr(movie, 'notes', None),
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

    def update_movie_notes(self, movie_id: int, notes: Optional[str]) -> bool:
        """Update notes for a movie."""
        movies = self._load_movies()
        for movie in movies:
            if movie.get("id") == movie_id:
                movie["notes"] = notes
                self._save_movies(movies)
                return True
        return False

    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """Get a movie by its ID."""
        movies = self._load_movies()
        for movie_data in movies:
            if movie_data.get("id") == movie_id:
                return Movie.from_db_row(movie_data)
        return None

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
            "notes": getattr(book, 'notes', None),
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

    def update_book_notes(self, book_id: int, notes: Optional[str]) -> bool:
        """Update notes for a book."""
        books = self._load_books()
        for book in books:
            if book.get("id") == book_id:
                book["notes"] = notes
                self._save_books(books)
                return True
        return False

    def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Get a book by its ID."""
        books = self._load_books()
        for book_data in books:
            if book_data.get("id") == book_id:
                return Book.from_db_row(book_data)
        return None

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

    # Search History
    def add_to_search_history(self, query: str, media_type: str, max_items: int = 20) -> None:
        """Add a search query to history."""
        history = self._load_search_history()
        key = f"{media_type}s" if not media_type.endswith('s') else media_type

        if key not in history:
            history[key] = []

        # Remove if already exists (to move to front)
        if query in history[key]:
            history[key].remove(query)

        # Add to front
        history[key].insert(0, query)

        # Trim to max items
        history[key] = history[key][:max_items]

        self._save_search_history(history)

    def get_search_history(self, media_type: str) -> List[str]:
        """Get search history for a media type."""
        history = self._load_search_history()
        key = f"{media_type}s" if not media_type.endswith('s') else media_type
        return history.get(key, [])

    def clear_search_history(self, media_type: str = None) -> None:
        """Clear search history. If media_type is None, clear all."""
        if media_type is None:
            self._save_search_history({"movies": [], "books": [], "series": []})
        else:
            history = self._load_search_history()
            key = f"{media_type}s" if not media_type.endswith('s') else media_type
            history[key] = []
            self._save_search_history(history)

    # Recent Items
    def get_recent_items(self, days: int = 7, limit: int = 20) -> dict:
        """Get recently added items across all media types."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        result = {"movies": [], "books": [], "series": []}

        # Recent movies
        movies = self._load_movies()
        recent_movies = [m for m in movies if m.get("date_added", "") >= cutoff_str]
        recent_movies.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        result["movies"] = [Movie.from_db_row(m) for m in recent_movies[:limit]]

        # Recent books
        books = self._load_books()
        recent_books = [b for b in books if b.get("date_added", "") >= cutoff_str]
        recent_books.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        result["books"] = [Book.from_db_row(b) for b in recent_books[:limit]]

        # Recent series
        series = self._load_series()
        recent_series = [s for s in series if s.get("date_added", "") >= cutoff_str]
        recent_series.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        result["series"] = [Series.from_db_row(s) for s in recent_series[:limit]]

        return result

    # Bulk Operations
    def bulk_update_movie_status(self, movie_ids: List[int], status: MovieStatus) -> int:
        """Update status for multiple movies. Returns count of updated movies."""
        movies = self._load_movies()
        updated = 0

        for movie in movies:
            if movie.get("id") in movie_ids:
                movie["status"] = status.value
                if status == MovieStatus.WATCHED:
                    movie["date_completed"] = datetime.now(timezone.utc).isoformat()
                else:
                    movie["date_completed"] = None
                updated += 1

        if updated > 0:
            self._save_movies(movies)

        return updated

    def bulk_delete_movies(self, movie_ids: List[int]) -> int:
        """Delete multiple movies. Returns count of deleted movies."""
        movies = self._load_movies()
        original_len = len(movies)
        movies = [m for m in movies if m.get("id") not in movie_ids]
        deleted = original_len - len(movies)

        if deleted > 0:
            self._save_movies(movies)

        return deleted

    def bulk_update_book_status(self, book_ids: List[int], status: BookStatus) -> int:
        """Update status for multiple books. Returns count of updated books."""
        books = self._load_books()
        updated = 0

        for book in books:
            if book.get("id") in book_ids:
                book["status"] = status.value
                if status == BookStatus.READ:
                    book["date_completed"] = datetime.now(timezone.utc).isoformat()
                else:
                    book["date_completed"] = None
                updated += 1

        if updated > 0:
            self._save_books(books)

        return updated

    def bulk_delete_books(self, book_ids: List[int]) -> int:
        """Delete multiple books. Returns count of deleted books."""
        books = self._load_books()
        original_len = len(books)
        books = [b for b in books if b.get("id") not in book_ids]
        deleted = original_len - len(books)

        if deleted > 0:
            self._save_books(books)

        return deleted

    # Series Operations
    def add_series(self, series: Series) -> int:
        """Add a series to the database. Returns the series ID."""
        all_series = self._load_series()
        series_id = self._get_next_id(all_series)

        data = {
            "id": series_id,
            "imdb_id": series.imdb_id,
            "title": series.title,
            "year": series.year,
            "genre": series.genre,
            "plot": series.plot,
            "poster_url": series.poster_url,
            "imdb_rating": series.imdb_rating,
            "total_seasons": series.total_seasons,
            "status": series.status.value,
            "user_rating": series.user_rating,
            "date_added": datetime.now(timezone.utc).isoformat(),
            "is_favorite": getattr(series, 'is_favorite', False),
            "notes": getattr(series, 'notes', None),
            "current_season": series.current_season,
            "current_episode": series.current_episode,
            "episodes_watched": series.episodes_watched,
        }

        all_series.append(data)
        self._save_series(all_series)
        return series_id

    def get_series_by_imdb_id(self, imdb_id: str) -> Optional[Series]:
        """Get a series by its IMDB ID."""
        all_series = self._load_series()
        for series_data in all_series:
            if series_data.get("imdb_id") == imdb_id:
                return Series.from_db_row(series_data)
        return None

    def get_series_by_id(self, series_id: int) -> Optional[Series]:
        """Get a series by its ID."""
        all_series = self._load_series()
        for series_data in all_series:
            if series_data.get("id") == series_id:
                return Series.from_db_row(series_data)
        return None

    def get_all_series(self) -> List[Series]:
        """Get all series."""
        all_series = self._load_series()
        all_series.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Series.from_db_row(s) for s in all_series]

    def get_series_by_status(self, status: SeriesStatus) -> List[Series]:
        """Get all series with a specific status."""
        all_series = self._load_series()
        filtered = [s for s in all_series if s.get("status") == status.value]
        filtered.sort(key=lambda x: x.get("date_added", ""), reverse=True)
        return [Series.from_db_row(s) for s in filtered]

    def update_series_status(
        self, series_id: int, status: SeriesStatus, user_rating: Optional[int] = None
    ) -> bool:
        """Update series status and optionally the user rating."""
        all_series = self._load_series()

        for series in all_series:
            if series.get("id") == series_id:
                series["status"] = status.value
                if user_rating is not None:
                    series["user_rating"] = user_rating
                self._save_series(all_series)
                return True

        return False

    def update_series_progress(
        self, series_id: int, season: int, episode: int, watched: bool = True
    ) -> bool:
        """Update series watch progress. Mark an episode as watched/unwatched."""
        all_series = self._load_series()

        for series in all_series:
            if series.get("id") == series_id:
                episodes_watched = series.get("episodes_watched", [])
                episode_key = {"season": season, "episode": episode}

                if watched:
                    if episode_key not in episodes_watched:
                        episodes_watched.append(episode_key)
                    series["current_season"] = season
                    series["current_episode"] = episode
                else:
                    episodes_watched = [e for e in episodes_watched
                                       if not (e["season"] == season and e["episode"] == episode)]

                series["episodes_watched"] = episodes_watched
                self._save_series(all_series)
                return True

        return False

    def update_series_notes(self, series_id: int, notes: Optional[str]) -> bool:
        """Update notes for a series."""
        all_series = self._load_series()
        for series in all_series:
            if series.get("id") == series_id:
                series["notes"] = notes
                self._save_series(all_series)
                return True
        return False

    def toggle_series_favorite(self, series_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status for a series."""
        all_series = self._load_series()

        for series in all_series:
            if series.get("id") == series_id:
                series["is_favorite"] = is_favorite
                self._save_series(all_series)
                return True
        return False

    def delete_series(self, series_id: int) -> bool:
        """Delete a series by ID."""
        all_series = self._load_series()
        original_len = len(all_series)
        all_series = [s for s in all_series if s.get("id") != series_id]

        if len(all_series) < original_len:
            self._save_series(all_series)
            return True
        return False

    def get_series_stats(self) -> dict:
        """Get series statistics."""
        all_series = self._load_series()
        stats = {}

        for status in SeriesStatus:
            count = sum(1 for s in all_series if s.get("status") == status.value)
            stats[status.value] = count

        # Get average rating
        ratings = [s["user_rating"] for s in all_series if s.get("user_rating") is not None]
        if ratings:
            stats["avg_user_rating"] = round(sum(ratings) / len(ratings), 1)
        else:
            stats["avg_user_rating"] = None

        # Get genre counts
        genres = {}
        for series in all_series:
            if series.get("genre"):
                for g in series["genre"].split(", "):
                    genres[g] = genres.get(g, 0) + 1
        stats["top_genres"] = sorted(genres.items(), key=lambda x: -x[1])[:5]

        # Total episodes watched
        total_episodes = sum(len(s.get("episodes_watched", [])) for s in all_series)
        stats["total_episodes_watched"] = total_episodes

        return stats

    # Export/Import
    def export_to_json(self, include_movies: bool = True, include_books: bool = True,
                       include_series: bool = True) -> str:
        """Export data to JSON string."""
        data = {}
        if include_movies:
            data["movies"] = self._load_movies()
        if include_books:
            data["books"] = self._load_books()
        if include_series:
            data["series"] = self._load_series()
        return json.dumps(data, indent=2, ensure_ascii=False)

    def export_to_csv(self, media_type: str) -> str:
        """Export data to CSV string."""
        output = io.StringIO()

        if media_type == "movie":
            items = self._load_movies()
            if not items:
                return ""
            fieldnames = ["id", "title", "year", "director", "genre", "status",
                         "user_rating", "imdb_rating", "date_added", "notes"]
        elif media_type == "book":
            items = self._load_books()
            if not items:
                return ""
            fieldnames = ["id", "title", "author", "publish_year", "subjects", "status",
                         "user_rating", "date_added", "notes"]
        elif media_type == "series":
            items = self._load_series()
            if not items:
                return ""
            fieldnames = ["id", "title", "year", "genre", "total_seasons", "status",
                         "user_rating", "imdb_rating", "current_season", "current_episode",
                         "date_added", "notes"]
        else:
            return ""

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(items)

        return output.getvalue()

    def export_to_text(self, media_type: str) -> str:
        """Export data to shareable text format."""
        lines = []

        if media_type == "movie":
            items = self._load_movies()
            lines.append("=== My Movie Collection ===\n")
            for item in items:
                status = item.get("status", "").replace("_", " ").title()
                rating = f" - Rating: {item.get('user_rating')}/10" if item.get('user_rating') else ""
                lines.append(f"- {item.get('title')} ({item.get('year', 'N/A')}) [{status}]{rating}")

        elif media_type == "book":
            items = self._load_books()
            lines.append("=== My Book Collection ===\n")
            for item in items:
                status = item.get("status", "").replace("_", " ").title()
                rating = f" - Rating: {item.get('user_rating')}/10" if item.get('user_rating') else ""
                author = item.get('author', 'Unknown')
                lines.append(f"- {item.get('title')} by {author} [{status}]{rating}")

        elif media_type == "series":
            items = self._load_series()
            lines.append("=== My TV Series Collection ===\n")
            for item in items:
                status = item.get("status", "").replace("_", " ").title()
                rating = f" - Rating: {item.get('user_rating')}/10" if item.get('user_rating') else ""
                progress = f" (S{item.get('current_season', 1)}E{item.get('current_episode', 1)})"
                lines.append(f"- {item.get('title')} ({item.get('year', 'N/A')}) [{status}]{progress}{rating}")

        return "\n".join(lines)

    def import_from_json(self, json_str: str, merge_strategy: str = "skip") -> dict:
        """Import data from JSON string.

        Args:
            json_str: JSON string containing data to import
            merge_strategy: "skip" (skip duplicates), "replace" (replace duplicates),
                          or "add" (add as new)

        Returns:
            dict with counts of imported items
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            raise DatabaseError("Invalid JSON format")

        result = {"movies": 0, "books": 0, "series": 0}

        if "movies" in data:
            movies = self._load_movies()
            existing_ids = {m.get("imdb_id") for m in movies}

            for movie in data["movies"]:
                imdb_id = movie.get("imdb_id")
                if merge_strategy == "skip" and imdb_id in existing_ids:
                    continue
                elif merge_strategy == "replace" and imdb_id in existing_ids:
                    movies = [m for m in movies if m.get("imdb_id") != imdb_id]

                movie["id"] = self._get_next_id(movies)
                if "date_added" not in movie:
                    movie["date_added"] = datetime.now(timezone.utc).isoformat()
                movies.append(movie)
                result["movies"] += 1

            self._save_movies(movies)

        if "books" in data:
            books = self._load_books()
            existing_ids = {b.get("olid") for b in books}

            for book in data["books"]:
                olid = book.get("olid")
                if merge_strategy == "skip" and olid in existing_ids:
                    continue
                elif merge_strategy == "replace" and olid in existing_ids:
                    books = [b for b in books if b.get("olid") != olid]

                book["id"] = self._get_next_id(books)
                if "date_added" not in book:
                    book["date_added"] = datetime.now(timezone.utc).isoformat()
                books.append(book)
                result["books"] += 1

            self._save_books(books)

        if "series" in data:
            all_series = self._load_series()
            existing_ids = {s.get("imdb_id") for s in all_series}

            for series in data["series"]:
                imdb_id = series.get("imdb_id")
                if merge_strategy == "skip" and imdb_id in existing_ids:
                    continue
                elif merge_strategy == "replace" and imdb_id in existing_ids:
                    all_series = [s for s in all_series if s.get("imdb_id") != imdb_id]

                series["id"] = self._get_next_id(all_series)
                if "date_added" not in series:
                    series["date_added"] = datetime.now(timezone.utc).isoformat()
                all_series.append(series)
                result["series"] += 1

            self._save_series(all_series)

        return result

    # Time-series Statistics
    def get_completion_by_month(self, media_type: str, months: int = 12) -> List[dict]:
        """Get completion counts by month for the past N months."""
        result = []
        now = datetime.now(timezone.utc)

        for i in range(months - 1, -1, -1):
            # Calculate month boundaries
            year = now.year - (i // 12)
            month = now.month - (i % 12)
            if month <= 0:
                month += 12
                year -= 1

            month_start = datetime(year, month, 1, tzinfo=timezone.utc)
            if month == 12:
                month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

            count = 0

            if media_type == "movie":
                movies = self._load_movies()
                for m in movies:
                    date_str = m.get("date_completed")
                    if date_str:
                        try:
                            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if month_start <= date < month_end:
                                count += 1
                        except ValueError:
                            pass

            elif media_type == "book":
                books = self._load_books()
                for b in books:
                    date_str = b.get("date_completed")
                    if date_str:
                        try:
                            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            if month_start <= date < month_end:
                                count += 1
                        except ValueError:
                            pass

            result.append({
                "month": month_start.strftime("%Y-%m"),
                "label": month_start.strftime("%b %Y"),
                "count": count
            })

        return result

    def get_rating_distribution(self, media_type: str) -> dict:
        """Get distribution of user ratings."""
        distribution = {str(i): 0 for i in range(1, 11)}
        distribution["unrated"] = 0

        if media_type == "movie":
            items = self._load_movies()
        elif media_type == "book":
            items = self._load_books()
        elif media_type == "series":
            items = self._load_series()
        else:
            return distribution

        for item in items:
            rating = item.get("user_rating")
            if rating is not None and 1 <= rating <= 10:
                distribution[str(rating)] += 1
            else:
                distribution["unrated"] += 1

        return distribution
