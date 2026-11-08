import React from 'react';

export const SPINNER_SVG: React.ReactNode = (
  <svg 
    className="animate-spin h-5 w-5 text-white" 
    xmlns="http://www.w3.org/2000/svg" 
    fill="none" 
    viewBox="0 0 24 24"
  >
    <circle 
      className="opacity-25" 
      cx="12" 
      cy="12" 
      r="10" 
      stroke="currentColor" 
      strokeWidth="4"
    ></circle>
    <path 
      className="opacity-75" 
      fill="currentColor" 
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    ></path>
  </svg>
);

export const DEFAULT_TINT_COLOR_HEX = "#FFFFFF";
export const INITIAL_HUE_DELTA = 0;
export const INITIAL_SATURATION_DELTA = 0;
export const INITIAL_LIGHTNESS_DELTA = 0;
export const INITIAL_CONTRAST_DELTA = 0;
export const INITIAL_ALPHA_DELTA = 0; // Added for alpha adjustment
export const INITIAL_TINT_AMOUNT = 0;

export const MAX_PALETTE_COLORS_DISPLAY = 100;
export const MAX_UNIQUE_COLORS_PROCESSING = 500; 
export const ALL_COLORS_GROUP_ID = 'ALL_COLORS_GROUP_ID';