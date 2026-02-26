# GUI Dark Luxury Visual Redesign

**Date:** 2026-02-26
**Scope:** Visual overhaul of `gui_app.py` — no changes to data layer, models, APIs, or database
**Approach:** In-place edit (Option A) — restyle existing code without architectural changes

---

## Goals

- Upgrade aesthetic from "dark cinematic orange" to "dark luxury crimson/gold"
- Add grid/list view toggle for media libraries
- Polish card layout, typography, and hover states
- Improve sidebar active states and header hierarchy

---

## Color Palette

| Token | Old Value | New Value | Role |
|---|---|---|---|
| `bg_primary` | `#0D0D0D` | `#080808` | Main app background |
| `bg_secondary` | `#141414` | `#0F0F0F` | Dialog/panel backgrounds |
| `bg_card` | `#1A1A1A` | `#141414` | Card backgrounds |
| `bg_card_hover` | `#252525` | `#1E1E1E` | Card hover state |
| `bg_sidebar` | `#0A0A0A` | `#050505` | Sidebar background |
| `accent_primary` | `#E65100` | `#DC143C` | Crimson — buttons, active states |
| `accent_hover` | `#FF8C00` | `#FF1744` | Hover state |
| `accent_glow` | `#FF6600` | `#FF0030` | Glow/border effects |
| `accent_subtle` | _(new)_ | `#1A0008` | Crimson-tinted bg for active nav |
| `rating_gold` | `#F5C518` | `#FFD700` | Richer gold for ratings |
| `status_watched` | `#4ADE80` | `#22C55E` | Green |
| `status_watching` | `#FB923C` | `#F97316` | Orange |
| `status_planned` | `#60A5FA` | `#3B82F6` | Blue |

---

## Components

### THEME dict (`gui_app.py` lines 32–57)
- Replace all color values per table above
- Add `accent_subtle` token

### MediaCard (grid view)
- Increase card padding: `padx=10`, `pady=(10, 8)`
- Title font: `size=15` (up from 14)
- Rating display: change `★ {rating}` → `⭐ {rating:.0f}` with `/10` suffix in muted color
- Status badge: add `border_width=1`, `border_color` matching status color at 60% opacity
- Favorite button: move from bottom row to **overlay position** — top-right corner of poster image using `.place(relx=1.0, rely=0, anchor="ne", x=-8, y=8)`
- Hover: crimson glow border (`accent_glow`) + `border_width=2`

### ListCard (new component)
New class `MediaListCard(ctk.CTkFrame)`:
- Height: 90px, full width
- Left: poster thumbnail `60×90px` with `corner_radius=6`
- Center column: title (bold, 14px), subtitle (12px muted: year · director/author · genre)
- Right: status badge pill + rating (`⭐ X`) + favorite heart button
- Same hover glow as MediaCard
- Same `on_click`, `on_favorite_toggle`, `is_favorite` interface as MediaCard

### View Toggle (header area)
In `MainContent.__init__`, add after sort dropdown:
- A `ctk.CTkSegmentedButton` (or two `CTkButton`s styled as segmented control) with values `["⊞", "☰"]`
- `self.view_mode = "grid"` state variable
- On toggle: re-render current grid via `_display_media_grid()` using appropriate card class

### Sidebar
- Active nav button background: `accent_subtle` (`#1A0008`) instead of `bg_card`
- Accent bar color: unchanged (crimson)
- Logo: add `ctk.CTkFrame` horizontal rule (height=1, `fg_color=accent_primary`) after "TRACKER" label
- Bottom: add version label `ctk.CTkLabel(text="local storage", ...)` pinned to bottom with `pack(side="bottom")`

### Header
- Section title font: `size=32` (up from 28)
- Add a `ctk.CTkFrame(height=3, width=40, fg_color=accent_primary)` underline accent beneath title label

### MediaDetailDialog
- Poster size: `240×360` (up from `220×330`)
- Genre display: parse comma-separated genres into individual pill badge `CTkLabel`s in a horizontal frame
- Rating display row: show 5 filled/empty stars (read-only visual) above the edit slider
- Action bar: `Save Changes` button `fg_color=accent_primary`

---

## What Does NOT Change

- All database operations (`database.py`)
- All API calls (`movie_api.py`, `book_api.py`)
- All models (`models.py`)
- All recommendation logic (`recommender.py`)
- Dialog logic (status mapping, save/delete callbacks)
- Search functionality
- Bulk operations
- Stats/charts section
- Series detail dialog logic

---

## File Touched

- `gui_app.py` — only file modified

---

## Success Criteria

- [ ] New color palette applied throughout (no old orange values remaining)
- [ ] Grid view cards use updated layout with poster-overlaid favorite button
- [ ] List view renders with thumbnail + info row
- [ ] View toggle switches between grid and list modes
- [ ] Sidebar active state uses crimson-tinted background
- [ ] Header title has crimson underline accent
- [ ] Detail dialog shows larger poster + genre pills
- [ ] App launches without errors
- [ ] Existing functionality (search, add, edit, delete, bulk ops) unaffected
