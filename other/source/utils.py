import subprocess
import os
import zlib
import re
import struct
import json
import requests
import pyparsing as pp
from pyparsing import *
import shutil
import time

def decompress_ssf(ssf_path, swf_path):
    """Decompress SSF to SWF, following the logic from Main.as."""
    with open(ssf_path, "rb") as f:
        data = f.read()

    decompressed = zlib.decompress(data)

    pos = 0
    l = struct.unpack_from(">I", decompressed, pos)[0]
    pos += 4
    n = struct.unpack_from(">I", decompressed, pos)[0]
    pos += 4

    pos += n * 4

    swf_data = decompressed[pos:pos + l]

    with open(swf_path, "wb") as f:
        f.write(swf_data)
    print(f"Decompressed {ssf_path} to {swf_path}")

def compress_swf(swf_path, ssf_path):
    """Compress SWF to SSF, following the logic from Main.as."""
    with open(swf_path, "rb") as f:
        swf_data = f.read()

    ssf_data = bytearray()
    ssf_data.extend(struct.pack(">I", len(swf_data)))
    ssf_data.extend(struct.pack(">I", 0))
    ssf_data.extend(swf_data)

    compressed = zlib.compress(ssf_data)

    with open(ssf_path, "wb") as f:
        f.write(compressed)
    print(f"Compressed {swf_path} to {ssf_path}")

def extract_misc_as(swf_path, output_as_path, java_path, ffdec_jar):
    """Extract Misc.as from SWF using JPEXS CLI."""
    swf_path = os.path.abspath(swf_path)
    output_as_path = os.path.abspath(output_as_path)
    output_dir = os.getcwd()

    cmd = [
        java_path,
        "-jar",
        ffdec_jar,
        "-export",
        "script",
        output_dir,
        swf_path,
        "misc.as"
    ]
    print(f"Executing command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Extracted Misc.as: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error extracting Misc.as: {e.stderr}")
        raise

def inject_misc_as(swf_path, new_as_path, output_swf_path, java_path, ffdec_jar):
    """Inject modified Misc.as into SWF using JPEXS CLI."""
    swf_path = os.path.abspath(swf_path)
    new_as_path = os.path.abspath(new_as_path)
    output_swf_path = os.path.abspath(output_swf_path)

    cmd = [
        java_path,
        "-jar",
        ffdec_jar,
        "-replace",
        swf_path,
        output_swf_path,
        "Misc",
        new_as_path
    ]
    print(f"Executing command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Injected Misc.as: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Error injecting Misc.as: {e.stderr}")
        raise

def modify_misc_as(original_as_path, new_as_path, costume_data, character):
    """Modify Misc.as to add a new costume for the selected character."""
    with open(original_as_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = f'_loc1_\\["{re.escape(character)}"\\]\\.push\\({{'
    character_entries = list(re.finditer(pattern, content))
    if not character_entries:
        end_of_loc1 = content.rfind('};')
        if end_of_loc1 == -1:
            raise ValueError("Could not find end of _loc1_ array in Misc.as")

        palette_swap_colors = ",".join(map(str, costume_data["paletteSwap"]["colors"]))
        palette_swap_replacements = ",".join(map(str, costume_data["paletteSwap"]["replacements"]))
        palette_swap_pa_colors = ",".join(map(str, costume_data["paletteSwapPA"]["colors"]))
        palette_swap_pa_replacements = ",".join(map(str, costume_data["paletteSwapPA"]["replacements"]))

        new_character_entry = f'\n         _loc1_["{character}"] = new Array();\n' \
                             f'         _loc1_["{character}"].push({{\n' \
                             f'            "paletteSwap":{{' \
                             f'\n               "colors":[{palette_swap_colors}],' \
                             f'\n               "replacements":[{palette_swap_replacements}]' \
                             f'\n            }},\n' \
                             f'            "paletteSwapPA":{{' \
                             f'\n               "colors":[{palette_swap_pa_colors}],' \
                             f'\n               "replacements":[{palette_swap_pa_replacements}]' \
                             f'\n            }}\n' \
                             f'         }});\n'
        print(f"Generated new character entry for {character}")
        new_content = content[:end_of_loc1] + new_character_entry + content[end_of_loc1:]
    else:
        last_entry_start = character_entries[-1].end()
        brace_count = 1
        pos = last_entry_start
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        if brace_count != 0:
            raise ValueError(f"Mismatched braces for character {character} in Misc.as")

        end_of_push = content.find('});', pos)
        if end_of_push == -1:
            raise ValueError(f"Could not find end of push statement for character {character} in Misc.as")

        lines_before_insertion = content[:pos].count('\n') + 1
        print(f"Inserting new entry at line {lines_before_insertion}")

        palette_swap_colors = ",".join(map(str, costume_data["paletteSwap"]["colors"]))
        palette_swap_replacements = ",".join(map(str, costume_data["paletteSwap"]["replacements"]))
        palette_swap_pa_colors = ",".join(map(str, costume_data["paletteSwapPA"]["colors"]))
        palette_swap_pa_replacements = ",".join(map(str, costume_data["paletteSwapPA"]["replacements"]))

        new_entry = f'\n         }});\n' \
                    f'\n         _loc1_["{character}"].push({{\n' \
                    f'            "paletteSwap":{{' \
                    f'\n               "colors":[{palette_swap_colors}],' \
                    f'\n               "replacements":[{palette_swap_replacements}]' \
                    f'\n            }},\n' \
                    f'            "paletteSwapPA":{{' \
                    f'\n               "colors":[{palette_swap_pa_colors}],' \
                    f'\n               "replacements":[{palette_swap_pa_replacements}]' \
                    f'\n            }}\n' \
                    f'         }});\n'
        print(f"Generated new entry for {character}")
        new_content = content[:end_of_push] + new_entry + content[end_of_push + 2:]

    with open(new_as_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Modified Misc.as with new costume for {character} at {new_as_path}")

def extract_character_names(as_path):
    """Extract character names from Misc.as."""
    if not os.path.exists(as_path):
        raise FileNotFoundError(f"Misc.as not found at {as_path}")

    with open(as_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'_loc1_\["([^"]+)"\]'
    matches = re.findall(pattern, content)
    characters = sorted(list(set(matches)))
    return characters

def parse_as3_object(s):
    LBRACE, RBRACE, LBRACK, RBRACK, COLON, COMMA = map(pp.Suppress, "{}[]:,")
    number = pp.pyparsing_common.number
    hex_number = pp.Regex(r"0x[0-9A-Fa-f]+").setParseAction(lambda t: int(t[0], 16))
    string = pp.quotedString.setParseAction(pp.removeQuotes)
    unquoted_key = pp.Word(pp.alphas + "_", pp.alphanums + "_").setParseAction(lambda t: str(t[0]))
    boolean = pp.Keyword("true") | pp.Keyword("false")
    boolean.setParseAction(lambda t: t[0] == "true")
    null = pp.Keyword("null")
    value = pp.Forward()
    array = pp.Group(LBRACK + pp.Optional(pp.delimitedList(value)) + RBRACK)
    key = string | unquoted_key
    pair = pp.Group(key + COLON + value)
    object_ = pp.Group(LBRACE + pp.Optional(pp.delimitedList(pair)) + RBRACE)
    value << (hex_number | number | string | boolean | null | array | object_)

    try:
        parsed = object_.parseString(s, parseAll=True)
        return parsed.asList()
    except pp.ParseException as e:
        print(f"Parse error: {e}\nInput string: {s}")
        raise

def as3_to_dict(parsed):
    if isinstance(parsed, list):
        if len(parsed) == 0:
            return []
        is_object = all(isinstance(item, list) and len(item) == 2 and isinstance(item[0], str) for item in parsed)
        if is_object:
            result = {}
            for key, value in parsed:
                result[key] = as3_to_dict(value)
            return result
        return [as3_to_dict(item) for item in parsed]
    else:
        return parsed

def extract_costumes(as_path, character):
    start_time = time.time()
    if not os.path.exists(as_path):
        raise FileNotFoundError(f"Misc.as not found at {as_path}")

    with open(as_path, "r", encoding="utf-8") as f:
        content = f.read()

    costumes = []
    pattern = f'_loc1_\\["{re.escape(character)}"\\]\\.push\\({{(.*?)}}\\);'
    matches = re.finditer(pattern, content, re.DOTALL)
    no_info_counter = 1

    for match in matches:
        costume_str = "{" + match.group(1).strip() + "}"
        try:
            parsed = parse_as3_object(costume_str)
            costume = as3_to_dict(parsed[0])
            if "team" in costume:
                costume["display_name"] = f"Team {costume['team'].capitalize()}"
            elif "base" in costume and costume["base"]:
                costume["display_name"] = "Base"
            elif "info" in costume:
                costume["display_name"] = costume["info"]
            else:
                costume["display_name"] = f"No Info #{no_info_counter}"
                no_info_counter += 1
            costumes.append(costume)
        except Exception as e:
            print(f"Error parsing costume: {e}\nCostume string: {costume_str[:1000]}...")  # Truncate for readability
            continue  # Skip malformed costume

    end_time = time.time()
    print(f"Extracted {len(costumes)} costumes in {end_time - start_time:.2f} seconds")
    return costumes


# ... (previous imports and functions remain unchanged)

def format_color_for_as3(color):
    """Format a color value for AS3 (e.g., 'FFFF0000' or 4294967295 to '0xFFFFFFFF', 'transparent' unchanged)."""
    if color == "transparent":
        return "transparent"
    try:
        if isinstance(color, str):
            # Handle string colors (hex format)
            color_str = color.replace("#", "").replace("0x", "")
            # Validate hex string (8 characters for RGBA)
            if len(color_str) == 8 and all(c in "0123456789ABCDEFabcdef" for c in color_str):
                return f"0x{color_str.upper()}"
        elif isinstance(color, int):
            # Handle integer colors (convert to 8-digit hex)
            if 0 <= color <= 0xFFFFFFFF:
                return f"0x{color:08X}"
        print(f"Invalid color format: {color}, defaulting to 0xFF000000")
        return "0xFF000000"
    except Exception as e:
        print(f"Error formatting color {color}: {str(e)}, defaulting to 0xFF000000")
        return "0xFF000000"

# ... (rest of the file remains unchanged)


def update_costumes(original_as_path, new_as_path, character, costumes):
    print(f"Starting update_costumes for character '{character}' with {len(costumes)} costumes")
    with open(original_as_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_pos = content.find(f'_loc1_["{character}"] = new Array();')
    if start_pos == -1:
        end_of_loc1 = content.rfind('};')
        if end_of_loc1 == -1:
            raise ValueError("Could not find end of _loc1_ array in Misc.as")
        new_content = content[:end_of_loc1] + f'\n         _loc1_["{character}"] = new Array();\n'
    else:
        pattern = f'_loc1_\\["{re.escape(character)}"\\]\\.push\\({{(.*?)}}\\);'
        character_entries = list(re.finditer(pattern, content, re.DOTALL))
        if not character_entries:
            end_pos = start_pos + len(f'_loc1_["{character}"] = new Array();')
        else:
            end_pos = character_entries[-1].end()
        new_content = content[:start_pos] + f'_loc1_["{character}"] = new Array();\n'

    for i, costume in enumerate(costumes):
        print(f"Processing costume {i} ({costume.get('display_name', f'Costume #{i}')})")
        try:
            if not all(key in costume for key in ["paletteSwap", "paletteSwapPA"]):
                raise ValueError(f"Costume {i} missing required keys: {list(set(['paletteSwap', 'paletteSwapPA']) - set(costume.keys()))}")
            for key in ["paletteSwap", "paletteSwapPA"]:
                if not isinstance(costume[key], dict):
                    raise ValueError(f"Costume {i} {key} is not a dictionary, got {type(costume[key])}")
                if not all(subkey in costume[key] for subkey in ["colors", "replacements"]):
                    raise ValueError(f"Costume {i} {key} missing subkeys: {list(set(['colors', 'replacements']) - set(costume[key].keys()))}")
                if not (isinstance(costume[key]["colors"], list) and isinstance(costume[key]["replacements"], list)):
                    raise ValueError(f"Costume {i} {key} has non-list subkeys: colors={type(costume[key]['colors'])}, replacements={type(costume[key]['replacements'])}")

            palette_swap_colors = ",".join(format_color_for_as3(color) for color in costume["paletteSwap"]["colors"])
            palette_swap_replacements = ",".join(format_color_for_as3(color) for color in costume["paletteSwap"]["replacements"])
            palette_swap_pa_colors = ",".join(format_color_for_as3(color) for color in costume["paletteSwapPA"]["colors"])
            palette_swap_pa_replacements = ",".join(format_color_for_as3(color) for color in costume["paletteSwapPA"]["replacements"])

            new_content += f'         _loc1_["{character}"].push({{\n'

            for key, value in costume.items():
                if key not in ["paletteSwap", "paletteSwapPA", "display_name"]:
                    if key == "base":
                        new_content += f'            "{key}":{str(value).lower()},\n'
                    elif isinstance(value, str):
                        new_content += f'            "{key}":"{value}",\n'
                    else:
                        new_content += f'            "{key}":{value},\n'

            new_content += f'            "paletteSwap":{{' \
                           f'\n               "colors":[{palette_swap_colors}],' \
                           f'\n               "replacements":[{palette_swap_replacements}]' \
                           f'\n            }},\n' \
                           f'            "paletteSwapPA":{{' \
                           f'\n               "colors":[{palette_swap_pa_colors}],' \
                           f'\n               "replacements":[{palette_swap_pa_replacements}]' \
                           f'\n            }}\n' \
                           f'         }});\n'
            print(f"Successfully processed costume {i}")
        except Exception as e:
            print(f"Error processing costume {i} ({costume.get('display_name', f'Costume #{i}')}): {str(e)}")
            raise

    if start_pos == -1:
        new_content += content[end_of_loc1:]
    else:
        new_content += content[end_pos:]

    with open(new_as_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated costumes for {character} at {new_as_path}")

def load_costumes_from_file(file_path):
    """Load costumes from a .as or .txt file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.strip()
    if content.startswith("[") and content.endswith("]"):
        content = content[1:-1]

    costumes = []
    brace_count = 0
    current_costume = ""
    no_info_counter = 1

    for char in content:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        current_costume += char
        if brace_count == 0 and current_costume.strip():
            try:
                costume = json.loads(current_costume.strip().rstrip(","))
                if not all(key in costume for key in ["paletteSwap", "paletteSwapPA"]):
                    print(f"Skipping costume: Missing 'paletteSwap' or 'paletteSwapPA' keys.")
                    continue
                for key in ["paletteSwap", "paletteSwapPA"]:
                    if not isinstance(costume[key], dict):
                        print(f"Skipping costume: {key} is not a dictionary.")
                        continue
                    if not all(subkey in costume[key] for subkey in ["colors", "replacements"]):
                        print(f"Skipping costume: {key} missing 'colors' or 'replacements'.")
                        continue
                    if not (isinstance(costume[key]["colors"], list) and isinstance(costume[key]["replacements"], list)):
                        print(f"Skipping costume: {key} 'colors' or 'replacements' are not lists.")
                        continue
                if "team" in costume:
                    team_color = costume["team"].capitalize()
                    costume["display_name"] = f"Team {team_color}"
                    print(f"File load - Found team costume: Team {team_color}")
                elif "base" in costume and costume["base"] is True:
                    costume["display_name"] = "Base"
                    print(f"File load - Found base costume: Base")
                elif "info" in costume:
                    costume["display_name"] = costume["info"]
                    print(f"File load - Using info as display name: {costume['display_name']}")
                else:
                    costume["display_name"] = f"No Info #{no_info_counter}"
                    no_info_counter += 1
                    print(f"File load - Assigned No Info: {costume['display_name']}")
                costumes.append(costume)
            except json.JSONDecodeError as e:
                print(f"Error parsing costume: {e}")
            current_costume = ""

    return costumes

def check_url_exists(url):
    """Check if a URL exists."""
    print(f"Checking if URL exists: {url}")
    try:
        response = requests.head(url, timeout=5)
        exists = response.status_code == 200
        print(f"URL check result: {'Exists' if exists else 'Does not exist'} (Status code: {response.status_code})")
        return exists
    except requests.RequestException as e:
        print(f"Error checking URL: {str(e)}")
        return False

def load_costumes_from_url(url):
    """Load costumes from a URL."""
    print(f"Fetching costumes from URL: {url}")
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        content = response.text.strip()
        print(f"Successfully fetched content from URL (length: {len(content)} characters)")

        if content.startswith("[") and content.endswith("]"):
            content = content[1:-1]

        content = content.strip().rstrip(",")

        costumes = []
        brace_count = 0
        current_costume = ""
        no_info_counter = 1

        for char in content:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            current_costume += char
            if brace_count == 0 and current_costume.strip():
                cleaned_costume = current_costume.strip()
                if cleaned_costume.startswith("{") and cleaned_costume.endswith("}"):
                    try:
                        costume = json.loads(cleaned_costume.rstrip(","))
                        if not all(key in costume for key in ["paletteSwap", "paletteSwapPA"]):
                            print(f"Skipping costume from URL: Missing 'paletteSwap' or 'paletteSwapPA' keys.")
                            continue
                        for key in ["paletteSwap", "paletteSwapPA"]:
                            if not isinstance(costume[key], dict):
                                print(f"Skipping costume from URL: {key} is not a dictionary.")
                                continue
                            if not all(subkey in costume[key] for subkey in ["colors", "replacements"]):
                                print(f"Skipping costume from URL: {key} missing 'colors' or 'replacements'.")
                                continue
                            if not (isinstance(costume[key]["colors"], list) and isinstance(costume[key]["replacements"], list)):
                                print(f"Skipping costume from URL: {key} 'colors' or 'replacements' are not lists.")
                                continue
                        if "team" in costume:
                            team_color = costume["team"].capitalize()
                            costume["display_name"] = f"Team {team_color}"
                            print(f"URL load - Found team costume: Team {team_color}")
                        elif "base" in costume and costume["base"] is True:
                            costume["display_name"] = "Base"
                            print(f"URL load - Found base costume: Base")
                        elif "info" in costume:
                            costume["display_name"] = costume["info"]
                            print(f"URL load - Using info as display name: {costume['display_name']}")
                        else:
                            costume["display_name"] = f"No Info #{no_info_counter}"
                            no_info_counter += 1
                            print(f"URL load - Assigned No Info: {costume['display_name']}")
                        costumes.append(costume)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing costume from URL: {e}")
                current_costume = ""

        print(f"Loaded {len(costumes)} costumes from URL")
        return costumes
    except requests.RequestException as e:
        print(f"Failed to fetch costumes from URL: {str(e)}")
        raise

def launch_ssf2(exe_path):
    """Launch SSF2 executable."""
    if not os.path.isfile(exe_path) or not exe_path.endswith("SSF2.exe"):
        raise ValueError(f"Invalid SSF2 executable path: {exe_path}")
    subprocess.run([exe_path], check=True)

def copy_ssf2_directory(src_dir, dest_dir):
    """Copy the entire SSF2 directory to the destination."""
    if not os.path.isdir(src_dir):
        raise ValueError(f"Source directory does not exist: {src_dir}")

    ssf_path = os.path.join(src_dir, "data", "DAT135.ssf")
    exe_path = os.path.join(src_dir, "SSF2.exe")
    if not os.path.isfile(ssf_path) or not os.path.isfile(exe_path):
        raise ValueError("SSF2 directory is missing SSF2.exe or data/DAT135.ssf")

    if os.path.exists(dest_dir):
        print(f"Destination directory already exists: {dest_dir}")
        return False

    try:
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=False)
        print(f"Successfully copied SSF2 from {src_dir} to {dest_dir}")
        return True
    except PermissionError as e:
        print(f"Permission error copying SSF2: {e}. Try running as administrator.")
        raise
    except Exception as e:
        print(f"Error copying SSF2 directory: {e}")
        raise