# GUI Dark Luxury Visual Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restyle `gui_app.py` with a dark luxury crimson/gold palette, improved card layouts, a grid/list view toggle, and polished sidebar/header.

**Architecture:** Single-file in-place edit. All logic (database, API, models, recommender) is untouched. Only visual/layout code changes. The new `MediaListCard` class is added between `SearchResultCard` and `Sidebar`.

**Tech Stack:** Python 3, customtkinter (ctk), PIL/Pillow, tkinter

---

## Task 1: Update THEME dict

**Files:**
- Modify: `gui_app.py:31-57`

**Step 1: Replace the THEME dict**

Find and replace the entire THEME block (lines 32–57) with:

```python
# Dark Luxury Theme (crimson/gold premium)
THEME = {
    # Backgrounds
    "bg_primary": "#080808",       # Main app background (near-black)
    "bg_secondary": "#0F0F0F",      # Dialog/panel backgrounds
    "bg_card": "#141414",           # Card backgrounds
    "bg_card_hover": "#1E1E1E",     # Card hover state
    "bg_sidebar": "#050505",        # Sidebar background

    # Crimson Accents
    "accent_primary": "#DC143C",    # Crimson red
    "accent_hover": "#FF1744",      # Hover state
    "accent_glow": "#FF0030",       # Glow effects
    "accent_subtle": "#1A0008",     # Crimson-tinted bg for active nav

    # Text Colors
    "text_primary": "#FFFFFF",      # White
    "text_secondary": "#B3B3B3",    # Gray
    "text_muted": "#666666",        # Muted

    # Rating (rich gold)
    "rating_gold": "#FFD700",

    # Status Badge Colors
    "status_watched": "#22C55E",    # Green (completed)
    "status_watching": "#F97316",   # Orange (in progress)
    "status_planned": "#3B82F6",    # Blue (wishlist)
}
```

Also update the comment above `ctk.set_appearance_mode` on line 59:
```python
# Set appearance mode to dark only (luxury theme)
```

**Step 2: Launch the app to verify no crash**

```bash
cd /Users/dlgvnbyr/Documents/Hicheel/Deep\ Learning/media-tracker/local
python gui_app.py &
```

Expected: App opens, sidebar and buttons now show crimson instead of orange. Kill it.

**Step 3: Commit**

```bash
git add gui_app.py
git commit -m "style: apply dark luxury crimson/gold palette"
```

---

## Task 2: Polish the Sidebar

**Files:**
- Modify: `gui_app.py:410-518`

**Step 1: Update Sidebar docstring and logo section**

Find line 411 (`"""Dark cinematic sidebar navigation with orange accents."""`) and replace with:
```python
"""Dark luxury sidebar navigation with crimson accents."""
```

Find lines 424-448 (logo_frame block). After the "TRACKER" label pack call and before the "Local storage indicator" label, insert a crimson horizontal rule:

```python
        # Crimson rule under logo
        ctk.CTkFrame(
            logo_frame,
            height=2,
            fg_color=THEME["accent_primary"],
        ).pack(fill="x", pady=(8, 0))
```

**Step 2: Update active nav button background**

In `_on_click` (lines 496-514), find the active branch:
```python
                btn.configure(
                    fg_color=THEME["bg_card"],
                    text_color=THEME["text_primary"],
                )
```
Replace `THEME["bg_card"]` with `THEME["accent_subtle"]`:
```python
                btn.configure(
                    fg_color=THEME["accent_subtle"],
                    text_color=THEME["text_primary"],
                )
```

**Step 3: Update nav button comment**

Find line 464 (`"""Create a navigation button with orange accent bar."""`) and replace:
```python
        """Create a navigation button with crimson accent bar."""
```

**Step 4: Launch and verify**

```bash
python gui_app.py &
```

Expected: Active nav item has a dark crimson-tinted background. Crimson rule appears under logo. Kill it.

**Step 5: Commit**

```bash
git add gui_app.py
git commit -m "style: polish sidebar with crimson rule and active bg tint"
```

---

## Task 3: Update Header Title

**Files:**
- Modify: `gui_app.py:1017-1027`

**Step 1: Increase title font and add underline accent**

Find the `MainContent.__init__` header section. The header frame is height=60 — change it to height=70 to accommodate the underline:

```python
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=70)
```

Find the `self.title_label` block (lines 1021-1027). Replace it entirely:

```python
        # Title with crimson underline accent
        title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        title_frame.pack(side="left", anchor="w")

        self.title_label = ctk.CTkLabel(
            title_frame,
            text="Movies",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.title_label.pack(anchor="w")

        self.title_underline = ctk.CTkFrame(
            title_frame,
            height=3,
            width=44,
            corner_radius=2,
            fg_color=THEME["accent_primary"],
        )
        self.title_underline.pack(anchor="w", pady=(2, 0))
```

**Step 2: Launch and verify**

```bash
python gui_app.py &
```

Expected: Section title is larger (32px) with a short crimson underline below it. Kill it.

**Step 3: Commit**

```bash
git add gui_app.py
git commit -m "style: enlarge header title with crimson underline accent"
```

---

## Task 4: Add View Toggle to Header

**Files:**
- Modify: `gui_app.py:1086-1100` (after sort_menu.pack, before tab_frame)

**Step 1: Add view_mode state and toggle buttons**

After line 1085 (`self.sort_menu.pack(side="left")`), insert:

```python
        # View toggle: Grid / List
        ctk.CTkLabel(
            self.search_frame,
            text="View:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(15, 5))

        self.view_mode = "grid"
        self.view_toggle_frame = ctk.CTkFrame(
            self.search_frame,
            fg_color=THEME["bg_card"],
            corner_radius=8,
        )
        self.view_toggle_frame.pack(side="left")

        self.grid_btn = ctk.CTkButton(
            self.view_toggle_frame,
            text="⊞",
            width=34,
            height=34,
            corner_radius=7,
            font=ctk.CTkFont(size=16),
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=lambda: self._set_view_mode("grid"),
        )
        self.grid_btn.pack(side="left", padx=(2, 1), pady=2)

        self.list_btn = ctk.CTkButton(
            self.view_toggle_frame,
            text="☰",
            width=34,
            height=34,
            corner_radius=7,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            hover_color=THEME["bg_card_hover"],
            text_color=THEME["text_secondary"],
            command=lambda: self._set_view_mode("list"),
        )
        self.list_btn.pack(side="left", padx=(1, 2), pady=2)
```

**Step 2: Add `_set_view_mode` method**

Add this method to `MainContent` class, right after `_on_sort_change` (around line 1342):

```python
    def _set_view_mode(self, mode: str):
        """Switch between grid and list view."""
        self.view_mode = mode
        if mode == "grid":
            self.grid_btn.configure(fg_color=THEME["accent_primary"], text_color=THEME["text_primary"])
            self.list_btn.configure(fg_color="transparent", text_color=THEME["text_secondary"])
        else:
            self.list_btn.configure(fg_color=THEME["accent_primary"], text_color=THEME["text_primary"])
            self.grid_btn.configure(fg_color="transparent", text_color=THEME["text_secondary"])
        # Re-render current content
        self.app.refresh_content()
```

**Step 3: Launch and verify**

```bash
python gui_app.py &
```

Expected: Grid/List toggle appears in header. Clicking each highlights the active one in crimson. Kill it.

**Step 4: Commit**

```bash
git add gui_app.py
git commit -m "feat: add grid/list view toggle to header"
```

---

## Task 5: Add MediaListCard Component

**Files:**
- Modify: `gui_app.py` — insert new class after `SearchResultCard` (after line 408)

**Step 1: Add `MediaListCard` class**

Insert this new class between `SearchResultCard` and `Sidebar` (after the closing of `SearchResultCard`, around line 408):

```python
class MediaListCard(ctk.CTkFrame):
    """Dark luxury horizontal list card for media items."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        status: str,
        rating: Optional[int],
        image_url: Optional[str],
        on_click: Optional[Callable] = None,
        is_favorite: bool = False,
        on_favorite_toggle: Optional[Callable] = None,
        media_id: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.on_click = on_click
        self.on_favorite_toggle = on_favorite_toggle
        self.is_favorite = is_favorite
        self.media_id = media_id

        self.configure(
            corner_radius=10,
            fg_color=THEME["bg_card"],
            height=90,
        )
        self.pack_propagate(False)

        # Poster thumbnail
        self.image_label = ctk.CTkLabel(
            self,
            text="",
            width=60,
            height=82,
            corner_radius=6,
            fg_color=THEME["bg_secondary"],
        )
        self.image_label.pack(side="left", padx=(10, 12), pady=4)

        if image_url:
            ImageLoader.load_async(image_url, self._set_image, size=(60, 90))

        # Info column
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=12)

        ctk.CTkLabel(
            info_frame,
            text=title[:50] + "..." if len(title) > 50 else title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            info_frame,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Right side: status + rating + favorite
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", padx=15, pady=12)

        status_colors = {
            "watched": THEME["status_watched"],
            "watching": THEME["status_watching"],
            "want_to_watch": THEME["status_planned"],
            "read": THEME["status_watched"],
            "reading": THEME["status_watching"],
            "want_to_read": THEME["status_planned"],
            "completed": THEME["status_watched"],
            "on_hold": THEME["text_muted"],
            "dropped": THEME["text_muted"],
        }
        color = status_colors.get(status, THEME["text_muted"])

        ctk.CTkLabel(
            right_frame,
            text=status.replace("_", " ").title(),
            font=ctk.CTkFont(size=11),
            fg_color=color,
            corner_radius=6,
            text_color=THEME["bg_primary"],
            padx=8,
            pady=2,
        ).pack(anchor="e")

        rating_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        rating_row.pack(anchor="e", pady=(4, 0))

        if rating:
            ctk.CTkLabel(
                rating_row,
                text=f"⭐ {rating}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=THEME["rating_gold"],
            ).pack(side="left")
            ctk.CTkLabel(
                rating_row,
                text="/10",
                font=ctk.CTkFont(size=11),
                text_color=THEME["text_muted"],
            ).pack(side="left")

        heart_text = "❤️" if is_favorite else "🤍"
        self.favorite_btn = ctk.CTkButton(
            right_frame,
            text=heart_text,
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color=THEME["bg_card_hover"],
            command=self._toggle_favorite,
        )
        self.favorite_btn.pack(anchor="e", pady=(4, 0))

        # Bind hover and click
        if on_click:
            self._bind_events_recursive(self)

    def _bind_events_recursive(self, widget):
        if widget == self.favorite_btn:
            return
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Enter>", self._on_hover_enter)
        widget.bind("<Leave>", self._on_hover_leave)
        widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            self._bind_events_recursive(child)

    def _toggle_favorite(self):
        self.is_favorite = not self.is_favorite
        self.favorite_btn.configure(text="❤️" if self.is_favorite else "🤍")
        if self.on_favorite_toggle:
            self.on_favorite_toggle(self.is_favorite)

    def _on_hover_enter(self, event):
        self.configure(fg_color=THEME["bg_card_hover"], border_width=1, border_color=THEME["accent_glow"])

    def _on_hover_leave(self, event):
        self.configure(fg_color=THEME["bg_card"], border_width=0)

    def _handle_click(self, event):
        if self.on_click:
            self.on_click()

    def _set_image(self, image: Optional[ctk.CTkImage]):
        if image:
            self.image_label.configure(image=image, text="")
```

**Step 2: Launch and verify no crash**

```bash
python gui_app.py &
```

Expected: App launches normally (list cards aren't rendered yet, just defined). Kill it.

**Step 3: Commit**

```bash
git add gui_app.py
git commit -m "feat: add MediaListCard horizontal list component"
```

---

## Task 6: Wire List Mode into _display_media_grid

**Files:**
- Modify: `gui_app.py:1963-2058`

**Step 1: Update `_create_card_for_item` to support list mode**

Find `_create_card_for_item` (line 1963). The current method always creates a `MediaCard`. We need to check `self.view_mode` and create the right card type.

Replace the entire `_create_card_for_item` method:

```python
    def _create_card_for_item(self, parent, item, media_type: str):
        """Create a MediaCard or MediaListCard for an item based on current view mode."""
        if media_type == "movie":
            subtitle = f"{item.year or 'N/A'}"
            image_url = item.poster_url
            progress = None
        elif media_type == "book":
            subtitle = f"{item.author or 'Unknown'}"
            image_url = item.cover_url
            progress = None
        else:  # series
            subtitle = f"{item.year or 'N/A'}"
            image_url = item.poster_url
            total_watched = len(item.episodes_watched) if hasattr(item, 'episodes_watched') else 0
            estimated_total = item.total_seasons * 10 if hasattr(item, 'total_seasons') else 10
            progress = min(1.0, total_watched / estimated_total) if estimated_total > 0 else 0

        if self.view_mode == "list":
            card = MediaListCard(
                parent,
                title=item.title,
                subtitle=subtitle,
                status=item.status.value,
                rating=item.user_rating,
                image_url=image_url,
                on_click=lambda i=item, t=media_type: self.app.show_detail(i, t) if not self.selection_mode else None,
                is_favorite=item.is_favorite,
                on_favorite_toggle=lambda fav, i=item, t=media_type: self.app.toggle_favorite(i, t, fav),
                media_id=item.id,
            )
            card.pack(fill="x", padx=5, pady=4)
        else:
            card = MediaCard(
                parent,
                title=item.title,
                subtitle=subtitle,
                status=item.status.value,
                rating=item.user_rating,
                image_url=image_url,
                on_click=lambda i=item, t=media_type: self.app.show_detail(i, t) if not self.selection_mode else None,
                is_favorite=item.is_favorite,
                on_favorite_toggle=lambda fav, i=item, t=media_type: self.app.toggle_favorite(i, t, fav),
                selectable=self.selection_mode,
                selected=item.id in self.selected_items,
                on_select=self._on_item_select if self.selection_mode else None,
                media_id=item.id,
                progress=progress,
            )
            card.pack(side="left", padx=10, pady=10)
        return card
```

**Step 2: Update `_display_media_grid` to handle list layout**

In `_display_media_grid` (line 2001), the grid uses row frames with items packed `side="left"`. In list mode we want items stacked vertically in a single column frame.

Replace the grid creation block at the bottom of `_display_media_grid` (lines 2046–2058):

```python
        if self.view_mode == "list":
            # Single column list
            list_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
            list_frame.pack(fill="x", pady=5, padx=5)
            for item in items:
                self._create_card_for_item(list_frame, item, media_type)
        else:
            # Calculate columns based on width
            width = self.winfo_width()
            card_width = 210
            columns = max(1, (width - 60) // card_width)

            row_frame = None
            for i, item in enumerate(items):
                if i % columns == 0:
                    row_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
                    row_frame.pack(fill="x", pady=5)
                self._create_card_for_item(row_frame, item, media_type)
```

**Step 3: Launch and verify**

```bash
python gui_app.py &
```

Expected: Click ☰ List toggle → movies switch to horizontal list cards. Click ⊞ Grid → back to poster grid. Kill it.

**Step 4: Commit**

```bash
git add gui_app.py
git commit -m "feat: wire grid/list view toggle to media display"
```

---

## Task 7: Restyle MediaCard (Grid View)

**Files:**
- Modify: `gui_app.py:129-352`

**Step 1: Update card padding and title font**

In `MediaCard.__init__`, find the image_label pack line (line 192):
```python
        self.image_label.pack(padx=8, pady=(8, 5))
```
Change to:
```python
        self.image_label.pack(padx=10, pady=(10, 6))
```

Find the title_label (line 212-219). Change font size from 14 to 15:
```python
            font=ctk.CTkFont(size=15, weight="bold"),
```

**Step 2: Update rating display format**

Find lines 262-275 (the rating_frame block). Replace the `rating_label` text format:

```python
            self.rating_label = ctk.CTkLabel(
                rating_frame,
                text=f"⭐ {rating}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=THEME["rating_gold"],
            )
```

**Step 3: Move favorite button to poster overlay**

Currently the favorite button is in `bottom_frame`. We need to:
1. Remove it from `bottom_frame`
2. Re-add it as an overlay on the image using `.place()`

Find the bottom_frame section (lines 253-292). Remove the favorite button creation block from bottom_frame. Then, after the `self.image_label.pack(...)` line, add:

```python
        # Favorite button overlaid on poster (top-right)
        heart_text = "❤️" if is_favorite else "🤍"
        self.favorite_btn = ctk.CTkButton(
            self,
            text=heart_text,
            width=32,
            height=32,
            corner_radius=16,
            fg_color="#00000088",
            hover_color=THEME["bg_card_hover"],
            command=self._toggle_favorite,
        )
        self.favorite_btn.place(relx=1.0, rely=0, anchor="ne", x=-14, y=14)
```

Also update `_bind_events_recursive` — the check `if widget == self.favorite_btn` already handles this correctly (skips the favorite button), so no changes needed there.

**Step 4: Launch and verify**

```bash
python gui_app.py &
```

Expected: Cards show ⭐ gold rating, heart overlaid top-right of poster, slightly more padding. Kill it.

**Step 5: Commit**

```bash
git add gui_app.py
git commit -m "style: restyle grid MediaCard with overlay favorite, ⭐ rating"
```

---

## Task 8: Update MediaDetailDialog

**Files:**
- Modify: `gui_app.py:677-1005`

**Step 1: Increase poster size**

Find line 725-734 (self.image_label in MediaDetailDialog):
```python
        self.image_label = ctk.CTkLabel(
            scroll,
            text="Loading...",
            width=220,
            height=330,
```
Change to `width=240, height=360`.

Find line 738 (ImageLoader.load_async call):
```python
            ImageLoader.load_async(image_url, self._set_image, size=(220, 330))
```
Change to `size=(240, 360)`.

**Step 2: Add genre pill badges**

Find the genre/subjects display block (lines 763-778). This currently uses a plain `CTkLabel` with comma text. Replace:

For the movie genre block:
```python
        if media_type == "movie" and media.genre:
            genre_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            genre_frame.pack(anchor="w", pady=(0, 10))
            for g in media.genre.split(", ")[:4]:
                ctk.CTkLabel(
                    genre_frame,
                    text=g.strip(),
                    font=ctk.CTkFont(size=12),
                    fg_color=THEME["bg_card_hover"],
                    corner_radius=6,
                    text_color=THEME["text_secondary"],
                    padx=8,
                    pady=3,
                ).pack(side="left", padx=(0, 6))
```

For the book subjects block:
```python
        elif media_type == "book" and media.subjects:
            subj_frame = ctk.CTkFrame(scroll, fg_color="transparent")
            subj_frame.pack(anchor="w", pady=(0, 10))
            for s in media.subjects.split(", ")[:4]:
                ctk.CTkLabel(
                    subj_frame,
                    text=s.strip(),
                    font=ctk.CTkFont(size=12),
                    fg_color=THEME["bg_card_hover"],
                    corner_radius=6,
                    text_color=THEME["text_secondary"],
                    padx=8,
                    pady=3,
                ).pack(side="left", padx=(0, 6))
```

**Step 3: Update Save Changes button color**

Find line 926-934 (Save Changes button in MediaDetailDialog). Verify `fg_color=THEME["accent_primary"]` — this is already correct since THEME["accent_primary"] is now crimson. No change needed.

**Step 4: Launch and verify**

```bash
python gui_app.py &
```

Expected: Click any movie/book card → detail dialog opens with larger poster, genre tags as pill badges. Kill it.

**Step 5: Commit**

```bash
git add gui_app.py
git commit -m "style: detail dialog with larger poster and genre pill badges"
```

---

## Task 9: Final Polish Pass

**Files:**
- Modify: `gui_app.py` — minor fixes pass

**Step 1: Update MediaDetailDialog series status list**

The `MediaDetailDialog` has a hard-coded series status check but only maps movie/book (lines 799-804). Check line 799 — if `media_type == "series"` is missing a branch, it falls through silently. No change needed (series uses its own `SeriesDetailDialog` class).

**Step 2: Verify full app walkthrough**

```bash
python gui_app.py
```

Manual checklist:
- [ ] Crimson accent visible on sidebar active item, buttons, badges
- [ ] Gold rating stars on cards
- [ ] Header title 32px with crimson underline
- [ ] View toggle switches grid ↔ list
- [ ] List cards show thumbnail + info row
- [ ] Favorite heart overlaid on grid card posters
- [ ] Detail dialog: larger poster, genre pills
- [ ] Search still works (add a movie)
- [ ] Edit/delete still works
- [ ] Stats view still loads

**Step 3: Final commit**

```bash
git add gui_app.py
git commit -m "style: complete dark luxury visual overhaul"
```

---

## Summary

| Task | What changes | Lines |
|---|---|---|
| 1 | THEME dict — new colors | 32–57 |
| 2 | Sidebar — rule + active tint | 411–518 |
| 3 | Header title — size + underline | 1017–1027 |
| 4 | View toggle buttons + `_set_view_mode` | 1085+, ~1342 |
| 5 | New `MediaListCard` class | after line 408 |
| 6 | `_create_card_for_item` + `_display_media_grid` | 1963–2058 |
| 7 | `MediaCard` — overlay heart, ⭐ rating, padding | 129–352 |
| 8 | `MediaDetailDialog` — poster size, genre pills | 677–1005 |
| 9 | Final verification pass | — |
