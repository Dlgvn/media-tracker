#!/usr/bin/env python3
"""Media Tracker GUI - Instagram-like interface."""

import io
import os
import threading
from typing import Callable, Optional
from urllib.request import urlopen

import customtkinter as ctk
from PIL import Image, ImageDraw

from book_api import BookAPI, OpenLibraryError
from database import Database, DatabaseError
from models import Book, BookStatus, Movie, MovieStatus
from movie_api import MovieAPI, OMDBError
from recommender import Recommender


# Set appearance mode to system (follows OS dark/light mode)
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class ImageLoader:
    """Async image loader with caching."""

    _cache: dict = {}

    @classmethod
    def load_async(
        cls,
        url: str,
        callback: Callable[[Optional[ctk.CTkImage]], None],
        size: tuple = (150, 220),
    ):
        """Load image asynchronously and call callback with result."""
        if not url or url == "N/A":
            callback(None)
            return

        if url in cls._cache:
            callback(cls._cache[url])
            return

        def _load():
            try:
                with urlopen(url, timeout=10) as response:
                    image_data = response.read()
                pil_image = Image.open(io.BytesIO(image_data))
                pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
                ctk_image = ctk.CTkImage(
                    light_image=pil_image, dark_image=pil_image, size=size
                )
                cls._cache[url] = ctk_image
                callback(ctk_image)
            except Exception:
                callback(None)

        threading.Thread(target=_load, daemon=True).start()


class MediaCard(ctk.CTkFrame):
    """Instagram-style card for displaying media items."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        status: str,
        rating: Optional[int],
        image_url: Optional[str],
        on_click: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.on_click = on_click
        self.configure(corner_radius=15, fg_color=("gray90", "gray17"))

        # Image placeholder
        self.image_label = ctk.CTkLabel(
            self,
            text="📷",
            width=150,
            height=220,
            corner_radius=10,
            fg_color=("gray80", "gray25"),
        )
        self.image_label.pack(padx=10, pady=(10, 5))

        # Load image async
        if image_url:
            ImageLoader.load_async(image_url, self._set_image)

        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=title[:25] + "..." if len(title) > 25 else title,
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=150,
        )
        self.title_label.pack(padx=10, pady=(5, 0))

        # Subtitle (year/author)
        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        )
        self.subtitle_label.pack(padx=10)

        # Status badge
        status_colors = {
            "watched": ("#22c55e", "#16a34a"),
            "watching": ("#3b82f6", "#2563eb"),
            "want_to_watch": ("#f59e0b", "#d97706"),
            "read": ("#22c55e", "#16a34a"),
            "reading": ("#3b82f6", "#2563eb"),
            "want_to_read": ("#f59e0b", "#d97706"),
        }
        color = status_colors.get(status, ("#6b7280", "#4b5563"))

        self.status_badge = ctk.CTkLabel(
            self,
            text=status.replace("_", " ").title(),
            font=ctk.CTkFont(size=11),
            fg_color=color,
            corner_radius=8,
            text_color="white",
            padx=8,
            pady=2,
        )
        self.status_badge.pack(pady=(5, 0))

        # Rating
        if rating:
            self.rating_label = ctk.CTkLabel(
                self,
                text=f"★ {rating}/10",
                font=ctk.CTkFont(size=12),
                text_color=("#f59e0b", "#fbbf24"),
            )
            self.rating_label.pack(pady=(5, 10))
        else:
            self.rating_label = ctk.CTkLabel(self, text="", height=10)
            self.rating_label.pack(pady=(0, 10))

        # Bind click to all widgets
        if on_click:
            self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        """Bind click event to widget and all its children."""
        widget.bind("<Button-1>", self._handle_click)
        widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            self._bind_click_recursive(child)

    def _handle_click(self, event):
        """Handle click event."""
        if self.on_click:
            self.on_click()

    def _set_image(self, image: Optional[ctk.CTkImage]):
        """Set the card image."""
        if image:
            self.image_label.configure(image=image, text="")


class SearchResultCard(ctk.CTkFrame):
    """Card for search results."""

    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        on_add: Callable,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.configure(corner_radius=12, fg_color=("gray90", "gray17"))

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
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            text_frame,
            text=subtitle[:40] + "..." if len(subtitle) > 40 else subtitle,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
            anchor="w",
        ).pack(anchor="w")

        # Add button - always visible on the right
        self.add_btn = ctk.CTkButton(
            content,
            text="+ Add",
            width=80,
            height=35,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=on_add,
        )
        self.add_btn.grid(row=0, column=1, padx=(15, 0), sticky="e")


class Sidebar(ctk.CTkFrame):
    """Instagram-style sidebar navigation."""

    def __init__(self, parent, on_navigate: Callable, **kwargs):
        super().__init__(parent, **kwargs)

        self.configure(width=220, corner_radius=0, fg_color=("gray95", "gray10"))
        self.pack_propagate(False)

        self.on_navigate = on_navigate
        self.buttons = {}
        self.active = None

        # Logo/Title
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(25, 30))

        ctk.CTkLabel(
            logo_frame,
            text="📽️ Media",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame,
            text="Tracker",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")

        # Navigation items
        nav_items = [
            ("movies", "🎬", "Movies"),
            ("books", "📚", "Books"),
            ("recommend", "✨", "For You"),
            ("stats", "📊", "Statistics"),
        ]

        for key, icon, label in nav_items:
            self._create_nav_button(key, icon, label)

        # Spacer
        ctk.CTkFrame(self, fg_color="transparent", height=20).pack(fill="x")

        # Theme toggle at bottom
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="Dark Mode",
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light",
        )
        self.theme_switch.pack(anchor="w")

        # Set initial state based on system
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()

    def _create_nav_button(self, key: str, icon: str, label: str):
        """Create a navigation button."""
        btn = ctk.CTkButton(
            self,
            text=f"  {icon}  {label}",
            font=ctk.CTkFont(size=15),
            anchor="w",
            height=45,
            corner_radius=10,
            fg_color="transparent",
            text_color=("gray20", "gray80"),
            hover_color=("gray85", "gray20"),
            command=lambda: self._on_click(key),
        )
        btn.pack(fill="x", padx=15, pady=3)
        self.buttons[key] = btn

    def _on_click(self, key: str):
        """Handle navigation click."""
        # Update visual state
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(
                    fg_color=("gray80", "gray25"),
                    text_color=("gray10", "white"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray20", "gray80"),
                )

        self.active = key
        self.on_navigate(key)

    def _toggle_theme(self):
        """Toggle between dark and light mode."""
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)

    def set_active(self, key: str):
        """Set active navigation item."""
        self._on_click(key)


class AddMediaDialog(ctk.CTkToplevel):
    """Dialog for adding media with status selection."""

    def __init__(self, parent, media_type: str, title: str, on_confirm: Callable):
        super().__init__(parent)

        self.on_confirm = on_confirm
        self.media_type = media_type
        self.result = None

        self.title(f"Add {media_type.title()}")
        self.geometry("420x400")
        self.resizable(False, False)

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
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self,
            text=title[:45] + "..." if len(title) > 45 else title,
            font=ctk.CTkFont(size=14),
            text_color=("gray40", "gray60"),
        ).pack(pady=(0, 15))

        # Status selection
        ctk.CTkLabel(self, text="Status:", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=40)

        if media_type == "movie":
            statuses = ["Want to Watch", "Watching", "Watched"]
        else:
            statuses = ["Want to Read", "Reading", "Read"]

        self.status_var = ctk.StringVar(value=statuses[0])
        self.status_menu = ctk.CTkOptionMenu(
            self,
            values=statuses,
            variable=self.status_var,
            width=340,
            height=38,
            corner_radius=8,
        )
        self.status_menu.pack(pady=(5, 15))

        # Rating section
        ctk.CTkLabel(self, text="Rating (optional):", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=40)

        rating_row = ctk.CTkFrame(self, fg_color="transparent")
        rating_row.pack(fill="x", padx=40, pady=(5, 5))

        self.rating_slider = ctk.CTkSlider(
            rating_row, from_=1, to=10, number_of_steps=9, width=280
        )
        self.rating_slider.pack(side="left")
        self.rating_slider.set(5)

        self.rating_label = ctk.CTkLabel(
            rating_row, text="5", font=ctk.CTkFont(size=16, weight="bold"), width=40
        )
        self.rating_label.pack(side="left", padx=(10, 0))

        self.rating_slider.configure(command=self._update_rating_label)

        self.use_rating = ctk.CTkCheckBox(self, text="Include rating")
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
            text_color=("gray20", "gray80"),
            command=self.destroy,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="Add to Library",
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
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
    """Dialog showing media details with edit options."""

    def __init__(
        self,
        parent,
        media,
        media_type: str,
        on_update: Callable,
        on_delete: Callable,
    ):
        super().__init__(parent)

        self.media = media
        self.media_type = media_type
        self.on_update = on_update
        self.on_delete = on_delete

        self.title("Details")
        self.geometry("500x650")
        self.minsize(400, 500)

        self.transient(parent)
        self.grab_set()
        self.lift()
        self.focus_force()

        # Center the dialog on screen
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 325
        self.geometry(f"500x650+{x}+{y}")

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # Image
        self.image_label = ctk.CTkLabel(
            scroll,
            text="Loading...",
            width=200,
            height=300,
            corner_radius=15,
            fg_color=("gray80", "gray25"),
        )
        self.image_label.pack(pady=(0, 20))

        image_url = media.poster_url if media_type == "movie" else media.cover_url
        if image_url:
            ImageLoader.load_async(image_url, self._set_image, size=(200, 300))

        # Title
        ctk.CTkLabel(
            scroll,
            text=media.title,
            font=ctk.CTkFont(size=22, weight="bold"),
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
            text_color=("gray40", "gray60"),
        ).pack(pady=(0, 15))

        # Genre/Subjects
        if media_type == "movie" and media.genre:
            ctk.CTkLabel(
                scroll,
                text=media.genre,
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "gray50"),
                wraplength=450,
            ).pack(pady=(0, 10))
        elif media_type == "book" and media.subjects:
            ctk.CTkLabel(
                scroll,
                text=media.subjects,
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "gray50"),
                wraplength=450,
            ).pack(pady=(0, 10))

        # Plot (movies only)
        if media_type == "movie" and media.plot:
            ctk.CTkLabel(
                scroll,
                text=media.plot,
                font=ctk.CTkFont(size=13),
                wraplength=450,
                justify="left",
            ).pack(pady=(0, 15))

        # Status selector
        ctk.CTkLabel(
            scroll, text="Status", font=ctk.CTkFont(size=14, weight="bold")
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
        )
        self.status_menu.pack(anchor="w", pady=(0, 15))

        # Rating
        ctk.CTkLabel(
            scroll, text="Your Rating", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(10, 5))

        rating_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rating_frame.pack(anchor="w", pady=(0, 20))

        self.rating_slider = ctk.CTkSlider(
            rating_frame, from_=1, to=10, number_of_steps=9, width=200
        )
        self.rating_slider.pack(side="left")
        self.rating_slider.set(media.user_rating or 5)

        self.rating_label = ctk.CTkLabel(
            rating_frame,
            text=str(media.user_rating or 5),
            font=ctk.CTkFont(size=14),
            width=30,
        )
        self.rating_label.pack(side="left", padx=10)

        self.rating_slider.configure(command=self._update_rating_label)

        self.use_rating = ctk.CTkCheckBox(scroll, text="Include rating")
        if media.user_rating:
            self.use_rating.select()
        self.use_rating.pack(anchor="w", pady=(0, 20))

        # Action buttons
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Delete",
            width=100,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._delete,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame, text="Save Changes", width=150, command=self._save
        ).pack(side="right")

    def _set_image(self, image):
        if image:
            self.image_label.configure(image=image, text="")

    def _update_rating_label(self, value):
        self.rating_label.configure(text=str(int(value)))

    def _save(self):
        status_text = self.status_var.get().lower().replace(" ", "_")
        rating = int(self.rating_slider.get()) if self.use_rating.get() else None
        self.on_update(self.media.id, status_text, rating)
        self.destroy()

    def _delete(self):
        self.on_delete(self.media.id)
        self.destroy()


class MainContent(ctk.CTkFrame):
    """Main content area."""

    def __init__(self, parent, app: "MediaTrackerApp", **kwargs):
        super().__init__(parent, **kwargs)

        self.app = app
        self.configure(fg_color="transparent")

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        self.header.pack(fill="x", padx=30, pady=(20, 10))
        self.header.pack_propagate(False)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Movies",
            font=ctk.CTkFont(size=28, weight="bold"),
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
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._on_search())

        self.search_btn = ctk.CTkButton(
            self.search_frame,
            text="🔍",
            width=38,
            height=38,
            corner_radius=10,
            command=self._on_search,
        )
        self.search_btn.pack(side="left")

        # Tab bar for filtering
        self.tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_frame.pack(fill="x", padx=30, pady=(0, 10))

        self.tabs = {}
        self.current_tab = "all"

        # Content area (scrollable)
        self.content_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.content_scroll.pack(fill="both", expand=True, padx=20, pady=10)

        # Grid frame for cards
        self.grid_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)

        # Bind resize
        self.bind("<Configure>", self._on_resize)
        self._last_width = 0

    def _create_tabs(self, tabs: list):
        """Create filter tabs."""
        for widget in self.tab_frame.winfo_children():
            widget.destroy()

        self.tabs = {}
        for key, label in tabs:
            btn = ctk.CTkButton(
                self.tab_frame,
                text=label,
                height=32,
                corner_radius=8,
                fg_color="transparent" if key != self.current_tab else ("gray80", "gray25"),
                text_color=("gray40", "gray60") if key != self.current_tab else ("gray10", "white"),
                hover_color=("gray85", "gray20"),
                command=lambda k=key: self._on_tab_click(k),
            )
            btn.pack(side="left", padx=(0, 8))
            self.tabs[key] = btn

    def _on_tab_click(self, key: str):
        """Handle tab click."""
        self.current_tab = key
        for k, btn in self.tabs.items():
            if k == key:
                btn.configure(
                    fg_color=("gray80", "gray25"),
                    text_color=("gray10", "white"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray40", "gray60"),
                )
        self.app.refresh_content()

    def _on_search(self):
        """Handle search."""
        query = self.search_entry.get().strip()
        if query:
            self.app.perform_search(query)

    def _on_resize(self, event):
        """Handle window resize for responsive grid."""
        if abs(event.width - self._last_width) > 50:
            self._last_width = event.width
            self.app.refresh_content()

    def show_movies(self, movies: list):
        """Display movies in grid."""
        self.title_label.configure(text="Movies")
        self.search_entry.configure(placeholder_text="Search movies...")
        self._create_tabs([
            ("all", "All"),
            ("watched", "Watched"),
            ("watching", "Watching"),
            ("want_to_watch", "Want to Watch"),
        ])
        self._display_media_grid(movies, "movie")

    def show_books(self, books: list):
        """Display books in grid."""
        self.title_label.configure(text="Books")
        self.search_entry.configure(placeholder_text="Search books...")
        self._create_tabs([
            ("all", "All"),
            ("read", "Read"),
            ("reading", "Reading"),
            ("want_to_read", "Want to Read"),
        ])
        self._display_media_grid(books, "book")

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
                text_color=("gray40", "gray60"),
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
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            section,
            text=reason,
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
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

    def show_stats(self, movie_stats, book_stats):
        """Display statistics."""
        self.title_label.configure(text="Statistics")
        self.search_frame.pack_forget()
        self._create_tabs([])

        # Clear grid
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        # Stats container
        container = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Movie stats
        self._create_stats_card(container, "🎬 Movies", movie_stats, "movie")

        # Book stats
        self._create_stats_card(container, "📚 Books", book_stats, "book")

        self.search_frame.pack(side="right")

    def _create_stats_card(self, parent, title, stats, media_type):
        """Create a statistics card."""
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color=("gray90", "gray17"))
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold"),
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
        else:
            items = [
                ("Read", stats.get("read", 0)),
                ("Reading", stats.get("reading", 0)),
                ("Want to Read", stats.get("want_to_read", 0)),
            ]

        for label, value in items:
            stat_item = ctk.CTkFrame(stats_frame, fg_color="transparent")
            stat_item.pack(side="left", expand=True)

            ctk.CTkLabel(
                stat_item,
                text=str(value),
                font=ctk.CTkFont(size=32, weight="bold"),
            ).pack()

            ctk.CTkLabel(
                stat_item,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=("gray40", "gray60"),
            ).pack()

        # Average rating
        if stats.get("avg_user_rating"):
            ctk.CTkLabel(
                card,
                text=f"Average Rating: ★ {stats['avg_user_rating']}/10",
                font=ctk.CTkFont(size=14),
                text_color=("#f59e0b", "#fbbf24"),
            ).pack(anchor="w", padx=20, pady=(0, 10))

        # Top genres/subjects
        top_items = stats.get("top_genres" if media_type == "movie" else "top_subjects", [])
        if top_items:
            label = "Top Genres" if media_type == "movie" else "Top Subjects"
            items_text = ", ".join([f"{item[0]} ({item[1]})" for item in top_items[:5]])
            ctk.CTkLabel(
                card,
                text=f"{label}: {items_text}",
                font=ctk.CTkFont(size=13),
                text_color=("gray40", "gray60"),
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
                text_color=("gray40", "gray60"),
            ).pack(pady=50)
            return

        ctk.CTkLabel(
            self.grid_frame,
            text=f"Search Results ({len(results)})",
            font=ctk.CTkFont(size=16, weight="bold"),
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
            else:
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
            card.pack(fill="x", padx=10, pady=5)

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
                text_color=("gray40", "gray60"),
            ).pack(pady=50)
            return

        # Filter by tab
        if self.current_tab != "all":
            items = [i for i in items if i.status.value == self.current_tab]

        if not items:
            ctk.CTkLabel(
                self.grid_frame,
                text=f"No {media_type}s in this category",
                font=ctk.CTkFont(size=16),
                text_color=("gray40", "gray60"),
            ).pack(pady=50)
            return

        # Calculate columns based on width
        width = self.winfo_width()
        card_width = 190
        columns = max(1, (width - 60) // card_width)

        # Create grid
        row_frame = None
        for i, item in enumerate(items):
            if i % columns == 0:
                row_frame = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=5)

            if media_type == "movie":
                card = MediaCard(
                    row_frame,
                    title=item.title,
                    subtitle=f"{item.year or 'N/A'}",
                    status=item.status.value,
                    rating=item.user_rating,
                    image_url=item.poster_url,
                    on_click=lambda m=item: self.app.show_detail(m, "movie"),
                )
            else:
                card = MediaCard(
                    row_frame,
                    title=item.title,
                    subtitle=f"{item.author or 'Unknown'}",
                    status=item.status.value,
                    rating=item.user_rating,
                    image_url=item.cover_url,
                    on_click=lambda b=item: self.app.show_detail(b, "book"),
                )
            card.pack(side="left", padx=10, pady=10)


class MediaTrackerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Media Tracker")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # Initialize backend
        try:
            self.db = Database()
            self.recommender = Recommender(self.db)
        except DatabaseError as e:
            self._show_error(f"Database Error: {e}")
            return

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
        elif self.current_view == "recommend":
            movie, movie_reason = self.recommender.get_recommendation("movie", smart=True)
            book, book_reason = self.recommender.get_recommendation("book", smart=True)
            self.main_content.show_recommendations(movie, book, movie_reason, book_reason)
        elif self.current_view == "stats":
            movie_stats = self.db.get_movie_stats()
            book_stats = self.db.get_book_stats()
            self.main_content.show_stats(movie_stats, book_stats)

    def perform_search(self, query: str):
        """Perform search."""
        self.search_mode = True

        if self.current_view == "movies":
            if not self.movie_api:
                self._show_error("OMDB API key not configured")
                return
            try:
                results = self.movie_api.search(query)
                self.main_content.show_search_results(results, "movie")
            except OMDBError as e:
                self._show_error(str(e))
        elif self.current_view == "books":
            try:
                results = self.book_api.search(query)
                self.main_content.show_search_results(results, "book")
            except OpenLibraryError as e:
                self._show_error(str(e))

    def add_movie_from_search(self, result: dict):
        """Add movie from search result."""
        # Check if already exists
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
        # Check if already exists
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

        def on_update(media_id: int, status: str, rating: Optional[int]):
            if media_type == "movie":
                status_enum = MovieStatus(status)
                self.db.update_movie_status(media_id, status_enum, rating)
            else:
                status_enum = BookStatus(status)
                self.db.update_book_status(media_id, status_enum, rating)
            self.refresh_content()

        def on_delete(media_id: int):
            if media_type == "movie":
                self.db.delete_movie(media_id)
            else:
                self.db.delete_book(media_id)
            self.refresh_content()

        MediaDetailDialog(self, media, media_type, on_update, on_delete)

    def _show_error(self, message: str):
        """Show error dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Error")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        dialog.geometry(f"400x150+{x}+{y}")

        ctk.CTkLabel(
            dialog,
            text="⚠️ Error",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            dialog,
            text=message,
            font=ctk.CTkFont(size=14),
            wraplength=350,
        ).pack(pady=(0, 20))

        ctk.CTkButton(dialog, text="OK", width=100, command=dialog.destroy).pack()


def main():
    app = MediaTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
