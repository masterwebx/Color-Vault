

import React from 'react';
import { RGBColor } from '../types';
import { hexToRgb } from '../services/colorService';
import { 
  DEFAULT_TINT_COLOR_HEX,
  INITIAL_HUE_DELTA,
  INITIAL_SATURATION_DELTA,
  INITIAL_LIGHTNESS_DELTA,
  INITIAL_CONTRAST_DELTA, 
  INITIAL_ALPHA_DELTA, // Import new constant
  INITIAL_TINT_AMOUNT
} from '../constants';


interface ColorControlsProps {
  hueDelta: number;
  setHueDelta: (value: number) => void;
  saturationDelta: number;
  setSaturationDelta: (value: number) => void;
  lightnessDelta: number;
  setLightnessDelta: (value: number) => void;
  contrastDelta: number; 
  setContrastDelta: (value: number) => void; 
  alphaDelta: number; // New prop for alpha
  setAlphaDelta: (value: number) => void; // New setter for alpha
  tintColor: RGBColor;
  setTintColor: (color: RGBColor) => void;
  tintAmount: number;
  setTintAmount: (value: number) => void;
  onResetControls: () => void;
  isProcessing: boolean;
}

const SliderControl: React.FC<{
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  disabled: boolean;
  displaySuffix?: string;
  presets?: number[]; // Optional presets for the slider
  onPresetClick?: (value: number) => void; // Handler for preset clicks
}> = ({ label, value, min, max, step, onChange, disabled, displaySuffix = "", presets, onPresetClick }) => (
  <div className="mb-4">
    <div className="flex justify-between items-center mb-1">
        <label className="block text-sm font-medium text-slate-300">
        {label}: <span className="font-semibold text-sky-400">{value}{displaySuffix}</span>
        </label>
        {presets && onPresetClick && (
            <div className="flex space-x-1">
                {presets.map(pVal => (
                    <button
                        key={pVal}
                        onClick={() => onPresetClick(pVal)}
                        disabled={disabled}
                        className={`text-xs px-1.5 py-0.5 rounded ${ value === pVal ? 'bg-sky-500 text-white' : 'bg-slate-600 hover:bg-slate-500 text-slate-200'} focus:outline-none focus:ring-1 focus:ring-sky-400 disabled:opacity-50`}
                    >
                        {pVal}
                    </button>
                ))}
            </div>
        )}
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      disabled={disabled}
      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500 disabled:opacity-50"
    />
  </div>
);


const ColorControls: React.FC<ColorControlsProps> = ({
  hueDelta, setHueDelta,
  saturationDelta, setSaturationDelta,
  lightnessDelta, setLightnessDelta,
  contrastDelta, setContrastDelta, 
  alphaDelta, setAlphaDelta, // Destructure new alpha props
  tintColor, setTintColor,
  tintAmount, setTintAmount,
  onResetControls,
  isProcessing
}) => {

  const handleTintColorChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newHexColor = event.target.value;
    const newRgbColor = hexToRgb(newHexColor);
    if (newRgbColor) {
      setTintColor(newRgbColor);
    }
  };
  
  const currentTintColorHex = `#${tintColor.r.toString(16).padStart(2, '0')}${tintColor.g.toString(16).padStart(2, '0')}${tintColor.b.toString(16).padStart(2, '0')}`;
  const tintAmountPresets = [0, 25, 50, 75, 100];
  const alphaDeltaPresets = [-100, -50, 0];


  return (
    // Removed mt-4 from here, as App.tsx will handle its spacing
    <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-semibold text-sky-400">Color Controls</h3>
        <button
            onClick={onResetControls}
            disabled={isProcessing}
            className="text-xs bg-slate-600 hover:bg-slate-500 text-slate-200 font-medium py-1 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
        >
            Reset
        </button>
      </div>

      <SliderControl label="Hue Shift" value={hueDelta} min={-180} max={180} step={1} onChange={setHueDelta} disabled={isProcessing} displaySuffix="°"/>
      <SliderControl label="Saturation Adjust" value={saturationDelta} min={-100} max={100} step={1} onChange={setSaturationDelta} disabled={isProcessing} displaySuffix="%"/>
      <SliderControl label="Lightness Adjust" value={lightnessDelta} min={-100} max={100} step={1} onChange={setLightnessDelta} disabled={isProcessing} displaySuffix="%"/>
      <SliderControl label="Contrast Adjust" value={contrastDelta} min={-100} max={100} step={1} onChange={setContrastDelta} disabled={isProcessing} displaySuffix="%"/> 
      <SliderControl 
        label="Alpha Adjust" 
        value={alphaDelta} 
        min={-100} max={0} 
        step={1} 
        onChange={setAlphaDelta} 
        disabled={isProcessing} 
        displaySuffix="%"
        presets={alphaDeltaPresets}
        onPresetClick={setAlphaDelta}
      />


      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-300 mb-1">Tint Color</label>
        <div className="flex items-center space-x-2">
           <input
            type="color"
            value={currentTintColorHex}
            onChange={handleTintColorChange}
            disabled={isProcessing}
            className="w-10 h-10 p-0 border-none rounded-md cursor-pointer disabled:opacity-50"
          />
          <span className="text-sm text-slate-400">{currentTintColorHex.toUpperCase()}</span>
        </div>
      </div>
      
      <SliderControl 
        label="Tint Amount" 
        value={tintAmount} 
        min={0} max={100} 
        step={1} 
        onChange={setTintAmount} 
        disabled={isProcessing} 
        displaySuffix="%"
        presets={tintAmountPresets}
        onPresetClick={setTintAmount}
      />
    </div>
  );
};

export default ColorControls;
