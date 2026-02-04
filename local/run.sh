#!/bin/bash
# Run the Local CLI app (no Supabase required)

export OMDB_API_KEY="2a73cc47"

cd "$(dirname "$0")"
python3 media_tracker.py
