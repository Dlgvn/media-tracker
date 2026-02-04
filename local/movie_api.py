"""OMDB API integration for movie data."""

import os
from typing import Dict, List, Optional

import requests

from models import Movie, MovieStatus


class OMDBError(Exception):
    """Exception for OMDB API errors."""

    pass


class MovieAPI:
    BASE_URL = "http://www.omdbapi.com/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OMDB_API_KEY")
        if not self.api_key:
            raise OMDBError(
                "OMDB API key not found. Please set the OMDB_API_KEY environment variable.\n"
                "Get a free API key at: https://www.omdbapi.com/apikey.aspx"
            )

    def search(self, title: str) -> List[Dict]:
        """Search for movies by title. Returns a list of search results."""
        try:
            response = requests.get(
                self.BASE_URL,
                params={"apikey": self.api_key, "s": title, "type": "movie"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                error = data.get("Error", "Unknown error")
                if error == "Movie not found!":
                    return []
                raise OMDBError(error)

            return data.get("Search", [])
        except requests.RequestException as e:
            raise OMDBError(f"Network error: {e}")

    def get_details(self, imdb_id: str) -> Dict:
        """Get detailed information about a movie by IMDB ID."""
        try:
            response = requests.get(
                self.BASE_URL,
                params={"apikey": self.api_key, "i": imdb_id, "plot": "short"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "False":
                raise OMDBError(data.get("Error", "Unknown error"))

            return data
        except requests.RequestException as e:
            raise OMDBError(f"Network error: {e}")

    def create_movie_from_api(
        self, imdb_id: str, status: MovieStatus = MovieStatus.WANT_TO_WATCH
    ) -> Movie:
        """Fetch movie details and create a Movie object."""
        data = self.get_details(imdb_id)

        poster_url = data.get("Poster")
        if poster_url == "N/A":
            poster_url = None

        return Movie(
            id=None,
            imdb_id=data["imdbID"],
            title=data["Title"],
            year=data.get("Year"),
            genre=data.get("Genre") if data.get("Genre") != "N/A" else None,
            director=data.get("Director") if data.get("Director") != "N/A" else None,
            plot=data.get("Plot") if data.get("Plot") != "N/A" else None,
            poster_url=poster_url,
            imdb_rating=(
                data.get("imdbRating") if data.get("imdbRating") != "N/A" else None
            ),
            status=status,
        )
