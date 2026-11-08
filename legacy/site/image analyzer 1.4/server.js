// server.js
const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// Serve static files from the current directory
app.use(express.static(__dirname));

// Endpoint to get filenames from the sheets directory
app.get('/sheets', (req, res) => {
    const sheetsDir = path.join(__dirname, 'sheets');
    fs.readdir(sheetsDir, (err, files) => {
        if (err) {
            return res.status(500).json({ error: 'Unable to scan directory' });
        }
        // Filter to include only image files
        const imageFiles = files.filter(file => /\.(png|jpg|jpeg|gif)$/i.test(file));
        res.json(imageFiles);
    });
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});