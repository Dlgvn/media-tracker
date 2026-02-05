#!/usr/bin/env python3
"""Media Tracker GUI (Local) - Stores data in local JSON files."""

import io
import os
import threading
import tkinter as tk
from tkinter import filedialog
from typing import Callable, List, Optional, Tuple
from urllib.request import urlopen

import customtkinter as ctk
from PIL import Image, ImageDraw

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from book_api import BookAPI, OpenLibraryError
from database import Database, DatabaseError
from models import Book, BookStatus, Movie, MovieStatus, Series, SeriesStatus
from movie_api import MovieAPI, OMDBError
from recommender import Recommender


# Dark Cinematic Theme (Netflix/IMDB inspired)
THEME = {
    # Backgrounds
    "bg_primary": "#0D0D0D",       # Main app background (near-black)
    "bg_secondary": "#141414",      # Netflix-style dark
    "bg_card": "#1A1A1A",           # Card backgrounds
    "bg_card_hover": "#252525",     # Card hover state
    "bg_sidebar": "#0A0A0A",        # Sidebar background

    # Orange Accents (Netflix + IMDB inspired)
    "accent_primary": "#E65100",    # Main orange
    "accent_hover": "#FF8C00",      # Hover state
    "accent_glow": "#FF6600",       # Glow effects

    # Text Colors
    "text_primary": "#FFFFFF",      # White
    "text_secondary": "#B3B3B3",    # Gray
    "text_muted": "#666666",        # Muted

    # Rating (IMDB-style gold)
    "rating_gold": "#F5C518",

    # Status Badge Colors
    "status_watched": "#4ADE80",    # Green (completed)
    "status_watching": "#FB923C",   # Orange (in progress)
    "status_planned": "#60A5FA",    # Blue (wishlist)
}

# Set appearance mode to dark only (cinematic theme)
ctk.set_appearance_mode("dark")


class ImageLoader:
    """Async image loader with caching and gradient overlay support."""

    _cache: dict = {}

    @classmethod
    def load_async(
        cls,
        url: str,
        callback: Callable[[Optional[ctk.CTkImage]], None],
        size: tuple = (180, 270),
        add_gradient: bool = False,
    ):
        """Load image asynchronously and call callback with result."""
        if not url or url == "N/A":
            callback(None)
            return

        cache_key = f"{url}_{size}_{add_gradient}"
        if cache_key in cls._cache:
            callback(cls._cache[cache_key])
            return

        def _load():
            try:
                with urlopen(url, timeout=10) as response:
                    image_data = response.read()
                pil_image = Image.open(io.BytesIO(image_data))
                pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)

                # Add gradient overlay for cinematic effect
                if add_gradient:
                    pil_image = cls._add_gradient_overlay(pil_image)

                ctk_image = ctk.CTkImage(
                    light_image=pil_image, dark_image=pil_image, size=size
                )
                cls._cache[cache_key] = ctk_image
                callback(ctk_image)
            except Exception:
                callback(None)

        threading.Thread(target=_load, daemon=True).start()

    @classmethod
    def _add_gradient_overlay(cls, image: Image.Image) -> Image.Image:
        """Add a bottom gradient overlay for text readability."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        width, height = image.size
        gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)

        # Create gradient in bottom third
        gradient_height = height // 3
        for y in range(gradient_height):
            alpha = int(180 * (y / gradient_height))
            draw.line(
                [(0, height - gradient_height + y), (width, height - gradient_height + y)],
                fill=(0, 0, 0, alpha),
            )

        return Image.alpha_composite(image, gradient)


class MediaCard(ctk.CTkFrame):
    """Dark cinematic card for displaying media items with hover effects."""

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
        selectable: bool = False,
        selected: bool = False,
        on_select: Optional[Callable] = None,
        media_id: Optional[int] = None,
        progress: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.on_click = on_click
        self.on_favorite_toggle = on_favorite_toggle
        self.is_favorite = is_favorite
        self.selectable = selectable
        self.selected = selected
        self.on_select = on_select
        self.media_id = media_id
        self.configure(
            corner_radius=12,
            fg_color=THEME["bg_card"],
            border_width=2 if selected else 0,
            border_color=THEME["accent_primary"] if selected else THEME["bg_card"],
        )

        # Selection checkbox (shown when selectable)
        if selectable:
            self.checkbox = ctk.CTkCheckBox(
                self,
                text="",
                width=24,
                height=24,
                checkbox_width=20,
                checkbox_height=20,
                fg_color=THEME["accent_primary"],
                hover_color=THEME["accent_hover"],
                command=self._on_checkbox_toggle,
            )
            self.checkbox.place(x=12, y=12, anchor="nw")
            if selected:
                self.checkbox.select()

        # Image placeholder (larger 180x270 for cinematic ratio)
        self.image_label = ctk.CTkLabel(
            self,
            text="🎬",
            width=180,
            height=270,
            corner_radius=8,
            fg_color=THEME["bg_secondary"],
        )
        self.image_label.pack(padx=8, pady=(8, 5))

        # Load image async with gradient overlay
        if image_url:
            ImageLoader.load_async(image_url, self._set_image, size=(180, 270), add_gradient=True)

        # Progress bar for series
        if progress is not None:
            progress_frame = ctk.CTkFrame(self, fg_color="transparent", height=6)
            progress_frame.pack(fill="x", padx=12, pady=(0, 2))
            self.progress_bar = ctk.CTkProgressBar(
                progress_frame,
                height=4,
                progress_color=THEME["accent_primary"],
                fg_color=THEME["bg_secondary"],
            )
            self.progress_bar.pack(fill="x")
            self.progress_bar.set(progress)

        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title[:25] + "..." if len(title) > 25 else title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=170,
        )
        self.title_label.pack(padx=8, pady=(5, 0))

        # Subtitle (year/author)
        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        )
        self.subtitle_label.pack(padx=8)

        # Status badge with themed colors
        status_colors = {
            "watched": THEME["status_watched"],
            "watching": THEME["status_watching"],
            "want_to_watch": THEME["status_planned"],
            "read": THEME["status_watched"],
            "reading": THEME["status_watching"],
            "want_to_read": THEME["status_planned"],
        }
        color = status_colors.get(status, THEME["text_muted"])

        self.status_badge = ctk.CTkLabel(
            self,
            text=status.replace("_", " ").title(),
            font=ctk.CTkFont(size=11),
            fg_color=color,
            corner_radius=8,
            text_color=THEME["bg_primary"],
            padx=8,
            pady=2,
        )
        self.status_badge.pack(pady=(5, 0))

        # Bottom row with rating and favorite button
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=8, pady=(5, 10))

        # IMDB-style gold rating badge
        if rating:
            rating_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
            rating_frame.pack(side="left")

            self.rating_label = ctk.CTkLabel(
                rating_frame,
                text=f"★ {rating}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=THEME["rating_gold"],
            )
            self.rating_label.pack(side="left")

            ctk.CTkLabel(
                rating_frame,
                text="/10",
                font=ctk.CTkFont(size=11),
                text_color=THEME["text_muted"],
            ).pack(side="left")
        else:
            self.rating_label = ctk.CTkLabel(bottom_frame, text="", height=10)
            self.rating_label.pack(side="left")

        # Favorite heart button
        heart_text = "❤️" if is_favorite else "🤍"
        self.favorite_btn = ctk.CTkButton(
            bottom_frame,
            text=heart_text,
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color=THEME["bg_card_hover"],
            command=self._toggle_favorite,
        )
        self.favorite_btn.pack(side="right")

        # Bind click and hover to all widgets
        if on_click:
            self._bind_events_recursive(self)

    def _bind_events_recursive(self, widget):
        """Bind click and hover events to widget and all its children."""
        # Skip the favorite button - it has its own click handler
        if widget == self.favorite_btn:
            return
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Enter>", self._on_hover_enter)
        widget.bind("<Leave>", self._on_hover_leave)
        widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            self._bind_events_recursive(child)

    def _toggle_favorite(self):
        """Toggle favorite status."""
        self.is_favorite = not self.is_favorite
        heart_text = "❤️" if self.is_favorite else "🤍"
        self.favorite_btn.configure(text=heart_text)
        if self.on_favorite_toggle:
            self.on_favorite_toggle(self.is_favorite)

    def _on_checkbox_toggle(self):
        """Handle checkbox toggle in selection mode."""
        self.selected = not self.selected
        self.configure(
            border_width=2 if self.selected else 0,
            border_color=THEME["accent_primary"] if self.selected else THEME["bg_card"],
        )
        if self.on_select:
            self.on_select(self.media_id, self.selected)

    def _on_hover_enter(self, event):
        """Handle hover enter - orange glow effect."""
        self.configure(
            fg_color=THEME["bg_card_hover"],
            border_width=2,
            border_color=THEME["accent_glow"],
        )

    def _on_hover_leave(self, event):
        """Handle hover leave - remove glow."""
        self.configure(
            fg_color=THEME["bg_card"],
            border_width=0,
        )

    def _handle_click(self, event):
        """Handle click event."""
        if self.on_click:
            self.on_click()

    def _set_image(self, image: Optional[ctk.CTkImage]):
        """Set the card image."""
        if image:
            self.image_label.configure(image=image, text="")


class SearchResultCard(ctk.CTkFrame):
    """Dark themed card for search results."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        on_add: Callable,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.configure(corner_radius=12, fg_color=THEME["bg_card"])

        # Content frame using grid for better layout
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)
        content.grid_columnconfigure(0, weight=1)

        # Text info
        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            text_frame,
            text=title[:45] + "..." if len(title) > 45 else title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text=subtitle[:40] + "..." if len(subtitle) > 40 else subtitle,
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
        ).pack(anchor="w")

        # Orange Add button
        self.add_btn = ctk.CTkButton(
            content,
            text="+ Add",
            width=80,
            height=35,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=on_add,
        )
        self.add_btn.grid(row=0, column=1, padx=(15, 0), sticky="e")


class Sidebar(ctk.CTkFrame):
    """Dark cinematic sidebar navigation with orange accents."""

    def __init__(self, parent, on_navigate: Callable, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(width=220, corner_radius=0, fg_color=THEME["bg_sidebar"])
        self.pack_propagate(False)

        self.on_navigate = on_navigate
        self.buttons = {}
        self.accent_bars = {}
        self.active = None

        # Logo/Title with orange accent
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(25, 30))

        ctk.CTkLabel(
            logo_frame,
            text="MEDIA",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=THEME["accent_primary"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame,
            text="TRACKER",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w")

        # Local storage indicator
        ctk.CTkLabel(
            logo_frame,
            text="📁 Local Storage",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_muted"],
        ).pack(anchor="w", pady=(5, 0))

        # Navigation items
        nav_items = [
            ("movies", "🎬", "Movies"),
            ("books", "📚", "Books"),
            ("series", "📺", "TV Series"),
            ("recent", "🕐", "Recently Added"),
            ("recommend", "✨", "For You"),
            ("stats", "📊", "Statistics"),
        ]

        for key, icon, label in nav_items:
            self._create_nav_button(key, icon, label)

    def _create_nav_button(self, key: str, icon: str, label: str):
        """Create a navigation button with orange accent bar."""
        # Container for accent bar + button
        container = ctk.CTkFrame(self, fg_color="transparent", height=45)
        container.pack(fill="x", pady=3)
        container.pack_propagate(False)

        # Orange accent bar on left (hidden by default)
        accent_bar = ctk.CTkFrame(
            container,
            width=4,
            height=35,
            corner_radius=2,
            fg_color="transparent",
        )
        accent_bar.place(x=0, rely=0.5, anchor="w")
        self.accent_bars[key] = accent_bar

        btn = ctk.CTkButton(
            container,
            text=f"  {icon}  {label}",
            font=ctk.CTkFont(size=15),
            anchor="w",
            height=45,
            corner_radius=10,
            fg_color="transparent",
            text_color=THEME["text_secondary"],
            hover_color=THEME["bg_card"],
            command=lambda: self._on_click(key),
        )
        btn.pack(fill="x", padx=(15, 15), side="left", expand=True)
        self.buttons[key] = btn

    def _on_click(self, key: str):
        """Handle navigation click."""
        # Update visual state
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(
                    fg_color=THEME["bg_card"],
                    text_color=THEME["text_primary"],
                )
                self.accent_bars[k].configure(fg_color=THEME["accent_primary"])
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text_secondary"],
                )
                self.accent_bars[k].configure(fg_color="transparent")

        self.active = key
        self.on_navigate(key)

    def set_active(self, key: str):
        """Set active navigation item."""
        self._on_click(key)


class AddMediaDialog(ctk.CTkToplevel):
    """Dark cinematic dialog for adding media with status selection."""

    def __init__(self, parent, media_type: str, title: str, on_confirm: Callable):
        super().__init__(parent)

        self.on_confirm = on_confirm
        self.media_type = media_type
        self.result = None

        self.title(f"Add {media_type.title()}")
        self.geometry("420x400")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_secondary"])

        # Center on parent and focus
        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Center the dialog on screen
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 210
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 200
        self.geometry(f"420x400+{x}+{y}")

        # Content
        ctk.CTkLabel(
            self,
            text="Add to your library",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=title[:45] + "..." if len(title) > 45 else title,
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_secondary"],
        ).pack(pady=(0, 15))

        # Status selection
        ctk.CTkLabel(
            self,
            text="Status:",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=40)

        if media_type == "movie":
            statuses = ["Want to Watch", "Watching", "Watched"]
        elif media_type == "book":
            statuses = ["Want to Read", "Reading", "Read"]
        else:  # series
            statuses = ["Want to Watch", "Watching", "Completed", "On Hold", "Dropped"]

        self.status_var = ctk.StringVar(value=statuses[0])
        self.status_menu = ctk.CTkOptionMenu(
            self,
            values=statuses,
            variable=self.status_var,
            width=340,
            height=38,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
        )
        self.status_menu.pack(pady=(5, 15))

        # Rating section
        ctk.CTkLabel(
            self,
            text="Rating (optional):",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=40)

        rating_row = ctk.CTkFrame(self, fg_color="transparent")
        rating_row.pack(fill="x", padx=40, pady=(5, 5))

        self.rating_slider = ctk.CTkSlider(
            rating_row,
            from_=1,
            to=10,
            number_of_steps=9,
            width=280,
            progress_color=THEME["accent_primary"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
        )
        self.rating_slider.pack(side="left")
        self.rating_slider.set(5)

        self.rating_label = ctk.CTkLabel(
            rating_row,
            text="5",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=40,
            text_color=THEME["rating_gold"],
        )
        self.rating_label.pack(side="left", padx=(10, 0))

        self.rating_slider.configure(command=self._update_rating_label)

        self.use_rating = ctk.CTkCheckBox(
            self,
            text="Include rating",
            text_color=THEME["text_secondary"],
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
        )
        self.use_rating.pack(pady=(10, 15))

        # Buttons - at the bottom
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 25))

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=120,
            height=40,
            fg_color="transparent",
            border_width=2,
            border_color=THEME["text_muted"],
            text_color=THEME["text_secondary"],
            hover_color=THEME["bg_card"],
            command=self.destroy,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Add to Library",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=self._confirm,
        ).pack(side="left", padx=10)

    def _update_rating_label(self, value):
        self.rating_label.configure(text=str(int(value)))

    def _confirm(self):
        status_text = self.status_var.get().lower().replace(" ", "_")
        rating = int(self.rating_slider.get()) if self.use_rating.get() else None
        self.on_confirm(status_text, rating)
        self.destroy()


class MediaDetailDialog(ctk.CTkToplevel):
    """Dark cinematic dialog showing media details with edit options."""

    def __init__(
        self,
        parent,
        media,
        media_type: str,
        on_update: Callable,
        on_delete: Callable,
        similar_items: Optional[List[Tuple]] = None,
        on_show_similar: Optional[Callable] = None,
    ):
        super().__init__(parent)

        self.media = media
        self.media_type = media_type
        self.on_update = on_update
        self.on_delete = on_delete
        self.similar_items = similar_items or []
        self.on_show_similar = on_show_similar

        self.title("Details")
        self.geometry("500x800")
        self.minsize(400, 600)
        self.configure(fg_color=THEME["bg_secondary"])

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Center the dialog on screen
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 350
        self.geometry(f"500x700+{x}+{y}")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=THEME["bg_card"],
            scrollbar_button_hover_color=THEME["bg_card_hover"],
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Larger poster image (cinematic)
        self.image_label = ctk.CTkLabel(
            scroll,
            text="Loading...",
            width=220,
            height=330,
            corner_radius=12,
            fg_color=THEME["bg_card"],
            text_color=THEME["text_muted"],
        )
        self.image_label.pack(pady=(0, 20))

        image_url = media.poster_url if media_type == "movie" else media.cover_url
        if image_url:
            ImageLoader.load_async(image_url, self._set_image, size=(220, 330))

        # Title
        ctk.CTkLabel(
            scroll,
            text=media.title,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=450,
        ).pack(pady=(0, 5))

        # Subtitle
        if media_type == "movie":
            subtitle = f"{media.year or 'N/A'} • {media.director or 'Unknown Director'}"
        else:
            subtitle = f"{media.publish_year or 'N/A'} • {media.author or 'Unknown Author'}"

        ctk.CTkLabel(
            scroll,
            text=subtitle,
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_secondary"],
        ).pack(pady=(0, 15))

        # Genre/Subjects
        if media_type == "movie" and media.genre:
            ctk.CTkLabel(
                scroll,
                text=media.genre,
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"],
                wraplength=450,
            ).pack(pady=(0, 10))
        elif media_type == "book" and media.subjects:
            ctk.CTkLabel(
                scroll,
                text=media.subjects,
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"],
                wraplength=450,
            ).pack(pady=(0, 10))

        # Plot (movies only)
        if media_type == "movie" and media.plot:
            ctk.CTkLabel(
                scroll,
                text=media.plot,
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"],
                wraplength=450,
                justify="left",
            ).pack(pady=(0, 15))

        # Status selector
        ctk.CTkLabel(
            scroll,
            text="Status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        if media_type == "movie":
            statuses = ["want_to_watch", "watching", "watched"]
            status_labels = ["Want to Watch", "Watching", "Watched"]
        else:
            statuses = ["want_to_read", "reading", "read"]
            status_labels = ["Want to Read", "Reading", "Read"]

        current_status = media.status.value
        self.status_var = ctk.StringVar(value=status_labels[statuses.index(current_status)])

        self.status_menu = ctk.CTkOptionMenu(
            scroll,
            values=status_labels,
            variable=self.status_var,
            width=200,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
        )
        self.status_menu.pack(anchor="w", pady=(0, 15))

        # Rating
        ctk.CTkLabel(
            scroll,
            text="Your Rating",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        rating_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rating_frame.pack(anchor="w", pady=(0, 20))

        self.rating_slider = ctk.CTkSlider(
            rating_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            width=200,
            progress_color=THEME["accent_primary"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
        )
        self.rating_slider.pack(side="left")
        self.rating_slider.set(media.user_rating or 5)

        self.rating_label = ctk.CTkLabel(
            rating_frame,
            text=str(media.user_rating or 5),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["rating_gold"],
            width=30,
        )
        self.rating_label.pack(side="left", padx=10)

        self.rating_slider.configure(command=self._update_rating_label)

        self.use_rating = ctk.CTkCheckBox(
            scroll,
            text="Include rating",
            text_color=THEME["text_secondary"],
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
        )
        if media.user_rating:
            self.use_rating.select()
        self.use_rating.pack(anchor="w", pady=(0, 20))

        # Notes section
        ctk.CTkLabel(
            scroll,
            text="Notes / Review",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        self.notes_textbox = ctk.CTkTextbox(
            scroll,
            height=120,
            width=450,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
            border_color=THEME["bg_card_hover"],
            border_width=1,
            wrap="word",
        )
        self.notes_textbox.pack(anchor="w", pady=(0, 20))
        if media.notes:
            self.notes_textbox.insert("1.0", media.notes)

        # Similar items section
        if self.similar_items:
            ctk.CTkLabel(
                scroll,
                text="Similar in Your Library",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=THEME["text_primary"],
            ).pack(anchor="w", pady=(10, 5))

            similar_scroll = ctk.CTkScrollableFrame(
                scroll,
                height=140,
                fg_color="transparent",
                orientation="horizontal",
            )
            similar_scroll.pack(fill="x", pady=(0, 20))

            for item, score in self.similar_items[:5]:
                self._create_mini_card(similar_scroll, item)

        # Action buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            width=100,
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color=THEME["text_primary"],
            command=self._delete,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Save Changes",
            width=150,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=self._save,
        ).pack(side="right")

    def _set_image(self, image):
        if image:
            self.image_label.configure(image=image, text="")

    def _update_rating_label(self, value):
        self.rating_label.configure(text=str(int(value)))

    def _save(self):
        status_text = self.status_var.get().lower().replace(" ", "_")
        rating = int(self.rating_slider.get()) if self.use_rating.get() else None
        notes = self.notes_textbox.get("1.0", "end-1c").strip() or None
        self.on_update(self.media.id, status_text, rating, notes)
        self.destroy()

    def _delete(self):
        self.on_delete(self.media.id)
        self.destroy()

    def _create_mini_card(self, parent, item):
        """Create a mini card for similar items."""
        card = ctk.CTkFrame(parent, width=80, height=130, fg_color=THEME["bg_card"], corner_radius=8)
        card.pack(side="left", padx=5)
        card.pack_propagate(False)

        # Mini poster
        poster_label = ctk.CTkLabel(
            card,
            text="",
            width=70,
            height=100,
            corner_radius=4,
            fg_color=THEME["bg_secondary"],
        )
        poster_label.pack(padx=5, pady=(5, 2))

        # Get image URL based on media type
        if self.media_type == "movie":
            image_url = item.poster_url
        elif self.media_type == "book":
            image_url = item.cover_url
        else:
            image_url = getattr(item, 'poster_url', None)

        if image_url:
            ImageLoader.load_async(
                image_url,
                lambda img, lbl=poster_label: lbl.configure(image=img) if img else None,
                size=(70, 100)
            )

        # Title (truncated)
        title_text = item.title[:10] + "..." if len(item.title) > 10 else item.title
        ctk.CTkLabel(
            card,
            text=title_text,
            font=ctk.CTkFont(size=10),
            text_color=THEME["text_secondary"],
        ).pack()

        # Make clickable
        if self.on_show_similar:
            card.bind("<Button-1>", lambda e, i=item: self._open_similar(i))
            card.configure(cursor="hand2")

    def _open_similar(self, item):
        """Open similar item detail."""
        self.destroy()
        if self.on_show_similar:
            self.on_show_similar(item, self.media_type)


class MainContent(ctk.CTkFrame):
    """Dark cinematic main content area."""

    def __init__(self, parent, app: "MediaTrackerApp", **kwargs):
        super().__init__(parent, **kwargs)

        self.app = app
        self.configure(fg_color=THEME["bg_primary"])

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header.pack(fill="x", padx=30, pady=(20, 10))
        self.header.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Movies",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.title_label.pack(side="left", anchor="w")

        # Search frame
        self.search_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.search_frame.pack(side="right")

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Search...",
            width=250,
            height=38,
            corner_radius=10,
            fg_color=THEME["bg_card"],
            border_color=THEME["bg_card_hover"],
            text_color=THEME["text_primary"],
            placeholder_text_color=THEME["text_muted"],
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        self.search_btn = ctk.CTkButton(
            self.search_frame,
            text="🔍",
            width=38,
            height=38,
            corner_radius=10,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            command=self._on_search,
        )
        self.search_btn.pack(side="left")

        # Sort dropdown
        self.current_sort = "date_added"
        self.sort_options = ["Date Added", "Title (A-Z)", "Title (Z-A)", "Rating (High-Low)", "Rating (Low-High)"]
        self.sort_var = ctk.StringVar(value=self.sort_options[0])

        ctk.CTkLabel(
            self.search_frame,
            text="Sort:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(15, 5))

        self.sort_menu = ctk.CTkOptionMenu(
            self.search_frame,
            values=self.sort_options,
            variable=self.sort_var,
            width=140,
            height=38,
            corner_radius=10,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_sort_change,
        )
        self.sort_menu.pack(side="left")

        # Tab bar for filtering
        self.tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_frame.pack(fill="x", padx=30, pady=(0, 10))

        self.tabs = {}
        self.tab_underlines = {}
        self.current_tab = "all"

        # Filter state
        self.genre_filter = None
        self.year_filter = None
        self.rating_filter = None
        self.available_genres = []

        # Selection mode state
        self.selection_mode = False
        self.selected_items = set()

        # Filter bar
        self.filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_frame.pack(fill="x", padx=30, pady=(0, 5))

        # Genre filter
        ctk.CTkLabel(
            self.filter_frame,
            text="Genre:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(0, 5))

        self.genre_var = ctk.StringVar(value="All Genres")
        self.genre_menu = ctk.CTkOptionMenu(
            self.filter_frame,
            values=["All Genres"],
            variable=self.genre_var,
            width=130,
            height=30,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_filter_change,
        )
        self.genre_menu.pack(side="left", padx=(0, 15))

        # Year filter
        ctk.CTkLabel(
            self.filter_frame,
            text="Year:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(0, 5))

        year_options = ["All Years", "2020s", "2010s", "2000s", "1990s", "1980s", "Older"]
        self.year_var = ctk.StringVar(value="All Years")
        self.year_menu = ctk.CTkOptionMenu(
            self.filter_frame,
            values=year_options,
            variable=self.year_var,
            width=100,
            height=30,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_filter_change,
        )
        self.year_menu.pack(side="left", padx=(0, 15))

        # Rating filter
        ctk.CTkLabel(
            self.filter_frame,
            text="Rating:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(0, 5))

        rating_options = ["All Ratings", "8-10", "6-7", "4-5", "1-3", "Unrated"]
        self.rating_var = ctk.StringVar(value="All Ratings")
        self.rating_menu = ctk.CTkOptionMenu(
            self.filter_frame,
            values=rating_options,
            variable=self.rating_var,
            width=110,
            height=30,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_filter_change,
        )
        self.rating_menu.pack(side="left", padx=(0, 15))

        # Select button for bulk operations
        self.select_btn = ctk.CTkButton(
            self.filter_frame,
            text="Select",
            width=70,
            height=30,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            hover_color=THEME["bg_card_hover"],
            text_color=THEME["text_secondary"],
            command=self._toggle_selection_mode,
        )
        self.select_btn.pack(side="right")

        # Content area (scrollable)
        self.content_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=THEME["bg_card"],
            scrollbar_button_hover_color=THEME["bg_card_hover"],
        )
        self.content_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Grid frame for cards
        self.grid_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

        # Bulk action toolbar (hidden by default)
        self.bulk_toolbar = ctk.CTkFrame(self, fg_color=THEME["bg_card"], corner_radius=12, height=60)
        self.bulk_toolbar.pack_propagate(False)

        self.selected_count_label = ctk.CTkLabel(
            self.bulk_toolbar,
            text="0 selected",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_primary"],
        )
        self.selected_count_label.pack(side="left", padx=20)

        # Status change dropdown in toolbar
        self.bulk_status_var = ctk.StringVar(value="Change Status")
        self.bulk_status_menu = ctk.CTkOptionMenu(
            self.bulk_toolbar,
            values=["Change Status"],
            variable=self.bulk_status_var,
            width=150,
            height=35,
            corner_radius=8,
            fg_color=THEME["accent_primary"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_bulk_status_change,
        )
        self.bulk_status_menu.pack(side="left", padx=10)

        # Delete button in toolbar
        ctk.CTkButton(
            self.bulk_toolbar,
            text="Delete Selected",
            width=120,
            height=35,
            corner_radius=8,
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color=THEME["text_primary"],
            command=self._on_bulk_delete,
        ).pack(side="left", padx=10)

        # Cancel button
        ctk.CTkButton(
            self.bulk_toolbar,
            text="Cancel",
            width=80,
            height=35,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=THEME["text_muted"],
            hover_color=THEME["bg_card_hover"],
            text_color=THEME["text_secondary"],
            command=self._exit_selection_mode,
        ).pack(side="right", padx=20)

        # Bind resize
        self.bind("<Configure>", self._on_resize)
        self._last_width = 0

    def _create_tabs(self, tabs: list):
        """Create filter tabs with orange underline indicator."""
        for widget in self.tab_frame.winfo_children():
            widget.destroy()

        self.tabs = {}
        self.tab_underlines = {}

        for key, label in tabs:
            # Container for tab + underline
            tab_container = ctk.CTkFrame(self.tab_frame, fg_color="transparent")
            tab_container.pack(side="left", padx=(0, 8))

            btn = ctk.CTkButton(
                tab_container,
                text=label,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                text_color=THEME["text_primary"] if key == self.current_tab else THEME["text_secondary"],
                hover_color=THEME["bg_card"],
                command=lambda k=key: self._on_tab_click(k),
            )
            btn.pack()

            # Orange underline for active tab
            underline = ctk.CTkFrame(
                tab_container,
                height=3,
                corner_radius=2,
                fg_color=THEME["accent_primary"] if key == self.current_tab else "transparent",
            )
            underline.pack(fill="x", pady=(2, 0))

            self.tabs[key] = btn
            self.tab_underlines[key] = underline

    def _on_tab_click(self, key: str):
        """Handle tab click."""
        self.current_tab = key
        for k, btn in self.tabs.items():
            if k == key:
                btn.configure(text_color=THEME["text_primary"])
                self.tab_underlines[k].configure(fg_color=THEME["accent_primary"])
            else:
                btn.configure(text_color=THEME["text_secondary"])
                self.tab_underlines[k].configure(fg_color="transparent")
        self.app.refresh_content()

    def _on_search(self):
        """Handle search."""
        query = self.search_entry.get().strip()
        if query:
            self.app.perform_search(query)

    def _on_sort_change(self, choice: str):
        """Handle sort option change."""
        sort_map = {
            "Date Added": "date_added",
            "Title (A-Z)": "title_asc",
            "Title (Z-A)": "title_desc",
            "Rating (High-Low)": "rating_desc",
            "Rating (Low-High)": "rating_asc",
        }
        self.current_sort = sort_map.get(choice, "date_added")
        self.app.refresh_content()

    def _on_resize(self, event):
        """Handle window resize for responsive grid."""
        if abs(event.width - self._last_width) > 50:
            self._last_width = event.width
            self.app.refresh_content()

    def _on_filter_change(self, choice: str = None):
        """Handle filter change."""
        self.genre_filter = self.genre_var.get() if self.genre_var.get() != "All Genres" else None
        self.year_filter = self.year_var.get() if self.year_var.get() != "All Years" else None
        self.rating_filter = self.rating_var.get() if self.rating_var.get() != "All Ratings" else None
        self.app.refresh_content()

    def _update_genre_options(self, items: list, media_type: str):
        """Update genre filter options based on current data."""
        genres = set()
        for item in items:
            genre_str = item.genre if media_type in ("movie", "series") else item.subjects
            if genre_str:
                for g in genre_str.split(", "):
                    genres.add(g.strip())

        self.available_genres = sorted(genres)
        options = ["All Genres"] + self.available_genres
        self.genre_menu.configure(values=options)

    def _toggle_selection_mode(self):
        """Toggle selection mode for bulk operations."""
        self.selection_mode = not self.selection_mode
        self.selected_items.clear()

        if self.selection_mode:
            self.select_btn.configure(
                text="Cancel",
                fg_color=THEME["accent_primary"],
                text_color=THEME["text_primary"],
            )
            self.bulk_toolbar.pack(fill="x", padx=20, pady=(0, 10))
            self._update_bulk_status_options()
        else:
            self._exit_selection_mode()

        self.app.refresh_content()

    def _exit_selection_mode(self):
        """Exit selection mode."""
        self.selection_mode = False
        self.selected_items.clear()
        self.select_btn.configure(
            text="Select",
            fg_color=THEME["bg_card"],
            text_color=THEME["text_secondary"],
        )
        self.bulk_toolbar.pack_forget()
        self.app.refresh_content()

    def _update_bulk_status_options(self):
        """Update bulk status menu options based on current view."""
        if self.app.current_view == "movies":
            options = ["Change Status", "Want to Watch", "Watching", "Watched"]
        elif self.app.current_view == "books":
            options = ["Change Status", "Want to Read", "Reading", "Read"]
        elif self.app.current_view == "series":
            options = ["Change Status", "Want to Watch", "Watching", "Completed", "On Hold", "Dropped"]
        else:
            options = ["Change Status"]

        self.bulk_status_menu.configure(values=options)
        self.bulk_status_var.set("Change Status")

    def _on_item_select(self, item_id: int, selected: bool):
        """Handle item selection toggle."""
        if selected:
            self.selected_items.add(item_id)
        else:
            self.selected_items.discard(item_id)

        self.selected_count_label.configure(text=f"{len(self.selected_items)} selected")

    def _on_bulk_status_change(self, status: str):
        """Handle bulk status change."""
        if status == "Change Status" or not self.selected_items:
            return

        self.app.bulk_update_status(list(self.selected_items), status)
        self._exit_selection_mode()

    def _on_bulk_delete(self):
        """Handle bulk delete."""
        if not self.selected_items:
            return

        self.app.bulk_delete(list(self.selected_items))
        self._exit_selection_mode()

    def _apply_filters(self, items: list, media_type: str) -> list:
        """Apply genre, year, and rating filters to items."""
        filtered = items

        # Genre filter
        if self.genre_filter:
            def has_genre(item):
                genre_str = item.genre if media_type in ("movie", "series") else item.subjects
                return genre_str and self.genre_filter in genre_str
            filtered = [i for i in filtered if has_genre(i)]

        # Year filter
        if self.year_filter:
            def matches_year(item):
                year = item.year if media_type in ("movie", "series") else str(item.publish_year) if item.publish_year else None
                if not year:
                    return False
                # Handle year ranges like "2019-2023"
                year_str = year.split("-")[0] if "-" in str(year) else str(year)
                if not year_str.isdigit():
                    return False
                y = int(year_str)
                if self.year_filter == "2020s":
                    return 2020 <= y <= 2029
                elif self.year_filter == "2010s":
                    return 2010 <= y <= 2019
                elif self.year_filter == "2000s":
                    return 2000 <= y <= 2009
                elif self.year_filter == "1990s":
                    return 1990 <= y <= 1999
                elif self.year_filter == "1980s":
                    return 1980 <= y <= 1989
                elif self.year_filter == "Older":
                    return y < 1980
                return True
            filtered = [i for i in filtered if matches_year(i)]

        # Rating filter
        if self.rating_filter:
            def matches_rating(item):
                rating = item.user_rating
                if self.rating_filter == "Unrated":
                    return rating is None
                elif self.rating_filter == "8-10":
                    return rating is not None and 8 <= rating <= 10
                elif self.rating_filter == "6-7":
                    return rating is not None and 6 <= rating <= 7
                elif self.rating_filter == "4-5":
                    return rating is not None and 4 <= rating <= 5
                elif self.rating_filter == "1-3":
                    return rating is not None and 1 <= rating <= 3
                return True
            filtered = [i for i in filtered if matches_rating(i)]

        return filtered

    def show_movies(self, movies: list):
        """Display movies in grid."""
        self.title_label.configure(text="Movies")
        self.search_entry.configure(placeholder_text="Search movies...")
        self.filter_frame.pack(fill="x", padx=30, pady=(0, 5))
        self._create_tabs([
            ("all", "All"),
            ("favorites", "❤️ Favorites"),
            ("watched", "Watched"),
            ("watching", "Watching"),
            ("want_to_watch", "Want to Watch"),
        ])
        self._update_genre_options(movies, "movie")
        self._display_media_grid(movies, "movie")

    def show_books(self, books: list):
        """Display books in grid."""
        self.title_label.configure(text="Books")
        self.search_entry.configure(placeholder_text="Search books...")
        self.filter_frame.pack(fill="x", padx=30, pady=(0, 5))
        self._create_tabs([
            ("all", "All"),
            ("favorites", "❤️ Favorites"),
            ("read", "Read"),
            ("reading", "Reading"),
            ("want_to_read", "Want to Read"),
        ])
        self._update_genre_options(books, "book")
        self._display_media_grid(books, "book")

    def show_series(self, series: list):
        """Display TV series in grid."""
        self.title_label.configure(text="TV Series")
        self.search_entry.configure(placeholder_text="Search series...")
        self.filter_frame.pack(fill="x", padx=30, pady=(0, 5))
        self._create_tabs([
            ("all", "All"),
            ("favorites", "❤️ Favorites"),
            ("watching", "Watching"),
            ("completed", "Completed"),
            ("on_hold", "On Hold"),
            ("want_to_watch", "Want to Watch"),
        ])
        self._update_genre_options(series, "series")
        self._display_media_grid(series, "series")

    def show_recent(self, recent_data: dict):
        """Display recently added items."""
        self.title_label.configure(text="Recently Added")
        self.search_frame.pack_forget()
        self.filter_frame.pack_forget()
        self._create_tabs([])

        # Clear grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        has_items = False

        # Recent movies section
        if recent_data.get("movies"):
            has_items = True
            self._create_recent_section("🎬 Recent Movies", recent_data["movies"], "movie")

        # Recent books section
        if recent_data.get("books"):
            has_items = True
            self._create_recent_section("📚 Recent Books", recent_data["books"], "book")

        # Recent series section
        if recent_data.get("series"):
            has_items = True
            self._create_recent_section("📺 Recent Series", recent_data["series"], "series")

        if not has_items:
            ctk.CTkLabel(
                self.grid_frame,
                text="No items added in the last 7 days.\nAdd some movies, books, or series to see them here!",
                font=ctk.CTkFont(size=16),
                text_color=THEME["text_secondary"],
            ).pack(pady=50)

        self.search_frame.pack(side="right")

    def _create_recent_section(self, title: str, items: list, media_type: str):
        """Create a section for recently added items."""
        section = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        section.pack(fill="x", pady=15, padx=10)

        ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(0, 10))

        # Horizontal scroll for items
        scroll_frame = ctk.CTkScrollableFrame(
            section,
            height=380,
            fg_color="transparent",
            orientation="horizontal",
        )
        scroll_frame.pack(fill="x")

        for item in items[:10]:
            self._create_card_for_item(scroll_frame, item, media_type)

    def show_recommendations(self, movie_rec, book_rec, movie_reason, book_reason):
        """Display recommendations."""
        self.title_label.configure(text="For You")
        self.search_frame.pack_forget()
        self._create_tabs([])

        # Clear grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Movie recommendation
        if movie_rec:
            self._create_recommendation_section(
                "🎬 Movie Recommendation", movie_rec, "movie", movie_reason
            )

        # Book recommendation
        if book_rec:
            self._create_recommendation_section(
                "📚 Book Recommendation", book_rec, "book", book_reason
            )

        if not movie_rec and not book_rec:
            ctk.CTkLabel(
                self.grid_frame,
                text="Add some movies and books to your watchlist\nto get personalized recommendations!",
                font=ctk.CTkFont(size=16),
                text_color=THEME["text_secondary"],
            ).pack(pady=50)

        self.search_frame.pack(side="right")

    def _create_recommendation_section(self, title, media, media_type, reason):
        """Create a recommendation section."""
        section = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        section.pack(fill="x", pady=20, padx=10)

        ctk.CTkLabel(
            section,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            section,
            text=reason,
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"],
        ).pack(anchor="w", pady=(0, 15))

        if media_type == "movie":
            card = MediaCard(
                section,
                title=media.title,
                subtitle=f"{media.year or 'N/A'} • {media.director or ''}",
                status=media.status.value,
                rating=media.user_rating,
                image_url=media.poster_url,
                on_click=lambda: self.app.show_detail(media, media_type),
            )
        else:
            card = MediaCard(
                section,
                title=media.title,
                subtitle=f"{media.publish_year or 'N/A'} • {media.author or ''}",
                status=media.status.value,
                rating=media.user_rating,
                image_url=media.cover_url,
                on_click=lambda: self.app.show_detail(media, media_type),
            )
        card.pack(anchor="w")

    def show_stats(self, movie_stats, book_stats, series_stats=None, chart_data=None):
        """Display statistics with optional charts."""
        self.title_label.configure(text="Statistics")
        self.search_frame.pack_forget()
        self.filter_frame.pack_forget()
        self._create_tabs([])

        # Clear grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Stats container
        container = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Export button
        export_btn = ctk.CTkButton(
            container,
            text="📥 Export Data",
            width=120,
            height=35,
            corner_radius=8,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=self.app.show_export_dialog,
        )
        export_btn.pack(anchor="e", pady=(0, 15))

        # Movie stats
        self._create_stats_card(container, "🎬 Movies", movie_stats, "movie")

        # Book stats
        self._create_stats_card(container, "📚 Books", book_stats, "book")

        # Series stats
        if series_stats:
            self._create_stats_card(container, "📺 TV Series", series_stats, "series")

        # Charts section (if matplotlib available and data provided)
        if MATPLOTLIB_AVAILABLE and chart_data:
            self._create_charts_section(container, chart_data)

        self.search_frame.pack(side="right")

    def _create_charts_section(self, parent, chart_data):
        """Create charts section with matplotlib."""
        chart_frame = ctk.CTkFrame(parent, corner_radius=15, fg_color=THEME["bg_card"])
        chart_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            chart_frame,
            text="📈 Completion Over Time",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Create matplotlib figure with dark theme
        fig = Figure(figsize=(8, 3), dpi=100, facecolor=THEME["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg_secondary"])

        # Plot data
        movie_data = chart_data.get("movies", [])
        book_data = chart_data.get("books", [])

        if movie_data:
            labels = [d["label"] for d in movie_data]
            values = [d["count"] for d in movie_data]
            ax.plot(labels, values, color=THEME["accent_primary"], marker='o', label="Movies", linewidth=2)

        if book_data:
            labels = [d["label"] for d in book_data]
            values = [d["count"] for d in book_data]
            ax.plot(labels, values, color=THEME["status_planned"], marker='s', label="Books", linewidth=2)

        ax.legend(facecolor=THEME["bg_card"], edgecolor=THEME["bg_card_hover"],
                  labelcolor=THEME["text_primary"])
        ax.tick_params(colors=THEME["text_secondary"], labelsize=8)
        ax.spines['bottom'].set_color(THEME["text_muted"])
        ax.spines['left'].set_color(THEME["text_muted"])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        # Rotate x labels
        plt_labels = ax.get_xticklabels()
        for label in plt_labels:
            label.set_rotation(45)
            label.set_ha('right')

        fig.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=20, pady=(0, 15))

        # Rating distribution chart
        self._create_rating_distribution_chart(parent, chart_data)

    def _create_rating_distribution_chart(self, parent, chart_data):
        """Create rating distribution bar chart."""
        if not MATPLOTLIB_AVAILABLE:
            return

        chart_frame = ctk.CTkFrame(parent, corner_radius=15, fg_color=THEME["bg_card"])
        chart_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            chart_frame,
            text="📊 Rating Distribution",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=20, pady=(15, 10))

        fig = Figure(figsize=(8, 3), dpi=100, facecolor=THEME["bg_card"])
        ax = fig.add_subplot(111)
        ax.set_facecolor(THEME["bg_secondary"])

        # Combine movie and book ratings
        movie_dist = chart_data.get("movie_ratings", {})
        book_dist = chart_data.get("book_ratings", {})

        ratings = [str(i) for i in range(1, 11)]
        movie_values = [movie_dist.get(r, 0) for r in ratings]
        book_values = [book_dist.get(r, 0) for r in ratings]

        x = range(len(ratings))
        width = 0.35

        ax.bar([i - width/2 for i in x], movie_values, width, label='Movies',
               color=THEME["accent_primary"])
        ax.bar([i + width/2 for i in x], book_values, width, label='Books',
               color=THEME["status_planned"])

        ax.set_xticks(x)
        ax.set_xticklabels(ratings)
        ax.legend(facecolor=THEME["bg_card"], edgecolor=THEME["bg_card_hover"],
                  labelcolor=THEME["text_primary"])
        ax.tick_params(colors=THEME["text_secondary"])
        ax.spines['bottom'].set_color(THEME["text_muted"])
        ax.spines['left'].set_color(THEME["text_muted"])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=20, pady=(0, 15))

    def _create_stats_card(self, parent, title, stats, media_type):
        """Create a dark themed statistics card."""
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color=THEME["bg_card"])
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=20, pady=(20, 15))

        # Stats grid
        stats_frame = ctk.CTkFrame(card, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=(0, 15))

        if media_type == "movie":
            items = [
                ("Watched", stats.get("watched", 0)),
                ("Watching", stats.get("watching", 0)),
                ("Want to Watch", stats.get("want_to_watch", 0)),
            ]
        elif media_type == "book":
            items = [
                ("Read", stats.get("read", 0)),
                ("Reading", stats.get("reading", 0)),
                ("Want to Read", stats.get("want_to_read", 0)),
            ]
        else:  # series
            items = [
                ("Watching", stats.get("watching", 0)),
                ("Completed", stats.get("completed", 0)),
                ("Want to Watch", stats.get("want_to_watch", 0)),
            ]

        for label, value in items:
            stat_item = ctk.CTkFrame(stats_frame, fg_color="transparent")
            stat_item.pack(side="left", expand=True)

            ctk.CTkLabel(
                stat_item,
                text=str(value),
                font=ctk.CTkFont(size=32, weight="bold"),
                text_color=THEME["text_primary"],
            ).pack()

            ctk.CTkLabel(
                stat_item,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=THEME["text_secondary"],
            ).pack()

        # Average rating with gold color
        if stats.get("avg_user_rating"):
            ctk.CTkLabel(
                card,
                text=f"Average Rating: ★ {stats['avg_user_rating']}/10",
                font=ctk.CTkFont(size=14),
                text_color=THEME["rating_gold"],
            ).pack(anchor="w", padx=20, pady=(0, 10))

        # Series-specific: total episodes watched
        if media_type == "series" and stats.get("total_episodes_watched"):
            ctk.CTkLabel(
                card,
                text=f"Total Episodes Watched: {stats['total_episodes_watched']}",
                font=ctk.CTkFont(size=14),
                text_color=THEME["text_secondary"],
            ).pack(anchor="w", padx=20, pady=(0, 10))

        # Top genres/subjects
        top_items = stats.get("top_genres" if media_type in ("movie", "series") else "top_subjects", [])
        if top_items:
            label = "Top Genres" if media_type in ("movie", "series") else "Top Subjects"
            items_text = ", ".join([f"{item[0]} ({item[1]})" for item in top_items[:5]])
            ctk.CTkLabel(
                card,
                text=f"{label}: {items_text}",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"],
                wraplength=500,
            ).pack(anchor="w", padx=20, pady=(0, 20))

    def show_search_results(self, results: list, media_type: str):
        """Display search results."""
        # Clear grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not results:
            ctk.CTkLabel(
                self.grid_frame,
                text="No results found",
                font=ctk.CTkFont(size=16),
                text_color=THEME["text_secondary"],
            ).pack(pady=50)
            return

        ctk.CTkLabel(
            self.grid_frame,
            text=f"Search Results ({len(results)})",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=10, pady=(10, 15))

        for result in results:
            if media_type == "movie":
                title = result.get("Title", "Unknown")
                subtitle = result.get("Year", "N/A")
                card = SearchResultCard(
                    self.grid_frame,
                    title=title,
                    subtitle=subtitle,
                    on_add=lambda r=result: self.app.add_movie_from_search(r),
                )
            elif media_type == "book":
                title = result.get("title", "Unknown")
                author = result.get("author", "Unknown Author")
                year = result.get("first_publish_year", "")
                subtitle = f"{author}" + (f" ({year})" if year else "")
                card = SearchResultCard(
                    self.grid_frame,
                    title=title,
                    subtitle=subtitle,
                    on_add=lambda r=result: self.app.add_book_from_search(r),
                )
            else:  # series
                title = result.get("Title", "Unknown")
                subtitle = result.get("Year", "N/A")
                card = SearchResultCard(
                    self.grid_frame,
                    title=title,
                    subtitle=f"TV Series • {subtitle}",
                    on_add=lambda r=result: self.app.add_series_from_search(r),
                )
            card.pack(fill="x", padx=10, pady=5)

    def _create_card_for_item(self, parent, item, media_type: str):
        """Create a MediaCard for an item."""
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
            # Calculate progress for series
            total_watched = len(item.episodes_watched) if hasattr(item, 'episodes_watched') else 0
            # Estimate total episodes (10 per season as rough estimate)
            estimated_total = item.total_seasons * 10 if hasattr(item, 'total_seasons') else 10
            progress = min(1.0, total_watched / estimated_total) if estimated_total > 0 else 0

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

    def _display_media_grid(self, items: list, media_type: str):
        """Display media items in a responsive grid."""
        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        if not items:
            ctk.CTkLabel(
                self.grid_frame,
                text=f"No {media_type}s yet. Search to add some!",
                font=ctk.CTkFont(size=16),
                text_color=THEME["text_secondary"],
            ).pack(pady=50)
            return

        # Filter by tab
        if self.current_tab == "favorites":
            items = [i for i in items if i.is_favorite]
        elif self.current_tab != "all":
            items = [i for i in items if i.status.value == self.current_tab]

        # Apply additional filters
        items = self._apply_filters(items, media_type)

        if not items:
            ctk.CTkLabel(
                self.grid_frame,
                text=f"No {media_type}s match the current filters",
                font=ctk.CTkFont(size=16),
                text_color=THEME["text_secondary"],
            ).pack(pady=50)
            return

        # Sort items based on current sort option
        if self.current_sort == "title_asc":
            items = sorted(items, key=lambda x: x.title.lower())
        elif self.current_sort == "title_desc":
            items = sorted(items, key=lambda x: x.title.lower(), reverse=True)
        elif self.current_sort == "rating_desc":
            items = sorted(items, key=lambda x: (x.user_rating is None, -(x.user_rating or 0)))
        elif self.current_sort == "rating_asc":
            items = sorted(items, key=lambda x: (x.user_rating is None, x.user_rating or 0))
        else:
            items = sorted(items, key=lambda x: x.date_added or "", reverse=True)

        # Calculate columns based on width
        width = self.winfo_width()
        card_width = 210
        columns = max(1, (width - 60) // card_width)

        # Create grid
        row_frame = None
        for i, item in enumerate(items):
            if i % columns == 0:
                row_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=5)

            self._create_card_for_item(row_frame, item, media_type)


class ExportDialog(ctk.CTkToplevel):
    """Dialog for exporting data to various formats."""

    def __init__(self, parent, on_export: Callable):
        super().__init__(parent)

        self.on_export = on_export

        self.title("Export Data")
        self.geometry("400x450")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_secondary"])

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Center dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 225
        self.geometry(f"400x450+{x}+{y}")

        # Title
        ctk.CTkLabel(
            self,
            text="Export Your Data",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(pady=(25, 20))

        # Format selection
        ctk.CTkLabel(
            self,
            text="Export Format:",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=40)

        self.format_var = ctk.StringVar(value="json")

        formats = [
            ("JSON (Full backup)", "json"),
            ("CSV (Spreadsheet)", "csv"),
            ("Text (Shareable list)", "text"),
        ]

        for label, value in formats:
            ctk.CTkRadioButton(
                self,
                text=label,
                variable=self.format_var,
                value=value,
                fg_color=THEME["accent_primary"],
                hover_color=THEME["accent_hover"],
                text_color=THEME["text_secondary"],
            ).pack(anchor="w", padx=50, pady=5)

        # Data selection
        ctk.CTkLabel(
            self,
            text="Include:",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", padx=40, pady=(20, 5))

        self.include_movies = ctk.CTkCheckBox(
            self,
            text="Movies",
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_secondary"],
        )
        self.include_movies.pack(anchor="w", padx=50, pady=3)
        self.include_movies.select()

        self.include_books = ctk.CTkCheckBox(
            self,
            text="Books",
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_secondary"],
        )
        self.include_books.pack(anchor="w", padx=50, pady=3)
        self.include_books.select()

        self.include_series = ctk.CTkCheckBox(
            self,
            text="TV Series",
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_secondary"],
        )
        self.include_series.pack(anchor="w", padx=50, pady=3)
        self.include_series.select()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=30)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            height=38,
            fg_color="transparent",
            border_width=2,
            border_color=THEME["text_muted"],
            text_color=THEME["text_secondary"],
            hover_color=THEME["bg_card"],
            command=self.destroy,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Export",
            width=120,
            height=38,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=self._export,
        ).pack(side="left", padx=10)

    def _export(self):
        """Handle export."""
        format_type = self.format_var.get()
        include = {
            "movies": self.include_movies.get(),
            "books": self.include_books.get(),
            "series": self.include_series.get(),
        }
        self.on_export(format_type, include)
        self.destroy()


class SeriesDetailDialog(ctk.CTkToplevel):
    """Dialog for viewing and editing TV series details with episode tracking."""

    def __init__(
        self,
        parent,
        series,
        on_update: Callable,
        on_delete: Callable,
        get_episodes: Callable,
        on_episode_toggle: Callable,
    ):
        super().__init__(parent)

        self.series = series
        self.on_update = on_update
        self.on_delete = on_delete
        self.get_episodes = get_episodes
        self.on_episode_toggle = on_episode_toggle
        self.current_season = series.current_season

        self.title("Series Details")
        self.geometry("550x800")
        self.minsize(450, 600)
        self.configure(fg_color=THEME["bg_secondary"])

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Center dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 275
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 400
        self.geometry(f"550x800+{x}+{y}")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=THEME["bg_card"],
            scrollbar_button_hover_color=THEME["bg_card_hover"],
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Poster
        self.image_label = ctk.CTkLabel(
            scroll,
            text="Loading...",
            width=200,
            height=300,
            corner_radius=12,
            fg_color=THEME["bg_card"],
            text_color=THEME["text_muted"],
        )
        self.image_label.pack(pady=(0, 20))

        if series.poster_url:
            ImageLoader.load_async(series.poster_url, self._set_image, size=(200, 300))

        # Title
        ctk.CTkLabel(
            scroll,
            text=series.title,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=THEME["text_primary"],
            wraplength=500,
        ).pack(pady=(0, 5))

        # Info line
        ctk.CTkLabel(
            scroll,
            text=f"{series.year or 'N/A'} • {series.total_seasons} Season{'s' if series.total_seasons != 1 else ''}",
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_secondary"],
        ).pack(pady=(0, 10))

        # Genre
        if series.genre:
            ctk.CTkLabel(
                scroll,
                text=series.genre,
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"],
            ).pack(pady=(0, 10))

        # Plot
        if series.plot:
            ctk.CTkLabel(
                scroll,
                text=series.plot,
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"],
                wraplength=500,
                justify="left",
            ).pack(pady=(0, 15))

        # Status selector
        ctk.CTkLabel(
            scroll,
            text="Status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        statuses = ["want_to_watch", "watching", "completed", "on_hold", "dropped"]
        status_labels = ["Want to Watch", "Watching", "Completed", "On Hold", "Dropped"]
        current_status = series.status.value
        self.status_var = ctk.StringVar(value=status_labels[statuses.index(current_status)])

        self.status_menu = ctk.CTkOptionMenu(
            scroll,
            values=status_labels,
            variable=self.status_var,
            width=200,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
        )
        self.status_menu.pack(anchor="w", pady=(0, 15))

        # Rating
        ctk.CTkLabel(
            scroll,
            text="Your Rating",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        rating_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rating_frame.pack(anchor="w", pady=(0, 15))

        self.rating_slider = ctk.CTkSlider(
            rating_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            width=200,
            progress_color=THEME["accent_primary"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
        )
        self.rating_slider.pack(side="left")
        self.rating_slider.set(series.user_rating or 5)

        self.rating_label = ctk.CTkLabel(
            rating_frame,
            text=str(series.user_rating or 5),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["rating_gold"],
            width=30,
        )
        self.rating_label.pack(side="left", padx=10)
        self.rating_slider.configure(command=self._update_rating_label)

        self.use_rating = ctk.CTkCheckBox(
            scroll,
            text="Include rating",
            text_color=THEME["text_secondary"],
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
        )
        if series.user_rating:
            self.use_rating.select()
        self.use_rating.pack(anchor="w", pady=(0, 15))

        # Notes
        ctk.CTkLabel(
            scroll,
            text="Notes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        self.notes_textbox = ctk.CTkTextbox(
            scroll,
            height=80,
            width=500,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
            border_color=THEME["bg_card_hover"],
            border_width=1,
            wrap="word",
        )
        self.notes_textbox.pack(anchor="w", pady=(0, 15))
        if series.notes:
            self.notes_textbox.insert("1.0", series.notes)

        # Episode tracking section
        ctk.CTkLabel(
            scroll,
            text="Episode Progress",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(10, 5))

        # Season selector
        season_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        season_frame.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            season_frame,
            text="Season:",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(0, 10))

        seasons = [str(i) for i in range(1, series.total_seasons + 1)]
        self.season_var = ctk.StringVar(value=str(self.current_season))
        self.season_menu = ctk.CTkOptionMenu(
            season_frame,
            values=seasons,
            variable=self.season_var,
            width=80,
            corner_radius=8,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent_primary"],
            button_hover_color=THEME["accent_hover"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_hover_color=THEME["bg_card_hover"],
            command=self._on_season_change,
        )
        self.season_menu.pack(side="left")

        # Episode list frame
        self.episodes_frame = ctk.CTkFrame(scroll, fg_color=THEME["bg_card"], corner_radius=8)
        self.episodes_frame.pack(fill="x", pady=(0, 15))

        self._load_episodes()

        # Action buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            width=100,
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color=THEME["text_primary"],
            command=self._delete,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Save Changes",
            width=150,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=self._save,
        ).pack(side="right")

    def _set_image(self, image):
        if image:
            self.image_label.configure(image=image, text="")

    def _update_rating_label(self, value):
        self.rating_label.configure(text=str(int(value)))

    def _on_season_change(self, season: str):
        self.current_season = int(season)
        self._load_episodes()

    def _load_episodes(self):
        """Load episodes for current season."""
        for widget in self.episodes_frame.winfo_children():
            widget.destroy()

        episodes = self.get_episodes(self.series.imdb_id, self.current_season)

        if not episodes:
            ctk.CTkLabel(
                self.episodes_frame,
                text="No episode data available",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"],
            ).pack(pady=15)
            return

        for ep in episodes:
            ep_frame = ctk.CTkFrame(self.episodes_frame, fg_color="transparent")
            ep_frame.pack(fill="x", padx=10, pady=3)

            # Check if episode is watched
            is_watched = any(
                e.get("season") == self.current_season and e.get("episode") == ep["episode"]
                for e in self.series.episodes_watched
            )

            cb = ctk.CTkCheckBox(
                ep_frame,
                text=f"E{ep['episode']}: {ep['title']}",
                fg_color=THEME["accent_primary"],
                hover_color=THEME["accent_hover"],
                text_color=THEME["text_primary"] if is_watched else THEME["text_secondary"],
                command=lambda e=ep["episode"], cb_ref=None: self._toggle_episode(e),
            )
            if is_watched:
                cb.select()
            cb.pack(side="left")

    def _toggle_episode(self, episode: int):
        """Toggle episode watched status."""
        is_currently_watched = any(
            e.get("season") == self.current_season and e.get("episode") == episode
            for e in self.series.episodes_watched
        )

        self.on_episode_toggle(
            self.series.id,
            self.current_season,
            episode,
            not is_currently_watched
        )

        # Update local state
        if is_currently_watched:
            self.series.episodes_watched = [
                e for e in self.series.episodes_watched
                if not (e.get("season") == self.current_season and e.get("episode") == episode)
            ]
        else:
            self.series.episodes_watched.append({
                "season": self.current_season,
                "episode": episode
            })

    def _save(self):
        status_text = self.status_var.get().lower().replace(" ", "_")
        rating = int(self.rating_slider.get()) if self.use_rating.get() else None
        notes = self.notes_textbox.get("1.0", "end-1c").strip() or None
        self.on_update(self.series.id, status_text, rating, notes)
        self.destroy()

    def _delete(self):
        self.on_delete(self.series.id)
        self.destroy()


class MediaTrackerApp(ctk.CTk):
    """Main application window with local JSON storage."""

    def __init__(self):
        super().__init__()

        self.title("Media Tracker (Local)")
        self.geometry("1200x800")
        self.minsize(800, 600)
        self.configure(fg_color=THEME["bg_primary"])

        # Initialize local database
        try:
            self.db = Database()
            self.recommender = Recommender(self.db)
        except Exception as e:
            self._show_error(f"Database Error: {e}")
            return

        # Movie API (optional - needs OMDB_API_KEY)
        try:
            self.movie_api = MovieAPI()
        except OMDBError as e:
            self.movie_api = None
            print(f"Warning: {e}")

        self.book_api = BookAPI()

        self.current_view = "movies"
        self.search_mode = False

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = Sidebar(self, on_navigate=self._navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        # Main content
        self.main_content = MainContent(self, app=self)
        self.main_content.grid(row=0, column=1, sticky="nsew")

        # Start with movies view
        self.sidebar.set_active("movies")

    def _navigate(self, view: str):
        """Handle navigation."""
        self.current_view = view
        self.search_mode = False
        self.refresh_content()

    def refresh_content(self):
        """Refresh the current view."""
        if self.search_mode:
            return

        if self.current_view == "movies":
            movies = self.db.get_all_movies()
            self.main_content.show_movies(movies)
        elif self.current_view == "books":
            books = self.db.get_all_books()
            self.main_content.show_books(books)
        elif self.current_view == "series":
            series = self.db.get_all_series()
            self.main_content.show_series(series)
        elif self.current_view == "recent":
            recent_data = self.db.get_recent_items(days=7)
            self.main_content.show_recent(recent_data)
        elif self.current_view == "recommend":
            movie, movie_reason = self.recommender.get_recommendation("movie", smart=True)
            book, book_reason = self.recommender.get_recommendation("book", smart=True)
            self.main_content.show_recommendations(movie, book, movie_reason, book_reason)
        elif self.current_view == "stats":
            movie_stats = self.db.get_movie_stats()
            book_stats = self.db.get_book_stats()
            series_stats = self.db.get_series_stats()

            # Prepare chart data
            chart_data = None
            if MATPLOTLIB_AVAILABLE:
                chart_data = {
                    "movies": self.db.get_completion_by_month("movie", 12),
                    "books": self.db.get_completion_by_month("book", 12),
                    "movie_ratings": self.db.get_rating_distribution("movie"),
                    "book_ratings": self.db.get_rating_distribution("book"),
                }

            self.main_content.show_stats(movie_stats, book_stats, series_stats, chart_data)

    def perform_search(self, query: str):
        """Perform search."""
        self.search_mode = True

        # Save to search history
        self.db.add_to_search_history(query, self.current_view)

        if self.current_view == "movies":
            if not self.movie_api:
                self._show_error("OMDB API key not configured.\nSet OMDB_API_KEY environment variable.")
                return
            try:
                results = self.movie_api.search(query, media_type="movie")
                self.main_content.show_search_results(results, "movie")
            except OMDBError as e:
                self._show_error(str(e))
        elif self.current_view == "books":
            try:
                results = self.book_api.search(query)
                self.main_content.show_search_results(results, "book")
            except OpenLibraryError as e:
                self._show_error(str(e))
        elif self.current_view == "series":
            if not self.movie_api:
                self._show_error("OMDB API key not configured.\nSet OMDB_API_KEY environment variable.")
                return
            try:
                results = self.movie_api.search(query, media_type="series")
                self.main_content.show_search_results(results, "series")
            except OMDBError as e:
                self._show_error(str(e))

    def add_movie_from_search(self, result: dict):
        """Add movie from search result."""
        existing = self.db.get_movie_by_imdb_id(result["imdbID"])
        if existing:
            self._show_error(f"'{result['Title']}' is already in your library")
            return

        def on_confirm(status: str, rating: Optional[int]):
            try:
                status_enum = MovieStatus(status)
                movie = self.movie_api.create_movie_from_api(result["imdbID"], status_enum)
                movie.user_rating = rating
                self.db.add_movie(movie)
                self.search_mode = False
                self.refresh_content()
            except OMDBError as e:
                self._show_error(str(e))

        AddMediaDialog(self, "movie", result["Title"], on_confirm)

    def add_book_from_search(self, result: dict):
        """Add book from search result."""
        existing = self.db.get_book_by_olid(result["olid"])
        if existing:
            self._show_error(f"'{result['title']}' is already in your library")
            return

        def on_confirm(status: str, rating: Optional[int]):
            try:
                status_enum = BookStatus(status)
                book = self.book_api.create_book_from_search(result, status_enum)
                book.user_rating = rating
                self.db.add_book(book)
                self.search_mode = False
                self.refresh_content()
            except OpenLibraryError as e:
                self._show_error(str(e))

        AddMediaDialog(self, "book", result["title"], on_confirm)

    def show_detail(self, media, media_type: str):
        """Show media detail dialog."""

        def on_update(media_id: int, status: str, rating: Optional[int], notes: Optional[str] = None):
            if media_type == "movie":
                status_enum = MovieStatus(status)
                self.db.update_movie_status(media_id, status_enum, rating)
                if notes is not None:
                    self.db.update_movie_notes(media_id, notes)
            elif media_type == "book":
                status_enum = BookStatus(status)
                self.db.update_book_status(media_id, status_enum, rating)
                if notes is not None:
                    self.db.update_book_notes(media_id, notes)
            elif media_type == "series":
                status_enum = SeriesStatus(status)
                self.db.update_series_status(media_id, status_enum, rating)
                if notes is not None:
                    self.db.update_series_notes(media_id, notes)
            self.refresh_content()

        def on_delete(media_id: int):
            if media_type == "movie":
                self.db.delete_movie(media_id)
            elif media_type == "book":
                self.db.delete_book(media_id)
            elif media_type == "series":
                self.db.delete_series(media_id)
            self.refresh_content()

        def on_show_similar(item, item_type):
            self.show_detail(item, item_type)

        # Handle series differently
        if media_type == "series":
            def get_episodes(imdb_id, season):
                if self.movie_api:
                    return self.movie_api.get_season_episodes(imdb_id, season)
                return []

            def on_episode_toggle(series_id, season, episode, watched):
                self.db.update_series_progress(series_id, season, episode, watched)

            SeriesDetailDialog(
                self, media, on_update, on_delete, get_episodes, on_episode_toggle
            )
        else:
            # Get similar items
            similar_items = []
            if media_type == "movie":
                similar_items = self.recommender.get_similar_movies(media, limit=5)
            elif media_type == "book":
                similar_items = self.recommender.get_similar_books(media, limit=5)

            MediaDetailDialog(
                self, media, media_type, on_update, on_delete,
                similar_items=similar_items, on_show_similar=on_show_similar
            )

    def toggle_favorite(self, media, media_type: str, is_favorite: bool):
        """Toggle favorite status for a media item."""
        if media_type == "movie":
            self.db.toggle_movie_favorite(media.id, is_favorite)
        elif media_type == "book":
            self.db.toggle_book_favorite(media.id, is_favorite)
        elif media_type == "series":
            self.db.toggle_series_favorite(media.id, is_favorite)

    def add_series_from_search(self, result: dict):
        """Add series from search result."""
        existing = self.db.get_series_by_imdb_id(result["imdbID"])
        if existing:
            self._show_error(f"'{result['Title']}' is already in your library")
            return

        def on_confirm(status: str, rating: Optional[int]):
            try:
                status_enum = SeriesStatus(status)
                series = self.movie_api.create_series_from_api(result["imdbID"], status_enum)
                series.user_rating = rating
                self.db.add_series(series)
                self.search_mode = False
                self.refresh_content()
            except OMDBError as e:
                self._show_error(str(e))

        AddMediaDialog(self, "series", result["Title"], on_confirm)

    def bulk_update_status(self, item_ids: List[int], status: str):
        """Bulk update status for selected items."""
        status_key = status.lower().replace(" ", "_")

        if self.current_view == "movies":
            status_enum = MovieStatus(status_key)
            self.db.bulk_update_movie_status(item_ids, status_enum)
        elif self.current_view == "books":
            status_enum = BookStatus(status_key)
            self.db.bulk_update_book_status(item_ids, status_enum)

        self.refresh_content()

    def bulk_delete(self, item_ids: List[int]):
        """Bulk delete selected items."""
        if self.current_view == "movies":
            self.db.bulk_delete_movies(item_ids)
        elif self.current_view == "books":
            self.db.bulk_delete_books(item_ids)

        self.refresh_content()

    def show_export_dialog(self):
        """Show export dialog."""
        def on_export(format_type: str, include: dict):
            # Get file extension
            extensions = {"json": ".json", "csv": ".csv", "text": ".txt"}
            ext = extensions.get(format_type, ".txt")

            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[
                    ("JSON files", "*.json") if format_type == "json" else
                    ("CSV files", "*.csv") if format_type == "csv" else
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
                initialfile=f"media_tracker_export{ext}",
            )

            if not file_path:
                return

            try:
                if format_type == "json":
                    content = self.db.export_to_json(
                        include_movies=include["movies"],
                        include_books=include["books"],
                        include_series=include["series"],
                    )
                elif format_type == "csv":
                    # CSV exports one type at a time, export the first selected
                    if include["movies"]:
                        content = self.db.export_to_csv("movie")
                    elif include["books"]:
                        content = self.db.export_to_csv("book")
                    elif include["series"]:
                        content = self.db.export_to_csv("series")
                    else:
                        content = ""
                else:  # text
                    parts = []
                    if include["movies"]:
                        parts.append(self.db.export_to_text("movie"))
                    if include["books"]:
                        parts.append(self.db.export_to_text("book"))
                    if include["series"]:
                        parts.append(self.db.export_to_text("series"))
                    content = "\n\n".join(parts)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self._show_success(f"Data exported successfully to:\n{file_path}")
            except Exception as e:
                self._show_error(f"Export failed: {e}")

        ExportDialog(self, on_export)

    def _show_success(self, message: str):
        """Show success dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Success")
        dialog.geometry("400x150")
        dialog.configure(fg_color=THEME["bg_secondary"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        dialog.geometry(f"400x150+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="✅ Success",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["status_watched"],
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_secondary"],
            wraplength=350,
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            dialog,
            text="OK",
            width=100,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=dialog.destroy,
        ).pack()

    def _show_error(self, message: str):
        """Show dark themed error dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Error")
        dialog.geometry("400x150")
        dialog.configure(fg_color=THEME["bg_secondary"])
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        dialog.geometry(f"400x150+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="⚠️ Error",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=14),
            text_color=THEME["text_secondary"],
            wraplength=350,
        ).pack(pady=(0, 20))

        ctk.CTkButton(
            dialog,
            text="OK",
            width=100,
            fg_color=THEME["accent_primary"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            command=dialog.destroy,
        ).pack()


def main():
    app = MediaTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
