"""Recommendation engine for the Media Tracker application."""

import random
from collections import defaultdict
from typing import List, Optional, Tuple, Union

from database import Database
from models import Book, BookStatus, Movie, MovieStatus, Series, SeriesStatus


class Recommender:
    def __init__(self, db: Database):
        self.db = db

    def get_random_movie_recommendation(self) -> Optional[Movie]:
        """Get a random movie from the want_to_watch list."""
        movies = self.db.get_movies_by_status(MovieStatus.WANT_TO_WATCH)
        return random.choice(movies) if movies else None

    def get_random_book_recommendation(self) -> Optional[Book]:
        """Get a random book from the want_to_read list."""
        books = self.db.get_books_by_status(BookStatus.WANT_TO_READ)
        return random.choice(books) if books else None

    def _analyze_movie_genres(self) -> dict:
        """Analyze genres from watched movies weighted by user rating."""
        watched = self.db.get_movies_by_status(MovieStatus.WATCHED)
        genre_scores = defaultdict(float)

        for movie in watched:
            if movie.genre:
                # Weight by user rating (default to 5 if no rating)
                weight = movie.user_rating if movie.user_rating else 5
                for genre in movie.genre.split(", "):
                    genre_scores[genre.strip()] += weight

        return dict(genre_scores)

    def _analyze_book_subjects(self) -> dict:
        """Analyze subjects from read books weighted by user rating."""
        read = self.db.get_books_by_status(BookStatus.READ)
        subject_scores = defaultdict(float)

        for book in read:
            if book.subjects:
                # Weight by user rating (default to 5 if no rating)
                weight = book.user_rating if book.user_rating else 5
                for subject in book.subjects.split(", "):
                    subject_scores[subject.strip()] += weight

        return dict(subject_scores)

    def _score_movie(self, movie: Movie, genre_scores: dict) -> float:
        """Score a movie based on genre preferences."""
        if not movie.genre:
            return 0.0

        score = 0.0
        for genre in movie.genre.split(", "):
            score += genre_scores.get(genre.strip(), 0)

        return score

    def _score_book(self, book: Book, subject_scores: dict) -> float:
        """Score a book based on subject preferences."""
        if not book.subjects:
            return 0.0

        score = 0.0
        for subject in book.subjects.split(", "):
            score += subject_scores.get(subject.strip(), 0)

        return score

    def get_smart_movie_recommendation(self) -> Tuple[Optional[Movie], str]:
        """
        Get a movie recommendation based on genre preferences.
        Returns the movie and a reason for the recommendation.
        """
        want_to_watch = self.db.get_movies_by_status(MovieStatus.WANT_TO_WATCH)
        if not want_to_watch:
            return None, "No movies in your want to watch list."

        genre_scores = self._analyze_movie_genres()

        if not genre_scores:
            # No watched movies with ratings, return random
            movie = random.choice(want_to_watch)
            return movie, "Random pick (no watched movies to base preferences on)."

        # Score all want_to_watch movies
        scored_movies: List[Tuple[Movie, float]] = [
            (m, self._score_movie(m, genre_scores)) for m in want_to_watch
        ]

        # Sort by score descending
        scored_movies.sort(key=lambda x: x[1], reverse=True)

        # Get top movies (all with the highest score)
        top_score = scored_movies[0][1]
        top_movies = [m for m, s in scored_movies if s == top_score]

        # If multiple have the same score, pick randomly among them
        movie = random.choice(top_movies)

        # Generate reason
        if top_score > 0:
            top_genres = sorted(genre_scores.items(), key=lambda x: -x[1])[:3]
            genre_list = ", ".join([g[0] for g in top_genres])
            reason = f"Based on your favorite genres: {genre_list}"
        else:
            reason = "Random pick (no matching genres in watchlist)."

        return movie, reason

    def get_smart_book_recommendation(self) -> Tuple[Optional[Book], str]:
        """
        Get a book recommendation based on subject preferences.
        Returns the book and a reason for the recommendation.
        """
        want_to_read = self.db.get_books_by_status(BookStatus.WANT_TO_READ)
        if not want_to_read:
            return None, "No books in your want to read list."

        subject_scores = self._analyze_book_subjects()

        if not subject_scores:
            # No read books with ratings, return random
            book = random.choice(want_to_read)
            return book, "Random pick (no read books to base preferences on)."

        # Score all want_to_read books
        scored_books: List[Tuple[Book, float]] = [
            (b, self._score_book(b, subject_scores)) for b in want_to_read
        ]

        # Sort by score descending
        scored_books.sort(key=lambda x: x[1], reverse=True)

        # Get top books (all with the highest score)
        top_score = scored_books[0][1]
        top_books = [b for b, s in scored_books if s == top_score]

        # If multiple have the same score, pick randomly among them
        book = random.choice(top_books)

        # Generate reason
        if top_score > 0:
            top_subjects = sorted(subject_scores.items(), key=lambda x: -x[1])[:3]
            subject_list = ", ".join([s[0] for s in top_subjects])
            reason = f"Based on your favorite subjects: {subject_list}"
        else:
            reason = "Random pick (no matching subjects in reading list)."

        return book, reason

    def get_recommendation(
        self, media_type: str, smart: bool = True
    ) -> Tuple[Optional[Union[Movie, Book]], str]:
        """
        Get a recommendation for movies or books.

        Args:
            media_type: "movie" or "book"
            smart: If True, use genre/subject-based recommendation

        Returns:
            Tuple of (media item, reason string)
        """
        if media_type == "movie":
            if smart:
                return self.get_smart_movie_recommendation()
            else:
                movie = self.get_random_movie_recommendation()
                return movie, "Random pick from your watchlist." if movie else "No movies in your want to watch list."
        elif media_type == "book":
            if smart:
                return self.get_smart_book_recommendation()
            else:
                book = self.get_random_book_recommendation()
                return book, "Random pick from your reading list." if book else "No books in your want to read list."
        else:
            return None, f"Unknown media type: {media_type}"

    def get_similar_movies(self, movie: Movie, limit: int = 5) -> List[Tuple[Movie, float]]:
        """Get similar movies from the library based on genre, director, year, and rating.

        Scoring:
        - Genre overlap: 2 points per matching genre
        - Same director: 3 points
        - Year proximity: 0.5 points (max 5 points for same decade)
        - Similar rating: 0.3 points (max 3 points for same rating)

        Returns list of (Movie, score) tuples sorted by score descending.
        """
        all_movies = self.db.get_all_movies()
        scored: List[Tuple[Movie, float]] = []

        movie_genres = set(g.strip() for g in (movie.genre or "").split(", ") if g.strip())
        movie_year = int(movie.year) if movie.year and movie.year.isdigit() else None

        for other in all_movies:
            if other.id == movie.id:
                continue

            score = 0.0

            # Genre overlap (2 points each)
            other_genres = set(g.strip() for g in (other.genre or "").split(", ") if g.strip())
            common_genres = movie_genres & other_genres
            score += len(common_genres) * 2

            # Same director (3 points)
            if movie.director and other.director and movie.director.lower() == other.director.lower():
                score += 3

            # Year proximity (up to 5 points for same decade)
            other_year = int(other.year) if other.year and other.year.isdigit() else None
            if movie_year and other_year:
                year_diff = abs(movie_year - other_year)
                if year_diff <= 10:
                    score += 0.5 * (10 - year_diff)

            # Similar rating (up to 3 points)
            if movie.user_rating and other.user_rating:
                rating_diff = abs(movie.user_rating - other.user_rating)
                if rating_diff <= 3:
                    score += 0.3 * (10 - rating_diff)

            if score > 0:
                scored.append((other, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def get_similar_books(self, book: Book, limit: int = 5) -> List[Tuple[Book, float]]:
        """Get similar books from the library based on subjects and author.

        Scoring:
        - Subject overlap: 2 points per matching subject
        - Same author: 4 points

        Returns list of (Book, score) tuples sorted by score descending.
        """
        all_books = self.db.get_all_books()
        scored: List[Tuple[Book, float]] = []

        book_subjects = set(s.strip() for s in (book.subjects or "").split(", ") if s.strip())

        for other in all_books:
            if other.id == book.id:
                continue

            score = 0.0

            # Subject overlap (2 points each)
            other_subjects = set(s.strip() for s in (other.subjects or "").split(", ") if s.strip())
            common_subjects = book_subjects & other_subjects
            score += len(common_subjects) * 2

            # Same author (4 points)
            if book.author and other.author and book.author.lower() == other.author.lower():
                score += 4

            if score > 0:
                scored.append((other, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def get_similar_series(self, series: Series, limit: int = 5) -> List[Tuple[Series, float]]:
        """Get similar series from the library based on genre.

        Scoring:
        - Genre overlap: 2 points per matching genre
        - Year proximity: 0.5 points (max 5 points for same decade)

        Returns list of (Series, score) tuples sorted by score descending.
        """
        all_series = self.db.get_all_series()
        scored: List[Tuple[Series, float]] = []

        series_genres = set(g.strip() for g in (series.genre or "").split(", ") if g.strip())
        series_year = None
        if series.year:
            # Handle year ranges like "2019-2023"
            year_str = series.year.split("-")[0] if "-" in series.year else series.year
            if year_str.isdigit():
                series_year = int(year_str)

        for other in all_series:
            if other.id == series.id:
                continue

            score = 0.0

            # Genre overlap (2 points each)
            other_genres = set(g.strip() for g in (other.genre or "").split(", ") if g.strip())
            common_genres = series_genres & other_genres
            score += len(common_genres) * 2

            # Year proximity
            other_year = None
            if other.year:
                year_str = other.year.split("-")[0] if "-" in other.year else other.year
                if year_str.isdigit():
                    other_year = int(year_str)

            if series_year and other_year:
                year_diff = abs(series_year - other_year)
                if year_diff <= 10:
                    score += 0.5 * (10 - year_diff)

            if score > 0:
                scored.append((other, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
