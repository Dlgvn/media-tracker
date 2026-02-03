# Media Tracker

A Python application to track movies and books with an Instagram-like GUI interface. Features local JSON storage or cloud storage with Supabase, API integrations for movie/book data, and personalized recommendations.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green.svg)

## Features

- **Modern GUI** - Netflix-inspired dark interface with orange accents
- **Movie Tracking** - Search movies via OMDB API, track watch status and ratings
- **Book Tracking** - Search books via Open Library API, track reading progress
- **Favorites** - Mark items with heart icon for quick access
- **Sort Options** - Sort by date added, title, or rating
- **Smart Recommendations** - Genre-based suggestions from your library
- **Statistics** - View your media consumption stats and favorite genres
- **Two Storage Options** - Local JSON files or Supabase cloud

## Quick Start (Local Storage)

No database setup required. Data stored in `~/.media-tracker/`.

### 1. Install Dependencies

```bash
pip install customtkinter Pillow requests
```

### 2. Run the App

**GUI App:**
```bash
./run_gui_local.sh
# or
python3 gui_app_local.py
```

**CLI App:**
```bash
./run_local.sh
# or
python3 media_tracker_local.py
```

### 3. Optional: Enable Movie Search

Get a free API key at [omdbapi.com](https://www.omdbapi.com/apikey.aspx), then:

```bash
export OMDB_API_KEY="your-key-here"
```

Book search works without any API key.

## Cloud Storage Setup (Supabase)

For cloud storage with Supabase:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run this SQL in the SQL Editor:

```sql
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
    date_completed TIMESTAMPTZ,
    is_favorite BOOLEAN DEFAULT FALSE
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
    date_completed TIMESTAMPTZ,
    is_favorite BOOLEAN DEFAULT FALSE
);

ALTER TABLE movies DISABLE ROW LEVEL SECURITY;
ALTER TABLE books DISABLE ROW LEVEL SECURITY;
```

### 3. Configure Environment

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export OMDB_API_KEY="your-omdb-key"
```

### 4. Run

```bash
./run_gui.sh      # GUI with Supabase
./run.sh          # CLI with Supabase
```

## Usage

### Adding Media

1. Select **Movies** or **Books** from the sidebar
2. Type in the search bar and press Enter
3. Click **+ Add** on any search result
4. Choose status and optional rating

### Managing Media

- Click on any card to view details and edit
- Change status (Want to Watch → Watching → Watched)
- Update your rating
- Delete items

### Favorites

- Click the **heart icon** on any card to toggle favorite
- Use the **Favorites tab** to filter

### Sorting

Use the **Sort dropdown** to sort by:
- Date Added (newest first)
- Title (A-Z or Z-A)
- Rating (highest or lowest first)

## Project Structure

```
media-tracker/
├── gui_app_local.py      # GUI app (local storage)
├── gui_app.py            # GUI app (Supabase)
├── media_tracker_local.py # CLI app (local storage)
├── media_tracker.py      # CLI app (Supabase)
├── local_database.py     # JSON file database
├── database.py           # Supabase database
├── movie_api.py          # OMDB API integration
├── book_api.py           # Open Library API
├── recommender.py        # Recommendation engine
├── models.py             # Data models
├── run_gui_local.sh      # Run local GUI
├── run_local.sh          # Run local CLI
├── run_gui.sh            # Run Supabase GUI
├── run.sh                # Run Supabase CLI
└── requirements.txt      # Dependencies
```

## Data Storage

### Local Storage
Data is stored in `~/.media-tracker/`:
- `movies.json` - Your movie library
- `books.json` - Your book library

### Cloud Storage
Data is stored in Supabase PostgreSQL tables.

## API References

- **OMDB API** - [omdbapi.com](https://www.omdbapi.com/) - Movie data (requires free API key)
- **Open Library API** - [openlibrary.org](https://openlibrary.org/developers/api) - Book data (no key required)

## Troubleshooting

### "OMDB API key not configured"
Set the environment variable:
```bash
export OMDB_API_KEY="your-key"
```

### GUI not appearing
Ensure you have a display and tkinter is installed:
```bash
python3 -c "import tkinter; tkinter.Tk()"
```

### Book search not working
Check your internet connection. Open Library API requires no key.

## License

MIT License - Feel free to use and modify.
