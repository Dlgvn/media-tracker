#!/usr/bin/env python3
"""Media Tracker (Local) - Track movies and books with local JSON storage."""

import sys
from typing import List, Optional

from book_api import BookAPI, OpenLibraryError
from database import Database
from models import Book, BookStatus, Movie, MovieStatus
from movie_api import MovieAPI, OMDBError
from recommender import Recommender


def clear_screen():
    """Clear the terminal screen."""
    print("\033[H\033[J", end="")


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'=' * 40}")
    print(f"  {title}")
    print(f"{'=' * 40}\n")


def get_input(prompt: str, valid_options: Optional[List[str]] = None) -> str:
    """Get user input with optional validation."""
    while True:
        try:
            value = input(prompt).strip()
            if valid_options is None or value in valid_options:
                return value
            print(f"Invalid option. Please choose from: {', '.join(valid_options)}")
        except (EOFError, KeyboardInterrupt):
            print("\n")
            return ""


def get_rating() -> Optional[int]:
    """Get a rating from the user (1-10)."""
    while True:
        value = get_input("Your rating (1-10, or press Enter to skip): ")
        if not value:
            return None
        try:
            rating = int(value)
            if 1 <= rating <= 10:
                return rating
            print("Rating must be between 1 and 10.")
        except ValueError:
            print("Please enter a valid number.")


def display_movie(movie: Movie, show_id: bool = False):
    """Display movie information."""
    id_str = f"[{movie.id}] " if show_id else ""
    fav_str = " ❤️" if getattr(movie, 'is_favorite', False) else ""
    print(f"{id_str}{movie.title} ({movie.year or 'N/A'}){fav_str}")
    if movie.director:
        print(f"   Director: {movie.director}")
    if movie.genre:
        print(f"   Genre: {movie.genre}")
    if movie.imdb_rating:
        print(f"   IMDB Rating: {movie.imdb_rating}")
    if movie.user_rating:
        print(f"   Your Rating: {movie.user_rating}/10")
    if movie.plot:
        print(f"   Plot: {movie.plot[:100]}..." if len(movie.plot) > 100 else f"   Plot: {movie.plot}")
    print()


def display_book(book: Book, show_id: bool = False):
    """Display book information."""
    id_str = f"[{book.id}] " if show_id else ""
    fav_str = " ❤️" if getattr(book, 'is_favorite', False) else ""
    year_str = f" ({book.publish_year})" if book.publish_year else ""
    print(f"{id_str}{book.title}{year_str}{fav_str}")
    if book.author:
        print(f"   Author: {book.author}")
    if book.subjects:
        print(f"   Subjects: {book.subjects}")
    if book.user_rating:
        print(f"   Your Rating: {book.user_rating}/10")
    print()


class MediaTracker:
    def __init__(self):
        print("Using local JSON storage (~/.media-tracker/)")
        self.db = Database()
        self.recommender = Recommender(self.db)
        self.movie_api: Optional[MovieAPI] = None
        self.book_api = BookAPI()

    def _init_movie_api(self) -> bool:
        """Initialize movie API (requires API key)."""
        if self.movie_api is not None:
            return True
        try:
            self.movie_api = MovieAPI()
            return True
        except OMDBError as e:
            print(f"\nError: {e}")
            print("Set OMDB_API_KEY environment variable to search movies.")
            return False

    def main_menu(self):
        """Display and handle main menu."""
        while True:
            print_header("Media Tracker (Local)")
            print("1. Movies")
            print("2. Books")
            print("3. Get Recommendation")
            print("4. Statistics")
            print("5. Toggle Favorite")
            print("6. Exit")

            choice = get_input("\nChoose an option: ", ["1", "2", "3", "4", "5", "6", ""])
            if choice == "" or choice == "6":
                print("\nGoodbye!")
                break
            elif choice == "1":
                self.movies_menu()
            elif choice == "2":
                self.books_menu()
            elif choice == "3":
                self.recommendation_menu()
            elif choice == "4":
                self.statistics_menu()
            elif choice == "5":
                self.toggle_favorite_menu()

    def movies_menu(self):
        """Display and handle movies submenu."""
        while True:
            print_header("Movies")
            print("1. Search & Add Movie")
            print("2. View Watched")
            print("3. View Watching")
            print("4. View Want to Watch")
            print("5. View Favorites")
            print("6. Update Movie Status")
            print("7. Remove Movie")
            print("8. Back")

            choice = get_input("\nChoose an option: ", ["1", "2", "3", "4", "5", "6", "7", "8", ""])
            if choice == "" or choice == "8":
                break
            elif choice == "1":
                self.search_add_movie()
            elif choice == "2":
                self.view_movies(MovieStatus.WATCHED)
            elif choice == "3":
                self.view_movies(MovieStatus.WATCHING)
            elif choice == "4":
                self.view_movies(MovieStatus.WANT_TO_WATCH)
            elif choice == "5":
                self.view_favorite_movies()
            elif choice == "6":
                self.update_movie_status()
            elif choice == "7":
                self.remove_movie()

    def search_add_movie(self):
        """Search for a movie and add it to the tracker."""
        if not self._init_movie_api():
            return

        print_header("Search Movies")
        query = get_input("Enter movie title: ")
        if not query:
            return

        print("\nSearching...")
        try:
            results = self.movie_api.search(query)
        except OMDBError as e:
            print(f"Error: {e}")
            return

        if not results:
            print("No movies found.")
            return

        print(f"\nFound {len(results)} result(s):\n")
        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result['Title']} ({result.get('Year', 'N/A')})")

        choice = get_input("\nSelect a movie number (or press Enter to cancel): ")
        if not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                selected = results[idx]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return

        # Check if already in database
        existing = self.db.get_movie_by_imdb_id(selected["imdbID"])
        if existing:
            print(f"\nThis movie is already in your library with status: {existing.status.value}")
            return

        # Select status
        print("\nSelect status:")
        print("1. Want to Watch")
        print("2. Watching")
        print("3. Watched")

        status_choice = get_input("Status: ", ["1", "2", "3"])
        status_map = {
            "1": MovieStatus.WANT_TO_WATCH,
            "2": MovieStatus.WATCHING,
            "3": MovieStatus.WATCHED,
        }
        status = status_map.get(status_choice, MovieStatus.WANT_TO_WATCH)

        # Get rating if watched
        user_rating = None
        if status == MovieStatus.WATCHED:
            user_rating = get_rating()

        try:
            movie = self.movie_api.create_movie_from_api(selected["imdbID"], status)
            movie.user_rating = user_rating
            self.db.add_movie(movie)
            print(f"\nAdded '{movie.title}' to your library!")
        except OMDBError as e:
            print(f"Error fetching movie details: {e}")

    def view_movies(self, status: MovieStatus):
        """View movies with a specific status."""
        status_names = {
            MovieStatus.WATCHED: "Watched Movies",
            MovieStatus.WATCHING: "Currently Watching",
            MovieStatus.WANT_TO_WATCH: "Want to Watch",
        }
        print_header(status_names[status])

        movies = self.db.get_movies_by_status(status)
        if not movies:
            print("No movies in this category.")
        else:
            for movie in movies:
                display_movie(movie, show_id=True)

        get_input("Press Enter to continue...")

    def view_favorite_movies(self):
        """View favorite movies."""
        print_header("Favorite Movies ❤️")

        movies = self.db.get_favorite_movies()
        if not movies:
            print("No favorite movies yet.")
        else:
            for movie in movies:
                display_movie(movie, show_id=True)

        get_input("Press Enter to continue...")

    def update_movie_status(self):
        """Update a movie's status."""
        print_header("Update Movie Status")

        movies = self.db.get_all_movies()
        if not movies:
            print("No movies in your library.")
            get_input("Press Enter to continue...")
            return

        for movie in movies:
            fav = " ❤️" if getattr(movie, 'is_favorite', False) else ""
            print(f"[{movie.id}] {movie.title} - {movie.status.value}{fav}")

        movie_id = get_input("\nEnter movie ID to update (or press Enter to cancel): ")
        if not movie_id:
            return

        try:
            movie_id = int(movie_id)
        except ValueError:
            print("Invalid ID.")
            return

        print("\nSelect new status:")
        print("1. Want to Watch")
        print("2. Watching")
        print("3. Watched")

        status_choice = get_input("Status: ", ["1", "2", "3"])
        status_map = {
            "1": MovieStatus.WANT_TO_WATCH,
            "2": MovieStatus.WATCHING,
            "3": MovieStatus.WATCHED,
        }
        new_status = status_map.get(status_choice)
        if not new_status:
            return

        user_rating = None
        if new_status == MovieStatus.WATCHED:
            user_rating = get_rating()

        if self.db.update_movie_status(movie_id, new_status, user_rating):
            print("Movie status updated!")
        else:
            print("Movie not found.")

    def remove_movie(self):
        """Remove a movie from the library."""
        print_header("Remove Movie")

        movies = self.db.get_all_movies()
        if not movies:
            print("No movies in your library.")
            get_input("Press Enter to continue...")
            return

        for movie in movies:
            print(f"[{movie.id}] {movie.title}")

        movie_id = get_input("\nEnter movie ID to remove (or press Enter to cancel): ")
        if not movie_id:
            return

        try:
            movie_id = int(movie_id)
        except ValueError:
            print("Invalid ID.")
            return

        confirm = get_input("Are you sure? (y/n): ")
        if confirm.lower() == "y":
            if self.db.delete_movie(movie_id):
                print("Movie removed.")
            else:
                print("Movie not found.")

    def books_menu(self):
        """Display and handle books submenu."""
        while True:
            print_header("Books")
            print("1. Search & Add Book")
            print("2. View Read")
            print("3. View Reading")
            print("4. View Want to Read")
            print("5. View Favorites")
            print("6. Update Book Status")
            print("7. Remove Book")
            print("8. Back")

            choice = get_input("\nChoose an option: ", ["1", "2", "3", "4", "5", "6", "7", "8", ""])
            if choice == "" or choice == "8":
                break
            elif choice == "1":
                self.search_add_book()
            elif choice == "2":
                self.view_books(BookStatus.READ)
            elif choice == "3":
                self.view_books(BookStatus.READING)
            elif choice == "4":
                self.view_books(BookStatus.WANT_TO_READ)
            elif choice == "5":
                self.view_favorite_books()
            elif choice == "6":
                self.update_book_status()
            elif choice == "7":
                self.remove_book()

    def search_add_book(self):
        """Search for a book and add it to the tracker."""
        print_header("Search Books")
        query = get_input("Enter book title or author: ")
        if not query:
            return

        print("\nSearching...")
        try:
            results = self.book_api.search(query)
        except OpenLibraryError as e:
            print(f"Error: {e}")
            return

        if not results:
            print("No books found.")
            return

        print(f"\nFound {len(results)} result(s):\n")
        for i, result in enumerate(results, 1):
            year = f" ({result['first_publish_year']})" if result.get("first_publish_year") else ""
            print(f"{i}. {result['title']}{year} by {result['author']}")

        choice = get_input("\nSelect a book number (or press Enter to cancel): ")
        if not choice:
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                selected = results[idx]
            else:
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return

        # Check if already in database
        existing = self.db.get_book_by_olid(selected["olid"])
        if existing:
            print(f"\nThis book is already in your library with status: {existing.status.value}")
            return

        # Select status
        print("\nSelect status:")
        print("1. Want to Read")
        print("2. Reading")
        print("3. Read")

        status_choice = get_input("Status: ", ["1", "2", "3"])
        status_map = {
            "1": BookStatus.WANT_TO_READ,
            "2": BookStatus.READING,
            "3": BookStatus.READ,
        }
        status = status_map.get(status_choice, BookStatus.WANT_TO_READ)

        # Get rating if read
        user_rating = None
        if status == BookStatus.READ:
            user_rating = get_rating()

        try:
            book = self.book_api.create_book_from_search(selected, status)
            book.user_rating = user_rating
            self.db.add_book(book)
            print(f"\nAdded '{book.title}' to your library!")
        except OpenLibraryError as e:
            print(f"Error: {e}")

    def view_books(self, status: BookStatus):
        """View books with a specific status."""
        status_names = {
            BookStatus.READ: "Read Books",
            BookStatus.READING: "Currently Reading",
            BookStatus.WANT_TO_READ: "Want to Read",
        }
        print_header(status_names[status])

        books = self.db.get_books_by_status(status)
        if not books:
            print("No books in this category.")
        else:
            for book in books:
                display_book(book, show_id=True)

        get_input("Press Enter to continue...")

    def view_favorite_books(self):
        """View favorite books."""
        print_header("Favorite Books ❤️")

        books = self.db.get_favorite_books()
        if not books:
            print("No favorite books yet.")
        else:
            for book in books:
                display_book(book, show_id=True)

        get_input("Press Enter to continue...")

    def update_book_status(self):
        """Update a book's status."""
        print_header("Update Book Status")

        books = self.db.get_all_books()
        if not books:
            print("No books in your library.")
            get_input("Press Enter to continue...")
            return

        for book in books:
            fav = " ❤️" if getattr(book, 'is_favorite', False) else ""
            print(f"[{book.id}] {book.title} - {book.status.value}{fav}")

        book_id = get_input("\nEnter book ID to update (or press Enter to cancel): ")
        if not book_id:
            return

        try:
            book_id = int(book_id)
        except ValueError:
            print("Invalid ID.")
            return

        print("\nSelect new status:")
        print("1. Want to Read")
        print("2. Reading")
        print("3. Read")

        status_choice = get_input("Status: ", ["1", "2", "3"])
        status_map = {
            "1": BookStatus.WANT_TO_READ,
            "2": BookStatus.READING,
            "3": BookStatus.READ,
        }
        new_status = status_map.get(status_choice)
        if not new_status:
            return

        user_rating = None
        if new_status == BookStatus.READ:
            user_rating = get_rating()

        if self.db.update_book_status(book_id, new_status, user_rating):
            print("Book status updated!")
        else:
            print("Book not found.")

    def remove_book(self):
        """Remove a book from the library."""
        print_header("Remove Book")

        books = self.db.get_all_books()
        if not books:
            print("No books in your library.")
            get_input("Press Enter to continue...")
            return

        for book in books:
            print(f"[{book.id}] {book.title}")

        book_id = get_input("\nEnter book ID to remove (or press Enter to cancel): ")
        if not book_id:
            return

        try:
            book_id = int(book_id)
        except ValueError:
            print("Invalid ID.")
            return

        confirm = get_input("Are you sure? (y/n): ")
        if confirm.lower() == "y":
            if self.db.delete_book(book_id):
                print("Book removed.")
            else:
                print("Book not found.")

    def toggle_favorite_menu(self):
        """Toggle favorite status for a media item."""
        print_header("Toggle Favorite")
        print("1. Toggle Movie Favorite")
        print("2. Toggle Book Favorite")
        print("3. Back")

        choice = get_input("\nChoose an option: ", ["1", "2", "3", ""])
        if choice == "" or choice == "3":
            return
        elif choice == "1":
            self._toggle_movie_favorite()
        elif choice == "2":
            self._toggle_book_favorite()

    def _toggle_movie_favorite(self):
        """Toggle favorite status for a movie."""
        movies = self.db.get_all_movies()
        if not movies:
            print("No movies in your library.")
            get_input("Press Enter to continue...")
            return

        print("\nMovies:")
        for movie in movies:
            fav = " ❤️" if getattr(movie, 'is_favorite', False) else ""
            print(f"[{movie.id}] {movie.title}{fav}")

        movie_id = get_input("\nEnter movie ID to toggle favorite (or press Enter to cancel): ")
        if not movie_id:
            return

        try:
            movie_id = int(movie_id)
        except ValueError:
            print("Invalid ID.")
            return

        # Find the movie and toggle
        for movie in movies:
            if movie.id == movie_id:
                new_status = not getattr(movie, 'is_favorite', False)
                if self.db.toggle_movie_favorite(movie_id, new_status):
                    status_text = "added to" if new_status else "removed from"
                    print(f"'{movie.title}' {status_text} favorites!")
                return

        print("Movie not found.")

    def _toggle_book_favorite(self):
        """Toggle favorite status for a book."""
        books = self.db.get_all_books()
        if not books:
            print("No books in your library.")
            get_input("Press Enter to continue...")
            return

        print("\nBooks:")
        for book in books:
            fav = " ❤️" if getattr(book, 'is_favorite', False) else ""
            print(f"[{book.id}] {book.title}{fav}")

        book_id = get_input("\nEnter book ID to toggle favorite (or press Enter to cancel): ")
        if not book_id:
            return

        try:
            book_id = int(book_id)
        except ValueError:
            print("Invalid ID.")
            return

        # Find the book and toggle
        for book in books:
            if book.id == book_id:
                new_status = not getattr(book, 'is_favorite', False)
                if self.db.toggle_book_favorite(book_id, new_status):
                    status_text = "added to" if new_status else "removed from"
                    print(f"'{book.title}' {status_text} favorites!")
                return

        print("Book not found.")

    def recommendation_menu(self):
        """Display and handle recommendation menu."""
        print_header("Get Recommendation")
        print("1. Movie Recommendation")
        print("2. Book Recommendation")
        print("3. Back")

        choice = get_input("\nChoose an option: ", ["1", "2", "3", ""])
        if choice == "" or choice == "3":
            return

        media_type = "movie" if choice == "1" else "book"

        print("\nRecommendation type:")
        print("1. Smart (based on your preferences)")
        print("2. Random")

        rec_type = get_input("Choose: ", ["1", "2"])
        smart = rec_type == "1"

        item, reason = self.recommender.get_recommendation(media_type, smart)

        print_header("Recommendation")
        if item:
            print(f"Reason: {reason}\n")
            if isinstance(item, Movie):
                display_movie(item)
            else:
                display_book(item)
        else:
            print(reason)

        get_input("Press Enter to continue...")

    def statistics_menu(self):
        """Display statistics."""
        print_header("Statistics")

        # Movie stats
        print("--- Movies ---")
        movie_stats = self.db.get_movie_stats()
        print(f"Watched: {movie_stats.get('watched', 0)}")
        print(f"Watching: {movie_stats.get('watching', 0)}")
        print(f"Want to Watch: {movie_stats.get('want_to_watch', 0)}")
        if movie_stats.get("avg_user_rating"):
            print(f"Average Rating: {movie_stats['avg_user_rating']}/10")
        if movie_stats.get("top_genres"):
            genres = ", ".join([f"{g[0]} ({g[1]})" for g in movie_stats["top_genres"]])
            print(f"Top Genres: {genres}")

        print()

        # Book stats
        print("--- Books ---")
        book_stats = self.db.get_book_stats()
        print(f"Read: {book_stats.get('read', 0)}")
        print(f"Reading: {book_stats.get('reading', 0)}")
        print(f"Want to Read: {book_stats.get('want_to_read', 0)}")
        if book_stats.get("avg_user_rating"):
            print(f"Average Rating: {book_stats['avg_user_rating']}/10")
        if book_stats.get("top_subjects"):
            subjects = ", ".join([f"{s[0]} ({s[1]})" for s in book_stats["top_subjects"]])
            print(f"Top Subjects: {subjects}")

        print()
        get_input("Press Enter to continue...")


def main():
    try:
        tracker = MediaTracker()
        tracker.main_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
