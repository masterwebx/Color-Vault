// This is the content for C:\Users\glwex\Downloads\archive 2025\pixel-art-recolor-tool\index.tsx
console.log("Vite App: index.tsx started executing!"); // ADD THIS LINE
import './index.css'; // This imports your CSS, so Vite bundles it
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);