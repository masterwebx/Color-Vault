import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox, Toplevel, Label
import sys
from io import StringIO
import os
import json
import shutil
import webbrowser
import subprocess
import requests
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO
import hashlib
import glob
import time
from utils import (
    decompress_ssf, extract_misc_as, modify_misc_as, inject_misc_as, compress_swf,
    extract_character_names, extract_costumes, update_costumes, load_costumes_from_file,
    check_url_exists, load_costumes_from_url, launch_ssf2, copy_ssf2_directory
)
import platform
from add_costume_window import AddCostumeWindow

def resource_path(relative_path):
    """Get the absolute path to a resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Use the current directory during development
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
class TextRedirector:
    """Redirect print statements to a Tkinter scrolledtext widget."""
    def __init__(self, widget):
        self.widget = widget
        self.buffer = StringIO()

    def write(self, text):
        self.buffer.write(text)
        try:
            if self.widget.winfo_exists():
                self.widget.insert(tk.END, text)
                self.widget.see(tk.END)
                self.widget.update()
        except tk.TclError:
            sys.__stdout__.write(text)

    def flush(self):
        self.buffer.seek(0)
        self.buffer.truncate()

class SSF2ModGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SSF2 Costume Injector v1.0.4")
        icon_path = resource_path("icon.ico")
        self.wm_iconbitmap(icon_path)        
        # Determine the directory of the executable or script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable (e.g., PyInstaller)
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running as Python script
            base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(base_dir, "config.json")
        print(f"Config file path set to: {self.config_file}")
        self.setup_completed = False
        
        self.preview_cache = {}
        self.help_mode = False
        self.tooltips = {}
        self.tooltips_list = []
        self.original_stdout = sys.stdout
        self.characters = ["Custom"]
        self.pan_debounce_timer = None
        self.pan_debounce_delay = 50
        self.cached_resized_image = None
        self.cached_zoom_scale = None
        self.characters_loaded = False
        self.loaded_misc_as = None
        self.ssf_source = None
        self.java_path = None
        self.last_selected_listbox = None
        self.costume_listbox = tk.Listbox(self)  # Current costumes listbox
        self.loaded_listbox = tk.Listbox(self)   # Loaded costumes listbox
        self.move_to_trash_button = tk.Button(self, text="Move to Trash", command=self.move_to_trash)
        self.add_new_button = tk.Button(self, text="Add New", command=self.add_costume)
        self.ffdec_jar = None
        self.original_ssf = None
        self.temp_swf = None
        self.log_visible = False
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
                print(f"Deleted cache directory on startup: {self.image_cache_dir}")
            except Exception as e:
                print(f"Error deleting cache directory on startup: {str(e)}")
        os.makedirs(self.image_cache_dir)
        self.suppress_prompts = {
            "jpexs_extract": False,
            "jpexs_inject": False,
            "ssf2_launch": False,
            "save_confirm": False,
            "load_original_confirm": False,
            "load_from_online_confirm": False,
            "save_and_play_confirm": False,
            "save_changes_confirm": False,
            "select_ssf2_folder_confirm": False
        }
        self.preview_debounce_timer = None
        self.preview_debounce_delay = 300

        window_width = 1200
        window_height = 800
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(False, False)

        print("Initializing SSF2ModGUI application...")
        print("Setting up default paths for SSF2 and JPEXS Decompiler...")
        self.load_config()

        self.ffdec_path = tk.StringVar(value=self.config.get("ffdec_path", ""))
        self.ssf_path = tk.StringVar(value=self.config.get("ssf_path", ""))
        self.ssf2_exe_path = tk.StringVar(value=self.config.get("ssf2_exe_path", ""))
        self.use_original = tk.BooleanVar(value=False)
        self.selected_character = tk.StringVar(value="Select a Character")
        self.custom_character = tk.StringVar()        

        print(f"Setup completed status: {self.setup_completed}")
        if not self.setup_completed:
            print("Starting setup process for first-time configuration...")
            self.run_setup()
        else:
            print("Setup already completed, proceeding to create main UI...")
            self.create_main_ui()
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.ui_initialized = True
            if self.validate_paths():
                print("Paths validated successfully, loading characters from SSF file...")
                self.load_characters()
            self.toggle_custom_field()
        print("About to call load_url_mappings...")
        self.character_to_url = self.load_url_mappings()

    def on_close(self):
        if os.path.exists(self.image_cache_dir):
            try:
                shutil.rmtree(self.image_cache_dir)
                print(f"Deleted cache directory on exit: {self.image_cache_dir}")
            except Exception as e:
                print(f"Error deleting cache directory on exit: {str(e)}")
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
        print("Loading character-to-URL mappings from remote URL...")
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
            print(f"Loaded {len(character_to_url)} mappings from remote URL.")
            return character_to_url
        except requests.RequestException as e:
            print(f"Error fetching mappings from URL: {str(e)}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from URL: {str(e)}")
            return {}

    def load_config(self):
        print("Loading config...")
        self.config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
                self.setup_completed = self.config.get("setup_completed", False)
                self.hide_log = tk.BooleanVar(value=self.config.get("hide_log", False))
                for key in self.suppress_prompts:
                    self.suppress_prompts[key] = self.config.get(f"suppress_{key}", False)
                print(f"Loaded suppress_prompts: {self.suppress_prompts}")
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            # Initialize default config with empty paths
            self.config = {
                "setup_completed": False,
                "ffdec_path": "",
                "ssf_path": "",
                "ssf2_exe_path": "",
                "hide_log": False
            }
            self.hide_log = tk.BooleanVar(value=False)
            print("Initialized default config with empty paths.")

    def save_config(self):
        print("Saving config...")
        self.config.update({
            "setup_completed": self.setup_completed,
            "ffdec_path": self.ffdec_path.get(),
            "ssf_path": self.ssf_path.get(),
            "ssf2_exe_path": self.ssf2_exe_path.get(),
            "hide_log": self.hide_log.get()
        })
        for key, value in self.suppress_prompts.items():
            self.config[f"suppress_{key}"] = value
        config_path = os.path.abspath(self.config_file)
        print(f"Attempting to save config to: {config_path}")
        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)  # Ensure directory exists
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            if os.path.exists(config_path):
                print(f"Config saved successfully to: {config_path}")
            else:
                print(f"Error: Config file was not created at {config_path}")
                messagebox.showerror("Error", f"Config file was not created at {config_path}")
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
            messagebox.showerror("Error", f"Failed to save config to {config_path}: {e}")

    def run_setup(self):
        print("Running setup wizard to configure paths...")
        self.setup_frame = tk.Frame(self)
        self.setup_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(self.setup_frame, text="Welcome to SSF2 Costume Injector Setup", font=("Arial", 14)).pack(pady=10)
        tk.Button(self.setup_frame, text="Cancel", command=self.destroy).pack(pady=10)

        self.log_text = scrolledtext.ScrolledText(self.setup_frame, height=10, width=60, state='normal')
        self.log_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        sys.stdout = TextRedirector(self.log_text)

        print("Setup UI initialized successfully.")

        self.setup_content_frame = tk.Frame(self.setup_frame)
        self.setup_content_frame.pack(fill=tk.X, pady=5)

        self.continue_button = tk.Button(self.setup_frame, text="Continue", command=self.complete_setup)
        self.continue_button.pack(pady=10)

        self.check_jpexs()
        self.check_ssf2()

    def clear_setup_content(self):
        print("Clearing setup content frame to update UI...")
        for widget in self.setup_content_frame.winfo_children():
            widget.destroy()

    def check_jpexs(self):
        print("Checking for JPEXS Decompiler installation...")
        self.clear_setup_content()
        default_ffdec = os.path.normpath(os.path.expandvars(r"C:\Program Files (x86)\FFDec\ffdec.jar"))
        if os.path.isfile(default_ffdec):
            self.ffdec_path.set(default_ffdec)
            print("JPEXS Decompiler found at default location: " + default_ffdec)
            return True
        print("JPEXS Decompiler not found at C:\\Program Files (x86)\\FFDec\\")
        tk.Label(self.setup_content_frame, text="Please download and install JPEXS Decompiler.").pack(pady=5)
        tk.Button(self.setup_content_frame, text="Download JPEXS", command=lambda: webbrowser.open("https://github.com/jindrapetrik/jpexs-decompiler/releases")).pack(pady=5)
        tk.Button(self.setup_content_frame, text="Select JPEXS ffdec.jar", command=self.browse_ffdec).pack(pady=5)
        return False

    def check_ssf2(self):
        print("Checking for SSF2 installation at specified paths...")
        self.clear_setup_content()
        ssf_path = self.ssf_path.get()
        exe_path = self.ssf2_exe_path.get()
        
        if os.path.isfile(ssf_path) and os.path.isfile(exe_path):
            print(f"SSF2 found at: {os.path.dirname(ssf_path)}")
            return True
        
        print(f"SSF2 not found at specified paths: ssf={ssf_path}, exe={exe_path}")
        tk.Label(self.setup_content_frame, text="SSF2 must be copied to a valid location for modding.").pack(pady=5)
        tk.Label(self.setup_content_frame, text="Please download SSF2 or select an existing installation to copy.").pack(pady=5)
        tk.Button(self.setup_content_frame, text="Download SSF2", command=lambda: webbrowser.open("https://www.supersmashflash.com/play/ssf2/downloads/")).pack(pady=5)
        tk.Button(self.setup_content_frame, text="Select SSF2 Folder to Copy", command=self.select_ssf2_folder).pack(pady=5)
        return False

    def complete_setup(self):
        print("Completing setup process and validating paths...")
        if self.check_jpexs() and self.check_ssf2():
            self.setup_completed = True
            self.save_config()
            sys.stdout = self.original_stdout
            print("Destroying setup frame to transition to main UI...")
            self.setup_frame.destroy()
            self.setup_frame = None
            print("Creating main UI for character selection and costume management...")
            self.create_main_ui()
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.ui_initialized = True
            if self.validate_paths():
                print("Paths validated, loading characters from SSF file...")
                self.load_characters()
            print("Setup completed successfully.")
        else:
            print("Setup incomplete. Required paths for JPEXS or SSF2 are missing.")

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
            with open(file_path, "w") as f:
                json.dump(costumes, f, indent=2)
            messagebox.showinfo("Success", "Costumes saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save costumes: {str(e)}")

    def edit_loaded_costume(self):
        print("Editing loaded costume...")
        if self.last_selected_listbox == 'costume' and self.costume_listbox.curselection():
            idx = self.costume_listbox.curselection()[0]
            costume = self.all_costumes[idx][1]
            source = 'current'
            image_path = self.get_image_path_for_costume(costume)
            print(f"Editing costume from current list, idx: {idx}, info: {costume.get('info', 'No info')}, image_path: {image_path}")
            # Ensure preview is cached
            self.update_preview()
            AddCostumeWindow(self, self.selected_character.get(), costume_data=costume, image_path=image_path, source=source, current_idx=idx, on_save_callback=self.add_new_costume_to_list)
        elif self.last_selected_listbox == 'loaded' and self.loaded_listbox.curselection():
            idx = self.loaded_listbox.curselection()[0]
            costume = self.loaded_costumes[idx]
            source = 'loaded'
            image_path = self.get_image_path_for_costume(costume)
            print(f"Editing costume from loaded list, idx: {idx}, info: {costume.get('info', 'No info')}, image_path: {image_path}")
            # Ensure preview is cached
            self.update_preview()
            AddCostumeWindow(self, self.selected_character.get(), costume_data=costume, image_path=image_path, source=source, loaded_idx=idx, on_save_callback=self.add_new_costume_to_list)
        else:
            print("No costume selected for editing")
            messagebox.showerror("Error", "Please select a costume to edit.")
        print("Edit loaded costume completed")

    def generate_image_from_preview(self, costume):
        """Generate an image from the preview cache for the given costume."""
        import json
        import hashlib
        print(f"Generating image from preview for costume: {costume.get('info', 'No info')}")
        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()
        
        try:
            # Generate the same hash used in update_preview
            costume_json = json.dumps(costume, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()
            
            if costume_hash not in self.preview_cache:
                print(f"No preview image in cache for costume hash: {costume_hash}")
                return None
            
            image = self.preview_cache[costume_hash]
            info = costume.get('info', 'No Info').replace(' ', '_')
            character_dir = os.path.join(os.getcwd(), "recolors", character)
            if not os.path.exists(character_dir):
                os.makedirs(character_dir)
                print(f"Created directory: {character_dir}")
            
            # Save the image with a unique filename
            image_path = os.path.join(character_dir, f"{info}.png")
            image.save(image_path)
            print(f"Saved generated image to: {image_path}")
            return image_path
        except Exception as e:
            print(f"Error generating image from preview: {str(e)}")
            return None

    def get_image_path_for_costume(self, costume):
        character_dir = os.path.join(os.getcwd(), "recolors", self.selected_character.get())
        print(f"Searching for image in directory: {character_dir}")
        if not os.path.exists(character_dir):
            print(f"Character directory does not exist: {character_dir}")
            return None
        info = costume.get('info', '')
        if not info:
            print(f"No 'info' field in costume: {costume}")
            return None
        filename_part = info.replace(' ', '_')
        print(f"Looking for .png files containing: {filename_part}")
        for file in os.listdir(character_dir):
            if file.endswith(".png"):
                if filename_part in file:
                    path = os.path.join(character_dir, file)
                    if os.path.exists(path):
                        print(f"Found image path: {path}")
                        return path
                    else:
                        print(f"File listed but does not exist: {path}")
                elif file == "EDIT ME.png":
                    print(f"Found EDIT ME.png, but info '{info}' does not match")
        print(f"No image found for costume with info '{info}' in {character_dir}")
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
        print("Creating main UI for SSF2 Costume Injector...")

        self.status_frame = tk.Frame(self)
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(self.status_frame, mode="determinate", maximum=100)
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.status_label = tk.Label(self.status_frame, text="Ready", fg="black", bg="#d9d9d9", anchor="center")
        self.status_label.place(in_=self.progress_bar, relx=0.5, rely=0.5, anchor="center")
        self.register_tooltip(self.progress_bar, "Progress indicator and status message for ongoing operations.")

        settings_button = tk.Button(self, text="Settings", command=self.open_settings)
        settings_button.pack(anchor="ne", padx=5, pady=5)
        self.register_tooltip(settings_button, "Open the settings menu to configure paths.")

        self.help_button = tk.Button(self, text="Help Tooltips", command=self.toggle_help_mode)
        self.help_button.pack(anchor="ne", padx=5)
        self.register_tooltip(self.help_button, "Toggle help mode to view tooltips for UI elements.")
        
        # Join Discord button below help button
        self.discord_button = tk.Button(self, text="Join Discord", command=lambda: webbrowser.open("https://discord.gg/xZtTqX4"))
        self.discord_button.pack(anchor="ne", padx=5, pady=5)
        self.char_selection_frame = tk.Frame(self)
        self.char_selection_frame.pack(fill=tk.X, padx=5)

        # Color creator button
        self.colorcreator_button = tk.Button(self, text="Create your own recolor", command=lambda: webbrowser.open("https://color-vault.github.io/Color-Vault/colorcreator2.html"))
        self.colorcreator_button.pack(anchor="ne", padx=5, pady=5)
        self.char_selection_frame = tk.Frame(self)
        self.char_selection_frame.pack(fill=tk.X, padx=5)

        tk.Label(self.char_selection_frame, text="Select Character:").pack(anchor="w")
        self.frame_char = tk.Frame(self.char_selection_frame)
        self.frame_char.pack(fill=tk.X, padx=5)

        self.character_dropdown = ttk.Combobox(self.frame_char, textvariable=self.selected_character, values=["Select a Character"] + self.characters, state="readonly", width=20)
        self.character_dropdown.bind("<<ComboboxSelected>>", self.toggle_custom_field)
        self.character_dropdown.pack(side=tk.LEFT, pady=5)
        self.register_tooltip(self.character_dropdown, "Select a character to modify costumes for. Choose 'Custom' to enter a new character name.")

        self.load_costume_button = tk.Button(self.frame_char, text="Load Costume List", command=self.load_costume_list)
        self.load_costume_button.pack(side=tk.LEFT, padx=5)
        self.register_tooltip(self.load_costume_button, "View and edit the costume list for the selected character.")

        self.custom_frame = tk.Frame(self.frame_char)
        tk.Label(self.custom_frame, text="Custom Character Name:").pack(side=tk.LEFT, padx=(10, 5))
        self.custom_entry = tk.Entry(self.custom_frame, textvariable=self.custom_character, width=20)
        self.custom_entry.pack(side=tk.LEFT)

        self.costume_list_frame = tk.Frame(self)

        if not self.hide_log.get():
            self.log_label = tk.Label(self, text="Log:")
            self.log_label.pack(pady=5, anchor="w")
            self.log_text = scrolledtext.ScrolledText(self, height=6, width=50, state='normal')
            self.log_text.pack(padx=5, pady=5, fill=tk.X)
            sys.stdout = TextRedirector(self.log_text)
            self.register_tooltip(self.log_text, "View logs and status messages for operations.")
            self.log_visible = True
        else:
            self.log_visible = False

        print("Main UI created successfully.")

    def open_settings(self):
        print("Opening settings menu to configure paths...")
        settings_window = Toplevel(self)
        settings_window.title("Settings")
        settings_window.transient(self)
        settings_window.grab_set()
        self.center_toplevel(settings_window, 600, 400)

        tk.Label(settings_window, text="FFDEC Path (ffdec.jar):").pack(pady=5)
        frame_ffdec = tk.Frame(settings_window)
        frame_ffdec.pack(fill=tk.X, padx=5)
        ffdec_entry = tk.Entry(frame_ffdec, textvariable=self.ffdec_path, width=50)
        ffdec_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ffdec, text="Browse", command=self.browse_ffdec).pack(side=tk.RIGHT)
        tk.Button(frame_ffdec, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ffdec_path.get()))).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ffdec_entry, "Path to JPEXS Decompiler's ffdec.jar file.")

        tk.Label(settings_window, text="SSF File (e.g., DAT67.ssf):").pack(pady=5)
        frame_ssf = tk.Frame(settings_window)
        frame_ssf.pack(fill=tk.X, padx=5)
        ssf_entry = tk.Entry(frame_ssf, textvariable=self.ssf_path, width=50)
        ssf_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ssf, text="Browse", command=self.browse_ssf).pack(side=tk.RIGHT)
        tk.Button(frame_ssf, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ssf_path.get()))).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ssf_entry, "Path to SSF2's DAT67.ssf file.")

        tk.Label(settings_window, text="SSF2 Executable (SSF2.exe):").pack(pady=5)
        frame_ssf2 = tk.Frame(settings_window)
        frame_ssf2.pack(fill=tk.X, padx=5)
        ssf2_entry = tk.Entry(frame_ssf2, textvariable=self.ssf2_exe_path, width=50)
        ssf2_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(frame_ssf2, text="Browse", command=self.browse_ssf2_exe).pack(side=tk.RIGHT)
        tk.Button(frame_ssf2, text="Open Folder", command=lambda: self.open_folder(os.path.dirname(self.ssf2_exe_path.get()))).pack(side=tk.RIGHT, padx=5)
        self.register_tooltip(ssf2_entry, "Path to SSF2 executable (SSF2.exe).")

        tk.Button(settings_window, text="Restart Setup", command=self.restart_setup).pack(pady=10)
        tk.Button(settings_window, text="Start Fresh", command=self.load_characters).pack(pady=10)
        tk.Button(settings_window, text="Download All Costumes from Github", command=self.download_all_costumes).pack(pady=10)
        tk.Button(settings_window, text="About", command=self.show_about).pack(pady=10)
        tk.Checkbutton(settings_window, text="Hide Log in Main Window", variable=self.hide_log).pack(pady=5)
        tk.Button(settings_window, text="Save", command=lambda: [self.save_config(), settings_window.destroy()]).pack(pady=10)

    def show_about(self):
        about_window = Toplevel(self)
        about_window.title("About")
        about_window.transient(self)
        about_window.grab_set()
        self.center_toplevel(about_window, 400, 150)        
        tk.Label(about_window, text="SSF2 Costume Injector\nVersion: 1.0.4\n\nA tool for injecting custom costumes into Super Smash Flash 2.").pack(pady=20)
        tk.Button(about_window, text="OK", command=about_window.destroy).pack(pady=10)

    def restart_setup(self):
        print("Restarting setup process to reconfigure paths...")
        self.setup_completed = False
        self.save_config()
        for widget in self.winfo_children():
            widget.destroy()
        self.ui_initialized = False
        sys.stdout = self.original_stdout
        print("Setup restarted, running setup wizard...")
        self.run_setup()

    def browse_ffdec(self):
        print("Browsing for JPEXS ffdec.jar file...")
        path = filedialog.askopenfilename(filetypes=[("JAR files", "*.jar")])
        if path:
            self.ffdec_path.set(path)
            self.save_config()
            if self.validate_paths() and not self.costume_list_visible:
                print("FFDEC path updated, loading characters...")
                self.load_characters()
            if self.setup_frame:
                self.check_jpexs()
        else:
            print("No FFDEC path selected.")

    def browse_ssf(self):
        print("Browsing for DAT67.ssf file...")
        path = filedialog.askopenfilename(filetypes=[("SSF files", "*.ssf")])
        if path:
            self.ssf_path.set(path)
            self.save_config()
            if self.validate_paths() and not self.costume_list_visible:
                print("SSF path updated, loading characters...")
                self.load_characters()
            if self.setup_frame:
                self.check_ssf2()
        else:
            print("No SSF path selected.")

    def browse_ssf2_exe(self):
        print("Browsing for SSF2.exe file...")
        path = filedialog.askopenfilename(filetypes=[("Executable files", "*.exe")])
        if path:
            self.ssf2_exe_path.set(path)
            self.save_config()
            if self.setup_frame:
                self.check_ssf2()
        else:
            print("No SSF2.exe path selected.")

    def select_ssf2_folder(self):
        print("Selecting SSF2 folder to copy...")
        src_folder = filedialog.askdirectory(title="Select SSF2 Source Folder")
        if not src_folder:
            print("No SSF2 source folder selected.")
            return
        dest_folder = filedialog.askdirectory(title="Select Destination Folder for SSF2")
        if not dest_folder:
            print("No destination folder selected.")
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
                        print("Copy operation cancelled by user.")
                        return
                else:
                    print(f"Directory already exists at {dest_dir}, overwriting as per user preference.")
            else:
                print(f"Creating destination directory: {dest_dir}")
                os.makedirs(dest_dir)
            shutil.rmtree(dest_dir, ignore_errors=True)
            copy_ssf2_directory(src_folder, dest_dir)
            self.ssf_path.set(os.path.join(dest_dir, "data", "DAT67.ssf"))
            self.ssf2_exe_path.set(os.path.join(dest_dir, "SSF2.exe"))
            self.save_config()
            print(f"SSF2 successfully copied to {dest_dir}")
            if self.setup_frame:
                self.check_ssf2()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy SSF2 to {dest_dir}: {str(e)}")
            print(f"Error copying SSF2: {str(e)}")

    def open_folder(self, path):
        print(f"Opening folder in file explorer: {path}")
        if os.path.exists(path):
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showerror("Error", f"Folder does not exist: {path}")
            print(f"Folder does not exist: {path}")

    def register_tooltip(self, widget, text):
        self.tooltips[widget] = text
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def toggle_help_mode(self):
        self.help_mode = not self.help_mode
        self.help_button.config(text="?" if not self.help_mode else "X")
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
        print(f"Setting application to busy state: {message} ({progress}%)")
        if self.ui_initialized:
            self.status_label.config(text=f"{message} ({progress}%)")
            self.progress_bar['value'] = progress
            self.configure(cursor="wait")
            self.load_costume_button.config(state="disabled")
            self.character_dropdown.config(state="disabled")
            self.custom_entry.config(state="disabled")
            self.update()
        else:
            print(f"Busy: {message} ({progress}%)")

    def clear_busy(self):
        print("Clearing busy state and resetting UI...")
        if self.ui_initialized:
            self.status_label.config(text="Ready")
            self.progress_bar['value'] = 0
            self.configure(cursor="")
            self.load_costume_button.config(state="normal")
            if self.characters_loaded:
                self.load_costume_button.config(state="normal")
            self.character_dropdown.config(state="readonly")
            self.custom_entry.config(state="normal")
            self.update()
        else:
            print("Application ready.")

    def toggle_custom_field(self, event=None):
        print("Toggling custom character field...")
        if self.selected_character.get() == "Custom":
            self.custom_frame.pack(side=tk.LEFT, padx=5)
        else:
            self.custom_frame.pack_forget()
            # Load costume list when a valid character is selected
            if self.selected_character.get() != "Select a Character" and self.characters_loaded:
                print(f"Loading costume list for: {self.selected_character.get()}")
                self.load_costume_list()

    def validate_paths(self):
        print("Validating file paths for JPEXS and SSF2...")
        ffdec = self.ffdec_path.get()
        if not ffdec or not os.path.isfile(ffdec) or not ffdec.endswith("ffdec.jar"):
            messagebox.showerror("Error", "Invalid FFDEC path. Please select a valid ffdec.jar file in Settings.")
            return False
        
        ssf = self.ssf_path.get()
        if not ssf or not os.path.isfile(ssf) or not ssf.endswith(".ssf"):
            print("Invalid SSF path: " + str(ssf))
            messagebox.showerror("Error", "Invalid SSF file path. Please select a valid DAT67.ssf file in Settings.")
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
            print(f"Java installed: {result.stderr.strip()}")
            java_found = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Java executable not found in PATH. Checking common Java installation paths...")
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
                        print(f"Java found at {java_path}: {result.stderr.strip()}")
                        java_found = True
                        # Update PATH temporarily for this session
                        os.environ["PATH"] = f"{os.path.dirname(java_path)};{os.environ.get('PATH', '')}"
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                if java_found:
                    break
        
        if not java_found:
            print("Java is not installed or not in PATH")
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
        
        print("All paths and Java installation validated successfully.")
        return True

    def validate_character(self):
        print("Validating selected character for costume loading...")
        character = self.selected_character.get()
        if character == "Select a Character":
            print("Error: No character selected.")
            messagebox.showerror("Error", "Please select a valid character.")
            return False
        if character == "Custom":
            custom_char = self.custom_character.get().strip()
            if not custom_char or not custom_char.isidentifier():
                print("Error: Invalid custom character name: " + str(custom_char))
                messagebox.showerror("Error", "Invalid custom character name. Please enter a valid name.")
                return False
        print("Character validated successfully: " + character)
        return True

    def handle_backup(self, ssf_path):
        print(f"Creating backup for SSF file: {ssf_path}")
        # Derive backup directory from the SSF2 folder
        ssf_dir = os.path.dirname(ssf_path)
        backup_base_dir = os.path.join(ssf_dir, "backup")
        backup_ssf = os.path.join(backup_base_dir, os.path.basename(ssf_path))
        
        try:
            if not os.path.exists(backup_base_dir):
                os.makedirs(backup_base_dir)
                print(f"Created backup directory: {backup_base_dir}")
            if not os.path.exists(backup_ssf):
                shutil.copy2(ssf_path, backup_ssf)
                print(f"Copied original SSF to backup: {backup_ssf}")
            return backup_ssf
        except PermissionError as e:
            print(f"Permission error creating backup: {e}")
            messagebox.showerror("Error", f"Cannot create backup in {backup_base_dir}. Please run the application as administrator or choose a different SSF path.")
            raise
        except Exception as e:
            print(f"Error creating backup: {e}")
            messagebox.showerror("Error", f"Failed to create backup: {str(e)}")
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
                print("User cancelled Load Original operation.")
                return False
        else:
            print("Proceeding with Load Original operation as per user preference.")

        print("Loading original SSF from backup for current character...")
        if not self.validate_paths():
            print("Error: Invalid SSF path.")
            messagebox.showerror("Error", "Invalid SSF path. Please check your configuration.")
            return False

        backup_ssf = self.ssf_source  # Use the backup path set by handle_backup

        if not os.path.exists(backup_ssf):
            print(f"Backup SSF not found at: {backup_ssf}")
            messagebox.showerror("Error", f"No backup SSF file found at {backup_ssf}.")
            return False

        if not os.access(self.ssf_path.get(), os.W_OK):
            print(f"Cannot write to SSF file: {self.ssf_path.get()}")
            messagebox.showerror("Error", f"Cannot write to SSF file: {self.ssf_path.get()}. Check file permissions.")
            return False

        self.set_busy("Restoring original SSF file", progress=0)
        try:
            shutil.copy2(backup_ssf, self.ssf_path.get())
            print(f"Restored backup SSF from {backup_ssf} to {self.ssf_path.get()}")
            self.set_busy("Restoring original SSF file", progress=25)

            self.temp_swf = os.path.abspath("temp.swf")
            original_as = os.path.abspath(os.path.join("scripts", "Misc.as"))
            if os.path.exists(self.temp_swf):
                os.remove(self.temp_swf)

            print(f"Decompressing SSF file {self.ssf_path.get()} to SWF...")
            decompress_ssf(self.ssf_path.get(), self.temp_swf)
            self.set_busy("Restoring original SSF file", progress=50)

            print(f"Extracting Misc.as from SWF using JPEXS Decompiler at {self.ffdec_jar}...")
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.loaded_misc_as = original_as
            self.set_busy("Restoring original SSF file", progress=75)

            self.load_costume_list_for_character(character)
            messagebox.showinfo("Success", "Successfully restored original costumes for this character.")
            return True
        except Exception as e:
            print(f"Error restoring backup: {str(e)}")
            messagebox.showerror("Error", f"Failed to restore backup: {str(e)}")
            return False
        finally:
            self.clear_busy()

    def convert_color(self, color):
        if isinstance(color, str):
            color = color.replace('#', '')
            try:
                color_int = int(color, 16)
                if len(color) == 6:
                    color_int = (color_int << 8) | 0xFF
                return color_int & 0xFFFFFFFF
            except ValueError:
                print(f"Invalid hex color: {color}")
                return 0xFF000000
        elif isinstance(color, int):
            return color & 0xFFFFFFFF
        else:
            print(f"Unsupported color type: {type(color)}, value: {color}")
            return 0xFF000000

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

    def int_to_hex(self, int_val):
        if int_val < 0:
            int_val += 0x100000000
        hex_str = hex(int_val)[2:].upper().zfill(8)
        return hex_str

    def hex_to_signed_32bit_int(self, hex_str):
        int_value = int(hex_str.replace('#', ''), 16)
        if int_value & 0x80000000:
            int_value -= 0x100000000
        return int_value | 0xFF000000

    def load_costume_list_for_character(self, character, offset=0, limit=50):
        print(f"Refreshing costume list for character '{character}' (offset: {offset}, limit: {limit})...")
        if not self.characters_loaded:
            print("Error: Please load characters first.")
            self.clear_busy()
            return
        if not self.validate_character():
            self.clear_busy()
            return
        if not self.loaded_misc_as or not os.path.exists(self.loaded_misc_as):
            print("Error: Misc.as not loaded. Please reload characters.")
            self.clear_busy()
            return
        self.set_busy("Refreshing costume list", progress=0)
        self.update()

        try:
            print(f"Extracting costumes for character '{character}' from updated Misc.as...")
            costumes_data = extract_costumes(self.loaded_misc_as, character)
            self.total_costumes = len(costumes_data)
            self.set_busy("Refreshing costume list", progress=50)

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
            print(f"Refreshed costume list with {len(self.all_costumes)} costumes for character '{character}'.")
            self.set_busy("Refreshing costume list", progress=100)

            if self.costume_count_label:
                self.costume_count_label.config(text=f"Current Costumes ({self.costume_offset}/{self.total_costumes})")
        except Exception as e:
            print(f"Error refreshing costume list: {str(e)}")
            self.clear_busy()

    def download_all_costumes(self):
        print("Initiating download of all costumes from Github for all available characters...")
        if not messagebox.askyesno("Confirm", "Are you sure you want to download all costumes for all available characters from Github? This will append new costumes to existing lists."):
            print("User cancelled download all costumes operation.")
            return

        if not self.characters_loaded:
            print("Error: Please load characters first.")
            messagebox.showerror("Error", "Please load characters first using 'Start Fresh' in Settings.")
            self.clear_busy()
            return
        if not self.validate_paths():
            print("Error: Invalid paths.")
            messagebox.showerror("Error", "Invalid FFDEC or SSF path. Please check your configuration.")
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
                print(f"Backup SSF not found at: {backup_ssf}")
                messagebox.showerror("Error", f"No backup SSF file found at {backup_ssf}. Please ensure a backup exists.")
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
            print(f"Decompressing backup SSF file {self.ssf_source} to SWF...")
            decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Downloading all costumes from Github", progress=10)

            print(f"Extracting Misc.as from SWF using JPEXS Decompiler at {self.ffdec_jar}...")
            if not messagebox.askyesno("Confirm", "This operation will use JPEXS Decompiler to extract scripts. Continue?"):
                print("User cancelled JPEXS Decompiler operation.")
                self.clear_busy()
                return
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.loaded_misc_as = original_as
            self.set_busy("Downloading all costumes from Github", progress=20)

            characters = [char for char in self.characters if char != "Custom"]
            updated_characters = []
            total_characters = len(characters)
            if total_characters == 0:
                print("No characters available to process.")
                messagebox.showinfo("Info", "No characters available to download costumes for.")
                self.clear_busy()
                return

            progress_per_character = 60 / total_characters
            current_progress = 20

            for i, character in enumerate(characters):
                self.set_busy(f"Processing costumes for {character}", progress=int(current_progress))
                online_url = f"https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/{character}.as"
                print(f"Checking costumes for character '{character}' at {online_url}")
                if not check_url_exists(online_url):
                    print(f"No costumes available for character '{character}' at {online_url}")
                    current_progress += progress_per_character
                    continue

                new_costumes = load_costumes_from_url(online_url)
                if not new_costumes:
                    print(f"No valid costumes loaded for character '{character}' from {online_url}")
                    current_progress += progress_per_character
                    continue

                existing_costumes = extract_costumes(self.loaded_misc_as, character)
                combined_costumes = existing_costumes + new_costumes
                if len(combined_costumes) == len(existing_costumes):
                    print(f"No new costumes to add for character '{character}'")
                    current_progress += progress_per_character
                    continue

                print(f"Appending {len(new_costumes)} costumes for character '{character}' to existing list...")
                update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, combined_costumes)
                updated_characters.append(character)
                print(f"Successfully appended {len(new_costumes)} costumes for character '{character}'")
                current_progress += progress_per_character

            if not updated_characters:
                print("No characters had valid costumes to download from Github.")
                messagebox.showinfo("Info", "No new costumes were found for any characters on Github.")
                self.clear_busy()
                return

            print(f"Injecting modified Misc.as into SWF using JPEXS Decompiler...")
            modified_swf = os.path.abspath("modified.swf")
            if not messagebox.askyesno("Confirm", "This operation will use JPEXS Decompiler to inject scripts. Continue?"):
                print("User cancelled JPEXS Decompiler operation.")
                self.clear_busy()
                return
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Injecting modified scripts", progress=90)

            print(f"Compressing modified SWF back to SSF file {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Compressing SSF file", progress=100)

            messagebox.showinfo("Success", f"Successfully appended costumes for {', '.join(updated_characters)} from Github.")

            self.cleanup_temp_files([modified_swf])
            self.load_characters()
        except Exception as e:
            print(f"Error downloading costumes: {str(e)}")
            messagebox.showerror("Error", f"Failed to download costumes: {str(e)}")
            self.cleanup_temp_files([modified_swf])
            self.clear_busy()
        finally:
            self.clear_busy()

    def load_characters(self):
        print("Loading characters from SSF file for costume management...")
        if not self.validate_paths():
            print("Error: Invalid FFDEC or SSF path.")
            self.clear_busy()
            return

        self.set_busy("Loading characters", progress=0)
        self.update()

        self.java_path = "java"
        self.ffdec_jar = os.path.abspath(self.ffdec_path.get())
        self.original_ssf = self.ssf_path.get()
        self.ssf_source = self.handle_backup(self.original_ssf)
        load_source = self.ssf_source if self.use_original.get() else self.original_ssf
        self.temp_swf = os.path.abspath("temp.swf")
        original_as = os.path.abspath(os.path.join("scripts", "Misc.as"))

        try:
            if not os.path.exists(self.temp_swf):
                print(f"Decompressing SSF file {load_source} to SWF...")
                decompress_ssf(load_source, self.temp_swf)
            self.set_busy("Loading characters", progress=33)

            print(f"Extracting Misc.as from SWF using JPEXS Decompiler at {self.ffdec_jar}...")
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
                    print("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            else:
                print("Proceeding with JPEXS Decompiler extraction as per user preference.")
            extract_misc_as(self.temp_swf, original_as, self.java_path, self.ffdec_jar)
            self.loaded_misc_as = original_as
            self.set_busy("Loading characters", progress=66)

            print(f"Extracting character names from Misc.as at {original_as}...")
            new_characters = extract_character_names(original_as)
            if not new_characters:
                print("No characters found in Misc.as.")
                self.clear_busy()
                return
            current_selection = self.selected_character.get()
            self.characters = sorted(list(set(new_characters + ["Custom"])))
            self.character_dropdown['values'] = ["Select a Character"] + self.characters
            self.selected_character.set(current_selection if current_selection in self.characters else "Select a Character")
            print(f"Updated character list: {', '.join(self.characters)}")
            self.characters_loaded = True
            self.set_busy("Loading characters", progress=100)
            self.clear_busy()
        except Exception as e:
            print(f"Error loading characters: {str(e)}")
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
        print("Cleaning up temporary files created during operations...")
        scripts_dir = os.path.abspath("scripts")
        for temp_file in files:
            if os.path.exists(temp_file) and temp_file != self.loaded_misc_as:
                os.remove(temp_file)
                print(f"Cleaned up temporary file: {temp_file}")
        if os.path.exists(scripts_dir) and not os.listdir(scripts_dir):
            os.rmdir(scripts_dir)
            print(f"Cleaned up empty scripts directory: {scripts_dir}")

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

    def add_costume(self):
        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()
        # Pass the callback to AddCostumeWindow to handle the new costume
        AddCostumeWindow(self, character, on_save_callback=self.add_new_costume_to_list)

    def add_from_file(self):
        print("Opening file dialog to load costumes from a file...")
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("ActionScript files", "*.as")])
        if not file_path:
            print("No file selected for loading costumes.")
            return
        try:
            print(f"Loading costumes from file: {file_path}")
            new_costumes = load_costumes_from_file(file_path)
            self.loaded_costumes.extend(new_costumes)
            for costume in new_costumes:
                self.loaded_listbox.insert(tk.END, costume['display_name'])
            print(f"Successfully loaded {len(new_costumes)} costumes from file.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load costumes from file: {str(e)}")
            print(f"Error loading costumes from file: {str(e)}")

    def add_new_costume_to_list(self, new_costume, source=None, current_idx=None, loaded_idx=None):
        # Handle new costume addition (source is None or not 'current'/'loaded')
        if source not in ['current', 'loaded']:
            display_name = self.get_display_name(new_costume)
            self.all_costumes.append((len(self.all_costumes), new_costume))
            self.costume_listbox.insert(tk.END, display_name)
            self.costume_listbox.select_set(len(self.all_costumes) - 1)
            print(f"Added new costume: {display_name}")
        # Optionally handle editing existing costumes if source is 'current' or 'loaded'
        elif source == 'current' and current_idx is not None:
            self.all_costumes[current_idx] = (current_idx, new_costume)
            self.update_costume_list()
            print(f"Updated costume at index {current_idx}")
        elif source == 'loaded' and loaded_idx is not None:
            self.loaded_costumes[loaded_idx] = new_costume
            self.loaded_listbox.delete(loaded_idx)
            self.loaded_listbox.insert(loaded_idx, self.get_display_name(new_costume))
            print(f"Updated loaded costume at index {loaded_idx}")

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
                print("User cancelled online costume loading operation.")
                return
        else:
            print("Proceeding with online costume loading as per user preference.")   

        try:
            new_costumes = load_costumes_from_url(self.online_url)
            self.loaded_costumes.extend(new_costumes)
            for costume in new_costumes:
                self.loaded_listbox.insert(tk.END, costume['display_name'])
            print(f"Successfully loaded {len(new_costumes)} costumes from online repository.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load costumes from online: {str(e)}")
            print(f"Error loading costumes from online: {str(e)}")

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
                print("User cancelled save and play operation.")
                return
        else:
            print("Proceeding with save and play operation as per user preference.")

        if not os.access(self.original_ssf, os.W_OK):
            print(f"Cannot write to SSF file: {self.original_ssf}")
            messagebox.showerror("Error", f"Cannot write to SSF file: {self.original_ssf}. Check file permissions.")
            return
        self.set_busy("Saving changes and launching SSF2", progress=0)
        modified_swf = os.path.abspath("modified.swf")
        try:
            costumes_to_save = [costume for idx, costume in self.all_costumes]
            print(f"Updating costumes for character '{character}' in Misc.as...")
            update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, costumes_to_save)
            self.set_busy("Saving changes and launching SSF2", progress=33)
            if not os.path.exists(self.temp_swf):
                print(f"Decompressing SSF file {self.ssf_source} to SWF...")
                decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Saving changes and launching SSF2", progress=50)
            print(f"Injecting modified Misc.as into SWF using JPEXS Decompiler...")
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
                    print("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            else:
                print("Proceeding with JPEXS Decompiler injection as per user preference.")
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Saving changes and launching SSF2", progress=75)
            print(f"Compressing modified SWF back to SSF file {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Saving changes and launching SSF2", progress=90)
            print(f"Launching SSF2 executable at {self.ssf2_exe_path.get()}...")
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
                    print("User cancelled SSF2 launch operation.")
                    self.clear_busy()
                    return
            else:
                print("Proceeding with SSF2 launch as per user preference.")
            launch_ssf2(self.ssf2_exe_path.get())
            self.set_busy("Saving changes and launching SSF2", progress=100)
            messagebox.showinfo("Success", f"Updated costumes for {character} and launched SSF2.")
            self.hide_costume_list()
            self.clear_busy()
        except Exception as e:
            print(f"Error saving or launching: {str(e)}")
            messagebox.showerror("Error", f"Failed to save or launch SSF2: {str(e)}")
            self.clear_busy()
        finally:
            self.cleanup_temp_files([modified_swf])

    def load_costume_list(self):
        print("Loading costume list for the selected character...")
        if not self.characters_loaded:
            print("Error: Please load characters first.")
            self.clear_busy()
            return
        if not self.validate_character():
            self.clear_busy()
            return
        if not self.loaded_misc_as or not os.path.exists(self.loaded_misc_as):
            print("Error: Misc.as not loaded. Please reload characters.")
            self.clear_busy()
            return

        self.set_busy("Loading costume list", progress=0)
        self.update()

        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()

        try:
            print(f"Extracting costumes for character '{character}' from Misc.as...")
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

            self.char_selection_frame.pack_forget()
            self.costume_list_frame.pack_forget()
            self.costume_list_frame = tk.Frame(self)
            self.costume_list_visible = True
            print(f"costume list visible")
            self.back_button = tk.Button(self.costume_list_frame, text="Back", command=self.hide_costume_list, font=("Arial", 16), width=10, height=2)
            self.back_button.pack(anchor="nw", padx=5, pady=5)
            self.register_tooltip(self.back_button, "Return to character selection.")

            main_frame = tk.Frame(self.costume_list_frame)
            main_frame.pack(fill=tk.BOTH, expand=True)

            left_panel = tk.Frame(main_frame)
            left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            right_panel = tk.Frame(main_frame)
            right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            tk.Label(left_panel, text=f"Costumes for {character}", font=("Arial", 14)).pack(pady=10)
            self.register_tooltip(tk.Label(left_panel, text=f"Costumes for {character}"), "List of costumes for the selected character.")

            listbox_frame = tk.Frame(left_panel)
            listbox_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

            self.costume_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED)
            self.costume_listbox.grid(row=1, column=0, padx=5, sticky="nsew")
            tk.Button(listbox_frame, text="Download Current", command=self.download_current_costumes).grid(row=2, column=0, pady=5)

            tk.Label(listbox_frame, text="Loaded Costumes").grid(row=0, column=1, padx=5)
            self.loaded_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED)
            self.loaded_listbox.grid(row=1, column=1, padx=5, sticky="nsew")
            tk.Button(listbox_frame, text="Download Loaded", command=self.download_loaded_costumes).grid(row=2, column=1, pady=5)

            tk.Label(listbox_frame, text="For Removal").grid(row=0, column=2, padx=5)
            self.remove_listbox = tk.Listbox(listbox_frame, height=10, width=30, selectmode=tk.EXTENDED)
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

            tk.Label(right_panel, text="Costume Preview", font=("Arial", 14)).pack(pady=10)
            self.preview_canvas = tk.Canvas(right_panel, width=600, height=400, bg="white", highlightthickness=1, highlightbackground="black")
            self.preview_canvas.pack(pady=10, padx=10)
            self.register_tooltip(self.preview_canvas, "Preview of the selected costume's recolored sheet.")
            self.preview_label = tk.Label(right_panel, text="Select a costume to preview", fg="gray")
            self.preview_label.pack(pady=5)

            

            self.button_frame = tk.Frame(left_panel)
            self.button_frame.pack(pady=5)

            self.move_up_button = tk.Button(self.button_frame, text="Move Up", command=self.move_up)
            self.move_up_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.move_up_button, "Move selected costumes up in the list.")

            self.move_down_button = tk.Button(self.button_frame, text="Move Down", command=self.move_down)
            self.move_down_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.move_down_button, "Move selected costumes down in the list.")

            self.move_to_trash_button = tk.Button(self.button_frame, text="Move to Trash", command=self.move_to_trash)
            self.move_to_trash_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.move_to_trash_button, "Move selected costumes to the removal list.")

            self.add_new_button = tk.Button(self.button_frame, text="Add New", command=self.add_costume)
            self.add_new_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.add_new_button, "Create a new costume.")

            self.add_from_file_button = tk.Button(self.button_frame, text="Add from File", command=self.add_from_file)
            self.add_from_file_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.add_from_file_button, "Load costumes from a .txt or .as file.")

            self.move_to_current_button = tk.Button(self.button_frame, text="Move to Current List", command=self.move_to_current_list)
            self.move_to_current_button.pack(side=tk.LEFT, padx=5)
            self.register_tooltip(self.move_to_current_button, "Add selected loaded costumes to the current list.")

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
                print(f"No online costumes available for character '{character}' at {self.online_url}")

            backup_ssf = self.ssf_source
            if os.path.exists(backup_ssf):
                self.load_original_button = tk.Button(self.online_button_frame, text="Load Original", width=25, command=lambda: self.load_original(character))
                self.load_original_button.pack(side=tk.LEFT, padx=5)
                self.register_tooltip(self.load_original_button, "Restore the original costume list for this character from the backup.")
            else:
                self.load_original_button = None
                print(f"No backup file found at {backup_ssf}, 'Load Original' button not added.")

            self.save_button = tk.Button(left_panel, text="Save Changes", command=lambda: self.save_changes(character))
            self.save_button.pack(side=tk.LEFT, pady=5)
            self.register_tooltip(self.save_button, "Save costume changes to the SSF file.")

            self.save_play_button = tk.Button(left_panel, text="Save and Play", command=lambda: self.save_and_play(character))
            self.save_play_button.pack(side=tk.LEFT, pady=5)
            self.register_tooltip(self.save_play_button, "Save costume changes and launch SSF2.")

            # tk.Button(left_panel, text="Open Recolors Directory", command=self.open_recolors_directory).pack(pady=5)
            # self.register_tooltip(tk.Button(left_panel, text="Open Recolors Directory"), "Open the directory containing recolor sheets for this character.")

            self.update_button_states()

            self.costume_list_frame.pack(fill=tk.BOTH, expand=True)
            self.set_busy("Loading costume list", progress=100)
            self.clear_busy()

            # Select first non-protected costume or first costume
            if self.all_costumes:
                select_idx = self.protected_count - 1 if self.protected_count < len(self.all_costumes) else 0
                self.costume_listbox.select_set(select_idx)
                self.last_selected_listbox = 'costume'
                self.update_preview()
            self.costume_listbox.bind("<ButtonRelease-1>", lambda event: [setattr(self, 'last_selected_listbox', 'costume'), self.update_preview()])
            self.loaded_listbox.bind("<ButtonRelease-1>", lambda event: [setattr(self, 'last_selected_listbox', 'loaded'), self.update_button_states(), self.update_preview() if self.loaded_listbox.curselection() else None])
            self.remove_listbox.bind("<ButtonRelease-1>", lambda event: self.update_button_states())

            # Trigger initial preview update only if a selection exists
            if self.costume_listbox.curselection():
                self.update_preview()

        except Exception as e:
            print(f"Error loading costume list: {str(e)}")
            self.hide_costume_list()
            self.clear_busy()

    def debounce_preview_update(self):
        if self.preview_debounce_timer:
            self.after_cancel(self.preview_debounce_timer)
        self.preview_debounce_timer = self.after(self.preview_debounce_delay, self.update_preview)

    def update_preview(self):
        import json
        import hashlib
        
        
        # Debounce: Skip if called within 300ms of last update
        if not hasattr(self, '_last_preview_time'):
            self._last_preview_time = 0        
        current_time = time.time() * 1000  # Convert to milliseconds
        
        self._last_preview_time = current_time        
        print("Update preview called")
        if not hasattr(self, 'preview_canvas') or not hasattr(self, 'preview_label'):
            print("Error: Preview canvas or label not defined.")
            return

        if self.last_selected_listbox == 'costume' and self.costume_listbox.curselection():
            idx = self.costume_listbox.curselection()[0]
            costume = self.all_costumes[idx][1] if idx < len(self.all_costumes) else None
        elif self.last_selected_listbox == 'loaded' and self.loaded_listbox.curselection():
            idx = self.loaded_listbox.curselection()[0]
            costume = self.loaded_costumes[idx] if idx < len(self.loaded_costumes) else None
        else:
            costume = None

        if not costume:
            self.preview_label.config(text="Select a costume to preview")
            self.preview_canvas.delete("all")
            return

        character = self.selected_character.get()
        if character == "Custom":
            character = self.custom_character.get().strip()

        palette_swap = costume.get("paletteSwap")
        palette_swap_pa = costume.get("paletteSwapPA")
        if not (palette_swap and palette_swap_pa and
                "colors" in palette_swap and "replacements" in palette_swap and
                "colors" in palette_swap_pa and "replacements" in palette_swap_pa):
            self.preview_label.config(text="Invalid costume data")
            return

        normalized_character = character.lower().replace(" ", "").replace("(sandbox)", "")
        image_url = self.character_to_url.get(normalized_character)
        if not image_url:
            self.preview_label.config(text=f"No preview for {character}")
            return

        try:
            costume_json = json.dumps(costume, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()

            if costume_hash in self.preview_cache:
                image = self.preview_cache[costume_hash]
            else:
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
                    r1, g1, b1 = (color1 >> 16) & 255, (color1 >> 8) & 255, color1 & 255
                    r2, g2, b2 = (color2 >> 16) & 255, (color2 >> 8) & 255, color2 & 255
                    return (abs(r1 - r2) <= tolerance and
                            abs(g1 - g2) <= tolerance and
                            abs(b1 - b2) <= tolerance)

                cache_swap = {}
                cache_swap_pa = {}

                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        if a == 0:
                            continue
                        pixel_int = ((r << 16) + (g << 8) + b) | 0xFF000000

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

                        new_r = (new_pixel_int >> 16) & 255
                        new_g = (new_pixel_int >> 8) & 255
                        new_b = new_pixel_int & 255
                        pixels[x, y] = (new_r, new_g, new_b, a)

                        pixel_int = ((new_r << 16) + (new_g << 8) + new_b) | 0xFF000000
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

                        new_r = (new_pixel_int >> 16) & 255
                        new_g = (new_pixel_int >> 8) & 255
                        new_b = new_pixel_int & 255
                        pixels[x, y] = (new_r, new_g, new_b, a)

                image.thumbnail((600, 400), Image.Resampling.LANCZOS)
                self.preview_cache[costume_hash] = image

            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_canvas.create_image((600 - image.width) // 2, (400 - image.height) // 2,
                                            anchor="nw", image=self.preview_photo)
            self.preview_label.config(text="")
            print("Preview updated successfully.")
        except Exception as e:
            print(f"Error updating preview: {str(e)}")
            self.preview_label.config(text="Failed to load preview")

    def load_more_costumes(self, character):
        print(f"Loading next 50 costumes for character '{character}'...")
        self.load_costume_list_for_character(character, offset=self.costume_offset, limit=50)

    def load_all_costumes(self, character):
        print(f"Loading all costumes for character '{character}'...")
        self.load_costume_list_for_character(character, offset=0, limit=self.total_costumes)

    def save_changes(self, character):
        print("Saving costume changes...")
        if not os.access(self.original_ssf, os.W_OK):
            print(f"Cannot write to: {self.original_ssf}")
            messagebox.showerror("Error", f"Cannot write to SSF file: {self.original_ssf}")
            return

        self.set_busy("Saving changes", progress=0)
        modified_swf = os.path.abspath("modified.swf")
        try:
            costumes_to_save = [costume for idx, costume in self.all_costumes]
            print(f"Updating costumes for '{character}'...")
            update_costumes(self.loaded_misc_as, self.loaded_misc_as, character, costumes_to_save)
            self.set_busy("Saving changes", progress=33)

            if not os.path.exists(self.temp_swf):
                print(f"Decompressing {self.ssf_source}...")
                decompress_ssf(self.ssf_source, self.temp_swf)
            self.set_busy("Saving changes", progress=50)

            print("Injecting modified Misc.as...")
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
                    print("User cancelled JPEXS Decompiler operation.")
                    self.clear_busy()
                    return
            inject_misc_as(self.temp_swf, self.loaded_misc_as, modified_swf, self.java_path, self.ffdec_jar)
            self.set_busy("Saving changes", progress=75)

            print(f"Compressing to {self.original_ssf}...")
            compress_swf(modified_swf, self.original_ssf)
            self.set_busy("Saving changes", progress=90)

            # Update the ssf_source backup to match the modified SSF
            backup_ssf = self.handle_backup(self.original_ssf)
            print(f"Updated ssf_source backup to: {backup_ssf}")
            self.ssf_source = backup_ssf
            self.set_busy("Saving changes", progress=95)

            if os.path.exists(self.original_ssf):
                print(f"SSF updated: {self.original_ssf}")
            else:
                raise Exception("SSF file not found after save")

            # Extract the updated Misc.as to ensure loaded_misc_as is current
            extract_misc_as(modified_swf, self.loaded_misc_as, self.java_path, self.ffdec_jar)
            print(f"Refreshed loaded_misc_as: {self.loaded_misc_as}")

            messagebox.showinfo("Success", f"Updated costumes for {character}")
            self.hide_costume_list()
            self.clear_busy()
        except Exception as e:
            print(f"Error saving: {str(e)}")
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
            self.clear_busy()
        finally:
            self.cleanup_temp_files([modified_swf])

    def hide_costume_list(self):
        print("Hiding costume list...")
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
    print("Starting SSF2ModGUI application...")
    app = SSF2ModGUI()
    app.mainloop()    
    print("Application closed.")