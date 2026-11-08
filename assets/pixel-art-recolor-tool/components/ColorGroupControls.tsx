
import React from 'react';

interface ColorGroupControlsProps {
  newGroupName: string;
  setNewGroupName: (name: string) => void;
  selectedPaletteColorsCount: number;
  onCreateGroup: () => void;
  onClearSelection: () => void;
  paletteExists: boolean; 
  isProcessing: boolean;
  isPixelHopperModeActive: boolean;
  togglePixelHopperMode: () => void;
  pixelHopperSelectedColorsCount: number;
  onAddHopperColorsToStaging: () => void;
  isEditingAnyGroup: boolean; // New prop
}

const ColorGroupControls: React.FC<ColorGroupControlsProps> = ({
  newGroupName,
  setNewGroupName,
  selectedPaletteColorsCount,
  onCreateGroup,
  onClearSelection,
  paletteExists,
  isProcessing,
  isPixelHopperModeActive,
  togglePixelHopperMode,
  pixelHopperSelectedColorsCount,
  onAddHopperColorsToStaging,
  isEditingAnyGroup, // Destructure new prop
}) => {
  const canCreateGroup = newGroupName.trim() !== '' && selectedPaletteColorsCount > 0;

  return (
    <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg space-y-4">
      <h3 className="text-lg font-semibold text-sky-400">Color Groups</h3>
      
      {paletteExists && (
        <div className="pt-2 pb-2 border-b border-slate-700/50">
          <div className="flex items-center justify-between mb-2">
            <label htmlFor="pixel-hopper-toggle" className="text-sm font-medium text-slate-300">
              Pixel Selection Mode
            </label>
            <button
              id="pixel-hopper-toggle"
              onClick={togglePixelHopperMode}
              disabled={isProcessing || !paletteExists || isEditingAnyGroup} // Disable if editing any group
              className={`px-3 py-1 text-xs rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-opacity-50 disabled:opacity-50
                ${isPixelHopperModeActive ? 'bg-sky-500 hover:bg-sky-600 text-white focus:ring-sky-400' : 'bg-slate-600 hover:bg-slate-500 text-slate-200 focus:ring-slate-400'}`}
              aria-pressed={isPixelHopperModeActive}
              title={isEditingAnyGroup ? "Finish editing group colors first" : (isPixelHopperModeActive ? "Turn OFF Pixel Selection" : "Turn ON Pixel Selection")}
            >
              {isPixelHopperModeActive ? 'ON' : 'OFF'}
            </button>
          </div>
          <p className="text-xs text-slate-400 mb-2">
            {isPixelHopperModeActive 
              ? 'Click pixels on the image to select/deselect their original colors. Selected colors are fully opaque, others are 90% transparent.' 
              : 'Turn ON to select colors directly from the image preview for staging.'
            }
             {isEditingAnyGroup && <span className="block text-yellow-400 text-xxs"> (Disabled while editing group colors below)</span>}
          </p>
          {isPixelHopperModeActive && (
            <button
              onClick={onAddHopperColorsToStaging}
              disabled={pixelHopperSelectedColorsCount === 0 || isProcessing || isEditingAnyGroup}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-1.5 px-3 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
            >
              Add Pixel Selection to Staging ({pixelHopperSelectedColorsCount})
            </button>
          )}
        </div>
      )}

      <div>
        <label htmlFor="new-group-name" className="block text-sm font-medium text-slate-300 mb-1">
          New Group Name ({selectedPaletteColorsCount} colors staged)
        </label>
        <input
          type="text"
          id="new-group-name"
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          placeholder="e.g., Skin Tones"
          disabled={isProcessing || !paletteExists || isEditingAnyGroup} 
          className="w-full bg-slate-700 border border-slate-600 text-slate-200 placeholder-slate-500 text-sm rounded-md p-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-50"
        />
        <div className="mt-2 grid grid-cols-2 gap-2">
          <button
            onClick={onCreateGroup}
            disabled={!canCreateGroup || isProcessing || !paletteExists || isEditingAnyGroup}
            className="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
          >
            Create Group
          </button>
          <button
            onClick={onClearSelection}
            disabled={selectedPaletteColorsCount === 0 || isProcessing || !paletteExists || isEditingAnyGroup}
            className="bg-slate-600 hover:bg-slate-500 text-slate-200 font-medium py-2 px-3 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
          >
            Clear Staging
          </button>
        </div>
      </div>
      
      {!paletteExists && (
         <p className="text-sm text-slate-400">Upload an image to begin. Color groups will be automatically generated from its palette.</p>
      )}
       {isEditingAnyGroup && paletteExists && (
         <p className="text-xs text-yellow-400 mt-2 text-center">Group creation controls are disabled while editing colors for an existing group in "Active Group Details".</p>
      )}
    </div>
  );
};

export default ColorGroupControls;
