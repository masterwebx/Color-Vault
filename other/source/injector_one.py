### injector_one.py
import sys
import os
import tkinter as tk

# Set the working directory to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print("Current working directory set to:", os.getcwd())

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
print("Python path:", sys.path)

# Verify gui.py exists
gui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui.py")
print("Does gui.py exist?", os.path.exists(gui_path))

from gui import SSF2ModGUI, TextRedirector
from utils import decompress_ssf, extract_misc_as, modify_misc_as, inject_misc_as, compress_swf

if __name__ == "__main__":
    FFDEC_JAR = "C:\\Program Files (x86)\\FFDec\\ffdec.jar"
    JAVA_PATH = "java"

    app = SSF2ModGUI()    
    app.mainloop()