"""Open Library API integration for book data."""

from typing import Dict, List, Optional

import requests

from models import Book, BookStatus


class OpenLibraryError(Exception):
    """Exception for Open Library API errors."""

    pass


class BookAPI:
    BASE_URL = "https://openlibrary.org"
    COVERS_URL = "https://covers.openlibrary.org/b/olid"

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for books by title or author. Returns a list of search results."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/search.json",
                params={"q": query, "limit": limit},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for doc in data.get("docs", []):
                # Only include results that have a work key (OLID)
                if "key" in doc:
                    olid = doc["key"].replace("/works/", "")
                    results.append(
                        {
                            "olid": olid,
                            "title": doc.get("title", "Unknown Title"),
                            "author": (
                                doc.get("author_name", ["Unknown Author"])[0]
                                if doc.get("author_name")
                                else "Unknown Author"
                            ),
                            "first_publish_year": doc.get("first_publish_year"),
                            "subjects": doc.get("subject", [])[:5],
                        }
                    )

            return results
        except requests.RequestException as e:
            raise OpenLibraryError(f"Network error: {e}")

    def get_details(self, olid: str) -> Dict:
        """Get detailed information about a book by Open Library work ID."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/works/{olid}.json",
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise OpenLibraryError(f"Network error: {e}")

    def get_cover_url(self, olid: str, size: str = "M") -> Optional[str]:
        """Get cover image URL for a book. Size: S, M, or L."""
        return f"{self.COVERS_URL}/{olid}-{size}.jpg"

    def create_book_from_search(
        self, search_result: Dict, status: BookStatus = BookStatus.WANT_TO_READ
    ) -> Book:
        """Create a Book object from a search result."""
        olid = search_result["olid"]
        subjects = search_result.get("subjects", [])
        subjects_str = ", ".join(subjects[:5]) if subjects else None

        return Book(
            id=None,
            olid=olid,
            title=search_result["title"],
            author=search_result.get("author"),
            subjects=subjects_str,
            publish_year=search_result.get("first_publish_year"),
            cover_url=self.get_cover_url(olid),
            status=status,
        )
