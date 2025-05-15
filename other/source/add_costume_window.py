import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, Toplevel, Label, Entry, Button
from PIL import Image, ImageTk, ImageDraw
import json
import requests
from io import BytesIO
import hashlib
import os
import subprocess
import time
import platform
from utils import format_color_for_as3, color_to_int, int_to_color_str

class CanvasState:
    def __init__(self):
        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.original_width = 0
        self.original_height = 0

class CanvasPanHandler:
    def __init__(self, canvas, update_callback, state):
        self.canvas = canvas
        self.update_callback = update_callback
        self.state = state
        self._bind_events()

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self.state.is_panning = True
        self.state.pan_start_x = event.x
        self.state.pan_start_y = event.y

    def on_move(self, event):
        if not self.state.is_panning:
            return
        dx = event.x - self.state.pan_start_x
        dy = event.y - self.state.pan_start_y
        self.state.pan_x -= dx / self.state.zoom_scale
        self.state.pan_y -= dy / self.state.zoom_scale
        self.state.pan_start_x = event.x
        self.state.pan_start_y = event.y
        self.update_callback()

    def on_release(self, event):
        self.state.is_panning = False

class AddCostumeWindow(tk.Toplevel):
    def __init__(self, main_app, character, on_save_callback=None, costume_data=None, image_path=None, source=None, current_idx=None, loaded_idx=None):
        super().__init__()
        self.main_app = main_app
        self.character = character
        self.on_save_callback = on_save_callback or (lambda costume, source, current_idx, loaded_idx: None)
        self.costume_data = costume_data
        self.image_path = image_path
        self.source = source
        self.current_idx = current_idx
        self.loaded_idx = loaded_idx
        self._setup_window()
        self._initialize_variables()
        self._create_ui()
        self._load_initial_data()

    def _setup_window(self):
        self.title("Add New Costume" if not self.costume_data else "Edit Costume")
        self.transient(self.main_app)
        self.grab_set()
        self.main_app.center_toplevel(self, 1200, 800)
        self.focus_set()
        initial_width = 1204
        initial_height = 712
        self.minsize(initial_width, initial_height)

    def _initialize_variables(self):
        self.uploaded_image = None
        self.original_recolor_sheet = None
        self.recolor_image = None  # Will store the precomputed palette-swapped image
        self.uploaded_photo = None
        self.recolor_photo = None
        self.extracted_palette_photo = None
        self.converted_palette_photo = None
        self.strip_data = []
        self.uploaded_palette_strips = []
        self.original_palette_strips = []
        self.uploaded_canvas_state = CanvasState()
        self.recolor_canvas_state = CanvasState()
        self.extracted_canvas_state = CanvasState()
        self.converted_canvas_state = CanvasState()
        self.online_name = self.main_app.config.get("online_name", "")
        self.uploaded_file_path = None
        self.last_image_mtime = 0
        self.last_costume_json = None  # Cache last JSON to detect changes

    def _create_ui(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(left_panel, text="New Costume JSON:").pack(pady=5)
        self.new_costume_text = scrolledtext.ScrolledText(left_panel, height=20, width=50)
        self.new_costume_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self._populate_json_text()

        self.button_frame = tk.Frame(left_panel)
        self.button_frame.pack(pady=5, fill=tk.X)

        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self._create_image_previews(right_panel)
        self._create_palette_previews(right_panel)
        self._create_buttons()
        self._setup_event_bindings()

    def _populate_json_text(self):
        if self.costume_data:
            self.new_costume_text.insert(tk.END, json.dumps(self.costume_data, indent=2))
        else:
            default_costume = {
                "info": "",
                "paletteSwap": {"colors": [], "replacements": []},
                "paletteSwapPA": {"colors": [], "replacements": []}
            }
            self.new_costume_text.insert(tk.END, json.dumps(default_costume, indent=2))

    def _create_image_previews(self, parent):
        image_previews_frame = tk.Frame(parent)
        image_previews_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(image_previews_frame, text="Uploaded Image Preview", font=("Arial", 12)).pack(pady=5)
        self.uploaded_preview_canvas = tk.Canvas(image_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.uploaded_preview_canvas.pack(pady=5)
        self.zoom_var = tk.DoubleVar(value=0.0)
        zoom_frame = tk.Frame(image_previews_frame)
        zoom_frame.pack(pady=5)
        tk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_slider = tk.Scale(zoom_frame, from_=-2.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.zoom_var, command=lambda _: self.update_uploaded_preview())
        self.zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.uploaded_preview_label = tk.Label(image_previews_frame, text="Upload an image to see the preview", fg="gray")
        self.uploaded_preview_label.pack(pady=5)

        tk.Label(image_previews_frame, text="Recolor Preview", font=("Arial", 12)).pack(pady=5)
        self.recolor_preview_canvas = tk.Canvas(image_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.recolor_preview_canvas.pack(pady=5)
        self.recolor_zoom_var = tk.DoubleVar(value=0.0)
        recolor_zoom_frame = tk.Frame(image_previews_frame)
        recolor_zoom_frame.pack(pady=5)
        tk.Label(recolor_zoom_frame, text="Recolor Zoom:").pack(side=tk.LEFT)
        self.recolor_zoom_slider = tk.Scale(recolor_zoom_frame, from_=-2.0, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.recolor_zoom_var, command=lambda _: self.update_recolor_preview())
        self.recolor_zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.recolor_preview_label = tk.Label(image_previews_frame, text="Select a character and upload an image to see the recolor", fg="gray")
        self.recolor_preview_label.pack(pady=5)

    def _create_palette_previews(self, parent):
        palette_previews_frame = tk.Frame(parent)
        palette_previews_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(palette_previews_frame, text="Extracted Palette Strips", font=("Arial", 12)).pack(pady=5)
        self.extracted_palette_canvas = tk.Canvas(palette_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.extracted_palette_canvas.pack(pady=5)
        self.extracted_palette_label = tk.Label(palette_previews_frame, text="Upload an image to see the extracted palettes", fg="gray")
        self.extracted_palette_label.pack(pady=5)

        tk.Label(palette_previews_frame, text="Converted Palette Strips", font=("Arial", 12)).pack(pady=5)
        self.converted_palette_canvas = tk.Canvas(palette_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.converted_palette_canvas.pack(pady=5)
        self.converted_palette_label = tk.Label(palette_previews_frame, text="Edit JSON data to see converted palettes", fg="gray")
        self.converted_palette_label.pack(pady=5)

    def _create_buttons(self):
        tk.Button(self.button_frame, text="Upload Image", command=self.upload_image).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Upload Recolor Sheet", command=self.upload_recolor_sheet).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Save", command=self.prompt_for_costume_name).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Refresh Previews", command=self.refresh_previews).pack(side=tk.LEFT, padx=5)

    def _setup_event_bindings(self):
        self.uploaded_pan_handler = CanvasPanHandler(self.uploaded_preview_canvas, self.update_uploaded_preview, self.uploaded_canvas_state)
        self.recolor_pan_handler = CanvasPanHandler(self.recolor_preview_canvas, self.update_recolor_preview, self.recolor_canvas_state)
        self.extracted_pan_handler = CanvasPanHandler(self.extracted_palette_canvas, self.update_extracted_palette_preview, self.extracted_canvas_state)
        self.converted_pan_handler = CanvasPanHandler(self.converted_palette_canvas, self.update_converted_palette_preview, self.converted_canvas_state)
        self.new_costume_text.bind("<<Modified>>", lambda event: [
            self._update_recolor_image(),
            self.update_recolor_preview(),
            self.update_converted_palette_preview(),
            self.new_costume_text.edit_modified(False)
        ])
    def _load_initial_data(self):
        self.load_recolor_sheet_preview()
        if self.image_path and os.path.exists(self.image_path):
            self._load_image_from_path(self.image_path)
        elif self.costume_data:
            self.generate_image_from_preview()
        self._update_json_with_palette_strips()
        self._update_recolor_image()  # Precompute initial recolor image
        self.update_all_previews()

    def _load_image_from_path(self, path):
        try:
            self.uploaded_image = Image.open(path).convert("RGBA")
            self.uploaded_file_path = path
            self.uploaded_canvas_state.original_width, self.uploaded_canvas_state.original_height = self.uploaded_image.size
            self.extract_palette_strips(self.uploaded_image)
            self._draw_palette_lines()
            self.last_image_mtime = os.path.getmtime(path)
            print(f"Successfully loaded image from {path}")
            self._update_recolor_image()  # Update recolor image when a new image is loaded
        except FileNotFoundError:
            print(f"File not found: {path}")
            self.uploaded_image = None
            self.uploaded_file_path = None
        except Image.UnidentifiedImageError:
            print(f"Invalid image file: {path}")
            self.uploaded_image = None
            self.uploaded_file_path = None
        except Exception as e:
            print(f"Unexpected error loading image: {str(e)}")
            self.uploaded_image = None
            self.uploaded_file_path = None

    def _draw_palette_lines(self):
        draw = ImageDraw.Draw(self.uploaded_image)
        for row, start_x, end_x in self.strip_data:
            draw.line([(start_x, row), (start_x, row + 1)], fill=(255, 0, 0, 255), width=1)
            draw.line([(end_x, row), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
            if row > 0:
                draw.line([(start_x, row - 1), (end_x, row - 1)], fill=(255, 0, 0, 255), width=1)
            if row < self.uploaded_canvas_state.original_height - 1:
                draw.line([(start_x, row + 1), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)

    def _update_json_with_palette_strips(self):
        if self.uploaded_image and self.original_palette_strips and self.uploaded_palette_strips:
            costume = {
                "info": self.costume_data.get("info", "") if self.costume_data else "",
                "paletteSwap": {
                    "colors": [int_to_color_str(color_to_int(c)) for c in self.original_palette_strips[0]],
                    "replacements": [int_to_color_str(color_to_int(c)) for c in self.uploaded_palette_strips[0]]
                },
                "paletteSwapPA": {
                    "colors": [int_to_color_str(color_to_int(c)) for c in self.original_palette_strips[1]] if len(self.original_palette_strips) > 1 else [],
                    "replacements": [int_to_color_str(color_to_int(c)) for c in self.uploaded_palette_strips[1]] if len(self.uploaded_palette_strips) > 1 else []
                }
            }
            self.new_costume_text.delete("1.0", tk.END)
            self.new_costume_text.insert(tk.END, json.dumps(costume, indent=2))
            print("Updated JSON with palette strips from loaded/generated image")
            self._update_recolor_image()  # Update recolor image after JSON update

    def _update_recolor_image(self):
        """Precompute the palette-swapped image based on current JSON and recolor sheet."""
        if not self.original_recolor_sheet:
            self.recolor_image = None
            self.recolor_preview_label.config(text="No recolor sheet loaded")
            return

        # Get current JSON and check if it changed
        try:
            current_json = self.new_costume_text.get("1.0", tk.END).strip()
            if current_json == self.last_costume_json:
                return  # No change, skip recomputation
            costume = json.loads(current_json)
            self.last_costume_json = current_json
        except json.JSONDecodeError:
            self.recolor_image = self.original_recolor_sheet.copy().convert("RGBA")
            self.recolor_preview_label.config(text="Invalid JSON, showing original sheet")
            return

        # Create a copy of the original sheet and apply palette swap
        image = self.original_recolor_sheet.copy().convert("RGBA")
        try:
            self._apply_palette_swap(image, costume)
            self.recolor_image = image.convert("RGBA")  # Ensure RGBA mode
            self.recolor_canvas_state.original_width, self.recolor_canvas_state.original_height = self.recolor_image.size
            print("Precomputed palette-swapped recolor image")
        except Exception as e:
            print(f"Error applying palette swap: {str(e)}")
            self.recolor_image = self.original_recolor_sheet.copy().convert("RGBA")
            self.recolor_preview_label.config(text="Error applying palette, showing original sheet")
    def update_all_previews(self):
        self.update_uploaded_preview()
        self.update_extracted_palette_preview()
        self.update_recolor_preview()
        self.update_converted_palette_preview()

    def generate_image_from_preview(self):
        if not self.costume_data:
            self.uploaded_preview_label.config(text="No costume data to generate image")
            return
        try:
            costume_json = json.dumps(self.costume_data, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()
            if costume_hash not in self.main_app.preview_cache:
                self.uploaded_preview_label.config(text="No preview image available")
                return
            image = self.main_app.preview_cache[costume_hash]
            info = self.costume_data.get('info', 'No Info').replace(' ', '_')
            character_dir = os.path.join(os.getcwd(), "recolors", self.character)
            os.makedirs(character_dir, exist_ok=True)
            self.uploaded_file_path = os.path.join(character_dir, f"{info}.png")
            image.save(self.uploaded_file_path)
            self.uploaded_image = Image.open(self.uploaded_file_path).convert("RGBA")
            self.uploaded_canvas_state.original_width, self.uploaded_canvas_state.original_height = self.uploaded_image.size
            self.extract_palette_strips(self.uploaded_image)
            self._draw_palette_lines()
            self.last_image_mtime = os.path.getmtime(self.uploaded_file_path)
            print("Successfully generated and loaded image from preview")
            self._update_recolor_image()  # Update recolor image after generating
        except Exception as e:
            print(f"Error generating image from preview: {str(e)}")
            self.uploaded_image = None
            self.uploaded_file_path = None
            self.uploaded_preview_label.config(text="Failed to generate image")

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if not file_path:
            return
        self._load_image_from_path(file_path)
        self._update_json_with_palette_strips()
        self.update_all_previews()

    def refresh_previews(self):
        if self.uploaded_file_path and os.path.exists(self.uploaded_file_path):
            current_mtime = os.path.getmtime(self.uploaded_file_path)
            if current_mtime > self.last_image_mtime:
                self._load_image_from_path(self.uploaded_file_path)
                self._update_json_with_palette_strips()
        self._update_recolor_image()  # Refresh recolor image if JSON or image changed
        self.update_all_previews()

    def load_recolor_sheet_preview(self):
        normalized_character = self.character.lower().replace(" ", "").replace("(sandbox)", "")
        image_url = self.main_app.character_to_url.get(normalized_character)
        if not image_url:
            self.recolor_preview_label.config(text=f"No preview for {self.character}")
            return
        try:
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_file = os.path.join(self.main_app.image_cache_dir, f"{url_hash}.png")
            if os.path.exists(cache_file):
                img = Image.open(cache_file).convert("RGBA")
            else:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content)).convert("RGBA")
                img.save(cache_file)
            self.original_recolor_sheet = img
            self.extract_original_colors()
            self._update_recolor_image()  # Precompute recolor image after loading sheet
            self.update_recolor_preview()
            self.update_extracted_palette_preview()
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to load recolor sheet: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recolor sheet: {str(e)}")

    def upload_recolor_sheet(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if not file_path:
            return
        try:
            self.original_recolor_sheet = Image.open(file_path).convert("RGBA")
            self.extract_original_colors()
            self._update_recolor_image()  # Precompute recolor image after uploading sheet
            self.update_recolor_preview()
            self.update_extracted_palette_preview()
            self.update_converted_palette_preview()
        except Image.UnidentifiedImageError:
            messagebox.showerror("Error", f"Invalid image format: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process recolor sheet: {str(e)}")

    def extract_original_colors(self):
        if not self.original_recolor_sheet:
            return
        self.extract_palette_strips(self.original_recolor_sheet)
        self.original_palette_strips = self.uploaded_palette_strips
        self.uploaded_palette_strips = []

    def extract_palette_strips(self, img):
        if not img:
            return
        pixels = img.load()
        width, height = img.size
        row_colors = [set() for _ in range(height)]
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                row_colors[y].add(color)
        common_colors = set.intersection(*row_colors) if row_colors else set()
        palette_rows = []
        self.strip_data = []

        for y in range(height):
            if len(palette_rows) >= 2:
                break
            color_counts = {}
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                color_counts[color] = color_counts.get(color, 0) + 1
            ignored_colors = {c for c, count in color_counts.items() if count > width // 2 or c in common_colors}
            adjacent_colors = set()
            if y > 0:
                adjacent_colors.update(row_colors[y - 1])
            if y < height - 1:
                adjacent_colors.update(row_colors[y + 1])
            ignored_colors.update(adjacent_colors)

            has_valid_strip = False
            valid_strip_colors = []
            start_x = 0
            end_x = 0
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                if color not in ignored_colors:
                    strip_colors = [color]
                    for pos in range(x + 1, width):
                        r2, g2, b2, a2 = pixels[pos, y]
                        color2 = "transparent" if a2 == 0 else (r2 << 16) + (g2 << 8) + b2 | (a2 << 24)
                        if color2 not in ignored_colors:
                            strip_colors.append(color2)
                        else:
                            break
                    if len(set(strip_colors) - {"transparent"}) >= 5:
                        if self._is_valid_strip(pixels, y, x, pos - 1, strip_colors, height):
                            has_valid_strip = True
                            self.strip_data.append((y, x, pos - 1))
                            valid_strip_colors = strip_colors
                            start_x, end_x = x, pos - 1
                            break
            if has_valid_strip and y not in palette_rows:
                palette_rows.append((y, start_x, end_x, valid_strip_colors))

        self.uploaded_palette_strips = []
        for y, start_x, end_x, valid_strip_colors in palette_rows:
            strip_colors = []
            adjacent_colors = set()
            if y > 0:
                for x in range(width):
                    r, g, b, a = pixels[x, y - 1]
                    color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                    adjacent_colors.add(color)
            if y < height - 1:
                for x in range(width):
                    r, g, b, a = pixels[x, y + 1]
                    color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                    adjacent_colors.add(color)
            for x in range(start_x, end_x + 1):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                if color in adjacent_colors:
                    strip_colors.append("transparent")
                else:
                    color_str = color if color == "transparent" else f"{color:08X}"
                    strip_colors.append(color_str)
            self.uploaded_palette_strips.append(strip_colors)

    def _is_valid_strip(self, pixels, y, start_x, end_x, strip_colors, height):
        for pos in range(start_x, end_x + 1):
            if y > 0:
                r_above, g_above, b_above, a_above = pixels[pos, y - 1]
                above_color = "transparent" if a_above == 0 else (r_above << 16) + (g_above << 8) + b_above | (a_above << 24)
                if above_color in strip_colors:
                    return False
            if y < height - 1:
                r_below, g_below, b_below, a_below = pixels[pos, y + 1]
                below_color = "transparent" if a_below == 0 else (r_below << 16) + (g_below << 8) + b_below | (a_below << 24)
                if below_color in strip_colors:
                    return False
        return True

    def _get_full_strip_colors(self, pixels, y, start_x, end_x, ignored_colors):
        full_strip_colors = []
        for pos in range(start_x, end_x + 1):
            r, g, b, a = pixels[pos, y]
            if a != 0:
                color = (r << 16) + (g << 8) + b | (a << 24)
                include_color = (y == 0 or pixels[pos, y - 1] != (r, g, b, a)) and \
                                (y >= self.uploaded_canvas_state.original_height - 1 or pixels[pos, y + 1] != (r, g, b, a))
                if include_color and color not in ignored_colors:
                    full_strip_colors.append(f"{color:08X}")
            else:
                full_strip_colors.append("transparent")
        return full_strip_colors

    def update_uploaded_preview(self):
        self.uploaded_preview_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        if not self.uploaded_image:
            self.uploaded_preview_label.config(text="No image loaded")
            return
        try:
            img = self.uploaded_image.copy()
            self.uploaded_canvas_state.zoom_scale = 2 ** self.zoom_var.get()
            new_width = int(self.uploaded_canvas_state.original_width * self.uploaded_canvas_state.zoom_scale)
            new_height = int(self.uploaded_canvas_state.original_height * self.uploaded_canvas_state.zoom_scale)
            img = img.resize((new_width, new_height), Image.Resampling.NEAREST)
            display_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            offset_x, offset_y = self._calculate_offsets(new_width, new_height, canvas_width, canvas_height, self.uploaded_canvas_state)
            display_img.paste(img, (offset_x, offset_y))
            self.uploaded_photo = ImageTk.PhotoImage(display_img)
            self.uploaded_preview_canvas.create_image(0, 0, anchor="nw", image=self.uploaded_photo)
            self.uploaded_preview_label.config(text="")
        except Exception as e:
            print(f"Error updating uploaded preview: {str(e)}")
            self.uploaded_preview_label.config(text="Failed to display image")

    def update_recolor_preview(self):
        """Update the recolor preview by resizing and panning the precomputed recolor image."""
        self.recolor_preview_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        if not self.recolor_image:
            self.recolor_preview_label.config(text="No recolor image available")
            return

        try:
            img = self.recolor_image.copy()  # Use precomputed image
            self.recolor_canvas_state.zoom_scale = 2 ** self.recolor_zoom_var.get()
            new_width = int(self.recolor_canvas_state.original_width * self.recolor_canvas_state.zoom_scale)
            new_height = int(self.recolor_canvas_state.original_height * self.recolor_canvas_state.zoom_scale)
            # Prevent resize errors with extreme zoom values
            if new_width <= 0 or new_height <= 0:
                self.recolor_preview_label.config(text="Zoom level too extreme")
                return
            img = img.resize((new_width, new_height), Image.Resampling.NEAREST)
            display_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            offset_x, offset_y = self._calculate_offsets(new_width, new_height, canvas_width, canvas_height, self.recolor_canvas_state)
            display_img.paste(img, (offset_x, offset_y))
            self.recolor_photo = ImageTk.PhotoImage(display_img)
            self.recolor_preview_canvas.create_image(0, 0, anchor="nw", image=self.recolor_photo)
            self.recolor_preview_label.config(text="")
        except Exception as e:
            print(f"Error updating recolor preview: {str(e)}")
            self.recolor_preview_label.config(text="Failed to display recolor")

    def _apply_palette_swap(self, image, costume):
        palette_swap = costume.get("paletteSwap", {"colors": [], "replacements": []})
        palette_swap_pa = costume.get("paletteSwapPA", {"colors": [], "replacements": []})
        pixels = image.load()
        width, height = image.size
        color_map = {}
        for orig, repl in zip(palette_swap["colors"], palette_swap["replacements"]):
            orig_int = self.main_app.convert_color(orig) if orig != "transparent" else "transparent"
            repl_int = self.main_app.convert_color(repl) if repl != "transparent" else "transparent"
            if orig_int != repl_int:
                color_map[orig_int] = repl_int
        for orig, repl in zip(palette_swap_pa["colors"], palette_swap_pa["replacements"]):
            orig_int = self.main_app.convert_color(orig) if orig != "transparent" else "transparent"
            repl_int = self.main_app.convert_color(repl) if repl != "transparent" else "transparent"
            if orig_int != repl_int:
                color_map[orig_int] = repl_int
        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                if color in color_map:
                    new_color = color_map[color]
                    pixels[x, y] = (0, 0, 0, 0) if new_color == "transparent" else (
                        (new_color >> 16) & 255, (new_color >> 8) & 255, new_color & 255, (new_color >> 24) & 255
                    )

    def _calculate_offsets(self, new_width, new_height, canvas_width, canvas_height, state):
        offset_x = max(0, (canvas_width - new_width) // 2) - int(state.pan_x)
        offset_y = max(0, (canvas_height - new_height) // 2) - int(state.pan_y)
        if new_width > canvas_width:
            offset_x = max(-(new_width - canvas_width), min(0, offset_x))
        else:
            offset_x = max(0, min(offset_x, canvas_width - new_width))
        if new_height > canvas_height:
            offset_y = max(-(new_height - canvas_height), min(0, offset_y))
        else:
            offset_y = max(0, min(offset_y, canvas_height - new_height))
        return offset_x, offset_y

    def update_extracted_palette_preview(self):
        self.extracted_palette_canvas.delete("all")
        row_height = 45
        
        uploaded_strips_to_display = self.uploaded_palette_strips[:2]
        original_strips_to_display = self.original_palette_strips[:2]
        all_strips = uploaded_strips_to_display + original_strips_to_display
        
        if all_strips:
            max_length = max(len(strip) for strip in all_strips)
        else:
            max_length = 0
        
        required_width = 20 + max_length * 10  # 10 pixels per color, plus 20 for padding
        required_height = 20 + len(all_strips) * row_height  # 45 pixels per strip, plus 20 for padding
        
        palette_img = Image.new("RGBA", (required_width, required_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(palette_img)
        
        y_offset = 10
        self._draw_palette_strips(draw, y_offset, row_height, uploaded_strips_to_display, "Uploaded")
        y_offset += len(uploaded_strips_to_display) * row_height
        self._draw_palette_strips(draw, y_offset, row_height, original_strips_to_display, "Original")
        
        self.extracted_palette_photo = ImageTk.PhotoImage(palette_img)
        self.extracted_palette_canvas.create_image(-self.extracted_canvas_state.pan_x, -self.extracted_canvas_state.pan_y, anchor="nw", image=self.extracted_palette_photo)
        self.extracted_palette_label.config(text="")

    def update_converted_palette_preview(self):
        self.converted_palette_canvas.delete("all")
        row_height = 45
        
        try:
            costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
            palette_swap = costume.get("paletteSwap", {"colors": [], "replacements": []})
            palette_swap_pa = costume.get("paletteSwapPA", {"colors": [], "replacements": []})
            
            lists = [
                palette_swap.get("colors", []),
                palette_swap.get("replacements", []),
                palette_swap_pa.get("colors", []),
                palette_swap_pa.get("replacements", [])
            ]
            if any(lists):
                max_length = max(len(lst) for lst in lists)
            else:
                max_length = 0
            
            required_width = 20 + max_length * 10  # 10 pixels per color, plus 20 for padding
            required_height = 20 + 4 * row_height  # 4 rows at 45 pixels each, plus 20 for padding
            
            palette_img = Image.new("RGBA", (required_width, required_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(palette_img)
            
            y_offset = 10
            self._draw_converted_strips(draw, y_offset, row_height, palette_swap, "paletteSwap")
            y_offset += 2 * row_height
            self._draw_converted_strips(draw, y_offset, row_height, palette_swap_pa, "paletteSwapPA")
            
            self.converted_palette_photo = ImageTk.PhotoImage(palette_img)
            self.converted_palette_canvas.create_image(-self.converted_canvas_state.pan_x, -self.converted_canvas_state.pan_y, anchor="nw", image=self.converted_palette_photo)
            self.converted_palette_label.config(text="")
        except json.JSONDecodeError:
            self.converted_palette_label.config(text="Invalid JSON data")

    def _draw_palette_strips(self, draw, y_offset, row_height, strips, prefix):
        for i, strip in enumerate(strips):
            if i >= 2:
                break
            draw.text((10, y_offset), f"{prefix} paletteSwap{'PA' if i else ''}", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(strip):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    color_int = int(color, 16)
                    r, g, b, a = (color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255, (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
            y_offset += row_height

    def _draw_converted_strips(self, draw, y_offset, row_height, palette, name):
        for key in ["colors", "replacements"]:
            draw.text((10, y_offset), f"{name} {key}", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(palette.get(key, [])):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    color_int = self.main_app.convert_color(color)
                    if color_int != 0:
                        r, g, b, a = (color_int >> 16) & 255, (color_int >> 8) & 255, color_int & 255, (color_int >> 24) & 255
                        draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
            y_offset += row_height

    def prompt_for_costume_name(self):
        dialog = Toplevel(self)
        dialog.title("Costume Name")
        dialog.transient(self)
        dialog.grab_set()
        self.main_app.center_toplevel(dialog, 400, 200)
        tk.Label(dialog, text="Costume Name:").pack(pady=5)
        costume_name_entry = tk.Entry(dialog)
        costume_name_entry.pack(pady=5)
        tk.Label(dialog, text="Online Name:").pack(pady=5)
        online_name_entry = tk.Entry(dialog)
        online_name_entry.insert(0, self.online_name)
        online_name_entry.pack(pady=5)
        tk.Label(dialog, text="Note: Names must be JSON-friendly.\nAvoid special characters like quotes and braces.").pack(pady=5)
        tk.Button(dialog, text="Save", command=lambda: self._save_costume_from_dialog(costume_name_entry, online_name_entry, dialog)).pack(pady=10)

    def _save_costume_from_dialog(self, costume_name_entry, online_name_entry, dialog):
        costume_name = costume_name_entry.get().strip()
        online_name = online_name_entry.get().strip()
        if not costume_name or not online_name:
            messagebox.showerror("Error", "Both fields are required.")
            return
        self.online_name = online_name
        self.main_app.config["online_name"] = online_name
        self.main_app.save_config()
        self.save_new_costume(costume_name, online_name)
        dialog.destroy()

    def save_new_costume(self, costume_name, online_name):
        try:
            # Parse JSON from text area
            costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
            
            # Set the costume name in the 'info' field
            costume['info'] = costume_name + " by " + online_name
            
            # Remove 'display_name' if it exists to avoid confusion
            if 'display_name' in costume:
                del costume['display_name']
            
            # Log the costume data for debugging
            print(f"Saving costume: {json.dumps(costume, indent=2)}")
            
            # Call the callback with the costume data
            self.on_save_callback(costume, self.source, self.current_idx, self.loaded_idx)
            
            # Close the window
            self.destroy()
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON data: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save costume: {str(e)}")