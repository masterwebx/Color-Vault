document.getElementById('upload').addEventListener('change', handleImageUpload);
document.getElementById('hue-slider').addEventListener('input', handleHueChange);
document.getElementById('canvas').addEventListener('mousemove', handleCanvasHover);
document.getElementById('canvas').addEventListener('mouseout', hideColorPreview);
document.getElementById('canvas').addEventListener('click', handleCanvasClick);
document.getElementById('create-group-btn').addEventListener('click', createGroup);
document.getElementById('download-groups-btn').addEventListener('click', downloadGroups);
document.getElementById('upload-groups').addEventListener('change', uploadGroups);

let canvas = document.getElementById('canvas');
let ctx = canvas.getContext('2d', { willReadFrequently: true });
let image = new Image();
let originalImageData;
let selectedColors = new Set();
let colorGroups = [];
let activeGroup = null;
let colorMap = new Map();

function handleImageUpload(event) {
    let file = event.target.files[0];
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

            if (colorSet.size > 500) {
                alert("The image has more than 500 colors and cannot be loaded.");
                return;
            }

            image.src = e.target.result;
            image.onload = function() {
                canvas.width = image.width;
                canvas.height = image.height;
                ctx.drawImage(image, 0, 0);
                originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                clearGroups();
                displayPalette(colorSet);
                loadGroupData(file.name);
                triggerWaveEffect();
            }
        }
        tempImage.src = e.target.result;
    }
    reader.readAsDataURL(file);
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

function handleColorHover(colorBox) {
    if (!colorBox.classList.contains('selected')) {
        colorBox.classList.add('hover');
    }
}

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
    colorPreview.style.left = `${event.clientX + 10}px`;
    colorPreview.style.top = `${event.clientY + 10}px`;
    colorPreview.style.display = 'grid';
    updateColorPreview(x, y);
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
    } else {
        selectedColors.add(color);
        colorBox.classList.add('selected');
        colorBox.classList.add('hover');
    }
    updateCenterBoxBorder(color);
    updateGroupColors();
}

function updateCenterBoxBorder(color) {
    let colorPreview = document.getElementById('color-preview');
    let centerBox = colorPreview.querySelector('.center');
    if (centerBox) {
        if (selectedColors.has(color)) {
            centerBox.classList.remove('not-selected');
        } else {
            centerBox.classList.add('not-selected');
        }
    }
}

function handleHueChange(event) {
    let hue = parseInt(event.target.value);
    let imageData = ctx.createImageData(originalImageData.width, originalImageData.height);

    if (activeGroup) {
        activeGroup.colors.forEach(color => {
            let [r, g, b, a] = colorMap.get(color) || getColorComponents(color);
            let [h, s, l] = rgbToHsl(r, g, b);
            h = (h + hue) % 360;
            [r, g, b] = hslToRgb(h, s, l);
            let newColor = `rgb(${r}, ${g}, ${b})`;
            colorMap.set(color, [r, g, b, a]);
        });
    }

    for (let i = 0; i < originalImageData.data.length; i += 4) {
        let r = originalImageData.data[i];
        let g = originalImageData.data[i + 1];
        let b = originalImageData.data[i + 2];
        let a = originalImageData.data[i + 3];
        let color = `rgb(${r}, ${g}, ${b})`;

        if (colorMap.has(color)) {
            [r, g, b, a] = colorMap.get(color);
        }

        imageData.data[i] = r;
        imageData.data[i + 1] = g;
        imageData.data[i + 2] = b;
        imageData.data[i + 3] = a;
    }

    ctx.putImageData(imageData, 0, 0);
    updateGroupColors();
}

function updateGroupColors() {
    let groupsContainer = document.getElementById('groups');
    let groupElements = groupsContainer.getElementsByClassName('group');

    colorGroups.forEach((group, index) => {
        let groupColorsContainer = groupElements[index].querySelector('.group-colors');
        groupColorsContainer.innerHTML = '';

        group.colors.forEach(color => {
            let colorElement = document.createElement('div');
            colorElement.className = 'group-color';
            colorElement.style.backgroundColor = color;
            groupColorsContainer.appendChild(colorElement);
        });
    });
}

function createGroup() {
    if (selectedColors.size === 0) {
        alert("Please select colors to create a group.");
        return;
    }

    let newGroup = { name: `Group ${colorGroups.length + 1}`, colors: new Set(selectedColors) };
    colorGroups.push(newGroup);
    selectedColors.clear();
    displayPalette(getColorSet(originalImageData)); // Refresh the palette to update selected colors
    displayGroups();
    saveGroupsLocally();
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
    if (activeGroup === colorGroups[index]) {
        activeGroup = null;
        selectedColors.clear();
    } else {
        activeGroup = colorGroups[index];
        selectedColors = new Set(activeGroup.colors);
    }

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
            colors: Array.from(group.colors)
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
            colors: new Set(group.colors)
        }));
        displayGroups();
    } else {
        colorGroups = [];
    }

    activeGroup = null;
    colorMap.clear();
}

function downloadGroups() {
    if (!image.src) {
        alert("Please upload an image before downloading groups.");
        return;
    }

    let groupData = {
        imageName: image.src.split('/').pop(),
        groups: colorGroups.map(group => ({
            name: group.name,
            colors: Array.from(group.colors)
        }))
    };

    let dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(groupData));
    let downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `${groupData.imageName}_groups.json`);
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
                colors: new Set(group.colors)
            }));
            displayGroups();
            saveGroupsLocally();
        } else {
            alert("Uploaded group data does not match the current image.");
        }
    }

    reader.readAsText(file);
}

function clearGroups() {
    colorGroups = [];
    activeGroup = null;
    colorMap.clear();
    document.getElementById('groups').innerHTML = '';
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

function updateColorPreview(x, y) {
    let colorPreview = document.getElementById('color-preview');
    colorPreview.innerHTML = '';

    for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
            let nx = Math.min(Math.max(0, x + dx), canvas.width - 1);
            let ny = Math.min(Math.max(0, y + dy), canvas.height - 1);
            let pixelData = ctx.getImageData(nx, ny, 1, 1).data;
            let color = `rgb(${pixelData[0]}, ${pixelData[1]}, ${pixelData[2]})`;

            let colorCell = document.createElement('div');
            colorCell.className = 'color-preview-cell';
            if (dx === 0 && dy === 0) {
                colorCell.classList.add('center');
                if (selectedColors.has(color)) {
                    colorCell.classList.remove('not-selected');
                } else {
                    colorCell.classList.add('not-selected');
                }
            }
            colorCell.style.backgroundColor = color;
            colorPreview.appendChild(colorCell);
        }
    }
}

function triggerWaveEffect() {
    let palette = document.getElementById('palette');
    let colorBoxes = palette.getElementsByClassName('color-box');

    let delay = 0;
    for (let i = 0; i < colorBoxes.length; i++) {
        setTimeout(() => {
            colorBoxes[i].classList.add('hover');
            setTimeout(() => {
                colorBoxes[i].classList.remove('hover');
            }, 200);
        }, delay);
        delay += 50 / 1.5; // 1.5x faster
    }
}
