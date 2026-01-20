# Media Tracker

A modern Python application to track movies and books with an Instagram-like GUI interface. Features cloud storage with Supabase, API integrations for movie/book data, and personalized recommendations.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green.svg)
![Supabase](https://img.shields.io/badge/Database-Supabase-orange.svg)

## Features

- **Modern GUI** - Instagram-inspired interface with dark/light mode support
- **Movie Tracking** - Search movies via OMDB API, track watch status and ratings
- **Book Tracking** - Search books via Open Library API, track reading progress
- **Cloud Storage** - Data persisted in Supabase (PostgreSQL)
- **Smart Recommendations** - Genre-based suggestions from your watchlist/reading list
- **Statistics** - View your media consumption stats and favorite genres
- **Responsive Design** - Adapts to window resizing

## Screenshots

The app features:
- Sidebar navigation (Movies, Books, For You, Statistics)
- Card-based media display with posters/covers
- Status badges (Watched/Watching/Want to Watch)
- Star ratings
- Search with instant results

## Installation

### Prerequisites

- Python 3.8 or higher
- Supabase account (free tier works)
- OMDB API key (free at [omdbapi.com](https://www.omdbapi.com/apikey.aspx))

### 1. Clone/Download

```bash
cd ~/media-tracker
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run:

```sql
-- Create tables
CREATE TABLE movies (
    id BIGSERIAL PRIMARY KEY,
    imdb_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    year TEXT,
    genre TEXT,
    director TEXT,
    plot TEXT,
    poster_url TEXT,
    imdb_rating TEXT,
    status TEXT NOT NULL,
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 10),
    date_added TIMESTAMPTZ DEFAULT NOW(),
    date_completed TIMESTAMPTZ
);

CREATE TABLE books (
    id BIGSERIAL PRIMARY KEY,
    olid TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    subjects TEXT,
    publish_year INTEGER,
    cover_url TEXT,
    status TEXT NOT NULL,
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 10),
    date_added TIMESTAMPTZ DEFAULT NOW(),
    date_completed TIMESTAMPTZ
);

-- Disable RLS for personal use
ALTER TABLE movies DISABLE ROW LEVEL SECURITY;
ALTER TABLE books DISABLE ROW LEVEL SECURITY;

-- Optional: Add indexes
CREATE INDEX idx_movies_status ON movies(status);
CREATE INDEX idx_books_status ON books(status);
```

3. Get your credentials from Project Settings → API:
   - Project URL
   - Anon/Public key

### 4. Configure Environment

Edit `run_gui.sh` with your credentials:

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export OMDB_API_KEY="your-omdb-key"
```

Or set them manually:

```bash
export SUPABASE_URL="your-url"
export SUPABASE_KEY="your-key"
export OMDB_API_KEY="your-key"
```

## Usage

### GUI Application (Recommended)

```bash
./run_gui.sh
```

Or manually:

```bash
python3 gui_app.py
```

### CLI Application

```bash
./run.sh
```

Or manually:

```bash
python3 media_tracker.py
```

## How to Use

### Adding Media

1. Select **Movies** or **Books** from the sidebar
2. Type in the search bar and press Enter
3. Click **+ Add** on any search result
4. Choose status and optional rating
5. Click **Add to Library**

### Managing Media

1. Click on any media card to open details
2. Change status (Want to Watch → Watching → Watched)
3. Update your rating
4. Click **Save Changes** or **Delete**

### Getting Recommendations

1. Click **For You** in the sidebar
2. View smart recommendations based on your rated items
3. Recommendations favor genres/subjects you rate highly

### Viewing Statistics

1. Click **Statistics** in the sidebar
2. See counts by status
3. View average ratings and top genres/subjects

## Project Structure

```
media-tracker/
├── gui_app.py          # GUI application (CustomTkinter)
├── media_tracker.py    # CLI application
├── database.py         # Supabase database operations
├── movie_api.py        # OMDB API integration
├── book_api.py         # Open Library API integration
├── recommender.py      # Recommendation engine
├── models.py           # Data models (Movie, Book)
├── requirements.txt    # Python dependencies
├── run_gui.sh          # GUI launch script
├── run.sh              # CLI launch script
└── README.md           # This file
```

## Dependencies

- **customtkinter** - Modern GUI framework
- **Pillow** - Image processing for posters/covers
- **requests** - HTTP requests for APIs
- **supabase** - Supabase Python client

## API References

- **OMDB API** - [omdbapi.com](https://www.omdbapi.com/) - Movie data
- **Open Library API** - [openlibrary.org/developers](https://openlibrary.org/developers/api) - Book data

## Troubleshooting

### "Invalid API key" error
- Verify your Supabase anon key starts with `eyJ...`
- Check OMDB API key is valid at omdbapi.com

### GUI not appearing
- Ensure you have a display (not running headless)
- Try: `python3 -c "import tkinter; tkinter.Tk()"`

### Database connection failed
- Check Supabase URL format: `https://xxx.supabase.co`
- Verify RLS is disabled or policies are set

### Search not working
- Movies: Check OMDB_API_KEY is set
- Books: Open Library requires no key, check internet

## License

MIT License - Feel free to use and modify.
