if (typeof require !== 'undefined') {
    defaultColorGroups = require('./defaultColors');
}
document.getElementById('upload').addEventListener('change', handleImageUpload);
document.getElementById('hue-slider').addEventListener('input', handleHueChange);
document.getElementById('brightness-slider').addEventListener('input', handleBrightnessChange);
document.getElementById('contrast-slider').addEventListener('input', handleContrastChange);
document.getElementById('saturation-slider').addEventListener('input', handleSaturationChange);
document.getElementById('tint-slider').addEventListener('input', handleTintChange);
document.getElementById('tint-color').addEventListener('input', handleTintColorChange);
document.getElementById('canvas').addEventListener('mousemove', handleCanvasHover);
document.getElementById('canvas').addEventListener('mouseout', hideColorPreview);
document.getElementById('canvas').addEventListener('click', handleCanvasClick);
document.getElementById('download-groups-btn').addEventListener('click', downloadGroups);
document.getElementById('upload-groups').addEventListener('change', uploadGroups);
document.getElementById('select-all-colors-btn').addEventListener('click', selectAllColors);
document.getElementById('cancel-group-name-btn').addEventListener('click', function() {
    document.getElementById('group-name-popup').style.display = 'none';
});





let uploadedFileName = "";
let canvas = document.getElementById('canvas');
let ctx = canvas.getContext('2d', { willReadFrequently: true });
let image = new Image();
let originalImageData;
let selectedColors = new Set();
let colorGroups = [];
let activeGroup = null;

let currentHue = 0;
let currentBrightness = 0;
let currentContrast = 0;
let currentSaturation = 0;
let currentTintColor = '#ffffff';
let currentTintStrength = 0;

let tintRgb = hexToRgb(currentTintColor);
let selectedPortion = null;
let selectingPortion = false;
let startX, startY, endX, endY;

const imageList = [
    {
        "name": "Bandana Dee Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Bandana%20Dee%20Recolor%20Sheet.png"
    },
    {
        "name": "Black Mage Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Black%20Mage%20Recolor%20Sheet.png"
    },
    {
        "name": "Bomberman Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Bomberman%20Recolor%20Sheet.png"
    },
    {
        "name": "Bowser Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Bowser%20Recolor%20Sheet.png"
    },
    {
        "name": "Captain Falcon Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Captain%20Falcon%20Recolor%20Sheet.png"
    },
    {
        "name": "Chibi Robo Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Chibi%20Robo%20Recolor%20Sheet.png"
    },
    {
        "name": "Dio Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Dio%20(Sandbox)%20Recolor%20Sheet%20.png"
    },
    {
        "name": "Falco Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Falco%20Recolor%20Sheet.png"
    },
    {
        "name": "Ganondorf Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Ganondorf%20Recolor%20Sheet.png"
    },
    {
        "name": "Ichigo Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Ichigo%20Recolor%20Sheet.png"
    },
    {
        "name": "gameandwatch Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/gameandwatch%20Recolor%20Sheet.png"
    },
    {
        "name": "Isaac Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Isaac%20Recolor%20Sheet.png"
    },
    {
        "name": "Jigglypuff Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Jigglypuff%20Recolor%20Sheet.png"
    },
    {
        "name": "Jotaro Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Jotaro%20(Sandbox)%20Recolor%20Sheet%20.png"
    },
    {
        "name": "Kirby Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Kirby%20Recolor%20Sheet.png"
    },
    {
        "name": "Krystal Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Krystal%20Recolor%20Sheet.png"
    },
    {
        "name": "Link Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Link%20Recolor%20Sheet.png"
    },
    {
        "name": "Lloyd Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Lloyd%20Recolor%20Sheet.png"
    },
    {
        "name": "Lucario Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Lucario%20Recolor%20Sheet.png"
    },
    {
        "name": "Luffy Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Luffy%20Recolor%20Sheet.png"
    },
    {
        "name": "Luigi Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Luigi%20Recolor%20Sheet.png"
    },
    {
        "name": "Mario Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Mario%20Recolor%20Sheet.png"
    },
    {
        "name": "Mega Man Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Mega%20Man%20Recolor%20Sheet.png"
    },
    {
        "name": "Meta Knight Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/MetaKnight_Recolor_Sheet.png"
    },
    {
        "name": "Naruto Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Naruto%20Recolor%20Sheet.png"
    },
    {
        "name": "Ness Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Ness%20Recolor%20Sheet.png"
    },
    {
        "name": "Pac Man Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Pac%20Man%20Recolor%20Sheet.png"
    },
    {
        "name": "Peach Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Peach%20Recolor%20Sheet.png"
    },
    {
        "name": "Pichu Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Pichu%20Recolor%20Sheet.png"
    },
    {
        "name": "Pikachu Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Pikachu%20Recolor%20Sheet.png"
    },
    {
        "name": "Pit Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Pit%20Recolor%20Sheet.png"
    },
    {
        "name": "Ryu Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Ryu%20Recolor%20Sheet.png"
    },
    {
        "name": "Rayman Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Rayman%20Recolor%20Sheet.png"
    },
    {
        "name": "Samus Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Samus%20Recolor%20Sheet.png"
    },
    {
        "name": "Sandbag Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Sandbag%20Recolor%20Sheet.png"
    },
    {
        "name": "Shiek Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Sheik_Recolor_Sheet.png"
    },
    {
        "name": "Simon Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Simon%20Recolor%20Sheet.png"
    },
    {
        "name": "Sonic Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Sonic%20Recolor%20Sheet.png"
    },
    {
        "name": "Sora Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Sora%20Recolor%20Sheet.png"
    },
    {
        "name": "Tails Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Tails%20Recolor%20Sheet.png"
    },
    {
        "name": "Waluigi Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Waluigi%20Recolor%20Sheet.png"
    },
    {
        "name": "Wario Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Wario%20Recolor%20Sheet.png"
    },
    {
        "name": "X Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/X%20(Sandbox)%20Recolor%20Sheet%20.png"
    },
    {
        "name": "Yoshi Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Yoshi%20Recolor%20Sheet.png"
    },
    {
        "name": "Zamus Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Zamus%20Recolor%20Sheet.png"
    },
    {
        "name": "Zelda Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Zelda_Recolor_Sheet.png"
    },
    {
        "name": "Zero Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Zero%20(Sandbox)%20Recolor%20Sheet%20.png"
    },
    {
        "name": "Dedede Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/Dedede%20Recolor%20Sheet.png"
    },
    {
        "name": "Goku Recolor Sheet",
        "url": "https://raw.githubusercontent.com/masterwebx/Color-Vault/refs/heads/master/other/color%20sheets/goku%20recolor%20sheet.png"
    }

];

function populateUrlSelect() {
    const urlSelect = document.getElementById('url-select');
    const defaultOption = document.createElement('option');
    defaultOption.value = "";
    defaultOption.text = "Select an image";
    //urlSelect.appendChild(defaultOption);

    imageList.forEach((image, index) => {
        const option = document.createElement('option');
        option.value = image.url;
        option.text = image.name;
        urlSelect.appendChild(option);
    });

    urlSelect.addEventListener('change', function() {
        const selectedUrl = urlSelect.value;
        if (selectedUrl) {
            const selectedImage = imageList.find(image => image.url === selectedUrl);
            if (selectedImage) {
                uploadedFileName = selectedImage.name; // Update the uploadedFileName to the selected image list name
                loadImageFromUrl(selectedUrl);
            }
        }
    });
}

function selectAllColors() {
    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');

    for (let colorBox of colorBoxes) {
        colorBox.click(); // Simulate a click on each colorBox
    }
    updateGroupColors();
    applyAdjustments(); // Apply all adjustments after selection changes
    saveGroupsLocally();
}

function loadImageFromUrl(url) {
    // Hide popups when a new image is loaded
    document.getElementById('group-name-popup').style.display = 'none';
    document.getElementById('group-dropdown-container').style.display = 'none';

    let tempImage = new Image();
    tempImage.crossOrigin = "Anonymous"; // Set crossOrigin attribute
    tempImage.onload = function() {
        let tempCanvas = document.createElement('canvas');
        let tempCtx = tempCanvas.getContext('2d');
        tempCanvas.width = tempImage.width;
        tempCanvas.height = tempImage.height;
        tempCtx.drawImage(tempImage, 0, 0);
        let tempImageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
        let colorSet = getColorSet(tempImageData);

        if (colorSet.size > 500) {
            alert("The image has more than 500 colors and cannot be loaded.");
            return;
        }

        image = new Image();
        image.crossOrigin = "Anonymous"; // Set crossOrigin attribute
        image.src = url;
        image.onload = function() {
            canvas.width = image.width;
            canvas.height = image.height;
            ctx.mozImageSmoothingEnabled = false;
            ctx.webkitImageSmoothingEnabled = false;
            ctx.msImageSmoothingEnabled = false;
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(image, 0, 0);
            originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            clearGroups();
            displayPalette(colorSet);
            loadDefaultColors();  // Call to load default colors
        };
    };
    tempImage.src = url;
}

document.addEventListener('DOMContentLoaded', function() {
    populateUrlSelect();
});

function handleImageUpload(event) {
    let file = event.target.files[0];
    uploadedFileName = file.name.split('.')[0]; // Get the base image name without extension

    // Hide popups when a new image is loaded
    document.getElementById('group-name-popup').style.display = 'none';
    document.getElementById('group-dropdown-container').style.display = 'none';

    let reader = new FileReader();

    reader.onload = function(e) {
        let tempImage = new Image();
        tempImage.onload = function() {
            let tempCanvas = document.createElement('canvas');
            let tempCtx = tempCanvas.getContext('2d');
            tempCanvas.width = tempImage.width;
            tempCanvas.height = tempImage.height;
            tempCtx.drawImage(tempImage, 0, 0);
            let tempImageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
            let colorSet = getColorSet(tempImageData);           

            image = new Image(); // Ensure `image` is initialized here
            image.src = e.target.result;
            image.onload = function() {
                canvas.width = image.width;
                canvas.height = image.height;
                ctx.mozImageSmoothingEnabled = false;
                ctx.webkitImageSmoothingEnabled = false;
                ctx.msImageSmoothingEnabled = false;
                ctx.imageSmoothingEnabled = false;
                ctx.drawImage(image, 0, 0);
                originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                clearGroups();
                displayPalette(colorSet);
                loadGroupData(file.name);
                loadDefaultColors();  // Call to load default colors
            };
        };
        tempImage.src = e.target.result;
    };
    reader.readAsDataURL(file);
}
function loadDefaultColors() {
    if (!image.src) return;

    const imageName = uploadedFileName; // Use the cleaned image name
    const matchedGroups = defaultColorGroups.filter(group => group.imageName === imageName);

    if (matchedGroups.length === 0) {
        return;
    } else if (matchedGroups.length === 1) {
        const defaultGroupData = matchedGroups[0];
        loadSelectedGroup(defaultGroupData);
    } else {
        showGroupDropdown(matchedGroups);
    }
}

function showGroupDropdown(matchedGroups) {
    const dropdownContainer = document.getElementById('group-dropdown-container');
    const groupSelect = document.getElementById('group-select');
    groupSelect.innerHTML = ''; // Clear previous options

    matchedGroups.forEach((groupData, index) => {
        const option = document.createElement('option');
        option.value = index;
        let displayName = groupData.groupName;
        if (groupData.authorName && groupData.authorName !== "Creator") {
            displayName += ` - ${groupData.authorName}`;
        }
        option.text = displayName;
        groupSelect.appendChild(option);
    });

    dropdownContainer.style.display = 'block';

    // Add event listener to dynamically load the selected group
    groupSelect.addEventListener('change', function() {
        const selectedIndex = groupSelect.value;
        if (selectedIndex !== null && selectedIndex !== '') {
            const selectedGroup = matchedGroups[selectedIndex];
            loadSelectedGroup(selectedGroup);
        }
    });

    // Automatically load the first group if available
    if (matchedGroups.length > 0) {
        groupSelect.value = 0;
        loadSelectedGroup(matchedGroups[0]);
    }
}

function loadSelectedGroup(selectedGroup) {
    colorGroups = selectedGroup.groups.map(group => ({
        name: group.name,
        colors: new Set(group.colors),
        hue: group.hue,
        brightness: group.brightness,
        contrast: group.contrast,
        saturation: group.saturation,
        tintColor: group.tintColor,
        tintStrength: group.tintStrength
    }));
    displayGroups();
    applyAdjustments(); // Update the image preview
}

function getColorSet(imageData) {
    let colorSet = new Set();
    for (let i = 0; i < imageData.data.length; i += 4) {
        let r = imageData.data[i];
        let g = imageData.data[i + 1];
        let b = imageData.data[i + 2];
        let color = `rgb(${r}, ${g}, ${b})`;
        colorSet.add(color);
    }
    return colorSet;
}

function displayPalette(colorSet) {
    let palette = document.getElementById('palette');
    palette.innerHTML = '';

    colorSet.forEach(color => {
        let colorBox = document.createElement('div');
        colorBox.style.backgroundColor = color;
        colorBox.classList.add('color-box');
        colorBox.addEventListener('click', () => toggleColorSelection(colorBox, color));
        colorBox.addEventListener('mouseover', () => handleColorHover(colorBox, color));
        colorBox.addEventListener('mouseout', () => handleColorOut(colorBox, color));
        palette.appendChild(colorBox);
    });
}
function showGroupNamePopup() {
    const popup = document.getElementById('group-name-popup');
    const imageNameInput = document.getElementById('image-name-input');
    const authorNameInput = document.getElementById('author-name-input');
    imageNameInput.value = uploadedFileName; // Set the current image name
    authorNameInput.value = "Creator"; // Default author name
    popup.style.display = 'block';
}

document.getElementById('save-group-name-btn').addEventListener('click', function() {
    const imageNameInput = document.getElementById('image-name-input');
    const groupNameInput = document.getElementById('group-name-input');
    const authorNameInput = document.getElementById('author-name-input');
    const newImageName = imageNameInput.value.trim();
    const groupName = groupNameInput.value.trim();
    const authorName = authorNameInput.value.trim();

    if (newImageName && groupName) {
        uploadedFileName = newImageName; // Update the global image name
        exportGroupData(newImageName, groupName, authorName);
        document.getElementById('group-name-popup').style.display = 'none';
    } else {
        alert('Please enter valid image, group, and author names.');
    }
});

function handleColorOut(colorBox) {
    if (!colorBox.classList.contains('selected')) {
        colorBox.classList.remove('hover');
    }
}

function handleCanvasHover(event) {
    if (!originalImageData) return;
    let rect = canvas.getBoundingClientRect();
    let x = Math.floor(event.clientX - rect.left);
    let y = Math.floor(event.clientY - rect.top);
    let index = (y * canvas.width + x) * 4;
    if (index < 0 || index >= originalImageData.data.length) return;

    let r = originalImageData.data[index];
    let g = originalImageData.data[index + 1];
    let b = originalImageData.data[index + 2];
    let color = `rgb(${r}, ${g}, ${b})`;
    handleColorHoverPalette(color);

    let colorPreview = document.getElementById('color-preview');
    colorPreview.style.left = `${rect.right + 20}px`; // Fixed in place to the right of the image preview
    colorPreview.style.top = `${rect.top}px`;
    colorPreview.style.display = 'grid';
    updateColorPreview(x, y);
}
function handleColorHover(colorBox, color) {
    if (!colorBox.classList.contains('selected')) {
        colorBox.classList.add('hover');
    }
}

function handleColorHoverPalette(color) {
    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');

    for (let colorBox of colorBoxes) {
        if (colorBox.style.backgroundColor === color) {
            if (!colorBox.classList.contains('selected')) {
                colorBox.classList.add('hover');
            }
        } else {
            colorBox.classList.remove('hover');
        }
    }
}

function hideColorPreview() {
    let colorPreview = document.getElementById('color-preview');
    colorPreview.style.display = 'none';

    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');
    for (let colorBox of colorBoxes) {
        if (!colorBox.classList.contains('selected')) {
            colorBox.classList.remove('hover');
        }
    }
}

function handleCanvasClick(event) {
    if (!originalImageData) return;
    let rect = canvas.getBoundingClientRect();
    let x = Math.floor(event.clientX - rect.left);
    let y = Math.floor(event.clientY - rect.top);
    let index = (y * canvas.width + x) * 4;
    if (index < 0 || index >= originalImageData.data.length) return;

    let r = originalImageData.data[index];
    let g = originalImageData.data[index + 1];
    let b = originalImageData.data[index + 2];
    let clickedColor = `rgb(${r}, ${g}, ${b})`;

    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');
    
    for (let colorBox of colorBoxes) {
        if (colorBox.style.backgroundColor === clickedColor) {
            toggleColorSelection(colorBox, clickedColor);
            break;
        }
    }
}

function toggleColorSelection(colorBox, color) {
    if (selectedColors.has(color)) {
        selectedColors.delete(color);
        colorBox.classList.remove('selected');
        colorBox.classList.remove('hover');
        if (activeGroup) {
            activeGroup.colors.delete(color);
        }
    } else {
        if (!activeGroup) {
            activeGroup = { name: `Group ${colorGroups.length + 1}`, colors: new Set(), tintColor: currentTintColor, tintStrength: currentTintStrength };
            colorGroups.push(activeGroup);
            displayGroups();
        }
        selectedColors.add(color);
        colorBox.classList.add('selected');
        colorBox.classList.add('hover');
        if (activeGroup) {
            activeGroup.colors.add(color);
        }
    }
    updateCenterBoxBorder(color);
    updateGroupColors();
    highlightSelectedColorPixels(color);
    applyAdjustments(); // Apply all adjustments after selection changes
    saveGroupsLocally();
}

function highlightSelectedColorPixels(color) {
    let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    let colorComponents = getColorComponents(color);

    for (let i = 0; i < imageData.data.length; i += 4) {
        if (
            imageData.data[i] === colorComponents[0] &&
            imageData.data[i + 1] === colorComponents[1] &&
            imageData.data[i + 2] === colorComponents[2]
        ) {
            imageData.data[i] = 255 - imageData.data[i];
            imageData.data[i + 1] = 255 - imageData.data[i + 1];
            imageData.data[i + 2] = 255 - imageData.data[i + 2];
        }
    }
    ctx.putImageData(imageData, 0, 0);
}

function updateCenterBoxBorder(color) {
    let colorPreview = document.getElementById('color-preview');
    let centerBox = colorPreview.querySelector('.center');
    if (centerBox) {
        if (selectedColors.has(color)) {
            centerBox.classList.add('selected');
            centerBox.style.borderWidth = '40px';
            centerBox.style.borderColor = 'red';
        } else {
            centerBox.classList.remove('selected');
            centerBox.style.borderWidth = '10px';
            centerBox.style.borderColor = '#000';
        }
    }
}

function handleHueChange(event) {
    currentHue = parseInt(event.target.value);
    document.getElementById('hue-value').innerText = currentHue;
    if (activeGroup) activeGroup.hue = currentHue;
    applyAdjustments();
}

function handleBrightnessChange(event) {
    currentBrightness = parseInt(event.target.value);
    document.getElementById('brightness-value').innerText = currentBrightness;
    if (activeGroup) activeGroup.brightness = currentBrightness;
    applyAdjustments();
}

function handleContrastChange(event) {
    currentContrast = parseInt(event.target.value);
    document.getElementById('contrast-value').innerText = currentContrast;
    if (activeGroup) activeGroup.contrast = currentContrast;
    applyAdjustments();
}

function handleSaturationChange(event) {
    currentSaturation = parseInt(event.target.value);
    document.getElementById('saturation-value').innerText = currentSaturation;
    if (activeGroup) activeGroup.saturation = currentSaturation;
    applyAdjustments();
}

function handleTintChange(event) {
    currentTintStrength = parseInt(event.target.value);
    document.getElementById('tint-value').innerText = currentTintStrength;
    if (currentTintStrength === 0) {
        currentTintColor = '#ffffff'; // Disable tinting
    } else {
        currentTintColor = document.getElementById('tint-color').value;
    }
    tintRgb = hexToRgb(currentTintColor);
    if (activeGroup) activeGroup.tintStrength = currentTintStrength;
    applyAdjustments();
}

function handleTintColorChange(event) {
    currentTintColor = event.target.value;
    tintRgb = hexToRgb(currentTintColor); // Update the global tint color value
    if (activeGroup) activeGroup.tintColor = currentTintColor;
    applyAdjustments();
}

function applyAdjustments() {
    let imageData = ctx.createImageData(originalImageData.width, originalImageData.height);
    let factor = (259 * (currentContrast + 255)) / (255 * (259 - currentContrast));

    for (let i = 0; i < originalImageData.data.length; i += 4) {
        let r = originalImageData.data[i];
        let g = originalImageData.data[i + 1];
        let b = originalImageData.data[i + 2];
        let a = originalImageData.data[i + 3];
        let color = `rgb(${r}, ${g}, ${b})`;

        let adjusted = false;

        colorGroups.forEach(group => {
            if (group.colors.has(color)) {
                let hue = group.hue !== undefined ? group.hue : 0;
                let brightness = group.brightness !== undefined ? group.brightness : 0;
                let contrast = group.contrast !== undefined ? group.contrast : 0;
                let saturation = group.saturation !== undefined ? group.saturation : 0;
                let tintColor = group.tintColor !== undefined ? group.tintColor : '#ffffff';
                let tintStrength = group.tintStrength !== undefined ? group.tintStrength : 0;

                let groupFactor = (259 * (contrast + 255)) / (255 * (259 - contrast));

                let [h, s, l] = rgbToHsl(r, g, b);
                h = (currentHue !== 0) ? (h + hue) % 360 : h;
                s = Math.min(Math.max(s + saturation / 100, 0), 1);
                [r, g, b] = hslToRgb(h, s, l);

                r = Math.min(Math.max(r + brightness, 0), 255);
                g = Math.min(Math.max(g + brightness, 0), 255);
                b = Math.min(Math.max(g + brightness, 0), 255);

                r = Math.min(Math.max(groupFactor * (r - 128) + 128, 0), 255);
                g = Math.min(Math.max(groupFactor * (g - 128) + 128, 0), 255);
                b = Math.min(Math.max(groupFactor * (b - 128) + 128, 0), 255);

                if (tintStrength > 0) {
                    let groupTintRgb = hexToRgb(tintColor);
                    r = blendColors(r, groupTintRgb.r, tintStrength);
                    g = blendColors(g, groupTintRgb.g, tintStrength);
                    b = blendColors(b, groupTintRgb.b, tintStrength);
                }

                adjusted = true;
            }
        });

        if (!adjusted) {
            r = originalImageData.data[i];
            g = originalImageData.data[i + 1];
            b = originalImageData.data[i + 2];
            a = originalImageData.data[i + 3];
        }

        imageData.data[i] = r;
        imageData.data[i + 1] = g;
        imageData.data[i + 2] = b;
        imageData.data[i + 3] = a;
    }

    ctx.putImageData(imageData, 0, 0);
}

function blendColors(color1, color2, strength) {
    return Math.round((color1 * (100 - strength) + color2 * strength) / 100);
}

function downloadGroups() {
    if (!image.src) {
        alert("Please upload an image before downloading groups.");
        return;
    }

    showGroupNamePopup(); // Show popup to get the group name, image name, and author name
}

function exportGroupData(newImageName, groupName, authorName) {
    let groupData = {
        imageName: newImageName,
        groupName: groupName,
        authorName: authorName,
        groups: colorGroups.map(group => ({
            name: group.name,
            colors: Array.from(group.colors),
            hue: group.hue !== undefined ? group.hue : 0,
            brightness: group.brightness !== undefined ? group.brightness : 0,
            contrast: group.contrast !== undefined ? group.contrast : 0,
            saturation: group.saturation !== undefined ? group.saturation : 0,
            tintColor: group.tintColor !== undefined ? group.tintColor : '#ffffff',
            tintStrength: group.tintStrength !== undefined ? group.tintStrength : 0
        }))
    };

    // Format the file name
    let fileName = `${newImageName}_${groupName}`;
    if (authorName !== "Creator") {
        fileName += `_${authorName}`;
    }
    fileName += "_groups.json";

    // Export format for direct copy-paste
    let dataStr = JSON.stringify(groupData, null, 4);
    let exportStr = `defaultColorGroups.push(${dataStr});\n`;
    let downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", "data:text/javascript;charset=utf-8," + encodeURIComponent(exportStr));
    downloadAnchorNode.setAttribute("download", fileName);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}
function uploadGroups(event) {
    let file = event.target.files[0];
    let reader = new FileReader();

    reader.onload = function(e) {
        let groupData = JSON.parse(e.target.result);

        if (groupData.imageName === image.src.split('/').pop()) {
            colorGroups = groupData.groups.map(group => ({
                name: group.name,
                colors: new Set(group.colors),
                hue: group.hue !== undefined ? group.hue : 0,
                brightness: group.brightness !== undefined ? group.brightness : 0,
                contrast: group.contrast !== undefined ? group.contrast : 0,
                saturation: group.saturation !== undefined ? group.saturation : 0,
                tintColor: group.tintColor !== undefined ? group.tintColor : '#ffffff',
                tintStrength: group.tintStrength !== undefined ? group.tintStrength : 0
            }));
            displayGroups();
            saveGroupsLocally();
        } else {
            alert("Uploaded group data does not match the current image.");
        }
    }

    reader.readAsText(file);
}
function displayGroups() {
    let groupsContainer = document.getElementById('groups');
    groupsContainer.innerHTML = '';

    colorGroups.forEach((group, index) => {
        let groupElement = document.createElement('div');
        groupElement.className = 'group';
        groupElement.innerHTML = `<span class="group-name" ondblclick="renameGroup(this, ${index})">${group.name}</span>`;
        groupElement.addEventListener('click', () => toggleGroupSelection(index));
        
        let groupColors = document.createElement('div');
        groupColors.className = 'group-colors';
        
        group.colors.forEach(color => {
            let colorElement = document.createElement('div');
            colorElement.className = 'group-color';
            colorElement.style.backgroundColor = color;
            groupColors.appendChild(colorElement);
        });
        
        groupElement.appendChild(groupColors);
        groupsContainer.appendChild(groupElement);
    });
}

function toggleGroupSelection(index) {
    if (activeGroup !== null) {
        activeGroup.hue = currentHue;
        activeGroup.brightness = currentBrightness;
        activeGroup.contrast = currentContrast;
        activeGroup.saturation = currentSaturation;
        activeGroup.tintColor = currentTintColor;
        activeGroup.tintStrength = currentTintStrength;
    }

    if (activeGroup === colorGroups[index]) {
        activeGroup = null;
        selectedColors.clear();
        resetSliders();
    } else {
        activeGroup = colorGroups[index];
        selectedColors = new Set(activeGroup.colors);

        currentHue = activeGroup.hue || 0;
        currentBrightness = activeGroup.brightness || 0;
        currentContrast = activeGroup.contrast || 0;
        currentSaturation = activeGroup.saturation || 0;
        currentTintColor = activeGroup.tintColor || '#ffffff';
        currentTintStrength = activeGroup.tintStrength || 0;

        document.getElementById('hue-slider').value = currentHue;
        document.getElementById('hue-value').innerText = currentHue;

        document.getElementById('brightness-slider').value = currentBrightness;
        document.getElementById('brightness-value').innerText = currentBrightness;

        document.getElementById('contrast-slider').value = currentContrast;
        document.getElementById('contrast-value').innerText = currentContrast;

        document.getElementById('saturation-slider').value = currentSaturation;
        document.getElementById('saturation-value').innerText = currentSaturation;

        document.getElementById('tint-slider').value = currentTintStrength;
        document.getElementById('tint-value').innerText = currentTintStrength;

        document.getElementById('tint-color').value = currentTintColor;
    }

    applyAdjustments();

    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');

    for (let colorBox of colorBoxes) {
        if (selectedColors.has(colorBox.style.backgroundColor)) {
            colorBox.classList.add('selected');
            colorBox.classList.add('hover');
        } else {
            colorBox.classList.remove('selected');
            colorBox.classList.remove('hover');
        }
    }

    let groupsContainer = document.getElementById('groups');
    let groupElements = groupsContainer.getElementsByClassName('group');

    for (let groupElement of groupElements) {
        groupElement.classList.remove('selected');
    }

    if (activeGroup) {
        groupElements[index].classList.add('selected');
    }

    updateGroupColors();
}

function resetSliders() {
    currentHue = 0;
    currentBrightness = 0;
    currentContrast = 0;
    currentSaturation = 0;
    currentTintStrength = 0;
    currentTintColor = '#ffffff';

    document.getElementById('hue-slider').value = currentHue;
    document.getElementById('brightness-slider').value = currentBrightness;
    document.getElementById('contrast-slider').value = currentContrast;
    document.getElementById('saturation-slider').value = currentSaturation;
    document.getElementById('tint-slider').value = currentTintStrength;
    document.getElementById('tint-color').value = currentTintColor;
}

function renameGroup(span, index) {
    let input = document.createElement('input');
    input.type = 'text';
    input.value = span.textContent;
    input.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            saveGroupName(input, span, index);
        }
    });
    span.replaceWith(input);
    input.focus();
}

function saveGroupName(input, span, index) {
    colorGroups[index].name = input.value;
    input.replaceWith(span);
    span.textContent = input.value;
    saveGroupsLocally();
}

function saveGroupsLocally() {
    if (!image.src) return;

    let groupData = {
        imageName: image.src.split('/').pop(),
        groups: colorGroups.map(group => ({
            name: group.name,
            colors: Array.from(group.colors),
            hue: group.hue !== undefined ? group.hue : 0,
            brightness: group.brightness !== undefined ? group.brightness : 0,
            contrast: group.contrast !== undefined ? group.contrast : 0,
            saturation: group.saturation !== undefined ? group.saturation : 0,
            tintColor: group.tintColor !== undefined ? group.tintColor : '#ffffff',
            tintStrength: group.tintStrength !== undefined ? group.tintStrength : 0
        }))
    };

    localStorage.setItem(groupData.imageName, JSON.stringify(groupData));
}

function loadGroupData(imageName) {
    let groupData = localStorage.getItem(imageName);

    if (groupData) {
        groupData = JSON.parse(groupData);
        colorGroups = groupData.groups.map(group => ({
            name: group.name,
            colors: new Set(group.colors),
            hue: group.hue !== undefined ? group.hue : 0,
            brightness: group.brightness !== undefined ? group.brightness : 0,
            contrast: group.contrast !== undefined ? group.contrast : 0,
            saturation: group.saturation !== undefined ? group.saturation : 0,
            tintColor: group.tintColor !== undefined ? group.tintColor : '#ffffff',
            tintStrength: group.tintStrength !== undefined ? group.tintStrength : 0
        }));
        displayGroups();
    } else {
        colorGroups = [];
    }

    activeGroup = null;
}
function drawSelectionRect(event) {
    let rect = canvas.getBoundingClientRect();
    endX = event.clientX - rect.left;
    endY = event.clientY - rect.top;
    ctx.putImageData(originalImageData, 0, 0); // Reset the canvas to the original image
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, endX - startX, endY - startY);
}
function getColorComponents(color) {
    let match = color.match(/\d+/g);
    return [parseInt(match[0]), parseInt(match[1]), parseInt(match[2]), 255];
}

function rgbToHsl(r, g, b) {
    r /= 255, g /= 255, b /= 255;
    let max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
        h = s = 0;
    } else {
        let d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }

    return [h * 360, s, l];
}

function hslToRgb(h, s, l) {
    let r, g, b;

    if (s === 0) {
        r = g = b = l;
    } else {
        let hue2rgb = function hue2rgb(p, q, t) {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 3) return q;
            if (t < 1 / 2) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        }

        let q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        let p = 2 * l - q;
        h /= 360;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }

    return [r * 255, g * 255, b * 255];
}

function hexToRgb(hex) {
    let bigint = parseInt(hex.slice(1), 16);
    return {
        r: (bigint >> 16) & 255,
        g: (bigint >> 8) & 255,
        b: bigint & 255
    };
}

function blendColors(color1, color2, strength) {
    return Math.round((color1 * (100 - strength) + color2 * strength) / 100);
}

function updateColorPreview(x, y) {
    let colorPreview = document.getElementById('color-preview');
    colorPreview.innerHTML = '';
    colorPreview.style.display = 'grid';
    colorPreview.style.gridTemplateColumns = 'repeat(33, 10px)'; // Adjust the number of columns and size as needed

    for (let dy = -16; dy <= 16; dy++) {
        for (let dx = -16; dx <= 16; dx++) {
            let nx = Math.min(Math.max(0, x + dx), canvas.width - 1);
            let ny = Math.min(Math.max(0, y + dy), canvas.height - 1);
            let pixelData = ctx.getImageData(nx, ny, 1, 1).data;
            let color = `rgb(${pixelData[0]}, ${pixelData[1]}, ${pixelData[2]})`;

            let colorCell = document.createElement('div');
            colorCell.className = 'color-preview-cell';
            if (dx === 0 && dy === 0) {
                colorCell.classList.add('center');
                if (selectedColors.has(color)) {
                    colorCell.classList.add('selected');
                } else {
                    colorCell.classList.remove('selected');
                }
            }
            colorCell.style.backgroundColor = color;
            colorPreview.appendChild(colorCell);
        }
    }
}

function adjustColorForGroup(r, g, b, group) {
    let factor = (259 * (group.contrast + 255)) / (255 * (259 - group.contrast));
    let [h, s, l] = rgbToHsl(r, g, b);
    h = (h + group.hue) % 360;
    s = Math.min(Math.max(s + group.saturation / 100, 0), 1);
    [r, g, b] = hslToRgb(h, s, l);
    r = Math.min(Math.max(factor * (r - 128) + 128 + group.brightness, 0), 255);
    g = Math.min(Math.max(factor * (g - 128) + 128 + group.brightness, 0), 255);
    b = Math.min(Math.max(factor * (b - 128) + 128 + group.brightness, 0), 255);
    return [r, g, b];
}
function clearGroups() {
    colorGroups = [];
    activeGroup = null;
    document.getElementById('groups').innerHTML = '';
}
function updateGroupColors() {
    let groupsContainer = document.getElementById('groups');

    colorGroups.forEach((group, index) => {
        let groupElement = groupsContainer.children[index];
        let groupColors = groupElement.querySelector('.group-colors');

        groupColors.innerHTML = '';

        group.colors.forEach(color => {
            let colorElement = document.createElement('div');
            colorElement.className = 'group-color';
            colorElement.style.backgroundColor = color;
            groupColors.appendChild(colorElement);
        });
    });
}

