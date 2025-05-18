import tkinter as tk
from tkinter import colorchooser
import requests
import appdirs
import tempfile
import shutil
from tkinter import filedialog, ttk, scrolledtext, messagebox, Toplevel, Label
import sys
import logging
import logging.handlers
from ttkbootstrap import Style
from io import StringIO
import os
import json
import shutil
import webbrowser
import subprocess
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import hashlib
import glob
import time
import re
from tkinter import filedialog
from PIL import Image, ImageTk
from utils import (
    decompress_ssf, extract_misc_as, modify_misc_as, inject_misc_as, compress_swf,
    extract_character_names, extract_costumes, update_costumes, load_costumes_from_file,
    check_url_exists, load_costumes_from_url, launch_ssf2, copy_ssf2_directory,
    color_to_int, int_to_color_str, resource_path, logger, setup_logging
)
import platform
from add_costume_window import AddCostumeWindow



def redact_path(path):
    """Redact user-specific paths for privacy."""
    if not path:
        return path
    try:
        home_dir = os.path.expanduser("~")
        if home_dir in path:
            path = path.replace(home_dir, "<USER_DIR>")
        if platform.system() == "Windows":
            user_profile = os.environ.get("USERPROFILE", "")
            if user_profile and user_profile in path:
                path = path.replace(user_profile, "<USER_DIR>")
        path = re.sub(r'[/\\]Users[/\\][^/\\]+[/\\]', r'\\Users\\<USERNAME>\\', path, flags=re.IGNORECASE)
        return path
    except Exception as e:
        logger.error(f"Error in redact_path: {e}")
        return path

class TextRedirector:
    def __init__(self, widget):
        self.widget = widget
        self.buffer = StringIO()
        self.last_update = 0
        self.update_interval = 100  # ms

    def write(self, text):
        self.buffer.write(text)
        logger.debug(f"TextRedirector received: {repr(text)}")
        current_time = time.time() * 1000
        if current_time - self.last_update >= self.update_interval:
            self.flush_buffer()

    def flush_buffer(self):
        """Update the widget with buffered text."""
        text = self.buffer.getvalue()
        if text:
            try:
                if self.widget.winfo_exists():
                    self.widget.insert(tk.END, text)
                    self.widget.see(tk.END)
            except tk.TclError as e:
                logger.warning(f"UI log update failed (widget destroyed): {e}")
        self.buffer.seek(0)
        self.buffer.truncate()
        self.last_update = time.time() * 1000
        if text:
            redacted_text = redact_path(text.rstrip('\n'))
            if redacted_text:
                logger.info(redacted_text)

    def flush(self):
        self.flush_buffer()
        for handler in logger.handlers:
            try:
                handler.flush()
            except AttributeError:
                pass

class SSF2ModGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        # Determine base directory based on whether the app is frozen (e.g., PyInstaller)
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        # Setup logging
        self.enable_file_logging = True
        setup_logging(base_dir, self.enable_file_logging, debug=False)
        logger.info("Initializing SSF2ModGUI application...")

        # Initialize config as empty dict to prevent attribute errors
        self.config = {}

        # Handle config migration
        old_config_path = os.path.join(base_dir, "config.json")
        config_migrated = False
        app_name = "SSF2CostumeInjector"
        app_author = "masterwebx"
        config_dir = appdirs.user_data_dir(app_name, app_author)
        os.makedirs(config_dir, exist_ok=True)
        self.config_file = os.path.join(config_dir, "config.json")
        logger.info(f"Target config file path: {redact_path(self.config_file)}")

        if os.path.exists(old_config_path):
            logger.info(f"Found config.json in application directory: {redact_path(old_config_path)}")
            try:
                shutil.copy2(old_config_path, self.config_file)
                logger.info(f"Copied config.json to user data directory: {redact_path(self.config_file)}")
                try:
                    os.remove(old_config_path)
                    logger.info(f"Removed old config.json from: {redact_path(old_config_path)}")
                except Exception as e:
                    logger.warning(f"Could not remove old config.json from {redact_path(old_config_path)}: {e}")
                config_migrated = True
            except Exception as e:
                logger.error(f"Error migrating config.json from {redact_path(old_config_path)} to {redact_path(self.config_file)}: {e}")
                self.config_file = old_config_path
                logger.info(f"Falling back to old config path: {redact_path(self.config_file)}")

        # Initialize suppress prompts
        self.suppress_prompts = {
            "jpexs_extract": False,
            "jpexs_inject": False,
            "ssf2_launch": False,
            "save_confirm": False,
            "load_original_confirm": False,
            "load_from_online_confirm": False,
            "save_and_play_confirm": False,
            "save_changes_confirm": False,
            "select_ssf2_folder_confirm": False,
            "skip_update_version": ""
        }

        # Set window properties
        self.title("SSF2 Costume Injector v1.0.6")
        self.APP_VERSION = "1.0.6"
        self.GITHUB_REPO = "masterwebx/Color-Vault"
        self.AUTO_UPDATE_CHECK = True
        icon_path = resource_path("icon.ico")
        self.wm_iconbitmap(resource_path("icon.ico"))

        # Initialize instance variables
        self.preview_cache = {}
        self.help_mode = False
        self.tooltips = {}
        self.tooltips_list = []
        self.original_stdout = sys.stdout
        self.characters = ["Custom"]
        self.pan_debounce_timer = None
        self.original_costumes = []
        self.pan_debounce_delay = 50
        self.cached_resized_image = None
        self.cached_zoom_scale = None
        self.characters_loaded = False
        self.loaded_misc_as = None
        self.ssf_source = None
        self.java_path = None
        self.last_selected_listbox = None
        self.costume_listbox = tk.Listbox(self)
        self.loaded_listbox = tk.Listbox(self)
        self.move_to_trash_button = tk.Button(self, text="Move to Trash", command=self.move_to_trash)
        self.add_new_button = tk.Button(self, text="Add New", command=self.add_costume)
        self.ffdec_jar = None
        self.original_ssf = None
        self.temp_swf = None
        self.log_visible = True
        self.costume_list_visible = False
        self.ui_initialized = False
        self.setup_frame = None
        self.was_log_visible = False
        self.costume_offset = 0
        self.total_costumes = 0
        self.costume_count_label = None
        self.preview_photo = None
        self.protected_count = 4
        self.image_cache_dir = os.path.join(os.getcwd(), "image_cache")
        if os.path.exists(self.image_cache_dir):
            try:
                shutil.rmtree(self.image_cache_dir)
                logger.info(f"Deleted cache directory on startup: {redact_path(self.image_cache_dir)}")
            except Exception as e:
                logger.error(f"Error deleting cache directory on startup: {e}")
        os.makedirs(self.image_cache_dir)
        self.preview_debounce_timer = None
        self.preview_debounce_delay = 100
        self.bg_image_cache = None
        self.last_window_size = None
        self.last_transparency = None
        self.resize_debounce_timer = None
        self.resize_debounce_delay = 100  # ms

        # Define themes
        self.themes = {
            "Light": {
                "fg": "black",
                "bg": "#d9d9d9",
                "canvas_bg": "#808080",
                "button_bg": "#f0f0f0",
                "button_fg": "black",
                "progress_bg": "#d9d9d9",
                "progress_fg": "#4CAF50"
            },
            "Dark": {
                "fg": "white",
                "bg": "#2e2e2e",
                "canvas_bg": "#555555",
                "button_bg": "#444444",
                "button_fg": "white",
                "progress_bg": "#2e2e2e",
                "progress_fg": "#4CAF50"
            },
            "Blue": {
                "fg": "white",
                "bg": "#2B4B9F",  # Lighter blue for better visibility
                "canvas_bg": "#3B82F6",
                "button_bg": "#1E40AF",
                "button_fg": "white",
                "progress_bg": "#2B4B9F",
                "progress_fg": "#60A5FA"
            },
            "Green": {
                "fg": "white",
                "bg": "#1A6B3F",  # Lighter green
                "canvas_bg": "#4ADE80",
                "button_bg": "#166534",
                "button_fg": "white",
                "progress_bg": "#1A6B3F",
                "progress_fg": "#86EFAC"
            },
            "Red": {
                "fg": "white",
                "bg": "#A12828",  # Lighter red
                "canvas_bg": "#F87171",
                "button_bg": "#991B1B",
                "button_fg": "white",
                "progress_bg": "#A12828",
                "progress_fg": "#FCA5A5"
            }
        }
        self._tscale_style_configured = False
        self.default_bg_image = resource_path("default.png")  # Default background image

        # Initialize transparency variables BEFORE loading config
        self.bg_transparency = tk.DoubleVar()
        self.theme_transparency = tk.BooleanVar()
        self.current_theme = tk.StringVar()
        self.bg_image_path = tk.StringVar()

        # Load config after initializing variables
        self.load_config()       

        # Initialize path variables
        logger.info("Setting up default paths for SSF2 and JPEXS Decompiler...")
        self.ffdec_path = tk.StringVar(value=self.config.get("ffdec_path", ""))
        self.ssf_path = tk.StringVar(value=self.config.get("ssf_path", ""))
        self.ssf2_exe_path = tk.StringVar(value=self.config.get("ssf2_exe_path", ""))
        self.use_original = tk.BooleanVar(value=False)
        self.selected_character = tk.StringVar(value="Select a Character")
        self.custom_character = tk.StringVar()

        # Initialize ttkbootstrap with lightweight theme
        theme_map = {
            "Light": "litera",
            "Dark": "darkly",
            "Blue": "flatly",
            "Green": "minty",
            "Red": "pulse"
        }
        bootstrap_theme = theme_map.get(self.current_theme.get(), "litera")
        self.style = Style(theme=bootstrap_theme)
        self.apply_theme()
        self.apply_background_image()
        self.bind("<Configure>", self.on_resize)

        # Set window geometry
        initial_width = 1204
        initial_height = 712
        self.minsize(initial_width, initial_height)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight() - 50
        x = (screen_width - initial_width) // 2
        y = (screen_height - initial_height) // 2
        self.geometry(f"{initial_width}x{initial_height}+{x}+{y}")

        

        # Run setup or create UI
        logger.info(f"Setup completed status: {self.setup_completed}")
        if not self.setup_completed:
            logger.info("Starting setup process for first-time configuration...")
            self.run_setup()
        else:
            logger.info("Setup already completed, proceeding to create main UI...")
            self.create_main_ui()
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.ui_initialized = True
            if self.validate_paths() and self.ssf_path.get() and self.ffdec_path.get():
                logger.info("Paths validated successfully, loading characters from SSF file...")
                self.temp_swf = os.path.abspath("temp.swf")
                self.load_characters()
            else:
                logger.warning("Invalid or missing paths, skipping character loading")
            self.toggle_custom_field()

        # Defer non-critical initialization
        self.after(1000, self.deferred_init)

        # Handle config migration save
        if config_migrated:
            logger.info("Config was migrated, saving to new location...")
            self.save_config()

    def on_resize(self, event):
        """Debounce resize events."""
        if self.resize_debounce_timer:
            self.after_cancel(self.resize_debounce_timer)
        # Increase debounce delay to 200ms to reduce rapid calls
        self.resize_debounce_timer = self.after(200, self.apply_background_image)
    def on_close(self):
        logger.info("Closing application...")
        # Restore stdout before destroying
        sys.stdout = self.original_stdout
        if os.path.exists(self.image_cache_dir):
            try:
                shutil.rmtree(self.image_cache_dir)
                logger.info(f"Deleted cache directory on exit: {self.image_cache_dir}")
            except Exception as e:
                logger.error(f"Error deleting cache directory on exit: {str(e)}")
        self.destroy()

    def get_display_name(self, costume):
        if 'team' in costume:
            return f"Team {costume['team'].capitalize()}"
        elif 'base' in costume and costume['base']:
            return "Base"
        elif 'info' in costume:
            return costume['info']
        else:
            return "No Info"

    def load_url_mappings(self):
        logger.info("Loading character-to-URL mappings from remote URL...")
        character_to_url = {}
        url = "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/urls.json"        
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            urls = response.json()
            for item in urls:
                name = item["name"].lower().replace(" recolor sheet", "").replace(" ", "")
                if "(sandbox)" in name:
                    name = name.replace("(sandbox)", "")
                character_to_url[name] = item["url"]
            logger.info(f"Loaded {len(character_to_url)} mappings from remote URL.")
            return character_to_url
        except requests.RequestException as e:
            logger.error(f"Error fetching mappings from URL: {str(e)}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from URL: {str(e)}")
            return {}

    def load_config(self):
        logger.info("Loading config...")
        default_config = {
            "setup_completed": False,
            "ffdec_path": "",
            "ssf_path": "",
            "ssf2_exe_path": "",
            "hide_log": False,
            "enable_file_logging": True,
            "theme": "Dark",
            "bg_image_path": self.default_bg_image,
            "bg_transparency": 70.0,
            "theme_transparency": False
        }
        self.config = default_config.copy()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                self.config.update(loaded_config)
                logger.info(f"Loaded config: {self.config}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading config from {redact_path(self.config_file)}: {e}")
                self.show_error("Error", f"Error loading config, resetting to defaults: {e}")
                self.save_config()
        else:
            logger.info("No config file found, using defaults")
            self.save_config()

        self.setup_completed = self.config.get("setup_completed", False)
        self.hide_log = tk.BooleanVar(value=self.config.get("hide_log", False))
        self.enable_file_logging = self.config.get("enable_file_logging", True)
        if self.enable_file_logging != default_config["enable_file_logging"]:
            setup_logging(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), self.enable_file_logging, debug=False)
            logger.info(f"Updated file logging setting to: {self.enable_file_logging}")
        for key in self.suppress_prompts:
            self.suppress_prompts[key] = self.config.get(f"suppress_{key}", False)
        logger.info(f"Loaded suppress_prompts: {self.suppress_prompts}")

        # Update theme and transparency variables
        theme_name = self.config.get("theme", "Dark")
        if theme_name not in self.themes:
            logger.warning(f"Invalid theme '{theme_name}' in config, falling back to 'Dark'")
            theme_name = "Dark"
            self.config["theme"] = theme_name
        self.current_theme.set(theme_name)
        self.bg_transparency.set(self.config.get("bg_transparency", 70.0))
        theme_transparency_value = self.config.get("theme_transparency", False)
        if isinstance(theme_transparency_value, (int, float)):
            theme_transparency_value = bool(theme_transparency_value)
        self.theme_transparency.set(theme_transparency_value)
        self.bg_image_path.set(self.config.get("bg_image_path", self.default_bg_image))

    def save_config(self):
        logger.info("Saving config...")
        config_path = os.path.abspath(self.config_file)
        self.config.update({
            "setup_completed": self.setup_completed,
            "ffdec_path": self.ffdec_path.get() if hasattr(self, 'ffdec_path') else "",
            "ssf_path": self.ssf_path.get() if hasattr(self, 'ssf_path') else "",
            "ssf2_exe_path": self.ssf2_exe_path.get() if hasattr(self, 'ssf2_exe_path') else "",
            "hide_log": self.hide_log.get(),
            "enable_file_logging": self.enable_file_logging,
            "theme": self.current_theme.get(),
            "bg_image_path": self.bg_image_path.get(),
            "bg_transparency": self.bg_transparency.get(),
            "theme_transparency": self.theme_transparency.get()
        })
        logger.info(f"Attempting to save config to: {redact_path(config_path)}")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            if os.path.exists(config_path):
                logger.info(f"Config saved successfully to: {redact_path(config_path)}")
            else:
                logger.error(f"Config file was not created at {redact_path(config_path)}")
                self.show_error("Error", f"Config file was not created at {redact_path(config_path)}")
        except Exception as e:
            logger.error(f"Error saving config to {redact_path(config_path)}: {e}")
            self.show_error("Error", f"Error saving config: {e}")

    def blend_color(self, color, transparency):
        """Blend the color with white to simulate transparency (0-100 scale)."""
        if not color.startswith("#") or len(color) not in (4, 7):
            return color  # Return unchanged if not a valid hex color
        try:
            # Convert hex color to RGB
            color = color.lstrip("#")
            if len(color) == 3:
                color = "".join(c * 2 for c in color)  # Expand shorthand hex
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            
            # Blend with white (255, 255, 255)
            alpha = transparency / 100.0
            r = int(r * alpha + 255 * (1 - alpha))
            g = int(g * alpha + 255 * (1 - alpha))
            b = int(b * alpha + 255 * (1 - alpha))
            
            # Ensure values are within 0-255
            r = min(255, max(0, r))
            g = min(255, max(0, g))
            b = min(255, max(0, b))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError) as e:
            logger.debug(f"Error blending color {color}: {e}")
            return color
    def update_widget_colors(self, widget, theme):
        """Update colors for tk widgets only."""
        fg = theme.get("fg", "black")
        bg = theme.get("bg", "#d9d9d9")
        canvas_bg = theme.get("canvas_bg", "#808080")
        button_fg = theme.get("button_fg", "black")
        button_bg = theme.get("button_bg", "#f0f0f0")

        try:
            if isinstance(widget, tk.Label):
                if self.theme_transparency.get():
                    widget.configure(fg=fg, bg="")
                else:
                    widget.configure(fg=fg, bg=bg)
            elif isinstance(widget, tk.Button):
                widget.configure(fg=button_fg, bg=button_bg)
            elif isinstance(widget, tk.Canvas):
                widget.configure(bg=canvas_bg)
            elif isinstance(widget, scrolledtext.ScrolledText):
                widget.configure(bg=bg, fg=fg)
            elif isinstance(widget, tk.Frame):
                if self.theme_transparency.get():
                    widget.configure(bg="")
                else:
                    widget.configure(bg=bg)
            elif isinstance(widget, tk.Listbox):
                widget.configure(fg=fg, bg=bg)
            elif isinstance(widget, tk.Entry):
                widget.configure(fg=fg, bg=bg, insertbackground=fg)
            elif isinstance(widget, tk.OptionMenu):
                widget.configure(fg=fg, bg=button_bg, activeforeground=fg, activebackground=button_bg)
                widget["menu"].configure(fg=fg, bg=bg)
            elif isinstance(widget, ttk.Frame):
                widget.configure(style="TFrame")
            else:
                logger.debug(f"Unhandled widget type: {widget.__class__.__name__}")
        except tk.TclError as e:
            logger.debug(f"Error updating widget {widget.__class__.__name__}: {e}")
        
        for child in widget.winfo_children():
            if not isinstance(child, (ttk.Combobox, ttk.Progressbar, ttk.Scale)):
                self.update_widget_colors(child, theme)

    def open_settings(self):
        logger.info("Opening settings menu to configure theme and background...")
        settings_window = Toplevel(self)
        settings_window.title("Settings")
        settings_window.transient(self)
        settings_window.grab_set()
        settings_window.wm_iconbitmap(resource_path("icon.ico"))
        settings_window.minsize(700, 700)
        self.center_toplevel(settings_window, 700, 700)

        theme_name = self.current_theme.get()
        if theme_name not in self.themes:
            logger.error(f"Invalid theme '{theme_name}', falling back to 'Light'")
            theme_name = "Light"
            self.current_theme.set(theme_name)
            self.config["theme"] = theme_name
            self.save_config()
        theme = self.themes[theme_name]
        settings_window.configure(bg=theme.get("bg", "#d9d9d9"))

        # Theme selection
        tk.Label(settings_window, text="Theme:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        theme_frame = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        theme_frame.pack(fill=tk.X, padx=5)
        theme_menu = tk.OptionMenu(theme_frame, self.current_theme, *self.themes.keys())
        theme_menu.config(fg=theme.get("fg", "black"), bg=theme.get("button_bg", "#f0f0f0"), activeforeground=theme.get("fg", "black"), activebackground=theme.get("button_bg", "#f0f0f0"))
        theme_menu["menu"].config(fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9"))
        theme_menu.pack(side=tk.LEFT)
        tk.Button(theme_frame, text="Apply Theme", command=self.apply_theme, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.LEFT, padx=5)
        tk.Label(theme_frame, text="Background Transparency:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(side=tk.LEFT, padx=5)
        transparency_slider = ttk.Scale(theme_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.bg_transparency, command=lambda _: self.apply_background_image(), style="TScale")
        transparency_slider.pack(side=tk.LEFT, padx=5)
        tk.Label(theme_frame, text="Theme Transparency:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(side=tk.LEFT, padx=5)
        theme_transparency_toggle = tk.Checkbutton(theme_frame, variable=self.theme_transparency, command=self.apply_theme, fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9"))
        theme_transparency_toggle.pack(side=tk.LEFT, padx=5)

        # Background image selection
        tk.Label(settings_window, text="Main Window Background Image:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        bg_frame = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        bg_frame.pack(fill=tk.X, padx=5)
        tk.Entry(bg_frame, textvariable=self.bg_image_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(bg_frame, text="Browse", command=self.choose_background_image, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT)
        tk.Button(bg_frame, text="Clear", command=self.clear_background_image, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)
        tk.Button(bg_frame, text="Restore Default", command=lambda: self.restore_default_background(), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)

        # ... rest of the method ...

        # Apply theme to ensure all settings window widgets are styled
        self.apply_theme()

    def run_setup(self):
        logger.info("Running setup wizard to configure paths...")
        theme = self.themes[self.current_theme.get()]
        self.setup_frame = tk.Frame(self, bg=theme["bg"])
        self.setup_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(self.setup_frame, text="Welcome to SSF2 Costume Injector Setup", font=("Arial", 14), fg=theme["fg"], bg=theme["bg"]).pack(pady=10)
        tk.Button(self.setup_frame, text="Cancel", command=self.destroy, fg=theme["button_fg"], bg=theme["button_bg"]).pack(pady=10)

        self.log_text = scrolledtext.ScrolledText(self.setup_frame, height=10, width=60, state='normal', bg=theme["bg"], fg=theme["fg"])
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        sys.stdout = TextRedirector(self.log_text)

        logger.info("Setup UI initialized successfully.")

        self.setup_content_frame = tk.Frame(self.setup_frame, bg=theme["bg"])
        self.setup_content_frame.pack(fill=tk.X, pady=5)

        self.continue_button = tk.Button(self.setup_frame, text="Continue", command=self.complete_setup, fg=theme["button_fg"], bg=theme["button_bg"])
        self.continue_button.pack(pady=10)

        self.check_jpexs()
        self.check_ssf2()
        self.apply_theme()
        logger.info("Setup UI initialized and theme applied successfully.")

    def clear_setup_content(self):
        logger.info("Clearing setup content frame to update UI...")
        for widget in self.setup_content_frame.winfo_children():
            widget.destroy()
    def apply_theme(self):
        """Apply the selected theme's colors to all UI elements."""
        theme_name = self.current_theme.get()
        if theme_name not in self.themes:
            logger.error(f"Invalid theme '{theme_name}', falling back to 'Light'")
            theme_name = "Light"
            self.current_theme.set(theme_name)
            self.config["theme"] = theme_name
            self.save_config()
        
        theme_map = {
            "Light": "litera",
            "Dark": "darkly",
            "Blue": "superhero",  # Darker theme for Blue
            "Green": "darkly",    # Darker theme for Green
            "Red": "cyborg"       # Darker theme for Red
        }
        bootstrap_theme = theme_map.get(theme_name, "litera")
        theme = self.themes[theme_name]
        logger.info(f"Applying theme: {theme_name} (bootstrap: {bootstrap_theme})")

        try:
            self.style.theme_use(bootstrap_theme)
        except tk.TclError as e:
            logger.warning(f"Non-fatal TclError applying ttkbootstrap theme '{bootstrap_theme}': {e}")

        try:
            self.style.configure("TProgressbar", background=theme["progress_fg"], troughcolor=theme["progress_bg"])
            self.style.configure("TCombobox", fieldbackground=theme["bg"], foreground=theme["fg"], background=theme["bg"], highlightcolor=theme["fg"])
            self.style.configure("TButton", background=theme["button_bg"], foreground=theme["button_fg"], highlightcolor=theme["fg"])
            self.style.configure("TLabel", background=theme["bg"], foreground=theme["fg"])
            self.style.configure("TCheckbutton", background=theme["bg"], foreground=theme["fg"])
            self.style.configure("TEntry", background=theme["bg"], foreground=theme["fg"], insertbackground=theme["fg"])
            if not self._tscale_style_configured:
                self.style.configure("TScale", background=theme["bg"], foreground=theme["fg"])
                self._tscale_style_configured = True
        except tk.TclError as e:
            logger.warning(f"Non-fatal error configuring ttk styles: {e}")

        try:
            self.configure(bg=theme["bg"])
            self.update_widget_colors(self, theme)
        except tk.TclError as e:
            logger.warning(f"Non-fatal error updating main window colors: {e}")

        for win in self.winfo_children():
            try:
                if win.winfo_exists():
                    if isinstance(win, tk.Toplevel):
                        win.configure(bg=theme["bg"])
                    self.update_widget_colors(win, theme)
                    for child in win.winfo_children():
                        if isinstance(child, ttk.Combobox) and child.winfo_exists():
                            child.configure(style="TCombobox")
                        elif isinstance(child, ttk.Button) and child.winfo_exists():
                            child.configure(style="TButton")
                        elif isinstance(child, ttk.Label) and child.winfo_exists():
                            child.configure(style="TLabel")
                        elif isinstance(child, ttk.Checkbutton) and child.winfo_exists():
                            child.configure(style="TCheckbutton")
                        elif isinstance(child, ttk.Entry) and child.winfo_exists():
                            child.configure(style="TEntry")
                        elif isinstance(child, ttk.Progressbar) and child.winfo_exists():
                            child.configure(style="TProgressbar")
                        elif isinstance(child, ttk.Scale) and child.winfo_exists():
                            child.configure(style="TScale")
                        # Note: ttk.OptionMenu is not styled directly, handled by tk.OptionMenu in update_widget_colors
            except tk.TclError as e:
                logger.debug(f"Skipping theme update for widget {win}: {e}")

        try:
            self.update()
        except tk.TclError as e:
            logger.warning(f"Non-fatal error during UI refresh: {e}")

        if self.ui_initialized:
            self.save_config()
    def prompt_for_update(self, release):
        """Prompt user to update with release details."""
        latest_version = release["tag_name"].lstrip("v")
        release_notes = release.get("body", "No release notes available.")
        dialog = Toplevel(self)
        dialog.title("Update Available")
        dialog.transient(self)
        dialog.grab_set()
        self.center_toplevel(dialog, 500, 300)

        tk.Label(dialog, text=f"New version {latest_version} is available!").pack(pady=10)
        tk.Label(dialog, text="Release Notes:").pack(anchor="w", padx=10)
        notes_text = scrolledtext.ScrolledText(dialog, height=5, width=50)
        notes_text.insert(tk.END, release_notes)
        notes_text.config(state="disabled")
        notes_text.pack(pady=5, padx=10)

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Update Now",
                command=lambda: [webbrowser.open(f"https://github.com/{self.GITHUB_REPO}/releases"), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Skip This Version",
                command=lambda: [self.suppress_prompts.update({"skip_update_version": latest_version}), self.save_config(), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Later", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    def check_for_updates(self):
        """Check GitHub for the latest release."""
        logger.info("Checking for updates...")
        self.set_busy("Checking for updates", progress=0)
        try:
            url = f"https://api.github.com/repos/{self.GITHUB_REPO}/releases/latest"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            release = response.json()
            latest_version = release["tag_name"].lstrip("v")  
            if latest_version == self.suppress_prompts.get("skip_update_version"):
                logger.info(f"Skipping update check for version {latest_version}.")
                self.clear_busy()
                return
            if latest_version > self.APP_VERSION:  # Assumes semantic versioning
                self.prompt_for_update(release)
            else:
                logger.info(f"No updates available. Current version: {self.APP_VERSION}")
            self.clear_busy()
        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            self.clear_busy()

    def check_jpexs(self):
        logger.info("Checking for JPEXS Decompiler installation...")
        self.clear_setup_content()
        default_ffdec = os.path.normpath(os.path.expandvars(r"C:\Program Files (x86)\FFDec\ffdec.jar"))
        if os.path.isfile(default_ffdec):
            self.ffdec_path.set(default_ffdec)
            logger.info("JPEXS Decompiler found at default location: " + default_ffdec)
            return True
        logger.info("JPEXS Decompiler not found at C:\\Program Files (x86)\\FFDec\\")
        tk.Label(self.setup_content_frame, text="Please download and install JPEXS Decompiler.").pack(pady=5)
        tk.Button(self.setup_content_frame, text="Download JPEXS", command=lambda: webbrowser.open("https://github.com/jindrapetrik/jpexs-decompiler/releases")).pack(pady=5)
        tk.Button(self.setup_content_frame, text="Select JPEXS ffdec.jar", command=self.browse_ffdec).pack(pady=5)
        return False

    def check_ssf2(self):
        logger.info("Checking for SSF2 installation at specified paths...")
        self.clear_setup_content()
        ssf_path = self.ssf_path.get()
        exe_path = self.ssf2_exe_path.get()
        
        if os.path.isfile(ssf_path) and os.path.isfile(exe_path):
            logger.info(f"SSF2 found at: {os.path.dirname(ssf_path)}")
            return True
        
        logger.info(f"SSF2 not found at specified paths: ssf={ssf_path}, exe={exe_path}")
        tk.Label(self.setup_content_frame, text="SSF2 must be copied to a valid location for modding.").pack(pady=5)
        tk.Label(self.setup_content_frame, text="Please download SSF2 or select an existing installation to copy.").pack(pady=5)
        tk.Button(self.setup_content_frame, text="Download SSF2", command=lambda: webbrowser.open("https://www.supersmashflash.com/play/ssf2/downloads/")).pack(pady=5)
        tk.Button(self.setup_content_frame, text="Select SSF2 Folder to Copy", command=self.select_ssf2_folder).pack(pady=5)
        return False

    def complete_setup(self):
        logger.info("Completing setup process and validating paths...")
        if self.check_jpexs() and self.check_ssf2():
            self.setup_completed = True
            self.save_config()
            sys.stdout = self.original_stdout
            logger.info("Destroying setup frame to transition to main UI...")
            self.setup_frame.destroy()
            self.setup_frame = None
            logger.info("Creating main UI for character selection and costume management...")
            self.create_main_ui()
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.ui_initialized = True
            if self.validate_paths():
                logger.info("Paths validated, loading characters from SSF file...")
                self.load_characters()
            logger.info("Setup completed successfully.")
        else:
            logger.info("Setup incomplete. Required paths for JPEXS or SSF2 are missing.")

    def fix_missing_commas(self, json_str):
        # Add commas between hex colors or "transparent" in arrays
        # Match hex colors (0x followed by 6-8 hex digits) or "transparent"
        json_str = re.sub(r'("0x[0-9A-Fa-f]{6,8}"|"transparent")\s+("0x[0-9A-Fa-f]{6,8}"|"transparent")', r'\1,\2', json_str)
        # Match numbers (positive or negative) for other arrays
        json_str = re.sub(r'(\d+)\s+(-\d+)', r'\1,\2', json_str)
        json_str = re.sub(r'(\d+)\s+(\d+)', r'\1,\2', json_str)
        return json_str
    def download_current_costumes(self):
        costumes = [costume for idx, costume in self.all_costumes]
        self.save_costumes_to_file(costumes)

    def download_loaded_costumes(self):
        self.save_costumes_to_file(self.loaded_costumes)

    def save_costumes_to_file(self, costumes):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        try:
            costumes_copy = json.loads(json.dumps(costumes))
            for costume in costumes_copy:
                for key in ["paletteSwap", "paletteSwapPA"]:
                    if key in costume:
                        for subkey in ["colors", "replacements"]:
                            if subkey in costume[key]:
                                costume[key][subkey] = [
                                    int_to_color_str(color_to_int(color))
                                    for color in costume[key][subkey]
                                ]
            json_str = json.dumps(costumes_copy, indent=2)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            messagebox.showinfo("Success", "Costumes saved successfully.")
        except Exception as e:
            self.show_error("Error", f"Failed to save costumes: {str(e)}")

    def edit_loaded_costume(self):
        logger.info("Editing loaded costume...")
        if self.last_selected_listbox == 'costume' and self.costume_listbox.curselection():
            idx = self.costume_listbox.curselection()[0]
            costume = self.all_costumes[idx][1]
            source = 'current'
            image_path = self.get_image_path_for_costume(costume)
            logger.info(f"Editing costume from current list, idx: {idx}, info: {costume.get('info', 'No info')}, image_path: {image_path}")
            # Ensure preview is cached
            self.update_preview()
            AddCostumeWindow(self, self.selected_character.get(), costume_data=costume, image_path=image_path, source=source, current_idx=idx, on_save_callback=self.add_new_costume_to_list, theme=self.themes[self.current_theme.get()], style=self.style)
        elif self.last_selected_listbox == 'loaded' and self.loaded_listbox.curselection():
            idx = self.loaded_listbox.curselection()[0]
            costume = self.loaded_costumes[idx]
            source = 'loaded'
            image_path = self.get_image_path_for_costume(costume)
            logger.info(f"Editing costume from loaded list, idx: {idx}, info: {costume.get('info', 'No info')}, image_path: {image_path}")
            # Ensure preview is cached
            self.update_preview()
            AddCostumeWindow(self, self.selected_character.get(), costume_data=costume, image_path=image_path, source=source, loaded_idx=idx, on_save_callback=self.add_new_costume_to_list, theme=self.themes[self.current_theme.get()], style=self.style)
        else:
            logger.info("No costume selected for editing")
            self.show_error("Error", "Please select a costume to edit.")
        logger.info("Edit loaded costume completed")

    def generate_image_from_preview(self, costume):
        """Generate an image from the preview cache for the given costume."""
        import json
        import hashlib
        logger.info(f"Generating image from preview for costume: {costume.get('info', 'No info')}")
        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()
        
        try:
            # Generate the same hash used in update_preview
            costume_json = json.dumps(costume, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()
            
            if costume_hash not in self.preview_cache:
                logger.info(f"No preview image in cache for costume hash: {costume_hash}")
                return None
            
            image = self.preview_cache[costume_hash]
            info = costume.get('info', 'No Info').replace(' ', '_')
            character_dir = os.path.join(os.getcwd(), "recolors", character)
            if not os.path.exists(character_dir):
                os.makedirs(character_dir)
                logger.info(f"Created directory: {character_dir}")
            
            # Save the image with a unique filename
            image_path = os.path.join(character_dir, f"{info}.png")
            image.save(image_path)
            logger.info(f"Saved generated image to: {image_path}")
            return image_path
        except Exception as e:
            logger.error(f"Error generating image from preview: {str(e)}")
            return None

    def get_image_path_for_costume(self, costume):
        character_dir = os.path.join(os.getcwd(), "recolors", self.selected_character.get())
        logger.info(f"Searching for image in directory: {character_dir}")
        if not os.path.exists(character_dir):
            logger.info(f"Character directory does not exist: {character_dir}")
            return None
        info = costume.get('info', '')
        if not info:
            logger.info(f"No 'info' field in costume: {costume}")
            return None
        filename_part = info.replace(' ', '_')
        logger.info(f"Looking for .png files containing: {filename_part}")
        for file in os.listdir(character_dir):
            if file.endswith(".png"):
                if filename_part in file:
                    path = os.path.join(character_dir, file)
                    if os.path.exists(path):
                        logger.info(f"Found image path: {path}")
                        return path
                    else:
                        logger.info(f"File listed but does not exist: {path}")
                elif file == "EDIT ME.png":
                    logger.info(f"Found EDIT ME.png, but info '{info}' does not match")
        logger.info(f"No image found for costume with info '{info}' in {character_dir}")
        return None

    def open_recolors_directory(self):
        character_dir = os.path.join(os.getcwd(), "recolors", self.selected_character.get())
        if not os.path.exists(character_dir):
            messagebox.showinfo("Info", "No recolors directory found for this character.")
            return
        if platform.system() == "Windows":
            os.startfile(character_dir)
        elif platform.system() == "Darwin":
            subprocess.run(["open", character_dir])
        else:
            subprocess.run(["xdg-open", character_dir])

    def create_main_ui(self):
        logger.info("Creating main UI for SSF2 Costume Injector...")
        try:
            theme = self.themes[self.current_theme.get()]

            # Status frame
            self.status_frame = tk.Frame(self, bg=theme["bg"])
            self.status_frame.pack(fill=tk.X, padx=5, pady=5)
            self.progress_bar = ttk.Progressbar(self.status_frame, mode="determinate", maximum=100, style="TProgressbar")
            self.progress_bar.pack(fill=tk.X, expand=True)
            self.status_label = tk.Label(self.status_frame, text="Ready", fg=theme["fg"], bg=theme["bg"], anchor="center")
            self.status_label.place(in_=self.progress_bar, relx=0.5, rely=0.5, anchor="center")
            self.register_tooltip(self.progress_bar, "Progress indicator and status messages.")

            # Top container (log and buttons)
            self.top_container = tk.Frame(self, bg=theme["bg"])
            self.top_container.pack(fill=tk.X, padx=5, pady=5)

            # Log frame (optional)
            self.log_frame = tk.Frame(self.top_container, bg=theme["bg"])
            if not self.hide_log.get():
                self.log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
                self.log_label = tk.Label(self.log_frame, text="Log:", fg=theme["fg"], bg=theme["bg"])
                self.log_label.pack(anchor="w", pady=5)
                self.log_text = scrolledtext.ScrolledText(self.log_frame, height=6, width=50, state='normal', bg=theme["bg"], fg=theme["fg"])
                self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                sys.stdout = TextRedirector(self.log_text)
                self.register_tooltip(self.log_text, "View logs and status messages.")
                self.log_visible = True
            else:
                self.log_visible = False

            # Button frame
            top_button_frame = tk.Frame(self.top_container, bg=theme["bg"])
            top_button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
            buttons = [
                ("Settings", self.open_settings, "Configure theme and background."),
                ("Help Tooltips", self.toggle_help_mode, "Toggle help tooltips."),
                ("Join Discord", lambda: webbrowser.open("https://discord.gg/xZtTqX4"), "Join the Discord community."),
                ("Create Recolor", lambda: webbrowser.open("https://color-vault.github.io/Color-Vault/colorcreator2.html"), "Create a custom recolor online."),
                ("Submit Bug", self.submit_bug_report, "Submit a bug report.")
            ]
            for text, command, tooltip in buttons:
                button = tk.Button(top_button_frame, text=text, command=command, fg=theme["button_fg"], bg=theme["button_bg"])
                button.pack(side=tk.TOP, padx=5, pady=5, anchor="ne")
                self.register_tooltip(button, tooltip)

            # Character selection frame
            self.char_selection_frame = tk.Frame(self, bg=theme["bg"])
            self.char_selection_frame.pack(fill=tk.X, padx=5)
            tk.Label(self.char_selection_frame, text="Select Character:", fg=theme["fg"], bg=theme["bg"]).pack(anchor="w")
            self.frame_char = tk.Frame(self.char_selection_frame, bg=theme["bg"])
            self.frame_char.pack(fill=tk.X, padx=5)
            self.character_dropdown = tk.OptionMenu(self.frame_char, self.selected_character, *(["Select a Character"] + self.characters))
            self.character_dropdown.config(
                fg=theme.get("fg", "black"),
                bg=theme.get("button_bg", "#f0f0f0"),
                activeforeground=theme.get("fg", "black"),
                activebackground=theme.get("button_bg", "#f0f0f0"),
                width=18,
                relief="flat",
                borderwidth=1,
                state="normal"  # Ensure the dropdown is interactive
            )
            self.character_dropdown["menu"].config(
                fg=theme.get("fg", "black"),
                bg=theme.get("bg", "#d9d9d9")
            )
            self.character_dropdown.pack(side=tk.LEFT, pady=5)
            self.register_tooltip(self.character_dropdown, "Select a character to modify costumes.")
            self.selected_character.trace_add("write", lambda *args: self.toggle_custom_field())
            self.load_costume_button = tk.Button(self.frame_char, text="Load Costume List", command=self.load_costume_list, fg=theme["button_fg"], bg=theme["button_bg"])
            self.load_costume_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.load_costume_button, "View and edit costumes.")
            self.custom_frame = tk.Frame(self.frame_char, bg=theme["bg"])
            tk.Label(self.custom_frame, text="Custom Character Name:", fg=theme["fg"], bg=theme["bg"]).pack(side=tk.LEFT, padx=(10, 5))
            self.custom_entry = tk.Entry(self.custom_frame, textvariable=self.custom_character, width=20)
            self.custom_entry.pack(side=tk.LEFT)
            self.apply_theme()
            logger.info("Main UI created successfully.")
        except Exception as e:
            logger.error(f"Error creating main UI: {str(e)}")
            self.show_error("Error", f"Failed to create main UI: {str(e)}")

    def choose_color(self, color_var):
        """Open a color picker and update the color variable."""
        color = colorchooser.askcolor(title="Choose Color", initialcolor=color_var.get())[1]
        if color:
            color_var.set(color)
            self.apply_colors()

    
    def apply_background_image(self):
        """Apply a custom background image with caching and transparency."""
        logger.info("Applying background image")
        path = self.bg_image_path.get()
        window_width = self.winfo_width() or 1204
        window_height = self.winfo_height() or 712
        current_size = (window_width, window_height)
        transparency = self.bg_transparency.get() / 100.0

        # Check if path, size, or transparency has changed
        cache_key = (path, current_size, transparency)
        if (hasattr(self, 'bg_cache_key') and self.bg_cache_key == cache_key and 
            self.bg_image_cache and hasattr(self, 'bg_label')):
            logger.info("Using cached background image")
            self.bg_label.configure(image=self.bg_photo)
            self.bg_label.lower()
            self.update_idletasks()
            return

        logger.info("Loading new background image")
        if path and os.path.exists(path):
            try:
                img = Image.open(path)
                img = img.resize(current_size, Image.Resampling.LANCZOS)
                if transparency < 1.0:
                    alpha = img.split()[3] if img.mode == 'RGBA' else Image.new('L', img.size, 255)
                    alpha = alpha.point(lambda p: int(p * transparency))
                    img.putalpha(alpha)
                self.bg_photo = ImageTk.PhotoImage(img)
                self.bg_image_cache = img
                self.bg_cache_key = cache_key
                self.last_window_size = current_size
                self.last_transparency = transparency
                if not hasattr(self, 'bg_label'):
                    self.bg_label = tk.Label(self, image=self.bg_photo)
                    self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                    self.bg_label.lower()
                else:
                    self.bg_label.configure(image=self.bg_photo)
                    self.bg_label.lower()
                self.update_idletasks()
                logger.info("Background image applied successfully")
            except Exception as e:
                logger.error(f"Failed to apply background image: {e}")
                self.clear_background_image()
        else:
            logger.info("No valid background image path, clearing background")
            self.clear_background_image()

    def clear_background_image(self):
        """Clear the background image."""
        self.bg_image_cache = None
        self.last_window_size = None
        self.last_transparency = None
        if hasattr(self, 'bg_label'):
            self.bg_label.destroy()
            del self.bg_label
        self.bg_photo = None

    def choose_background_image(self):
        """Open a file dialog to select a background image."""
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.bg_image_path.set(path)
            self.bg_image_cache = None  # Clear cache to force reload
            self.apply_background_image()
            self.save_config()
            logger.info(f"Selected new background image: {path}")

    def open_settings(self):
        logger.info("Opening settings menu to configure theme and background...")
        settings_window = Toplevel(self)
        settings_window.title("Settings")
        settings_window.transient(self)
        settings_window.grab_set()
        settings_window.wm_iconbitmap(resource_path("icon.ico"))
        self.center_toplevel(settings_window, 1000, 700)

        theme_name = self.current_theme.get()
        if theme_name not in self.themes:
            logger.error(f"Invalid theme '{theme_name}', falling back to 'Light'")
            theme_name = "Light"
            self.current_theme.set(theme_name)
            self.config["theme"] = theme_name
            self.save_config()
        theme = self.themes[theme_name]
        settings_window.configure(bg=theme.get("bg", "#d9d9d9"))

        # Theme selection
        tk.Label(settings_window, text="Theme:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        theme_frame = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        theme_frame.pack(fill=tk.X, padx=5)
        theme_menu = tk.OptionMenu(theme_frame, self.current_theme, *self.themes.keys())
        theme_menu.config(fg=theme.get("fg", "black"), bg=theme.get("button_bg", "#f0f0f0"), activeforeground=theme.get("fg", "black"), activebackground=theme.get("button_bg", "#f0f0f0"))
        theme_menu["menu"].config(fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9"))
        theme_menu.pack(side=tk.LEFT)
        tk.Button(theme_frame, text="Apply Theme", command=self.apply_theme, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.LEFT, padx=5)
        tk.Label(theme_frame, text="Background Transparency:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(side=tk.LEFT, padx=5)
        transparency_slider = ttk.Scale(theme_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.bg_transparency, command=lambda _: self.apply_background_image(), style="TScale")
        transparency_slider.pack(side=tk.LEFT, padx=5)
        tk.Label(theme_frame, text="Theme Transparency:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(side=tk.LEFT, padx=5)
        theme_transparency_toggle = tk.Checkbutton(theme_frame, variable=self.theme_transparency, command=self.apply_theme, fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9"))
        theme_transparency_toggle.pack(side=tk.LEFT, padx=5)

        # Background image selection
        tk.Label(settings_window, text="Main Window Background Image:", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        bg_frame = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        bg_frame.pack(fill=tk.X, padx=5)
        tk.Entry(bg_frame, textvariable=self.bg_image_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(bg_frame, text="Browse", command=self.choose_background_image, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT)
        tk.Button(bg_frame, text="Clear", command=self.clear_background_image, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)
        tk.Button(bg_frame, text="Restore Default", command=lambda: self.restore_default_background(), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)

        # Existing settings
        tk.Label(settings_window, text="FFDEC Path (ffdec.jar):", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        frame_ffdec = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        frame_ffdec.pack(fill=tk.X, padx=5)
        ffdec_entry = tk.Entry(frame_ffdec, textvariable=self.ffdec_path, width=50)
        ffdec_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ffdec, text="Browse", command=self.browse_ffdec, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT)
        tk.Button(frame_ffdec, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ffdec_path.get())), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ffdec_entry, "Path to JPEXS Decompiler's ffdec.jar file.")

        tk.Label(settings_window, text="SSF File (e.g., DAT67.ssf):", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        frame_ssf = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        frame_ssf.pack(fill=tk.X, padx=5)
        ssf_entry = tk.Entry(frame_ssf, textvariable=self.ssf_path, width=50)
        ssf_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ssf, text="Browse", command=self.browse_ssf, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT)
        tk.Button(frame_ssf, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ssf_path.get())), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ssf_entry, "Path to SSF2's DAT67.ssf file.")

        tk.Label(settings_window, text="SSF2 Executable (SSF2.exe):", fg=theme.get("fg", "black"), bg=theme.get("bg", "#d9d9d9")).pack(pady=5)
        frame_ssf2 = tk.Frame(settings_window, bg=theme.get("bg", "#d9d9d9"))
        frame_ssf2.pack(fill=tk.X, padx=5)
        ssf2_entry = tk.Entry(frame_ssf2, textvariable=self.ssf2_exe_path, width=50)
        ssf2_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ssf2, text="Browse", command=self.browse_ssf2_exe, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT)
        tk.Button(frame_ssf2, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ssf2_exe_path.get())), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ssf2_entry, "Path to SSF2 executable (SSF2.exe).")

        tk.Button(settings_window, text="Restart Setup", command=self.restart_setup, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="Start Fresh", command=self.load_characters, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="Download All Costumes from Github", command=self.download_all_costumes, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="About", command=self.show_about, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="Check for Updates", command=self.check_for_updates, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="Submit Bug Report", command=self.submit_bug_report, fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
        tk.Button(settings_window, text="Save", command=lambda: self.save_settings(settings_window), fg=theme.get("button_fg", "black"), bg=theme.get("button_bg", "#f0f0f0")).pack(pady=10)
    def submit_bug_report(self):
        """Open Google Form for bug report and prepare log.txt."""
        logger.info("Preparing bug report submission...")
        form_url = "https://forms.gle/kmY4s8bb5954Yjj39"
        
        # Prepare redacted log file
        log_file = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "log.txt")
        bug_report_log = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "bug_report_log.txt")
        
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                # Redact log content
                redacted_log = redact_path(log_content)
                with open(bug_report_log, 'w', encoding='utf-8') as f:
                    f.write(redacted_log)
                logger.info(f"Saved redacted bug report log to: {redact_path(bug_report_log)}")
            else:
                with open(bug_report_log, 'w', encoding='utf-8') as f:
                    f.write("No log file found.")
                logger.warning(f"No log file found at {redact_path(log_file)}, created empty bug report log.")
        except Exception as e:
            logger.error(f"Error preparing bug report log: {e}")
            with open(bug_report_log, 'w', encoding='utf-8') as f:
                f.write(f"Error: Could not read log file ({e})")

        # Show instructions dialog
        dialog = Toplevel(self)
        dialog.title("Submit Bug Report")
        dialog.transient(self)
        dialog.grab_set()
        self.center_toplevel(dialog, 600, 200)
        
        tk.Label(dialog, text="A bug report form will open in your browser. Please:\n"
                             "1. Describe the issue in detail.\n"
                             "2. Upload the file 'bug_report_log.txt' from the application directory.\n"
                             "Note: The log has been redacted, but please review it for sensitive information.").pack(pady=10)
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Open Form", 
                  command=lambda: [webbrowser.open(form_url), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Open Log Directory", 
                  command=lambda: self.open_folder(os.path.dirname(bug_report_log))).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    def show_error(self, title, message):
        """Custom error messagebox with option to submit bug report."""
        logger.error(f"Error displayed: {title} - {message}")
        dialog = Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        self.center_toplevel(dialog, 400, 200)
        
        tk.Label(dialog, text=message, wraplength=350).pack(pady=10)
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="OK", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Submit Bug Report", 
                  command=lambda: [dialog.destroy(), self.submit_bug_report()]).pack(side=tk.LEFT, padx=5)
    def show_about(self):
        about_window = Toplevel(self)
        about_window.title("About")
        about_window.transient(self)
        about_window.grab_set()
        self.center_toplevel(about_window, 400, 150)        
        tk.Label(about_window, text="SSF2 Costume Injector\nVersion: 1.0.6\n\nA tool for injecting custom costumes into Super Smash Flash 2.").pack(pady=20)
        tk.Button(about_window, text="OK", command=about_window.destroy).pack(pady=10)

    def restore_default_background(self):
        """Restore the default background image."""
        self.bg_image_path.set(self.default_bg_image)
        self.apply_background_image()
        self.save_config()
    def restart_setup(self):
        logger.info("Restarting setup process to reconfigure paths...")
        self.setup_completed = False
        self.save_config()
        for widget in self.winfo_children():
            widget.destroy()
        self.ui_initialized = False
        sys.stdout = self.original_stdout
        logger.info("Setup restarted, running setup wizard...")
        self.run_setup()

    def browse_ffdec(self):
        logger.info("Browsing for JPEXS ffdec.jar file...")
        path = filedialog.askopenfilename(filetypes=[("JAR files", "*.jar")])
        if path:
            self.ffdec_path.set(path)
            self.save_config()
            if self.validate_paths() and not self.costume_list_visible:
                logger.info("FFDEC path updated, loading characters...")
                self.load_characters()
            if self.setup_frame:
                self.check_jpexs()
        else:
            logger.info("No FFDEC path selected.")

    def browse_ssf(self):
        logger.info("Browsing for DAT67.ssf file...")
        path = filedialog.askopenfilename(filetypes=[("SSF files", "*.ssf")])
        if path:
            self.ssf_path.set(path)
            self.save_config()
            if self.validate_paths() and not self.costume_list_visible:
                logger.info("SSF path updated, loading characters...")
                self.load_characters()
            if self.setup_frame:
                self.check_ssf2()
        else:
            logger.info("No SSF path selected.")

    def browse_ssf2_exe(self):
        logger.info("Browsing for SSF2.exe file...")
        path = filedialog.askopenfilename(filetypes=[("Executable files", "*.exe")])
        if path:
            self.ssf2_exe_path.set(path)
            self.save_config()
            if self.setup_frame:
                self.check_ssf2()
        else:
            logger.info("No SSF2.exe path selected.")

    def select_ssf2_folder(self):
        logger.info("Selecting SSF2 folder to copy...")
        src_folder = filedialog.askdirectory(title="Select SSF2 Source Folder")
        if not src_folder:
            logger.info("No SSF2 source folder selected.")
            return
        dest_folder = filedialog.askdirectory(title="Select Destination Folder for SSF2")
        if not dest_folder:
            logger.info("No destination folder selected.")
            return
        try:
            dest_dir = os.path.normpath(dest_folder)
            if os.path.exists(dest_dir):
                if not self.suppress_prompts["select_ssf2_folder_confirm"]:
                    dialog = Toplevel(self)
                    dialog.title("Confirm")
                    dialog.transient(self)
                    dialog.grab_set()
                    self.center_toplevel(dialog, 700, 150)
                    tk.Label(dialog, text=f"Directory already exists at {dest_dir}. Overwrite?").pack(pady=10)
                    result = tk.BooleanVar(value=False)
                    suppress = tk.BooleanVar(value=False)
                    button_frame = tk.Frame(dialog)
                    button_frame.pack(pady=10)
                    tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                    tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                    tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
                    self.wait_window(dialog)
                    if suppress.get():
                        self.suppress_prompts["select_ssf2_folder_confirm"] = True
                        self.save_config()
                    if not result.get():
                        logger.info("Copy operation cancelled by user.")
                        return
                else:
                    logger.info(f"Directory already exists at {dest_dir}, overwriting as per user preference.")
            else:
                logger.info(f"Creating destination directory: {dest_dir}")
                os.makedirs(dest_dir)
            shutil.rmtree(dest_dir, ignore_errors=True)
            copy_ssf2_directory(src_folder, dest_dir)
            self.ssf_path.set(os.path.join(dest_dir, "data", "DAT67.ssf"))
            self.ssf2_exe_path.set(os.path.join(dest_dir, "SSF2.exe"))
            self.save_config()
            logger.info(f"SSF2 successfully copied to {dest_dir}")
            if self.setup_frame:
                self.check_ssf2()
        except Exception as e:
            self.show_error("Error", f"Failed to copy SSF2 to {dest_dir}: {str(e)}")
            logger.error(f"Error copying SSF2: {str(e)}")

    def open_folder(self, path):
        logger.info(f"Opening folder in file explorer: {path}")
        if os.path.exists(path):
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            self.show_error("Error", f"Folder does not exist: {path}")
            logger.info(f"Folder does not exist: {path}")

    def register_tooltip(self, widget, text):
        self.tooltips[widget] = text
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def toggle_help_mode(self):
        self.help_mode = not self.help_mode        
        if not self.help_mode:
            self.hide_all_tooltips()

    def show_tooltip(self, event):
        if not self.help_mode:
            return
        widget = event.widget
        if widget in self.tooltips:
            self.hide_all_tooltips()
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tooltip = Toplevel(self)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            label = Label(tooltip, text=self.tooltips[widget], background="yellow", relief="solid", borderwidth=1)
            label.pack()
            self.tooltips_list.append(tooltip)

    def hide_all_tooltips(self):
        for tooltip in self.tooltips_list:
            try:
                if tooltip.winfo_exists():
                    tooltip.destroy()
            except tk.TclError:
                pass
        self.tooltips_list.clear()

    def hide_tooltip(self, event=None):
        self.hide_all_tooltips()

    def set_busy(self, message, progress=0):
        logger.info(f"Setting application to busy state: {message} ({progress}%)")
        if self.ui_initialized:
            self.status_label.config(text=f"{message} ({progress}%)")
            self.progress_bar['value'] = progress
            self.configure(cursor="wait")
            self.load_costume_button.config(state="disabled")
            self.character_dropdown.config(state="disabled")
            self.custom_entry.config(state="disabled")
            self.update()
        else:
            logger.info(f"Busy: {message} ({progress}%)")

    def clear_busy(self):
        logger.info("Clearing busy state and resetting UI...")
        try:
            if self.ui_initialized:
                self.status_label.config(text="Ready")
                self.progress_bar['value'] = 0
                self.configure(cursor="")
                # Ensure interactive widgets are enabled
                if hasattr(self, 'load_costume_button') and self.load_costume_button.winfo_exists():
                    self.load_costume_button.config(state="normal")
                if hasattr(self, 'character_dropdown') and self.character_dropdown.winfo_exists():
                    self.character_dropdown.config(state="normal")  # Ensure dropdown is interactive
                if hasattr(self, 'custom_entry') and self.custom_entry.winfo_exists():
                    self.custom_entry.config(state="normal")
                self.update()
            else:
                logger.info("UI not initialized, skipping busy state reset.")
        except tk.TclError as e:
            logger.warning(f"TclError in clear_busy: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in clear_busy: {str(e)}")

    def toggle_custom_field(self, event=None):
        logger.info("Toggling custom character field...")
        if self.selected_character.get() == "Custom":
            self.custom_frame.pack(side=tk.LEFT, padx=5)
        else:
            self.custom_frame.pack_forget()
            # Load costume list when a valid character is selected
            if self.selected_character.get() != "Select a Character" and self.characters_loaded:
                logger.info(f"Loading costume list for: {self.selected_character.get()}")
                self.load_costume_list()

    def validate_paths(self):
        logger.info("Validating file paths for JPEXS and SSF2...")
        ffdec = self.ffdec_path.get()
        if not ffdec or not os.path.isfile(ffdec) or not ffdec.endswith("ffdec.jar"):
            self.show_error("Error", "Invalid FFDEC path. Please select a valid ffdec.jar file in Settings.")
            return False
        
        ssf = self.ssf_path.get()
        if not ssf or not os.path.isfile(ssf) or not ssf.endswith(".ssf"):
            logger.info("Invalid SSF path: " + str(ssf))
            self.show_error("Error", "Invalid SSF file path. Please select a valid DAT67.ssf file in Settings.")
            return False
        
        # Check if Java is installed
        java_found = False
        try:
            result = subprocess.run(
                ["java", "-version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logger.info(f"Java installed: {result.stderr.strip()}")
            java_found = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.info("Java executable not found in PATH. Checking common Java installation paths...")
            # Check common Java installation paths
            common_java_paths = [
                r"C:\Program Files\Java\jre*\bin\java.exe",
                r"C:\Program Files (x86)\Java\jre*\bin\java.exe",
                r"C:\Program Files\Java\jdk*\bin\java.exe",
                r"C:\Program Files (x86)\Java\jdk*\bin\java.exe",
            ]
            import glob
            for pattern in common_java_paths:
                for java_path in glob.glob(pattern):
                    try:
                        result = subprocess.run(
                            [java_path, "-version"],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        logger.info(f"Java found at {java_path}: {result.stderr.strip()}")
                        java_found = True
                        # Update PATH temporarily for this session
                        os.environ["PATH"] = f"{os.path.dirname(java_path)};{os.environ.get('PATH', '')}"
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                if java_found:
                    break
        
        if not java_found:
            logger.error("Java is not installed or not in PATH")
            # Create custom dialog
            dialog = Toplevel(self)
            dialog.title("Java Not Found")
            dialog.transient(self)
            dialog.grab_set()
            self.center_toplevel(dialog, 400, 200)
            
            tk.Label(
                dialog,
                text="Java is not installed or not in PATH, required for JPEXS Decompiler.\n"
                    "Please download and install Java or add it to your system PATH."
            ).pack(pady=10)
            
            tk.Button(
                dialog,
                text="Download Java",
                command=lambda: [webbrowser.open("https://www.java.com/en/download/"), dialog.destroy()]
            ).pack(pady=5)
            
            tk.Button(
                dialog,
                text="Cancel",
                command=dialog.destroy
            ).pack(pady=5)
            
            self.wait_window(dialog)
            return False
        
        logger.info("All paths and Java installation validated successfully.")
        return True

    def validate_character(self):
        logger.info("Validating selected character for costume loading...")
        character = self.selected_character.get()
        if character == "Select a Character":
            logger.error("Error: No character selected.")
            self.show_error("Error", "Please select a valid character.")
            return False
        if character == "Custom":
            custom_char = self.custom_character.get().strip()
            if not custom_char or not custom_char.isidentifier():
                logger.error("Error: Invalid custom character name: " + str(custom_char))
                self.show_error("Error", "Invalid custom character name. Please enter a valid name.")
                return False
        logger.info("Character validated successfully: " + character)
        return True

    def handle_backup(self, ssf_path):
        logger.info(f"Creating backup for SSF file: {ssf_path}")
        # Derive backup directory from the SSF2 folder
        ssf_dir = os.path.dirname(ssf_path)
        backup_base_dir = os.path.join(ssf_dir, "backup")
        backup_ssf = os.path.join(backup_base_dir, os.path.basename(ssf_path))
        
        try:
            if not os.path.exists(backup_base_dir):
                os.makedirs(backup_base_dir)
                logger.info(f"Created backup directory: {backup_base_dir}")
            if not os.path.exists(backup_ssf):
                shutil.copy2(ssf_path, backup_ssf)
                logger.info(f"Copied original SSF to backup: {backup_ssf}")
            return backup_ssf
        except PermissionError as e:
            logger.info(f"Permission error creating backup: {e}")
            self.show_error("Error", f"Cannot create backup in {backup_base_dir}. Please run the application as administrator or choose a different SSF path.")
            raise
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            self.show_error("Error", f"Failed to create backup: {str(e)}")
            raise

    def load_original(self, character):
        if not self.suppress_prompts["load_original_confirm"]:
            dialog = Toplevel(self)
            dialog.title("Confirm")
            dialog.transient(self)
            dialog.grab_set()
            self.center_toplevel(dialog, 400, 150)
            tk.Label(dialog, text="This will erase the existing costume list for this character and restore the original list from the backup. Proceed?").pack(pady=10)
            result = tk.BooleanVar(value=False)
            suppress = tk.BooleanVar(value=False)
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
            self.wait_window(dialog)
            if suppress.get():
                self.suppress_prompts["load_original_confirm"] = True
                self.save_config()
            if not result.get():
                logger.info("User cancelled Load Original operation.")
                return False
        else:
            logger.info("Proceeding with Load Original operation as per user preference.")

        logger.info("Loading original SSF from backup for current character...")
        if not self.validate_paths():
            logger.error("Error: Invalid SSF path.")
            self.show_error("Error", "Invalid SSF path. Please check your configuration.")
            return False

        backup_ssf = self.ssf_source  # Use the backup path set by handle_backup

        if not os.path.exists(backup_ssf):
            logger.info(f"Backup SSF not found at: {backup_ssf}")
            self.show_error("Error", f"No backup SSF file found at {backup_ssf}.")
            return False

        if not os.access(self.ssf_path.get(), os.W_OK):
            logger.info(f"Cannot write to SSF file: {self.ssf_path.get()}")
            self.show_error("Error", f"Cannot write to SSF file: {self.ssf_path.get()}. Check file permissions.")
            return False

        self.set_busy("Restoring original SSF file", progress=0)
        try:
            shutil.copy2(backup_ssf, self.ssf_path.get())
            logger.info(f"Restored backup SSF from {backup_ssf} to {self.ssf_path.get()}")
            self.set_busy("Restoring original SSF file", progress=25)

            self.temp_swf = os.path.abspath("temp.swf")
            original_as = os.path.abspath(os.path.join("scripts", "Misc.as"))
            if os.path.exists(self.temp_swf):
                os.remove(self.temp_swf)

            logger.info(f"Decompressing SSF file {self.ssf_path.get()} to SWF...")
            decompress_ssf(self.ssf_path.get(), self.temp_swf)
            self.set_busy("Restoring original SSF file", progress=50)

            logger.info(f"Extracting Misc.as from SWF using JPEXS Decompiler at {self.ffdec_jar}...")
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.loaded_misc_as = original_as
            self.set_busy("Restoring original SSF file", progress=75)

            self.load_costume_list_for_character(character)
            messagebox.showinfo("Success", "Successfully restored original costumes for this character.")
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            self.show_error("Error", f"Failed to restore backup: {str(e)}")
            return False
        finally:
            self.clear_busy()

    def convert_color(self, color):
        """Convert a color to a 32-bit integer."""
        return color_to_int(color)

    def update_costume_list(self):
        if not self.costume_list_visible:
            return
        # Store the current selection
        current_selection = self.costume_listbox.curselection()
        selected_idx = current_selection[0] if current_selection else None
        
        self.costume_listbox.delete(0, tk.END)
        for idx, costume in self.all_costumes:
            display_name = self.get_display_name(costume)
            self.costume_listbox.insert(tk.END, display_name)
        
        # Restore the selection if it existed and is still valid
        if selected_idx is not None and selected_idx < len(self.all_costumes):
            self.costume_listbox.select_set(selected_idx)
            self.last_selected_listbox = 'costume'
            self.update_preview()  # Ensure preview updates with the selection

    def update_costume_preview(self):
        self.update_preview()

    def hex_to_int(self, hex_str):
        """Convert a hex string (e.g., 'AARRGGBB' or '#AARRGGBB') to a 32-bit integer."""
        if hex_str.lower() == "transparent":
            return -1
        try:
            hex_str = hex_str.replace('#', '').replace('0x', '')
            if not all(c in "0123456789ABCDEFabcdef" for c in hex_str):
                raise ValueError(f"Invalid hex characters in {hex_str}")
            if len(hex_str) == 6:
                logger.info(f"Warning: Assuming opaque for 6-digit hex {hex_str}")
                return int(hex_str + "FF", 16)
            elif len(hex_str) == 8:
                return int(hex_str, 16)
            raise ValueError(f"Invalid hex string length: {hex_str}")
        except ValueError as e:
            logger.error(f"Error converting hex {hex_str}: {str(e)}")
            return 0xFF000000

    def int_to_hex(self, int_val):
        """Convert a 32-bit integer color to a hex string (e.g., 'AARRGGBB')."""
        if int_val == -1:
            return "transparent"
        int_val = int_val & 0xFFFFFFFF
        return f"0x{int_val:08X}"  # Include "0x" for consistency

    def load_costume_list_for_character(self, character, offset=0, limit=50):
        logger.info(f"Refreshing costume list for character '{character}' (offset: {offset}, limit: {limit})...")
        if not self.characters_loaded:
            logger.error("Error: Please load characters first.")
            self.clear_busy()
            return
        if not self.validate_character():
            self.clear_busy()
            return
        if not self.loaded_misc_as or not os.path.exists(self.loaded_misc_as):
            logger.error("Error: Misc.as not loaded. Please reload characters.")
            self.clear_busy()
            return
        self.set_busy("Refreshing costume list", progress=0)
        self.update()

        try:
            logger.info(f"Extracting costumes for character '{character}' from updated Misc.as...")
            costumes_data = extract_costumes(self.loaded_misc_as, character)
            self.total_costumes = len(costumes_data)
            self.set_busy("Refreshing costume list", progress=50)

            # Store original costumes for comparison
            self.original_costumes = costumes_data.copy()  # Deep copy to preserve original data

            costumes_data = costumes_data[offset:offset + limit]
            self.costume_offset = offset + len(costumes_data)

            self.all_costumes = []
            protected_costumes = []
            editable_costumes = []
            for idx, costume in enumerate(costumes_data):
                if 'team' in costume or 'base' in costume:
                    protected_costumes.append((idx + offset, costume))
                else:
                    editable_costumes.append((idx + offset, costume))

            self.all_costumes = [(idx, costume) for idx, costume in protected_costumes + editable_costumes]
            self.protected_count = len(protected_costumes)
            self.costume_listbox.delete(0, tk.END)
            for idx, costume in self.all_costumes:
                display_name = self.get_display_name(costume)
                self.costume_listbox.insert(tk.END, display_name)
            logger.info(f"Refreshed costume list with {len(self.all_costumes)} costumes for character '{character}'.")
            self.set_busy("Refreshing costume list", progress=100)

            if self.costume_count_label:
                self.costume_count_label.config(text=f"Current Costumes ({self.costume_offset}/{self.total_costumes})")
        except Exception as e:
            logger.error(f"Error refreshing costume list: {str(e)}")
            self.clear_busy()

    def download_all_costumes(self):
        logger.info("Initiating download of all costumes from Github for all available characters...")
        if not messagebox.askyesno("Confirm", "Are you sure you want to download all costumes for all available characters from Github? This will append new costumes to existing lists."):
            logger.info("User cancelled download all costumes operation.")
            return

        if not self.characters_loaded:
            logger.error("Error: Please load characters first.")
            self.show_error("Error", "Please load characters first using 'Start Fresh' in Settings.")
            self.clear_busy()
            return
        if not self.validate_paths():
            logger.error("Error: Invalid paths.")
            self.show_error("Error", "Invalid FFDEC or SSF path. Please check your configuration.")
            self.clear_busy()
            return

        for window in self.winfo_children():
            if isinstance(window, Toplevel) and window.title() == "Settings":
                window.destroy()
        self.focus_set()

        self.set_busy("Downloading all costumes from Github", progress=0)
        try:
            backup_ssf = self.ssf_source

            if not os.path.exists(backup_ssf):
                logger.info(f"Backup SSF not found at: {backup_ssf}")
                self.show_error("Error", f"No backup SSF file found at {backup_ssf}. Please ensure a backup exists.")
                self.clear_busy()
                return

            self.java_path = "java"
            self.ffdec_jar = os.path.abspath(self.ffdec_path.get())
            self.original_ssf = self.ssf_path.get()
            self.ssf_source = backup_ssf
            self.temp_swf = os.path.abspath("temp.swf")
            original_as = os.path.abspath(os.path.join("scripts", "Misc.as"))

            if os.path.exists(self.temp_swf):
                os.remove(self.temp_swf)
            logger.info(f"Decompressing backup SSF file {self.ssf_source} to SWF...")
            decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Downloading all costumes from Github", progress=10)

            logger.info(f"Extracting Misc.as from SWF using JPEXS Decompiler at {self.ffdec_jar}...")
            if not messagebox.askyesno("Confirm", "This operation will use JPEXS Decompiler to extract scripts. Continue?"):
                logger.info("User cancelled JPEXS Decompiler operation.")
                self.clear_busy()
                return
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.loaded_misc_as = original_as
            self.set_busy("Downloading all costumes from Github", progress=20)

            characters = [char for char in self.characters if char != "Custom"]
            updated_characters = []
            total_characters = len(characters)
            if total_characters == 0:
                logger.info("No characters available to process.")
                messagebox.showinfo("Info", "No characters available to download costumes for.")
                self.clear_busy()
                return

            progress_per_character = 60 / total_characters
            current_progress = 20

            for i, character in enumerate(characters):
                self.set_busy(f"Processing costumes for {character}", progress=int(current_progress))
                online_url = f"https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/{character}.as"
                logger.info(f"Checking costumes for character '{character}' at {online_url}")
                if not check_url_exists(online_url):
                    logger.info(f"No costumes available for character '{character}' at {online_url}")
                    current_progress += progress_per_character
                    continue

                new_costumes = load_costumes_from_url(online_url)
                if not new_costumes:
                    logger.info(f"No valid costumes loaded for character '{character}' from {online_url}")
                    current_progress += progress_per_character
                    continue

                existing_costumes = extract_costumes(self.loaded_misc_as, character)
                combined_costumes = existing_costumes + new_costumes
                if len(combined_costumes) == len(existing_costumes):
                    logger.info(f"No new costumes to add for character '{character}'")
                    current_progress += progress_per_character
                    continue

                logger.info(f"Appending {len(new_costumes)} costumes for character '{character}' to existing list...")
                update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, combined_costumes)
                updated_characters.append(character)
                logger.info(f"Successfully appended {len(new_costumes)} costumes for character '{character}'")
                current_progress += progress_per_character

            if not updated_characters:
                logger.info("No characters had valid costumes to download from Github.")
                messagebox.showinfo("Info", "No new costumes were found for any characters on Github.")
                self.clear_busy()
                return

            logger.info(f"Injecting modified Misc.as into SWF using JPEXS Decompiler...")
            modified_swf = os.path.abspath("modified.swf")
            if not messagebox.askyesno("Confirm", "This operation will use JPEXS Decompiler to inject scripts. Continue?"):
                logger.info("User cancelled JPEXS Decompiler operation.")
                self.clear_busy()
                return
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Injecting modified scripts", progress=90)

            logger.info(f"Compressing modified SWF back to SSF file {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Compressing SSF file", progress=100)

            messagebox.showinfo("Success", f"Successfully appended costumes for {', '.join(updated_characters)} from Github.")

            self.cleanup_temp_files([modified_swf])
            self.load_characters()
        except Exception as e:
            logger.error(f"Error downloading costumes: {str(e)}")
            self.show_error("Error", f"Failed to download costumes: {str(e)}")
            self.cleanup_temp_files([modified_swf])
            self.clear_busy()
        finally:
            self.clear_busy()

    def load_characters(self):
        logger.info("Loading characters from SSF file...")
        self.set_busy("Loading characters", progress=0)
        if not self.validate_paths():
            logger.error("Invalid paths, cannot load characters")
            self.clear_busy()
            return

        self.java_path = "java"
        self.ffdec_jar = self.ffdec_path.get()
        self.original_ssf = self.ssf_path.get()
        original_as = os.path.abspath("scripts/misc.as")
        os.makedirs(os.path.dirname(original_as), exist_ok=True)

        try:
            self.set_busy("Loading characters", progress=10)
            logger.info(f"Decompressing {self.original_ssf} to {self.temp_swf}...")
            decompress_ssf(self.original_ssf, self.temp_swf)
            self.set_busy("Loading characters", progress=50)
            if not self.suppress_prompts["jpexs_extract"]:
                dialog = Toplevel(self)
                dialog.title("Confirm")
                dialog.transient(self)
                dialog.grab_set()
                self.center_toplevel(dialog, 400, 150)
                tk.Label(dialog, text="This operation will use JPEXS Decompiler to extract scripts. Continue?").pack(pady=10)
                result = tk.BooleanVar(value=False)
                suppress = tk.BooleanVar(value=False)
                button_frame = tk.Frame(dialog)
                button_frame.pack(pady=10)
                tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
                self.wait_window(dialog)
                if suppress.get():
                    self.suppress_prompts["jpexs_extract"] = True
                    self.save_config()
                if not result.get():
                    logger.info("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            logger.info(f"Extracting Misc.as from {self.temp_swf}...")
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.set_busy("Loading characters", progress=75)
            logger.info(f"Extracting character names from {original_as}...")
            new_characters = extract_character_names(original_as)
            self.characters = sorted(list(set(new_characters + ["Custom"])))
            logger.info(f"Extracted characters: {', '.join(self.characters)}")

            # Update tk.OptionMenu menu
            try:
                if not hasattr(self, 'character_dropdown') or not self.character_dropdown.winfo_exists():
                    logger.error("Character dropdown not initialized or destroyed")
                    self.characters_loaded = False
                    self.clear_busy()
                    return
                self.character_dropdown.config(state="normal")  # Ensure dropdown is interactive
                menu = self.character_dropdown["menu"]
                menu.delete(0, tk.END)
                # Ensure at least default options if characters list is empty
                options = ["Select a Character"] + (self.characters or ["Custom"])
                for char in options:
                    menu.add_command(label=char, command=lambda value=char: self.selected_character.set(value))
                current_selection = self.selected_character.get()
                self.selected_character.set(current_selection if current_selection in self.characters else "Select a Character")
                logger.info(f"Updated character dropdown with options: {', '.join(options)}")
            except tk.TclError as e:
                logger.error(f"TclError updating character dropdown: {str(e)}")
                self.show_error("Error", f"Failed to update character dropdown: {str(e)}")
                self.characters_loaded = False
                self.clear_busy()
                return

            self.characters_loaded = True
            self.ssf_source = self.handle_backup(self.original_ssf)
            self.loaded_misc_as = original_as
            self.set_busy("Loading characters", progress=100)
            self.clear_busy()
        except Exception as e:
            logger.error(f"Error loading characters: {str(e)}")
            self.cleanup_temp_files([original_as])
            self.loaded_misc_as = None
            self.ssf_source = None
            self.java_path = None
            self.ffdec_jar = None
            self.original_ssf = None
            self.temp_swf = None
            self.characters_loaded = False
            self.clear_busy()
        finally:
            self.cleanup_temp_files([self.temp_swf, original_as])

    def cleanup_temp_files(self, files):
        logger.info("Cleaning up temporary files created during operations...")
        scripts_dir = os.path.abspath("scripts")
        for temp_file in files:
            if temp_file is None or temp_file == self.loaded_misc_as:
                continue
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.info(f"Cleaned up temporary file: {temp_file}")
        if os.path.exists(scripts_dir) and not os.listdir(scripts_dir):
            os.rmdir(scripts_dir)
            logger.info(f"Cleaned up empty scripts directory: {scripts_dir}")

    def update_button_states(self, event=None):
        costume_sel = self.costume_listbox.curselection()
        loaded_sel = self.loaded_listbox.curselection()
        remove_sel = self.remove_listbox.curselection()
        
        self.add_new_button.config(state=tk.NORMAL)
        if self.load_online_button:
            self.load_online_button.config(state=tk.NORMAL)
        if self.load_original_button:
            self.load_original_button.config(state=tk.NORMAL)

    def move_up(self):
        sel = self.costume_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        protected_costumes = [i for i, (idx, costume) in enumerate(self.all_costumes) if 'team' in costume or 'base' in costume]
        if idx <= len(protected_costumes):
            return
        self.costume_listbox.delete(idx)
        self.costume_listbox.insert(idx - 1, self.all_costumes[idx][1]['display_name'])
        self.all_costumes[idx], self.all_costumes[idx - 1] = self.all_costumes[idx - 1], self.all_costumes[idx]
        self.costume_listbox.select_set(idx - 1)

    def move_down(self):
        sel = self.costume_listbox.curselection()
        if not sel or sel[0] == len(self.all_costumes) - 1:
            return
        idx = sel[0]
        protected_costumes = [i for i, (idx, costume) in enumerate(self.all_costumes) if 'team' in costume or 'base' in costume]
        if idx < len(protected_costumes):
            return
        self.costume_listbox.delete(idx)
        self.costume_listbox.insert(idx + 1, self.all_costumes[idx][1]['display_name'])
        self.all_costumes[idx], self.all_costumes[idx + 1] = self.all_costumes[idx + 1], self.all_costumes[idx]
        self.costume_listbox.select_set(idx + 1)

    def move_to_trash(self):
        sel = self.costume_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        protected_costumes = [i for i, (idx, costume) in enumerate(self.all_costumes) if 'team' in costume or 'base' in costume]
        if idx < len(protected_costumes):
            return
        costume = self.all_costumes.pop(idx)[1]
        self.remove_listbox.insert(tk.END, costume['display_name'])
        self.costume_listbox.delete(idx)
        for i in range(len(self.all_costumes)):
            self.costume_listbox.delete(i)
            self.costume_listbox.insert(i, self.all_costumes[i][1]['display_name'])
        if len(self.all_costumes) > len(protected_costumes):
            self.costume_listbox.select_set(min(idx, len(self.all_costumes) - 1))

    def apply_colors(self):
        """Apply the selected colors to all relevant widgets."""
        # Set window background
        self.configure(bg=self.window_bg.get())

        # Update all labels
        def update_widget_colors(widget):
            if isinstance(widget, tk.Label):
                try:
                    widget.configure(fg=self.label_fg.get(), bg=self.window_bg.get())
                except tk.TclError:
                    pass
            elif isinstance(widget, tk.Canvas):
                try:
                    widget.configure(bg=self.canvas_bg.get())
                except tk.TclError:
                    pass
            elif isinstance(widget, scrolledtext.ScrolledText):
                try:
                    widget.configure(bg=self.log_text_bg.get(), fg=self.log_text_fg.get())
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                update_widget_colors(child)

        update_widget_colors(self)

        # Specifically update preview canvas if it exists
        if hasattr(self, 'preview_canvas'):
            try:
                self.preview_canvas.configure(bg=self.preview_canvas_bg.get())
            except tk.TclError:
                pass

        # Update status label background to match progress bar
        if hasattr(self, 'status_label') and hasattr(self, 'progress_bar'):
            try:
                self.status_label.configure(bg=self.window_bg.get())
            except tk.TclError:
                pass

    def add_costume(self):
        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()
        # Pass the callback to AddCostumeWindow to handle the new costume
        AddCostumeWindow(self, character, on_save_callback=self.add_new_costume_to_list, theme=self.themes[self.current_theme.get()], style=self.style)

    def add_from_file(self):
        logger.info("Opening file dialog to load costumes from a file...")
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("ActionScript files", "*.as")])
        if not file_path:
            logger.info("No file selected for loading costumes.")
            return
        try:
            logger.info(f"Loading costumes from file: {file_path}")
            new_costumes = load_costumes_from_file(file_path)
            self.loaded_costumes.extend(new_costumes)
            for costume in new_costumes:
                self.loaded_listbox.insert(tk.END, costume['display_name'])
            logger.info(f"Successfully loaded {len(new_costumes)} costumes from file.")
        except Exception as e:
            self.show_error("Error", f"Failed to load costumes from file: {str(e)}")
            logger.error(f"Error loading costumes from file: {str(e)}")

    def add_new_costume_to_list(self, new_costume, source=None, current_idx=None, loaded_idx=None):
        # Handle new costume addition (source is None or not 'current'/'loaded')
        if source not in ['current', 'loaded']:
            display_name = self.get_display_name(new_costume)
            self.all_costumes.append((len(self.all_costumes), new_costume))
            self.costume_listbox.insert(tk.END, display_name)
            self.costume_listbox.select_set(len(self.all_costumes) - 1)
            logger.info(f"Added new costume: {display_name}")
        # Optionally handle editing existing costumes if source is 'current' or 'loaded'
        elif source == 'current' and current_idx is not None:
            self.all_costumes[current_idx] = (current_idx, new_costume)
            self.update_costume_list()
            logger.info(f"Updated costume at index {current_idx}")
        elif source == 'loaded' and loaded_idx is not None:
            self.loaded_costumes[loaded_idx] = new_costume
            self.loaded_listbox.delete(loaded_idx)
            self.loaded_listbox.insert(loaded_idx, self.get_display_name(new_costume))
            logger.info(f"Updated loaded costume at index {loaded_idx}")

    def move_to_current_list(self):
        sel = sorted(self.loaded_listbox.curselection(), reverse=True)
        if not sel:
            return
        for idx in sel:
            costume = self.loaded_costumes.pop(idx)
            self.all_costumes.append((len(self.all_costumes), costume))
            self.loaded_listbox.delete(idx)
            self.costume_listbox.insert(tk.END, costume['display_name'])
        if self.loaded_costumes:
            self.loaded_listbox.select_set(min(sel[0], len(self.loaded_costumes) - 1))

    def load_from_online(self):
        if not self.suppress_prompts["load_from_online_confirm"]:
            dialog = Toplevel(self)
            dialog.title("Confirm")
            dialog.transient(self)
            dialog.grab_set()
            self.center_toplevel(dialog, 400, 150)
            tk.Label(dialog, text="This operation will fetch costumes from an online repository. Continue?").pack(pady=10)
            result = tk.BooleanVar(value=False)
            suppress = tk.BooleanVar(value=False)
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
            self.wait_window(dialog)
            if suppress.get():
                self.suppress_prompts["load_from_online_confirm"] = True
                self.save_config()
            if not result.get():
                logger.info("User cancelled online costume loading operation.")
                return
        else:
            logger.info("Proceeding with online costume loading as per user preference.")   

        try:
            new_costumes = load_costumes_from_url(self.online_url)
            self.loaded_costumes.extend(new_costumes)
            for costume in new_costumes:
                self.loaded_listbox.insert(tk.END, costume['display_name'])
            logger.info(f"Successfully loaded {len(new_costumes)} costumes from online repository.")
        except Exception as e:
            self.show_error("Error", f"Failed to load costumes from online: {str(e)}")
            logger.error(f"Error loading costumes from online: {str(e)}")

    def save_settings(self, settings_window):
        """Save settings and defer window destruction with increased delay."""
        try:
            self.apply_theme()
            self.apply_background_image()
            self.save_config()
            # Increase delay to 200ms to ensure ttkbootstrap completes all style updates
            settings_window.after(300, settings_window.destroy)
        except tk.TclError as e:
            logger.error(f"TclError during save_settings: {str(e)}")
            # Log the error but don't show an error dialog to avoid disrupting user experience
            settings_window.after(300, settings_window.destroy)
    def save_and_play(self, character):
        if not self.suppress_prompts["save_and_play_confirm"]:
            dialog = Toplevel(self)
            dialog.title("Confirm")
            dialog.transient(self)
            dialog.grab_set()
            self.center_toplevel(dialog, 400, 150)
            tk.Label(dialog, text="Save changes and launch SSF2?").pack(pady=10)
            result = tk.BooleanVar(value=False)
            suppress = tk.BooleanVar(value=False)
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
            self.wait_window(dialog)
            if suppress.get():
                self.suppress_prompts["save_and_play_confirm"] = True
                self.save_config()
            if not result.get():
                logger.info("User cancelled save and play operation.")
                return
        else:
            logger.info("Proceeding with save and play operation as per user preference.")

        if not os.access(self.original_ssf, os.W_OK):
            logger.info(f"Cannot write to SSF file: {self.original_ssf}")
            self.show_error("Error", f"Cannot write to SSF file: {self.original_ssf}. Check file permissions.")
            return
        self.set_busy("Saving changes and launching SSF2", progress=0)
        modified_swf = os.path.abspath("modified.swf")
        try:
            costumes_to_save = [costume for idx, costume in self.all_costumes]
            logger.info(f"Updating costumes for character '{character}' in Misc.as...")
            update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, costumes_to_save)
            self.set_busy("Saving changes and launching SSF2", progress=33)
            if not os.path.exists(self.temp_swf):
                logger.info(f"Decompressing SSF file {self.ssf_source} to SWF...")
                decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Saving changes and launching SSF2", progress=50)
            logger.info(f"Injecting modified Misc.as into SWF using JPEXS Decompiler...")
            if not self.suppress_prompts["jpexs_inject"]:
                dialog = Toplevel(self)
                dialog.title("Confirm")
                dialog.transient(self)
                dialog.grab_set()
                self.center_toplevel(dialog, 400, 150)
                tk.Label(dialog, text="This operation will use JPEXS Decompiler to inject scripts. Continue?").pack(pady=10)
                result = tk.BooleanVar(value=False)
                suppress = tk.BooleanVar(value=False)
                button_frame = tk.Frame(dialog)
                button_frame.pack(pady=10)
                tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
                self.wait_window(dialog)
                if suppress.get():
                    self.suppress_prompts["jpexs_inject"] = True
                    self.save_config()
                if not result.get():
                    logger.info("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            else:
                logger.info("Proceeding with JPEXS Decompiler injection as per user preference.")
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Saving changes and launching SSF2", progress=75)
            logger.info(f"Compressing modified SWF back to SSF file {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Saving changes and launching SSF2", progress=90)
            logger.info(f"Launching SSF2 executable at {self.ssf2_exe_path.get()}...")
            if not self.suppress_prompts["ssf2_launch"]:
                dialog = Toplevel(self)
                dialog.title("Confirm")
                dialog.transient(self)
                dialog.grab_set()
                self.center_toplevel(dialog, 400, 150)
                tk.Label(dialog, text="This operation will launch SSF2. Continue?").pack(pady=10)
                result = tk.BooleanVar(value=False)
                suppress = tk.BooleanVar(value=False)
                button_frame = tk.Frame(dialog)
                button_frame.pack(pady=10)
                tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
                self.wait_window(dialog)
                if suppress.get():
                    self.suppress_prompts["ssf2_launch"] = True
                    self.save_config()
                if not result.get():
                    logger.info("User cancelled SSF2 launch operation.")
                    self.clear_busy()
                    return
            else:
                logger.info("Proceeding with SSF2 launch as per user preference.")
            launch_ssf2(self.ssf2_exe_path.get())
            self.set_busy("Saving changes and launching SSF2", progress=100)
            messagebox.showinfo("Success", f"Updated costumes for {character} and launched SSF2.")
            self.hide_costume_list()
            self.clear_busy()
        except Exception as e:
            logger.error(f"Error saving or launching: {str(e)}")
            self.show_error("Error", f"Failed to save or launch SSF2: {str(e)}")
            self.clear_busy()
        finally:
            self.cleanup_temp_files([modified_swf])

    def load_costume_list(self):
        logger.info("Loading costume list for the selected character...")
        if not self.characters_loaded:
            logger.error("Error: Please load characters first.")
            self.clear_busy()
            return
        if not self.validate_character():
            self.clear_busy()
            return
        if not self.loaded_misc_as or not os.path.exists(self.loaded_misc_as):
            logger.error("Error: Misc.as not loaded. Please reload characters.")
            self.clear_busy()
            return

        self.set_busy("Loading costume list", progress=0)
        self.update()

        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()

        try:
            logger.info(f"Extracting costumes for character '{character}'...")
            costumes_data = extract_costumes(self.loaded_misc_as, character)
            self.total_costumes = len(costumes_data)
            self.costume_offset = 0
            self.set_busy("Loading costume list", progress=50)

            costumes_data = costumes_data[:50]
            self.costume_offset = len(costumes_data)

            protected_costumes = []
            editable_costumes = []
            for idx, costume in enumerate(costumes_data):
                if 'team' in costume or 'base' in costume:
                    protected_costumes.append((idx, costume))
                else:
                    editable_costumes.append((idx, costume))

            theme = self.themes[self.current_theme.get()]

            # Hide character selection
            self.char_selection_frame.pack_forget()
            if hasattr(self, 'costume_list_frame'):
                self.costume_list_frame.pack_forget()
            self.costume_list_frame = tk.Frame(self, bg=theme["bg"])
            self.costume_list_visible = True
            logger.info("costume list visible")

            # Header frame
            header_frame = tk.Frame(self.costume_list_frame, bg=theme["bg"])
            header_frame.pack(fill=tk.X, padx=5, pady=5)

            self.back_button = tk.Button(header_frame, text="Back", command=self.hide_costume_list, font=("Arial", 12), width=10, height=2, fg=theme["button_fg"], bg=theme["button_bg"])
            self.back_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.back_button, "Return to character selection.")

            costumes_label = tk.Label(header_frame, text=f"Costumes for {character}", font=("Arial", 14), fg=theme["fg"], bg=theme["bg"])
            costumes_label.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(costumes_label, "List of costumes for the selected character.")

            main_frame = tk.Frame(self.costume_list_frame, bg=theme["bg"])
            main_frame.pack(fill=tk.BOTH, expand=True)

            left_panel = tk.Frame(main_frame, bg=theme["bg"])
            left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            right_panel = tk.Frame(main_frame, bg=theme["bg"])
            right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            listbox_frame = tk.Frame(left_panel, bg=theme["bg"])
            listbox_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            self.costume_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED, fg=theme["fg"], bg=theme["bg"])
            self.costume_listbox.grid(row=1, column=0, padx=5, sticky="nsew")
            tk.Button(listbox_frame, text="Download Current", command=self.download_current_costumes, fg=theme["button_fg"], bg=theme["button_bg"]).grid(row=2, column=0, pady=5)

            tk.Label(listbox_frame, text="Loaded Costumes", fg=theme["fg"], bg=theme["bg"]).grid(row=0, column=1, padx=5)
            self.loaded_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED, fg=theme["fg"], bg=theme["bg"])
            self.loaded_listbox.grid(row=1, column=1, padx=5, sticky="nsew")
            tk.Button(listbox_frame, text="Download Loaded", command=self.download_loaded_costumes, fg=theme["button_fg"], bg=theme["button_bg"]).grid(row=2, column=1, pady=5)

            tk.Label(listbox_frame, text="For Removal", fg=theme["fg"], bg=theme["bg"]).grid(row=0, column=2, padx=5)
            self.remove_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED, fg=theme["fg"], bg=theme["bg"])
            self.remove_listbox.grid(row=1, column=2, padx=5, sticky="nsew")

            listbox_frame.grid_columnconfigure(0, weight=1)
            listbox_frame.grid_columnconfigure(1, weight=1)
            listbox_frame.grid_columnconfigure(2, weight=1)
            listbox_frame.grid_rowconfigure(1, weight=1)

            self.all_costumes = [(idx, costume) for idx, costume in protected_costumes + editable_costumes]
            for idx, costume in self.all_costumes:
                display_name = self.get_display_name(costume)
                self.costume_listbox.insert(tk.END, display_name)

            self.loaded_costumes = []

            # Costume preview section
            preview_header_frame = tk.Frame(right_panel, bg=theme["bg"])
            preview_header_frame.pack(fill=tk.X, pady=10)

            tk.Label(preview_header_frame, text="Costume Preview", font=("Arial", 14), fg=theme["fg"], bg=theme["bg"]).pack(side=tk.LEFT, padx=5)
            tk.Button(preview_header_frame, text="Download Code and Image for Selected", command=lambda: self.download_selected_costume(character), fg=theme["button_fg"], bg=theme["button_bg"]).pack(side=tk.LEFT, padx=5)
            self.register_tooltip(tk.Button(preview_header_frame, text="Download Code and Image for Selected"), "Download the selected costume's JSON code and preview image to a folder named after the character.")

            self.preview_canvas = tk.Canvas(right_panel, width=600, height=400, bg=theme["canvas_bg"], highlightthickness=1, highlightbackground="black")
            self.preview_canvas.pack(pady=10, padx=10)
            self.register_tooltip(self.preview_canvas, "Preview of the selected costume's recolored sheet.")
            self.preview_label = tk.Label(right_panel, text="Select a costume to preview", fg=theme["fg"], bg=theme["bg"])
            self.preview_label.pack(pady=5)

            # Button frame
            self.button_frame = tk.Frame(left_panel, bg=theme["bg"])
            self.button_frame.pack(pady=5, fill=tk.X)

            buttons = [
                ("Move Up", self.move_up, "Move selected costumes up in the list."),
                ("Move Down", self.move_down, "Move selected costumes down in the list."),
                ("Move to Trash", self.move_to_trash, "Move selected costumes to the removal list."),
                ("Add New", self.add_costume, "Create a new costume."),
                ("Add from File", self.add_from_file, "Load costumes from a .txt or .as file."),
                ("Move to Current List", self.move_to_current_list, "Add selected loaded costumes to the current list.")
            ]

            current_row = tk.Frame(self.button_frame, bg=theme["bg"])
            current_row.pack(side=tk.TOP, fill=tk.X, padx=5)
            max_width = 900
            current_width = 0

            for text, command, tooltip in buttons:
                button_width = len(text) * 10 + 20
                if current_width + button_width + 10 > max_width:
                    current_row = tk.Frame(self.button_frame, bg=theme["bg"])
                    current_row.pack(side=tk.TOP, fill=tk.X, padx=5)
                    current_width = 0

                button = tk.Button(current_row, text=text, command=command, fg=theme["button_fg"], bg=theme["button_bg"])
                button.pack(side=tk.LEFT, padx=5, pady=5)
                self.register_tooltip(button, tooltip)
                current_width += button_width + 10

            pagination_frame = tk.Frame(left_panel)
            pagination_frame.pack(pady=5)
            if self.costume_offset < self.total_costumes:
                tk.Button(pagination_frame, text="Load More (50)", command=lambda: self.load_more_costumes(character)).pack(side=tk.LEFT, padx=5)
                tk.Button(pagination_frame, text="Load All", command=lambda: self.load_all_costumes(character)).pack(side=tk.LEFT, padx=5)

            self.online_button_frame = tk.Frame(left_panel)
            self.online_button_frame.pack(pady=5)

            self.online_url = f"https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/{character}.as"
            if check_url_exists(self.online_url):
                self.load_online_button = tk.Button(self.online_button_frame, text="Load Costumes from Online", width=25, command=self.load_from_online)
                self.load_online_button.pack(side=tk.LEFT, padx=5)
                self.register_tooltip(self.load_online_button, "Load costumes from an online repository.")
            else:
                self.load_online_button = None
                logger.info(f"No online costumes available for character '{character}' at {self.online_url}")

            backup_ssf = self.ssf_source
            if os.path.exists(backup_ssf):
                self.load_original_button = tk.Button(self.online_button_frame, text="Load Original", width=25, command=lambda: self.load_original(character))
                self.load_original_button.pack(side=tk.LEFT, padx=5)
                self.register_tooltip(self.load_original_button, "Restore the original costume list for this character from the backup.")
            else:
                self.load_original_button = None
                logger.info(f"No backup file found at {backup_ssf}, 'Load Original' button not added.")

            self.save_button = tk.Button(left_panel, text="Save Changes", command=lambda: self.save_changes(character))
            self.save_button.pack(side=tk.LEFT, padx=5, pady=5)
            self.register_tooltip(self.save_button, "Save costume changes to the SSF file.")

            self.save_play_button = tk.Button(left_panel, text="Save and Play", command=lambda: self.save_and_play(character))
            self.save_play_button.pack(side=tk.LEFT, padx=5, pady=5)
            self.register_tooltip(self.save_play_button, "Save costume changes and launch SSF2.")

            self.update_button_states()

            self.costume_list_frame.pack(fill=tk.BOTH, expand=True)
            
            # Apply theme styles to new widgets
            try:
                self.update_widget_colors(self.costume_list_frame, theme)
            except tk.TclError as e:
                logger.warning(f"Non-fatal error applying theme to costume list widgets: {e}")

            self.set_busy("Loading costume list", progress=100)
            self.clear_busy()

            if self.all_costumes:
                select_idx = self.protected_count - 1 if self.protected_count < len(self.all_costumes) else 0
                self.costume_listbox.select_set(select_idx)
                self.last_selected_listbox = 'costume'
                self.debounce_preview_update()
        
            # Update bindings
            self.costume_listbox.bind("<ButtonRelease-1>", lambda event: [setattr(self, 'last_selected_listbox', 'costume'), self.debounce_preview_update()])
            self.costume_listbox.bind("<<ListboxSelect>>", lambda event: [setattr(self, 'last_selected_listbox', 'costume'), self.debounce_preview_update()])
            self.loaded_listbox.bind("<ButtonRelease-1>", lambda event: [setattr(self, 'last_selected_listbox', 'loaded'), self.update_button_states(), self.debounce_preview_update() if self.loaded_listbox.curselection() else None])
            self.loaded_listbox.bind("<<ListboxSelect>>", lambda event: [setattr(self, 'last_selected_listbox', 'loaded'), self.update_button_states(), self.debounce_preview_update() if self.loaded_listbox.curselection() else None])
            self.remove_listbox.bind("<ButtonRelease-1>", lambda event: self.update_button_states())

            if self.costume_listbox.curselection():
                self.debounce_preview_update()

        except tk.TclError as e:
            logger.error(f"TclError in load_costume_list: {str(e)}")
            self.hide_costume_list()
            self.clear_busy()
        except Exception as e:
            logger.error(f"Unexpected error in load_costume_list: {str(e)}")
            self.hide_costume_list()
            self.clear_busy()

    def download_selected_costume(self, character):
        import re
        import hashlib
        from PIL import Image, ImageTk

        if self.last_selected_listbox == 'costume' and self.costume_listbox.curselection():
            idx = self.costume_listbox.curselection()[0]
            costume = self.all_costumes[idx][1] if idx < len(self.all_costumes) else None
        elif self.last_selected_listbox == 'loaded' and self.loaded_listbox.curselection():
            idx = self.loaded_listbox.curselection()[0]
            costume = self.loaded_costumes[idx] if idx < len(self.loaded_costumes) else None
        else:
            self.show_error("Error", "Please select a costume to download.")
            return

        if not costume:
            self.show_error("Error", "No costume selected.")
            return

        # Sanitize filename from info key
        info = costume.get("info", "NoInfo")
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', info)
        safe_filename = safe_filename.replace(' ', '_').strip('_')
        if not safe_filename:
            safe_filename = "UnnamedCostume"

        # Create character folder
        character_dir = os.path.join(os.getcwd(), character)
        os.makedirs(character_dir, exist_ok=True)

        # Generate costume JSON
        costume_json = json.dumps(costume, indent=2)
        costume_json = self.fix_missing_commas(costume_json)
        costume_hash = hashlib.md5(costume_json.encode()).hexdigest()

        # Save JSON to .txt file
        json_filename = os.path.join(character_dir, f"{safe_filename}.txt")
        try:
            with open(json_filename, "w", encoding="utf-8") as f:
                f.write(costume_json)
            logger.info(f"Saved JSON to {json_filename}")
        except Exception as e:
            self.show_error("Error", f"Failed to save JSON file: {str(e)}")
            return

        # Generate full-resolution image
        image = self.generate_full_resolution_image(character, costume)
        if not image:
            messagebox.showwarning("Warning", f"No preview image available for this costume. JSON saved to {json_filename}")
            return

        # Save full-resolution image
        image_filename = os.path.join(character_dir, f"{safe_filename}.png")
        try:
            image.save(image_filename, quality=100)
            logger.info(f"Saved full-resolution image to {image_filename}")
            # Show custom success dialog
            dialog = Toplevel(self)
            dialog.title("Success")
            dialog.transient(self)
            dialog.grab_set()
            self.center_toplevel(dialog, 400, 150)
            tk.Label(dialog, text=f"Downloaded JSON and image to {character_dir}", wraplength=350).pack(pady=10)
            button_frame = tk.Frame(dialog)
            button_frame.pack(pady=10)
            tk.Button(button_frame, text="Open Directory", command=lambda: [self.open_folder(character_dir), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="OK", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        except Exception as e:
            self.show_error("Error", f"Failed to save image file: {str(e)}")
            return

    def generate_full_resolution_image(self, character, costume):
        import hashlib
        import requests
        from io import BytesIO
        from PIL import Image

        palette_swap = costume.get("paletteSwap")
        palette_swap_pa = costume.get("paletteSwapPA")
        if not (palette_swap and palette_swap_pa and
                "colors" in palette_swap and "replacements" in palette_swap and
                "colors" in palette_swap_pa and "replacements" in palette_swap_pa):
            logger.info("Invalid costume data for full-resolution image generation")
            return None

        normalized_character = character.lower().replace(" ", "").replace("(sandbox)", "")
        image_url = self.character_to_url.get(normalized_character)
        if not image_url:
            logger.info(f"No preview URL for character {character}")
            return None

        try:
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_file = os.path.join(self.image_cache_dir, f"{url_hash}.png")
            if os.path.exists(cache_file):
                image = Image.open(cache_file).convert("RGBA")
            else:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                image.save(cache_file)

            pixels = image.load()
            width, height = image.size
            color_map_swap = {self.convert_color(orig): self.convert_color(repl)
                            for orig, repl in zip(palette_swap["colors"], palette_swap["replacements"])}
            color_map_swap_pa = {self.convert_color(orig): self.convert_color(repl)
                                for orig, repl in zip(palette_swap_pa["colors"], palette_swap_pa["replacements"])}

            def colors_are_close(color1, color2, tolerance=0):
                if color1 == 0 or color2 == 0:
                    return color1 == color2
                r1, g1, b1, a1 = (color1 >> 16) & 255, (color1 >> 8) & 255, color1 & 255, (color1 >> 24) & 255
                r2, g2, b2, a2 = (color2 >> 16) & 255, (color2 >> 8) & 255, color2 & 255, (color2 >> 24) & 255
                return (abs(r1 - r2) <= tolerance and
                        abs(g1 - g2) <= tolerance and
                        abs(b1 - b2) <= tolerance and
                        abs(a1 - a2) <= tolerance)

            cache_swap = {}
            cache_swap_pa = {}

            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]
                    pixel_int = 0 if a == 0 else ((a << 24) | (r << 16) | (g << 8) | b)

                    if pixel_int in cache_swap:
                        new_pixel_int = cache_swap[pixel_int]
                    else:
                        if pixel_int in color_map_swap:
                            new_pixel_int = color_map_swap[pixel_int]
                        else:
                            for orig_int in color_map_swap:
                                if colors_are_close(pixel_int, orig_int):
                                    new_pixel_int = color_map_swap[orig_int]
                                    break
                            else:
                                new_pixel_int = pixel_int
                        cache_swap[pixel_int] = new_pixel_int

                    if new_pixel_int == 0:
                        pixels[x, y] = (0, 0, 0, 0)
                        continue
                    r = (new_pixel_int >> 16) & 255
                    g = (new_pixel_int >> 8) & 255
                    b = new_pixel_int & 255
                    a = (new_pixel_int >> 24) & 255
                    pixels[x, y] = (r, g, b, a)

                    pixel_int = ((a << 24) | (r << 16) | (g << 8) | b)
                    if pixel_int in cache_swap_pa:
                        new_pixel_int = cache_swap_pa[pixel_int]
                    else:
                        if pixel_int in color_map_swap_pa:
                            new_pixel_int = color_map_swap_pa[pixel_int]
                        else:
                            for orig_int in color_map_swap_pa:
                                if colors_are_close(pixel_int, orig_int):
                                    new_pixel_int = color_map_swap_pa[orig_int]
                                    break
                            else:
                                new_pixel_int = pixel_int
                        cache_swap_pa[pixel_int] = new_pixel_int

                    if new_pixel_int == 0:
                        pixels[x, y] = (0, 0, 0, 0)
                    else:
                        r = (new_pixel_int >> 16) & 255
                        g = (new_pixel_int >> 8) & 255
                        b = new_pixel_int & 255
                        a = (new_pixel_int >> 24) & 255
                        pixels[x, y] = (r, g, b, a)

            return image
        except Exception as e:
            logger.error(f"Error generating full-resolution image: {str(e)}")
            return None
    def generate_preview_image(self, character, costume):
        import hashlib
        import requests
        from io import BytesIO
        from PIL import Image

        palette_swap = costume.get("paletteSwap")
        palette_swap_pa = costume.get("paletteSwapPA")
        if not (palette_swap and palette_swap_pa and
                "colors" in palette_swap and "replacements" in palette_swap and
                "colors" in palette_swap_pa and "replacements" in palette_swap_pa):
            logger.info("Invalid costume data for preview generation")
            return None

        for key in ["colors", "replacements"]:
            for section in [palette_swap, palette_swap_pa]:
                for color in section.get(key, []):
                    try:
                        color_int = color_to_int(color)
                        if color_int == 0 or (0 <= color_int <= 0xFFFFFFFF):
                            continue
                        raise ValueError(f"Invalid color value: {color}")
                    except Exception as e:
                        logger.info(f"Invalid color in palette: {color} ({str(e)})")
                        self.show_error("Error", f"Invalid color in palette: {color}")
                        return None

        normalized_character = character.lower().replace(" ", "").replace("(sandbox)", "")
        image_url = self.character_to_url.get(normalized_character)
        if not image_url:
            logger.info(f"No preview URL for character {character}")
            return None

        try:
            costume_json = json.dumps(costume, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()

            if costume_hash in self.preview_cache:
                return self.preview_cache[costume_hash]

            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_file = os.path.join(self.image_cache_dir, f"{url_hash}.png")
            if os.path.exists(cache_file):
                image = Image.open(cache_file).convert("RGBA")
            else:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                image.save(cache_file)

            pixels = image.load()
            width, height = image.size
            color_map_swap = {self.convert_color(orig): self.convert_color(repl)
                            for orig, repl in zip(palette_swap["colors"], palette_swap["replacements"])}
            color_map_swap_pa = {self.convert_color(orig): self.convert_color(repl)
                                for orig, repl in zip(palette_swap_pa["colors"], palette_swap_pa["replacements"])}

            def colors_are_close(color1, color2, tolerance=5):
                if color1 == 0 or color2 == 0:
                    return color1 == color2
                r1, g1, b1, a1 = (color1 >> 16) & 255, (color1 >> 8) & 255, color1 & 255, (color1 >> 24) & 255
                r2, g2, b2, a2 = (color2 >> 16) & 255, (color2 >> 8) & 255, color2 & 255, (color2 >> 24) & 255
                return (abs(r1 - r2) <= tolerance and
                        abs(g1 - g2) <= tolerance and
                        abs(b1 - b2) <= tolerance and
                        abs(a1 - a2) <= tolerance)

            cache_swap = {}
            cache_swap_pa = {}

            for y in range(height):
                for x in range(width):
                    r, g, b, a = pixels[x, y]
                    pixel_int = 0 if a == 0 else ((a << 24) | (r << 16) | (g << 8) | b)

                    if pixel_int in cache_swap:
                        new_pixel_int = cache_swap[pixel_int]
                    else:
                        if pixel_int in color_map_swap:
                            new_pixel_int = color_map_swap[pixel_int]
                        else:
                            for orig_int in color_map_swap:
                                if colors_are_close(pixel_int, orig_int):
                                    new_pixel_int = color_map_swap[orig_int]
                                    break
                            else:
                                new_pixel_int = pixel_int
                        cache_swap[pixel_int] = new_pixel_int

                    if new_pixel_int == 0:
                        pixels[x, y] = (0, 0, 0, 0)
                        continue
                    r = (new_pixel_int >> 16) & 255
                    g = (new_pixel_int >> 8) & 255
                    b = new_pixel_int & 255
                    a = (new_pixel_int >> 24) & 255
                    pixels[x, y] = (r, g, b, a)

                    pixel_int = 0 if a == 0 else ((a << 24) | (r << 16) | (g << 8) | b)
                    if pixel_int in cache_swap_pa:
                        new_pixel_int = cache_swap_pa[pixel_int]
                    else:
                        if pixel_int in color_map_swap_pa:
                            new_pixel_int = color_map_swap_pa[pixel_int]
                        else:
                            for orig_int in color_map_swap_pa:
                                if colors_are_close(pixel_int, orig_int):
                                    new_pixel_int = color_map_swap_pa[orig_int]
                                    break
                            else:
                                new_pixel_int = pixel_int
                        cache_swap_pa[pixel_int] = new_pixel_int

                    if new_pixel_int == 0:
                        pixels[x, y] = (0, 0, 0, 0)
                    else:
                        r = (new_pixel_int >> 16) & 255
                        g = (new_pixel_int >> 8) & 255
                        b = new_pixel_int & 255
                        a = (new_pixel_int >> 24) & 255
                        pixels[x, y] = (r, g, b, a)

            image.thumbnail((600, 400), Image.Resampling.LANCZOS)
            self.preview_cache[costume_hash] = image
            return image
        except Exception as e:
            logger.error(f"Error generating preview image: {str(e)}")
            return None
    def deferred_init(self):
        """Run non-critical initialization tasks after UI is rendered."""
        logger.info("Running deferred initialization...")
        self.character_to_url = self.load_url_mappings()
        if self.AUTO_UPDATE_CHECK:
            self.check_for_updates()
    def debounce_preview_update(self):
        if self.preview_debounce_timer:
            self.after_cancel(self.preview_debounce_timer)
        self.preview_debounce_timer = self.after(self.preview_debounce_delay, self.update_preview)

    def update_preview(self):
        logger.info(f"Updating preview, last_selected_listbox: {self.last_selected_listbox}")
        if not hasattr(self, 'preview_canvas') or not hasattr(self, 'preview_label'):
            logger.error("Error: Preview canvas or label not defined.")
            return

        if self.last_selected_listbox == 'costume' and self.costume_listbox.curselection():
            idx = self.costume_listbox.curselection()[0]
            costume = self.all_costumes[idx][1] if idx < len(self.all_costumes) else None
            logger.info(f"Selected costume index: {idx}, costume: {costume.get('info', 'No info') if costume else None}")
        elif self.last_selected_listbox == 'loaded' and self.loaded_listbox.curselection():
            idx = self.loaded_listbox.curselection()[0]
            costume = self.loaded_costumes[idx] if idx < len(self.loaded_costumes) else None
            logger.info(f"Selected loaded costume index: {idx}, costume: {costume.get('info', 'No info') if costume else None}")
        else:
            costume = None
            logger.info("No costume selected for preview")

        if not costume:
            self.preview_label.config(text="Select a costume to preview")
            self.preview_canvas.delete("all")
            self.preview_canvas.config(bg="#808080")
            return

        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()
        logger.info(f"Character for preview: {character}")

        palette_swap = costume.get("paletteSwap")
        palette_swap_pa = costume.get("paletteSwapPA")
        if not (palette_swap and palette_swap_pa and
                "colors" in palette_swap and "replacements" in palette_swap and
                "colors" in palette_swap_pa and "replacements" in palette_swap_pa):
            self.preview_label.config(text="Invalid costume data")
            self.preview_canvas.delete("all")
            self.preview_canvas.config(bg="#808080")
            logger.error("Invalid costume data: missing paletteSwap or paletteSwapPA")
            return

        normalized_character = character.lower().replace(" ", "").replace("(sandbox)", "")
        image_url = self.character_to_url.get(normalized_character)
        if not image_url:
            self.preview_label.config(text=f"No preview for {character}")
            self.preview_canvas.delete("all")
            self.preview_canvas.config(bg="#808080")
            logger.error(f"No preview URL for character {character}")
            return

        try:
            costume_json = json.dumps(costume, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()
            logger.info(f"Costume hash: {costume_hash}")

            if costume_hash in self.preview_cache:
                image = self.preview_cache[costume_hash]
                logger.info("Using cached preview image")
            else:
                logger.info("Generating new preview image")
                url_hash = hashlib.md5(image_url.encode()).hexdigest()
                cache_file = os.path.join(self.image_cache_dir, f"{url_hash}.png")
                if os.path.exists(cache_file):
                    image = Image.open(cache_file).convert("RGBA")
                else:
                    response = requests.get(image_url, stream=True)
                    response.raise_for_status()
                    image = Image.open(BytesIO(response.content)).convert("RGBA")
                    image.save(cache_file)

                pixels = image.load()
                width, height = image.size
                color_map = {}
                for orig, repl in zip(palette_swap["colors"], palette_swap["replacements"]):
                    orig_int = color_to_int(orig)
                    repl_int = color_to_int(repl)
                    if orig_int != repl_int:
                        color_map[orig_int] = repl_int
                for orig, repl in zip(palette_swap_pa["colors"], palette_swap_pa["replacements"]):
                    orig_int = color_to_int(orig)
                    repl_int = color_to_int(repl)
                    if orig_int != repl_int:
                        color_map[orig_int] = repl_int

                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        color = 0 if a == 0 else ((a << 24) | (r << 16) | (g << 8) | b)
                        if color in color_map:
                            new_color = color_map[color]
                            if new_color == 0:
                                pixels[x, y] = (0, 0, 0, 0)
                            else:
                                pixels[x, y] = (
                                    (new_color >> 16) & 255,
                                    (new_color >> 8) & 255,
                                    new_color & 255,
                                    (new_color >> 24) & 255
                                )

                image.thumbnail((600, 400), Image.Resampling.LANCZOS)
                self.preview_cache[costume_hash] = image

            self.preview_canvas.delete("all")
            self.preview_canvas.config(bg="#808080")
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_canvas.create_image((600 - image.width) // 2, (400 - image.height) // 2,
                                            anchor="nw", image=self.preview_photo)
            self.preview_label.config(text="")
            logger.info("Preview updated successfully.")
        except Exception as e:
            logger.error(f"Error updating preview: {str(e)}")
            self.preview_label.config(text="Failed to load preview")
            self.preview_canvas.delete("all")
            self.preview_canvas.config(bg="#808080")

    def load_more_costumes(self, character):
        logger.info(f"Loading next 50 costumes for character '{character}'...")
        self.load_costume_list_for_character(character, offset=self.costume_offset, limit=50)

    def load_all_costumes(self, character):
        logger.info(f"Loading all costumes for character '{character}'...")
        self.load_costume_list_for_character(character, offset=0, limit=self.total_costumes)

    def save_changes(self, character):
        logger.info("Saving costume changes...")
        if not os.access(self.original_ssf, os.W_OK):
            logger.info(f"Cannot write to: {self.original_ssf}")
            self.show_error("Error", f"Cannot write to SSF file: {self.original_ssf}")
            return

        self.set_busy("Saving changes", progress=0)
        modified_swf = os.path.abspath("modified.swf")
        try:
            costumes_to_save = [costume for idx, costume in self.all_costumes]
            logger.info(f"Updating costumes for '{character}'...")
            update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, costumes_to_save)
            self.set_busy("Saving changes", progress=33)

            if not os.path.exists(self.temp_swf):
                logger.info(f"Decompressing {self.ssf_source}...")
                decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Saving changes", progress=50)

            logger.info("Injecting modified Misc.as...")
            if not self.suppress_prompts["jpexs_inject"]:
                dialog = Toplevel(self)
                dialog.title("Confirm")
                dialog.transient(self)
                dialog.grab_set()
                self.center_toplevel(dialog, 400, 150)
                tk.Label(dialog, text="This operation will use JPEXS Decompiler to inject scripts. Continue?").pack(pady=10)
                result = tk.BooleanVar(value=False)
                suppress = tk.BooleanVar(value=False)
                button_frame = tk.Frame(dialog)
                button_frame.pack(pady=10)
                tk.Button(button_frame, text="Yes", command=lambda: [result.set(True), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Button(button_frame, text="No", command=lambda: [result.set(False), dialog.destroy()]).pack(side=tk.LEFT, padx=5)
                tk.Checkbutton(button_frame, text="Do not show again", variable=suppress).pack(side=tk.LEFT, padx=5)
                self.wait_window(dialog)
                if suppress.get():
                    self.suppress_prompts["jpexs_inject"] = True
                    self.save_config()
                if not result.get():
                    logger.info("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Saving changes", progress=75)

            logger.info(f"Compressing to {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Saving changes", progress=90)

            # Update the ssf_source backup to match the modified SSF
            backup_ssf = self.handle_backup(self.original_ssf)
            logger.info(f"Updated ssf_source backup to: {backup_ssf}")
            self.ssf_source = backup_ssf
            self.set_busy("Saving changes", progress=95)

            if os.path.exists(self.original_ssf):
                logger.info(f"SSF updated: {self.original_ssf}")
            else:
                raise Exception("SSF file not found after save")

            # Extract the updated Misc.as to ensure loaded_misc_as is current
            extract_misc_as(modified_swf, self.loaded_misc_as, self.java_path, self.ffdec_jar)
            logger.info(f"Refreshed loaded_misc_as: {self.loaded_misc_as}")

            messagebox.showinfo("Success", f"Updated costumes for {character}")
            self.hide_costume_list()
            self.clear_busy()
        except Exception as e:
            logger.error(f"Error saving: {str(e)}")
            self.show_error("Error", f"Failed to save: {str(e)}")
            self.clear_busy()
        finally:
            self.cleanup_temp_files([modified_swf])

    def hide_costume_list(self):
        logger.info("Hiding costume list...")
        self.costume_list_frame.pack_forget()
        self.char_selection_frame.pack(fill=tk.X, padx=5)
        self.costume_list_visible = False
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.delete("all")
        if hasattr(self, 'preview_label'):
            self.preview_label.config(text="Select a costume to preview")
        self.clear_busy()

    def center_toplevel(self, toplevel, width, height):
        self.update_idletasks()
        main_width = self.winfo_width()
        main_height = self.winfo_height()
        main_x = self.winfo_rootx()
        main_y = self.winfo_rooty()
        x = main_x + (main_width - width) // 2
        y = main_y + (main_height - height) // 2
        toplevel.geometry(f"{width}x{height}+{x}+{y}")

if __name__ == "__main__":
    logger.info("Starting SSF2ModGUI application...")
    app = SSF2ModGUI()
    app.mainloop()    
    logger.info("Application closed.")