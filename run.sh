#!/bin/bash
export SUPABASE_URL="https://oouqsxzekomnwnsyehuu.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vdXFzeHpla29tbnduc3llaHV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg4ODgwNDQsImV4cCI6MjA4NDQ2NDA0NH0.hw9yJJIh7phdr5L68-GRxszdiRBlZNcmjnqqKtW4TXw"
export OMDB_API_KEY="2a73cc47"

cd "$(dirname "$0")"
python3 media_tracker.py
