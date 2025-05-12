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

class AddCostumeWindow(tk.Toplevel):    
    def __init__(self, main_app, character, costume_data=None, image_path=None, source=None, current_idx=None, loaded_idx=None):
        super().__init__()
        self.main_app = main_app
        self.character = character
        self.costume_data = costume_data
        self.image_path = image_path
        self.source = source
        self.current_idx = current_idx
        self.loaded_idx = loaded_idx
        self.title("Add New Costume" if not costume_data else "Edit Costume")
        self.transient(main_app)
        self.grab_set()
        self.main_app.center_toplevel(self, 1200, 800)
        self.focus_set()

        # Instance variables
        self.uploaded_image = None
        self.original_recolor_sheet = None
        self.recolor_image = None
        self.uploaded_photo = None
        self.recolor_photo = None
        self.extracted_palette_photo = None
        self.converted_palette_photo = None
        self.strip_data = []
        self.original_strip_data = []
        self.uploaded_palette_strips = []
        self.original_palette_strips = []
        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.is_panning = False
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.original_width = 0
        self.original_height = 0
        self.recolor_zoom_scale = 1.0
        self.recolor_pan_x = 0
        self.recolor_pan_y = 0
        self.recolor_is_panning = False
        self.recolor_pan_start_x = 0
        self.recolor_pan_start_y = 0
        self.recolor_original_width = 0
        self.recolor_original_height = 0
        self.extracted_pan_x = 0
        self.extracted_pan_y = 0
        self.extracted_is_panning = False
        self.extracted_pan_start_x = 0
        self.extracted_pan_start_y = 0
        self.converted_pan_x = 0
        self.converted_pan_y = 0
        self.converted_is_panning = False
        self.converted_pan_start_x = 0
        self.converted_pan_start_y = 0
        self.online_name = self.main_app.config.get("online_name", "")
        self.uploaded_file_path = None
        self.last_image_mtime = 0

        # Main frame
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel: JSON editor and buttons
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Right panel: Previews
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Left panel content
        tk.Label(left_panel, text="New Costume JSON:").pack(pady=5)
        self.new_costume_text = scrolledtext.ScrolledText(left_panel, height=20, width=50)
        self.new_costume_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        if costume_data:
            self.new_costume_text.insert(tk.END, json.dumps(costume_data, indent=2))
        else:
            default_costume = {"info": "", "paletteSwap": {"colors": [], "replacements": []}, "paletteSwapPA": {"colors": [], "replacements": []}}
            self.new_costume_text.insert(tk.END, json.dumps(default_costume, indent=2))

        self.button_frame = tk.Frame(left_panel)
        self.button_frame.pack(pady=5, fill=tk.X)

        # Right panel content
        # Image previews
        image_previews_frame = tk.Frame(right_panel)
        image_previews_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        tk.Label(image_previews_frame, text="Uploaded Image Preview", font=("Arial", 12)).pack(pady=5)
        self.uploaded_preview_canvas = tk.Canvas(image_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.uploaded_preview_canvas.pack(pady=5)
        self.zoom_var = tk.DoubleVar(value=0.0)
        zoom_frame = tk.Frame(image_previews_frame)
        zoom_frame.pack(pady=5)
        tk.Label(zoom_frame, text="Zoom:").pack(side=tk.LEFT)
        self.zoom_slider = tk.Scale(zoom_frame, from_=-20.0, to=20.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.zoom_var, command=lambda _: self.update_uploaded_preview())
        self.zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.uploaded_preview_label = tk.Label(image_previews_frame, text="Upload an image to see the preview", fg="gray")
        self.uploaded_preview_label.pack(pady=5)

        tk.Label(image_previews_frame, text="Recolor Preview", font=("Arial", 12)).pack(pady=5)
        self.recolor_preview_canvas = tk.Canvas(image_previews_frame, width=300, height=200, bg="#333333", highlightthickness=1, highlightbackground="black")
        self.recolor_preview_canvas.pack(pady=5)
        self.recolor_preview_label = tk.Label(image_previews_frame, text="Select a character and upload an image to see the recolor", fg="gray")
        self.recolor_preview_label.pack(pady=5)
        recolor_zoom_frame = tk.Frame(image_previews_frame)
        recolor_zoom_frame.pack(pady=5)
        tk.Label(recolor_zoom_frame, text="Recolor Zoom:").pack(side=tk.LEFT)
        self.recolor_zoom_var = tk.DoubleVar(value=0.0)
        self.recolor_zoom_slider = tk.Scale(recolor_zoom_frame, from_=-20.0, to=20.0, resolution=0.1, orient=tk.HORIZONTAL, variable=self.recolor_zoom_var, command=lambda _: self.update_recolor_preview())
        self.recolor_zoom_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Palette previews
        palette_previews_frame = tk.Frame(right_panel)
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

        # Buttons
        tk.Button(self.button_frame, text="Upload Image", command=self.upload_image).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Upload Recolor Sheet", command=self.upload_recolor_sheet).pack(side=tk.LEFT, padx=5)
        # tk.Button(self.button_frame, text="Edit Recolor Sheet", command=self.edit_recolor_sheet).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Save", command=self.prompt_for_costume_name).pack(side=tk.LEFT, padx=5)
        tk.Button(self.button_frame, text="Refresh Previews", command=self.refresh_previews).pack(side=tk.LEFT, padx=5)

        # Bindings for uploaded image preview
        self.uploaded_preview_canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.uploaded_preview_canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.uploaded_preview_canvas.bind("<ButtonRelease-1>", self.on_mouse_release)

        # Bindings for recolor preview
        self.recolor_preview_canvas.bind("<ButtonPress-1>", self.on_recolor_mouse_press)
        self.recolor_preview_canvas.bind("<B1-Motion>", self.on_recolor_mouse_move)
        self.recolor_preview_canvas.bind("<ButtonRelease-1>", self.on_recolor_mouse_release)

        # Bindings for extracted palette preview
        self.extracted_palette_canvas.bind("<ButtonPress-1>", self.on_extracted_mouse_press)
        self.extracted_palette_canvas.bind("<B1-Motion>", self.on_extracted_mouse_move)
        self.extracted_palette_canvas.bind("<ButtonRelease-1>", self.on_extracted_mouse_release)

        # Bindings for converted palette preview
        self.converted_palette_canvas.bind("<ButtonPress-1>", self.on_converted_mouse_press)
        self.converted_palette_canvas.bind("<B1-Motion>", self.on_converted_mouse_move)
        self.converted_palette_canvas.bind("<ButtonRelease-1>", self.on_converted_mouse_release)

        # Binding for JSON text modification
        self.new_costume_text.bind("<<Modified>>", lambda event: [self.update_recolor_preview(), self.update_converted_palette_preview(), self.new_costume_text.edit_modified(False)])

        # Load recolor sheet preview on initialization
        self.load_recolor_sheet_preview()

        # Load or generate image
        print(f"Attempting to load image from image_path: {self.image_path}")
        if self.image_path and os.path.exists(self.image_path):
            try:
                self.uploaded_image = Image.open(self.image_path).convert("RGBA")
                self.uploaded_file_path = self.image_path
                self.original_width, self.original_height = self.uploaded_image.size
                self.extract_palette_strips(self.uploaded_image)
                draw = ImageDraw.Draw(self.uploaded_image)
                for row, start_x, end_x in self.strip_data:
                    draw.line([(start_x, row), (start_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                    draw.line([(end_x, row), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                    if row > 0:
                        draw.line([(start_x, row - 1), (end_x, row - 1)], fill=(255, 0, 0, 255), width=1)
                    if row < self.original_height - 1:
                        draw.line([(start_x, row + 1), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                self.last_image_mtime = os.path.getmtime(self.image_path)
                print(f"Successfully loaded image from {self.image_path}")
            except Exception as e:
                print(f"Error loading image from {self.image_path}: {str(e)}")
                self.uploaded_image = None
                self.uploaded_file_path = None
        else:
            print(f"No valid image_path or file does not exist: {self.image_path}")
            # Generate image from preview cache if editing
            if costume_data:
                self.generate_image_from_preview()
        
        # Update JSON if palette strips are available
        if self.uploaded_image and self.original_palette_strips and self.uploaded_palette_strips:
            costume = {
                "info": costume_data.get("info", "") if costume_data else "",
                "paletteSwap": {
                    "colors": self.original_palette_strips[0],  # Already hex strings
                    "replacements": self.uploaded_palette_strips[0]  # Already hex strings
                },
                "paletteSwapPA": {
                    "colors": self.original_palette_strips[1] if len(self.original_palette_strips) > 1 else [],
                    "replacements": self.uploaded_palette_strips[1] if len(self.uploaded_palette_strips) > 1 else []
                }
            }
            self.new_costume_text.delete("1.0", tk.END)
            self.new_costume_text.insert(tk.END, json.dumps(costume, indent=2))
            print("Updated JSON with palette strips from loaded/generated image")

        # Update all previews after UI setup
        self.update_uploaded_preview()
        self.update_extracted_palette_preview()
        self.update_recolor_preview()
        self.update_converted_palette_preview()
    def generate_image_from_preview(self):
        print(f"Generating image from preview for costume: {self.costume_data.get('info', 'No info') if self.costume_data else 'No costume data'}")
        if not self.costume_data:
            print("No costume data provided, cannot generate image")
            self.uploaded_preview_label.config(text="No costume data to generate image")
            return

        try:
            costume_json = json.dumps(self.costume_data, sort_keys=True)
            costume_hash = hashlib.md5(costume_json.encode()).hexdigest()
            
            if costume_hash not in self.main_app.preview_cache:
                print(f"No preview image in cache for costume hash: {costume_hash}")
                self.uploaded_preview_label.config(text="No preview image available")
                return
            
            image = self.main_app.preview_cache[costume_hash]
            info = self.costume_data.get('info', 'No Info').replace(' ', '_')
            character_dir = os.path.join(os.getcwd(), "recolors", self.character)
            if not os.path.exists(character_dir):
                os.makedirs(character_dir)
                print(f"Created directory: {character_dir}")
            
            self.uploaded_file_path = os.path.join(character_dir, f"{info}.png")
            image.save(self.uploaded_file_path)
            print(f"Saved generated image to: {self.uploaded_file_path}")
            
            self.uploaded_image = Image.open(self.uploaded_file_path).convert("RGBA")
            self.original_width, self.original_height = self.uploaded_image.size
            self.extract_palette_strips(self.uploaded_image)
            draw = ImageDraw.Draw(self.uploaded_image)
            for row, start_x, end_x in self.strip_data:
                draw.line([(start_x, row), (start_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                draw.line([(end_x, row), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                if row > 0:
                    draw.line([(start_x, row - 1), (end_x, row - 1)], fill=(255, 0, 0, 255), width=1)
                if row < self.original_height - 1:
                    draw.line([(start_x, row + 1), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
            self.last_image_mtime = os.path.getmtime(self.uploaded_file_path)
            print("Successfully generated and loaded image from preview")
            
            if self.original_palette_strips and self.uploaded_palette_strips:
                costume = {
                    "info": self.costume_data.get("info", ""),
                    "paletteSwap": {
                        "colors": [c if c == "transparent" else c for c in self.original_palette_strips[0]],  # Already hex strings
                        "replacements": [c if c == "transparent" else c for c in self.uploaded_palette_strips[0]]  # Already hex strings
                    },
                    "paletteSwapPA": {
                        "colors": [c if c == "transparent" else c for c in self.original_palette_strips[1]] if len(self.original_palette_strips) > 1 else [],
                        "replacements": [c if c == "transparent" else c for c in self.uploaded_palette_strips[1]] if len(self.uploaded_palette_strips) > 1 else []
                    }
                }
                self.new_costume_text.delete("1.0", tk.END)
                self.new_costume_text.insert(tk.END, json.dumps(costume, indent=2))
                print("Updated JSON with palette strips from generated image")
        except Exception as e:
            print(f"Error generating image from preview: {str(e)}")
            self.uploaded_image = None
            self.uploaded_file_path = None
            self.uploaded_preview_label.config(text="Failed to generate image")
    def upload_image(self):
        print("Uploading new image...")
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if not file_path:
            print("No image selected")
            return
        try:
            self.uploaded_image = Image.open(file_path).convert("RGBA")
            self.uploaded_file_path = file_path
            self.original_width, self.original_height = self.uploaded_image.size
            self.extract_palette_strips(self.uploaded_image)
            draw = ImageDraw.Draw(self.uploaded_image)
            for row, start_x, end_x in self.strip_data:
                draw.line([(start_x, row), (start_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                draw.line([(end_x, row), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                if row > 0:
                    draw.line([(start_x, row - 1), (end_x, row - 1)], fill=(255, 0, 0, 255), width=1)
                if row < self.original_height - 1:
                    draw.line([(start_x, row + 1), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
            self.last_image_mtime = os.path.getmtime(file_path)
            print(f"Uploaded image: {file_path}")
            if self.original_palette_strips and self.uploaded_palette_strips:
                costume = {
                    "info": "",
                    "paletteSwap": {
                        "colors": [c if c == "transparent" else c for c in self.original_palette_strips[0]],  # Already hex strings
                        "replacements": [c if c == "transparent" else c for c in self.uploaded_palette_strips[0]]  # Already hex strings
                    },
                    "paletteSwapPA": {
                        "colors": [c if c == "transparent" else c for c in self.original_palette_strips[1]] if len(self.original_palette_strips) > 1 else [],
                        "replacements": [c if c == "transparent" else c for c in self.uploaded_palette_strips[1]] if len(self.uploaded_palette_strips) > 1 else []
                    }
                }
                self.new_costume_text.delete("1.0", tk.END)
                self.new_costume_text.insert(tk.END, json.dumps(costume, indent=2))
                print("Updated JSON with palette strips from uploaded image")
            self.update_uploaded_preview()
            self.update_extracted_palette_preview()
            self.update_recolor_preview()
            self.update_converted_palette_preview()
            print("Image upload completed")
        except Exception as e:
            print(f"Error uploading image from {file_path}: {str(e)}")
            self.uploaded_image = None
            self.uploaded_file_path = None
            self.uploaded_preview_label.config(text="Failed to upload image")
    def refresh_previews(self):
        print("Refreshing previews...")
        if (hasattr(self, 'uploaded_file_path') and 
            self.uploaded_file_path is not None and 
            os.path.exists(self.uploaded_file_path)):
            try:
                current_mtime = os.path.getmtime(self.uploaded_file_path)
                if not hasattr(self, 'last_image_mtime') or current_mtime > self.last_image_mtime:
                    self.uploaded_image = Image.open(self.uploaded_file_path).convert("RGBA")
                    self.original_width, self.original_height = self.uploaded_image.size
                    self.extract_palette_strips(self.uploaded_image)
                    draw = ImageDraw.Draw(self.uploaded_image)
                    for row, start_x, end_x in self.strip_data:
                        draw.line([(start_x, row), (start_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                        draw.line([(end_x, row), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                        if row > 0:
                            draw.line([(start_x, row - 1), (end_x, row - 1)], fill=(255, 0, 0, 255), width=1)
                        if row < self.original_height - 1:
                            draw.line([(start_x, row + 1), (end_x, row + 1)], fill=(255, 0, 0, 255), width=1)
                    self.last_image_mtime = current_mtime
                    self.uploaded_preview_label.config(text="")
                    print(f"Reloaded modified image from {self.uploaded_file_path}")
                    # Update JSON if palette strips are available
                    if self.original_palette_strips and self.uploaded_palette_strips:
                        try:
                            current_costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
                            info = current_costume.get("info", "")
                        except json.JSONDecodeError:
                            info = self.costume_data.get("info", "") if self.costume_data else ""
                        costume = {
                            "info": info,
                            "paletteSwap": {
                                "colors": [self.main_app.int_to_hex(c) if c != "transparent" else "transparent" for c in self.original_palette_strips[0]],
                                "replacements": [self.main_app.int_to_hex(c) if c != "transparent" else "transparent" for c in self.uploaded_palette_strips[0]]
                            },
                            "paletteSwapPA": {
                                "colors": [self.main_app.int_to_hex(c) if c != "transparent" else "transparent" for c in self.original_palette_strips[1]] if len(self.original_palette_strips) > 1 else [],
                                "replacements": [self.main_app.int_to_hex(c) if c != "transparent" else "transparent" for c in self.uploaded_palette_strips[1]] if len(self.uploaded_palette_strips) > 1 else []
                            }
                        }
                        self.new_costume_text.delete("1.0", tk.END)
                        self.new_costume_text.insert(tk.END, json.dumps(costume, indent=2))
                        print("Updated JSON with palette strips from reloaded image")
                else:
                    print(f"No changes to image at {self.uploaded_file_path}")
            except Exception as e:
                print(f"Error reloading image from {self.uploaded_file_path}: {str(e)}")
                self.uploaded_preview_label.config(text="Failed to reload image")
        else:
            print("No valid uploaded_file_path for refresh")
            if self.costume_data:
                print("Attempting to regenerate image from preview")
                self.generate_image_from_preview()
                if self.uploaded_file_path:
                    self.refresh_previews()  # Retry after generating
                else:
                    self.uploaded_preview_label.config(text="No image loaded to refresh")
            else:
                self.uploaded_preview_label.config(text="No image loaded to refresh")

        # Force update all previews
        self.update_uploaded_preview()
        self.update_extracted_palette_preview()
        self.update_recolor_preview()
        self.update_converted_palette_preview()
        print("Preview refresh completed")
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
            self.update_recolor_preview()
            self.update_extracted_palette_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load recolor sheet: {str(e)}")
            print(f"Error loading recolor sheet: {str(e)}")

    

    def upload_recolor_sheet(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif")])
        if not file_path:
            print("No recolor sheet selected.")
            return
        try:
            self.original_recolor_sheet = Image.open(file_path).convert("RGBA")
            print(f"Uploaded custom recolor sheet: {file_path}")
            self.extract_original_colors()
            self.update_recolor_preview()
            self.update_extracted_palette_preview()
            self.update_converted_palette_preview()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process recolor sheet: {str(e)}")
            print(f"Error processing recolor sheet: {str(e)}")

    def edit_recolor_sheet(self):
        character_dir = os.path.join(os.getcwd(), "recolors", self.character)
        if not os.path.exists(character_dir):
            os.makedirs(character_dir)
        edit_image_path = os.path.join(character_dir, "EDIT ME.png")
        if self.recolor_image:
            self.recolor_image.save(edit_image_path)
        elif self.original_recolor_sheet:
            self.original_recolor_sheet.save(edit_image_path)
        else:
            messagebox.showerror("Error", "No recolor sheet available to edit.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(character_dir)
            elif platform.system() == "Darwin":
                subprocess.run(["open", character_dir])
            else:
                subprocess.run(["xdg-open", character_dir])
            print(f"Opened directory: {character_dir}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open directory: {str(e)}")
            print(f"Error opening directory: {str(e)}")  

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
        common_colors = set.intersection(*row_colors)
        palette_strips = []
        self.strip_data = []

        for y in range(height):
            if len(palette_strips) >= 2:
                break
            color_counts = {}
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                color_counts[color] = color_counts.get(color, 0) + 1
            ignored_colors = {c for c, count in color_counts.items() if count > width // 2 or c in common_colors}
            strip_colors = []
            strip_start = None
            in_strip = False
            for x in range(width):
                r, g, b, a = pixels[x, y]
                color = "transparent" if a == 0 else (r << 16) + (g << 8) + b | (a << 24)
                if color not in ignored_colors:
                    if not in_strip:
                        strip_start = x
                        in_strip = True
                    strip_colors.append(color)
                elif in_strip:
                    if len(set(strip_colors) - {"transparent"}) >= 5:
                        valid_strip = True
                        end_x = x - 1
                        for pos in range(strip_start, end_x + 1):
                            if y > 0:
                                r_above, g_above, b_above, a_above = pixels[pos, y - 1]
                                above_color = "transparent" if a_above == 0 else (r_above << 16) + (g_above << 8) + b_above | (a_above << 24)
                                if above_color in strip_colors:
                                    valid_strip = False
                                    break
                            if y < height - 1:
                                r_below, g_below, b_below, a_below = pixels[pos, y + 1]
                                below_color = "transparent" if a_below == 0 else (r_below << 16) + (g_below << 8) + b_below | (a_below << 24)
                                if below_color in strip_colors:
                                    valid_strip = False
                                    break
                        if valid_strip:
                            full_strip_colors = []
                            for pos in range(strip_start, end_x + 1):
                                r, g, b, a = pixels[pos, y]
                                if a != 0:
                                    color = (r << 16) + (g << 8) + b | (a << 24)
                                    include_color = True
                                    if y > 0 and pixels[pos, y - 1] == (r, g, b, a):
                                        include_color = False
                                    if y < height - 1 and pixels[pos, y + 1] == (r, g, b, a):
                                        include_color = False
                                    if include_color and color not in ignored_colors:
                                        full_strip_colors.append(f"{color:08X}")
                                else:
                                    full_strip_colors.append("transparent")
                            if len(set(full_strip_colors) - {"transparent"}) >= 5:
                                palette_strips.append(full_strip_colors)
                                self.strip_data.append((y, strip_start, end_x))
                                print(f"Detected strip at row {y}: start_x={strip_start}, end_x={end_x}, num_colors={len(full_strip_colors)}")
                    strip_colors = []
                    in_strip = False
            if in_strip and len(set(strip_colors) - {"transparent"}) >= 5:
                valid_strip = True
                end_x = width - 1
                for pos in range(strip_start, end_x + 1):
                    if y > 0:
                        r_above, g_above, b_above, a_above = pixels[pos, y - 1]
                        above_color = "transparent" if a_above == 0 else (r_above << 16) + (g_above << 16) + b_above | (a_above << 24)
                        if above_color in strip_colors:
                            valid_strip = False
                            break
                    if y < height - 1:
                        r_below, g_below, b_below, a_below = pixels[pos, y + 1]
                        below_color = "transparent" if a_below == 0 else (r_below << 16) + (g_below << 8) + b_below | (a_below << 24)
                        if below_color in strip_colors:
                            valid_strip = False
                            break
                if valid_strip:
                    full_strip_colors = []
                    for pos in range(strip_start, end_x + 1):
                        r, g, b, a = pixels[pos, y]
                        if a != 0:
                            color = (r << 16) + (g << 8) + b | (a << 24)
                            include_color = True
                            if y > 0 and pixels[pos, y - 1] == (r, g, b, a):
                                include_color = False
                            if y < height - 1 and pixels[pos, y + 1] == (r, g, b, a):
                                include_color = False
                            if include_color and color not in ignored_colors:
                                full_strip_colors.append(f"{color:08X}")
                        else:
                            full_strip_colors.append("transparent")
                    if len(set(full_strip_colors) - {"transparent"}) >= 5:
                        palette_strips.append(full_strip_colors)
                        self.strip_data.append((y, strip_start, end_x))
                        print(f"Detected strip at row {y}: start_x={strip_start}, end_x={end_x}, num_colors={len(full_strip_colors)}")

        self.uploaded_palette_strips = palette_strips

    def extract_original_colors(self):
        if not self.original_recolor_sheet:
            return
        self.extract_palette_strips(self.original_recolor_sheet)
        self.original_palette_strips = self.uploaded_palette_strips
        self.uploaded_palette_strips = []
        self.original_strip_data = self.strip_data
        self.strip_data = []

    def on_mouse_press(self, event):
        if not self.uploaded_image:
            return
        self.is_panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def on_mouse_move(self, event):
        if not self.is_panning or not self.uploaded_image:
            return
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.pan_x -= dx
        self.pan_y -= dy
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.update_uploaded_preview()

    def on_mouse_release(self, event):
        self.is_panning = False

    def on_recolor_mouse_press(self, event):
        if not self.recolor_photo:
            return
        self.recolor_is_panning = True
        self.recolor_pan_start_x = event.x
        self.recolor_pan_start_y = event.y

    def on_recolor_mouse_move(self, event):
        if not self.recolor_is_panning or not self.recolor_photo:
            return
        dx = event.x - self.recolor_pan_start_x
        dy = event.y - self.recolor_pan_start_y
        self.recolor_pan_x -= dx
        self.recolor_pan_y -= dy
        self.recolor_pan_start_x = event.x
        self.recolor_pan_start_y = event.y
        self.update_recolor_preview()

    def on_recolor_mouse_release(self, event):
        self.recolor_is_panning = False

    def on_extracted_mouse_press(self, event):
        self.extracted_is_panning = True
        self.extracted_pan_start_x = event.x
        self.extracted_pan_start_y = event.y

    def on_extracted_mouse_move(self, event):
        if not self.extracted_is_panning:
            return
        dx = event.x - self.extracted_pan_start_x
        dy = event.y - self.extracted_pan_start_y
        self.extracted_pan_x -= dx
        self.extracted_pan_y -= dy
        self.extracted_pan_start_x = event.x
        self.extracted_pan_start_y = event.y
        self.update_extracted_palette_preview()

    def on_extracted_mouse_release(self, event):
        self.extracted_is_panning = False

    def on_converted_mouse_press(self, event):
        self.converted_is_panning = True
        self.converted_pan_start_x = event.x
        self.converted_pan_start_y = event.y

    def on_converted_mouse_move(self, event):
        if not self.converted_is_panning:
            return
        dx = event.x - self.converted_pan_start_x
        dy = event.y - self.converted_pan_start_y
        self.converted_pan_x -= dx
        self.converted_pan_y -= dy
        self.converted_pan_start_x = event.x
        self.converted_pan_start_y = event.y
        self.update_converted_palette_preview()

    def on_converted_mouse_release(self, event):
        self.converted_is_panning = False

    def update_uploaded_preview(self):
        print("Updating uploaded preview...")
        self.uploaded_preview_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        if not self.uploaded_image:
            self.uploaded_preview_label.config(text="No image loaded")
            print("No uploaded_image available")
            return
        
        try:
            img = self.uploaded_image.copy()
            self.zoom_scale = 2 ** self.zoom_var.get()
            new_width = int(self.original_width * self.zoom_scale)
            new_height = int(self.original_height * self.zoom_scale)
            img = img.resize((new_width, new_height), Image.Resampling.NEAREST)
            display_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
            offset_x = max(0, (canvas_width - new_width) // 2) - self.pan_x
            offset_y = max(0, (canvas_height - new_height) // 2) - self.pan_y
            if new_width > canvas_width:
                offset_x = max(-(new_width - canvas_width), min(0, offset_x))
            else:
                offset_x = max(0, min(offset_x, canvas_width - new_width))
            if new_height > canvas_height:
                offset_y = max(-(new_height - canvas_height), min(0, offset_y))
            else:
                offset_y = max(0, min(offset_y, canvas_height - new_height))
            display_img.paste(img, (offset_x, offset_y))
            self.uploaded_photo = ImageTk.PhotoImage(display_img)
            self.uploaded_preview_canvas.create_image(0, 0, anchor="nw", image=self.uploaded_photo)
            self.uploaded_preview_label.config(text="")
            print("Updated uploaded image preview successfully")
        except Exception as e:
            print(f"Error updating uploaded preview: {str(e)}")
            self.uploaded_preview_label.config(text="Failed to display image")

    def update_recolor_preview(self):
        self.recolor_preview_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        if not self.original_recolor_sheet:
            self.recolor_preview_label.config(text="No recolor sheet loaded")
            return

        image = self.original_recolor_sheet.copy()
        try:
            costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
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
                        if new_color == "transparent":
                            pixels[x, y] = (0, 0, 0, 0)
                        else:
                            pixels[x, y] = ((new_color >> 16) & 255, (new_color >> 8) & 255, new_color & 255, (new_color >> 24) & 255)
            self.recolor_image = image
        except json.JSONDecodeError:
            pass  # Use original image if JSON is invalid

        self.recolor_original_width, self.recolor_original_height = image.size
        self.recolor_zoom_scale = 2 ** self.recolor_zoom_var.get()
        new_width = int(self.recolor_original_width * self.recolor_zoom_scale)
        new_height = int(self.recolor_original_height * self.recolor_zoom_scale)
        image = image.resize((new_width, new_height), Image.Resampling.NEAREST)
        display_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        offset_x = max(0, (canvas_width - new_width) // 2) - self.recolor_pan_x
        offset_y = max(0, (canvas_height - new_height) // 2) - self.recolor_pan_y
        if new_width > canvas_width:
            offset_x = max(-(new_width - canvas_width), min(0, offset_x))
        else:
            offset_x = max(0, min(offset_x, canvas_width - new_width))
        if new_height > canvas_height:
            offset_y = max(-(new_height - canvas_height), min(0, offset_y))
        else:
            offset_y = max(0, min(offset_y, canvas_height - new_height))
        display_img.paste(image, (offset_x, offset_y))
        self.recolor_photo = ImageTk.PhotoImage(display_img)
        self.recolor_preview_canvas.create_image(0, 0, anchor="nw", image=self.recolor_photo)
        self.recolor_preview_label.config(text="")

    def update_extracted_palette_preview(self):
        print("Updating extracted palette preview...")
        self.extracted_palette_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        palette_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(palette_img)

        y_offset = 10
        row_height = 45

        if self.uploaded_palette_strips:
            draw.text((10, y_offset), "Uploaded paletteSwap", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(self.uploaded_palette_strips[0]):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    # Convert hex string to integer
                    color_int = int(color, 16)
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
            y_offset += row_height

        if len(self.uploaded_palette_strips) > 1:
            draw.text((10, y_offset), "Uploaded paletteSwapPA", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(self.uploaded_palette_strips[1]):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    # Convert hex string to integer
                    color_int = int(color, 16)
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
            y_offset += row_height

        if self.original_palette_strips:
            draw.text((10, y_offset), "Original paletteSwap", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(self.original_palette_strips[0]):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    # Convert hex string to integer
                    color_int = int(color, 16)
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
            y_offset += row_height

        if len(self.original_palette_strips) > 1:
            draw.text((10, y_offset), "Original paletteSwapPA", fill=(255, 255, 255, 255))
            y = y_offset + 10
            for x, color in enumerate(self.original_palette_strips[1]):
                if color == "transparent":
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
                else:
                    # Convert hex string to integer
                    color_int = int(color, 16)
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))

        self.extracted_palette_photo = ImageTk.PhotoImage(palette_img)
        self.extracted_palette_canvas.create_image(-self.extracted_pan_x, -self.extracted_pan_y, anchor="nw", image=self.extracted_palette_photo)
        self.extracted_palette_label.config(text="")
        print("Extracted palette preview updated successfully.")

    def update_converted_palette_preview(self):
        self.converted_palette_canvas.delete("all")
        canvas_width, canvas_height = 300, 200
        try:
            costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
            palette_swap = costume.get("paletteSwap", {"colors": [], "replacements": []})
            palette_swap_pa = costume.get("paletteSwapPA", {"colors": [], "replacements": []})
        except json.JSONDecodeError:
            self.converted_palette_label.config(text="Invalid JSON data")
            return

        palette_img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(palette_img)

        y_offset = 10
        row_height = 45

        draw.text((10, y_offset), "paletteSwap colors", fill=(255, 255, 255, 255))
        y = y_offset + 10
        for x, color in enumerate(palette_swap.get("colors", [])):
            if color == "transparent":
                draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
            else:
                color_int = self.main_app.convert_color(color)
                if color_int != 0:
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
        y_offset += row_height

        draw.text((10, y_offset), "paletteSwap replacements", fill=(255, 255, 255, 255))
        y = y_offset + 10
        for x, color in enumerate(palette_swap.get("replacements", [])):
            if color == "transparent":
                draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
            else:
                color_int = self.main_app.convert_color(color)
                if color_int != 0:
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
        y_offset += row_height

        draw.text((10, y_offset), "paletteSwapPA colors", fill=(255, 255, 255, 255))
        y = y_offset + 10
        for x, color in enumerate(palette_swap_pa.get("colors", [])):
            if color == "transparent":
                draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
            else:
                color_int = self.main_app.convert_color(color)
                if color_int != 0:
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))
        y_offset += row_height

        draw.text((10, y_offset), "paletteSwapPA replacements", fill=(255, 255, 255, 255))
        y = y_offset + 10
        for x, color in enumerate(palette_swap_pa.get("replacements", [])):
            if color == "transparent":
                draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(0, 0, 0, 0))
            else:
                color_int = self.main_app.convert_color(color)
                if color_int != 0:
                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255
                    a = (color_int >> 24) & 255
                    draw.rectangle([x * 10, y, x * 10 + 9, y + 9], fill=(r, g, b, a))

        self.converted_palette_photo = ImageTk.PhotoImage(palette_img)
        self.converted_palette_canvas.create_image(-self.converted_pan_x, -self.converted_pan_y, anchor="nw", image=self.converted_palette_photo)
        self.converted_palette_label.config(text="")

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

        def save_costume():
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

        tk.Button(dialog, text="Save", command=save_costume).pack(pady=10)
    def save_new_costume(self, costume_name, online_name):
        try:
            costume = json.loads(self.new_costume_text.get("1.0", tk.END).strip())
            costume['info'] = costume_name
            if 'display_name' in costume:
                del costume['display_name']
            
            if self.source == 'current' and self.current_idx is not None:
                # Update existing costume in all_costumes
                self.main_app.all_costumes[self.current_idx] = (self.main_app.all_costumes[self.current_idx][0], costume)
                self.main_app.update_costume_list()
                self.main_app.costume_listbox.select_set(self.current_idx)  # Preserve selection
                self.main_app.update_costume_preview()
            elif self.source == 'loaded' and self.loaded_idx is not None:
                # Update existing costume in loaded_costumes
                self.main_app.loaded_costumes[self.loaded_idx] = costume
                display_name = self.main_app.get_display_name(costume)
                self.main_app.loaded_listbox.delete(self.loaded_idx)
                self.main_app.loaded_listbox.insert(self.loaded_idx, display_name)
                self.main_app.loaded_listbox.select_set(self.loaded_idx)  # Preserve selection
                self.main_app.update_preview()
            else:
                # Add as new costume to all_costumes
                self.main_app.add_new_costume_to_list(costume)
                self.main_app.update_costume_list()
                self.main_app.update_costume_preview()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save costume: {str(e)}")
            print(f"Error saving costume: {str(e)}")