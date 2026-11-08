import React from 'react';
import { PaletteColor } from '../types';
import { MAX_PALETTE_COLORS_DISPLAY } from '../constants';

interface ColorPaletteProps {
  palette: PaletteColor[];
  selectedPaletteColors: Set<string>;
  onColorSelect: (hex: string) => void;
}

const ColorPalette: React.FC<ColorPaletteProps> = ({ palette, selectedPaletteColors, onColorSelect }) => {
  if (palette.length === 0) {
    return (
      <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg mt-4">
        <h3 className="text-lg font-semibold mb-2 text-sky-400">Extracted Palette</h3>
        <p className="text-slate-400">Upload an image to see its palette.</p>
      </div>
    );
  }

  const displayPalette = palette.slice(0, MAX_PALETTE_COLORS_DISPLAY);
  const hiddenColorsCount = palette.length - displayPalette.length;

  return (
    <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg mt-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-sky-400">Extracted Palette ({palette.length})</h3>
        {selectedPaletteColors.size > 0 && (
          <span className="text-sm text-sky-300">{selectedPaletteColors.size} selected</span>
        )}
      </div>
      <p className="text-xs text-slate-400 mb-3">Click colors to select them for grouping.</p>
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-60 overflow-y-auto custom-scrollbar pr-2">
        {displayPalette.map((color) => {
          const isSelected = selectedPaletteColors.has(color.hex);
          return (
            <div 
              key={color.hex} 
              className={`flex flex-col items-center cursor-pointer p-1 rounded-md transition-all duration-150 ease-in-out ${isSelected ? 'ring-2 ring-sky-400 scale-105 bg-sky-900/50' : 'hover:bg-slate-700/50'}`}
              title={color.hex}
              onClick={() => onColorSelect(color.hex)}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              aria-label={`Select color ${color.hex}`}
            >
              <div
                className="w-10 h-10 rounded border border-slate-600 shadow-md"
                style={{ backgroundColor: color.hex }}
              ></div>
              <span className={`text-xs mt-1 ${isSelected ? 'text-sky-300 font-medium': 'text-slate-400'}`}>{color.hex.substring(1)}</span>
            </div>
          );
        })}
      </div>
      {hiddenColorsCount > 0 && (
         <p className="text-xs text-slate-500 mt-2">...and {hiddenColorsCount} more colors.</p>
      )}
    </div>
  );
};

export default ColorPalette;
