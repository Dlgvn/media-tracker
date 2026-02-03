#!/bin/bash
# Run the local CLI app (no Supabase required)

# Optional: Set OMDB API key for movie search (get free key at omdbapi.com)
# export OMDB_API_KEY="your-key-here"

cd "$(dirname "$0")"
python3 media_tracker_local.py
