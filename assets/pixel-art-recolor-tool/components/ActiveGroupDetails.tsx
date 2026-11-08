

import React, { useState, ChangeEvent, useMemo } from 'react';
import { ColorGroup, PaletteColor, RGBColor, HSLValue } from '../types';
import { rgbToHex, rgbToHsl, hslToRgb, calculateTintedColorForGroupMember, hexToRgb } from '../services/colorService';
import { INITIAL_ALPHA_DELTA } from '../constants';

interface ActiveGroupDetailsProps {
  activeGroup: ColorGroup;
  displayPalette: PaletteColor[];
  groupPrimaryHex: string | null;
  onSetPrimaryColor: (groupId: string, colorHex: string) => void;
  currentGroupSliderValues: {
    hueDelta: number;
    saturationDelta: number;
    lightnessDelta: number;
    contrastDelta: number; 
    alphaDelta: number;
    tintColor: RGBColor;
    tintAmount: number;
  };
  isProcessing: boolean;
  allColorGroups: ColorGroup[]; 
  groupPrimaryColorHexesForTintCalc: Record<string, string>;
  onRemoveColorFromGroup: (groupId: string, colorHex: string) => void; 
  colorFinalOverrides: Record<string, RGBColor>; 
  onOverrideColor: (originalHex: string, newFinalRgbHex: string) => void; 
  onClearColorOverride: (originalHex: string) => void;

  isEditingThisGroup: boolean;
  stagedHexesForCurrentEdit: Set<string> | null; 
  onStartEdit: (groupId: string) => void;
  onSaveEdit: (groupId: string) => void;
  onCancelEdit: (groupId: string) => void;
  onToggleStagedColor: (hex: string) => void; 
  onSaveAsNewGroup: (originalGroupId: string, newGroupName: string) => void; // Updated signature
}

interface ColorSwatchProps {
  originalHex: string;
  activeGroupId: string; 
  isCurrentPrimary: boolean;
  isProcessing: boolean;
  displayPalette: PaletteColor[];
  colorFinalOverrides: Record<string, RGBColor>;
  currentGroupSliderValues: ActiveGroupDetailsProps['currentGroupSliderValues'];
  groupPrimaryColorHexesForTintCalc: Record<string, string>;
  onSetPrimaryColor: (groupId: string, colorHex: string) => void;
  onOverrideColor: (originalHex: string, newFinalRgbHex: string) => void;
  onClearColorOverride: (originalHex: string) => void;
  allColorGroups: ColorGroup[];
  isEditingThisGroupSwatches: boolean; 
  onToggleStagedColorForSwatch: (hex: string) => void; 
  isColorInStagedEditSet: boolean; 
}

const ColorSwatch: React.FC<ColorSwatchProps> = ({
  originalHex, activeGroupId, isCurrentPrimary, isProcessing, displayPalette,
  colorFinalOverrides, currentGroupSliderValues, groupPrimaryColorHexesForTintCalc,
  onSetPrimaryColor, onOverrideColor, onClearColorOverride,
  allColorGroups, isEditingThisGroupSwatches, onToggleStagedColorForSwatch, isColorInStagedEditSet
}) => {
  const [isEditingOverride, setIsEditingOverride] = useState(false);
  
  function getDisplayedRgb(): RGBColor {
    const currentActiveColorGroup = allColorGroups.find(g => g.id === activeGroupId);

    if (colorFinalOverrides[originalHex]) {
      return colorFinalOverrides[originalHex];
    }

    const pColor = displayPalette.find(p => p.hex === originalHex);
    if (!pColor) return { r: 0, g: 0, b: 0, a: 255 }; 

    let baseForHslSliders = { ...pColor.original };
    const { tintAmount, tintColor, hueDelta, saturationDelta, lightnessDelta, contrastDelta, alphaDelta } = currentGroupSliderValues; 

    let finalSwatchAlpha = pColor.original.a;
    if (alphaDelta !== INITIAL_ALPHA_DELTA) {
        const factor = 1 + (alphaDelta / 100.0); 
        finalSwatchAlpha = pColor.original.a * factor;
    }
    finalSwatchAlpha = Math.round(Math.max(0, Math.min(255, finalSwatchAlpha)));
    baseForHslSliders.a = finalSwatchAlpha;


    if (tintAmount > 0) {
      const actualPrimaryForTintCalcHex = groupPrimaryColorHexesForTintCalc[activeGroupId];
      let actualPrimaryOriginalRgb: RGBColor | null = null;
      if (actualPrimaryForTintCalcHex) {
        const primaryPColor = displayPalette.find(p => p.hex === actualPrimaryForTintCalcHex);
        if (primaryPColor) actualPrimaryOriginalRgb = primaryPColor.original;
      }
      
      if (!actualPrimaryOriginalRgb) {
        if (currentActiveColorGroup && currentActiveColorGroup.colorHexes.size > 0) {
            const firstHexInGroup = Array.from(currentActiveColorGroup.colorHexes)[0];
            const firstPColorInGroup = displayPalette.find(dp => dp.hex === firstHexInGroup);
            if (firstPColorInGroup) actualPrimaryOriginalRgb = firstPColorInGroup.original;
        }
      }

      if (actualPrimaryOriginalRgb) {
        baseForHslSliders = calculateTintedColorForGroupMember(
          {...pColor.original, a: baseForHslSliders.a}, 
          actualPrimaryOriginalRgb, 
          tintColor, 
          tintAmount / 100
        );
      }
    }

    const currentHsl = rgbToHsl(baseForHslSliders);
    let adjustedH = (currentHsl.h + hueDelta);
    adjustedH = ((adjustedH % 360) + 360) % 360;
    let adjustedS = currentHsl.s + (saturationDelta / 100);
    adjustedS = Math.max(0, Math.min(1, adjustedS));
    let adjustedL = currentHsl.l + (lightnessDelta / 100);
    
    if (contrastDelta !== 0) {
      const contrastFactor = 1 + contrastDelta / 100; 
      adjustedL = 0.5 + (adjustedL - 0.5) * contrastFactor;
    }
    adjustedL = Math.max(0, Math.min(1, adjustedL)); 

    return hslToRgb({ h: adjustedH, s: adjustedS, l: adjustedL }, baseForHslSliders.a);
  }
  
  const displayedRgbValue = getDisplayedRgb();
  const displayedHex = rgbToHex(displayedRgbValue); 
  const [overrideColorInput, setOverrideColorInput] = useState<string>(
    colorFinalOverrides[originalHex] 
      ? rgbToHex(colorFinalOverrides[originalHex]) 
      : displayedHex 
  );


  const originalHexShort = originalHex.substring(1);
  const displayedHexShort = displayedHex.substring(1); 
  const isOverridden = !!colorFinalOverrides[originalHex];

  const handleOverrideInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    setOverrideColorInput(e.target.value);
  };

  const handleApplyOverride = () => {
    onOverrideColor(originalHex, overrideColorInput);
    setIsEditingOverride(false);
  };

  const handleToggleEditOverride = () => {
    if (isEditingOverride) { 
        setIsEditingOverride(false);
    } else { 
        setOverrideColorInput(
            isOverridden 
            ? rgbToHex(colorFinalOverrides[originalHex]) 
            : rgbToHex(getDisplayedRgb()) 
        );
        setIsEditingOverride(true);
    }
  };


  return (
    <div className={`flex flex-col items-center p-2 rounded-md relative ${isCurrentPrimary ? 'bg-sky-700/50 ring-2 ring-sky-400' : 'bg-slate-700/30'} ${isOverridden ? 'ring-2 ring-yellow-400' : ''}`}>
      {isEditingThisGroupSwatches && isColorInStagedEditSet && (
        <button 
          title="Remove this color from the group (staged change)"
          onClick={() => onToggleStagedColorForSwatch(originalHex)}
          disabled={isProcessing}
          className="absolute top-0 right-0 -mt-1 -mr-1 bg-red-600 hover:bg-red-700 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center focus:outline-none focus:ring-1 focus:ring-red-400 disabled:opacity-50 z-10"
          aria-label={`Remove color ${originalHexShort} from group staging`}
        >
          &times;
        </button>
      )}
      <div
        className="w-10 h-10 rounded border border-slate-600 shadow-sm mb-1 cursor-pointer"
        style={{ 
          backgroundColor: `rgba(${displayedRgbValue.r}, ${displayedRgbValue.g}, ${displayedRgbValue.b}, ${displayedRgbValue.a / 255})`,
          cursor: isEditingThisGroupSwatches ? 'default' : 'pointer'
        }}
        title={`Original: ${originalHex} (Alpha: ${displayPalette.find(p=>p.hex === originalHex)?.original.a})\nCurrent: ${displayedHexShort} (Alpha: ${displayedRgbValue.a})\nClick to ${isEditingOverride ? 'close' : 'edit'} override`}
        onClick={isEditingThisGroupSwatches ? undefined : handleToggleEditOverride} 
      ></div>
      <div className="text-center">
        <span className="text-xs text-slate-400 block" title={`Original Hex: ${originalHex}`}>
          {originalHexShort}
        </span>
        <span className={`text-xs block ${isCurrentPrimary ? 'text-sky-200 font-bold' : 'text-slate-300'} ${isOverridden ? 'text-yellow-300' : ''}`} title={`Current Hex: ${displayedHexShort}, Alpha: ${displayedRgbValue.a}`}>
          &rarr; {displayedHexShort} <span className="text-xxs opacity-75">(A:{displayedRgbValue.a})</span>
        </span>
        {isOverridden && <span className="text-xxs text-yellow-400">(Overridden)</span>}
      </div>

      {isEditingOverride && !isEditingThisGroupSwatches && (
        <div className="mt-2 p-2 bg-slate-700 rounded shadow-lg w-full space-y-1">
          <input 
            type="color" 
            value={overrideColorInput} 
            onChange={handleOverrideInputChange}
            disabled={isProcessing}
            className="w-full h-8 p-0 border-none rounded cursor-pointer disabled:opacity-50"
          />
          <button onClick={handleApplyOverride} disabled={isProcessing} className="w-full text-xs bg-green-600 hover:bg-green-700 text-white py-1 px-1.5 rounded disabled:opacity-50">Apply</button>
          {isOverridden && <button onClick={() => { onClearColorOverride(originalHex); setIsEditingOverride(false); }} disabled={isProcessing} className="w-full text-xs bg-orange-600 hover:bg-orange-700 text-white py-1 px-1.5 rounded disabled:opacity-50 mt-1">Clear Override</button>}
          <button onClick={() => setIsEditingOverride(false)} disabled={isProcessing} className="w-full text-xs bg-slate-500 hover:bg-slate-400 text-white py-1 px-1.5 rounded disabled:opacity-50 mt-1">Cancel</button>
        </div>
      )}

      {!isCurrentPrimary && !isEditingOverride && !isEditingThisGroupSwatches && (
        <button
          onClick={() => onSetPrimaryColor(activeGroupId, originalHex)}
          disabled={isProcessing}
          className="mt-1 text-xs bg-sky-600 hover:bg-sky-500 text-white py-0.5 px-1.5 rounded disabled:opacity-50 disabled:cursor-not-allowed text-center w-full"
          title="Set this color as the primary for tinting operations in this group"
        >
          Make Primary
        </button>
      )}
      {isCurrentPrimary && !isEditingOverride && !isEditingThisGroupSwatches && (
        <span className="mt-1 text-xs text-sky-400 font-semibold py-0.5 px-1.5 text-center w-full">Primary</span>
      )}
    </div>
  );
};


const ActiveGroupDetails: React.FC<ActiveGroupDetailsProps> = (props) => {
  const { 
    activeGroup, 
    groupPrimaryHex, 
    displayPalette, 
    isProcessing,
    isEditingThisGroup,
    stagedHexesForCurrentEdit,
    onStartEdit,
    onSaveEdit,
    onCancelEdit,
    onToggleStagedColor,
    onSaveAsNewGroup
  } = props;

  const [isSavingAsNew, setIsSavingAsNew] = useState<boolean>(false);
  const [newGroupNameForSaveAs, setNewGroupNameForSaveAs] = useState<string>("");
  
  const colorsToDisplaySet = useMemo(() => {
    return (isEditingThisGroup && stagedHexesForCurrentEdit) ? stagedHexesForCurrentEdit : activeGroup.colorHexes;
  }, [activeGroup.colorHexes, isEditingThisGroup, stagedHexesForCurrentEdit]);

  const sortedGroupColors = useMemo(() => {
    const colorsArray = Array.from(colorsToDisplaySet);
    if (groupPrimaryHex && colorsArray.includes(groupPrimaryHex)) {
      return [
        groupPrimaryHex,
        ...colorsArray.filter(hex => hex !== groupPrimaryHex).sort((a,b) => {
            const palA = displayPalette.find(p=>p.hex === a)?.original;
            const palB = displayPalette.find(p=>p.hex === b)?.original;
            if (!palA || !palB) return a.localeCompare(b);
            const hslA = rgbToHsl(palA); const hslB = rgbToHsl(palB);
            if(hslA.l !== hslB.l) return hslA.l - hslB.l;
            if(hslA.s !== hslB.s) return hslA.s - hslB.s;
            return hslA.h - hslB.h;
        })
      ];
    }
    return colorsArray.sort((a,b) => {
        const palA = displayPalette.find(p=>p.hex === a)?.original;
        const palB = displayPalette.find(p=>p.hex === b)?.original;
        if (!palA || !palB) return a.localeCompare(b);
        const hslA = rgbToHsl(palA); const hslB = rgbToHsl(palB);
        if(hslA.l !== hslB.l) return hslA.l - hslB.l;
        if(hslA.s !== hslB.s) return hslA.s - hslB.s;
        return hslA.h - hslB.h;
    });
  }, [colorsToDisplaySet, groupPrimaryHex, displayPalette]);

  const handleStartSaveAsNew = () => {
    setIsSavingAsNew(true);
    setNewGroupNameForSaveAs(`Copy of ${activeGroup.name}`);
  };

  const handleConfirmSaveAsNew = () => {
    if (newGroupNameForSaveAs.trim() === "") {
      alert("New group name cannot be empty.");
      return;
    }
    if (!stagedHexesForCurrentEdit || stagedHexesForCurrentEdit.size === 0) {
        alert("Cannot save an empty group. Please add at least one color to the staging area.");
        return;
    }
    onSaveAsNewGroup(activeGroup.id, newGroupNameForSaveAs.trim());
    setIsSavingAsNew(false);
    setNewGroupNameForSaveAs("");
    // Exiting edit mode is handled by App.tsx's onSaveAsNewGroup
  };

  const handleCancelSaveAsNew = () => {
    setIsSavingAsNew(false);
    setNewGroupNameForSaveAs("");
  };


  return (
    <div className="mt-4 p-4 border border-slate-700 rounded-lg bg-slate-850 shadow-md">
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-md font-semibold text-sky-300">
          Colors in <span className="text-sky-100">{activeGroup.name}</span> ({colorsToDisplaySet.size})
        </h4>
        {activeGroup.id !== 'ALL_COLORS_GROUP_ID' && (
            <div>
            {!isEditingThisGroup ? (
                <button
                onClick={() => onStartEdit(activeGroup.id)}
                disabled={isProcessing || activeGroup.id === 'ALL_COLORS_GROUP_ID'}
                className="text-xs bg-blue-600 hover:bg-blue-700 text-white font-medium py-1 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-150 disabled:opacity-50"
                >
                Edit Colors in Image
                </button>
            ) : !isSavingAsNew ? ( // Show standard edit buttons if not in "Save As New" sub-mode
                <div className="flex space-x-1 sm:space-x-2">
                <button
                    onClick={() => onSaveEdit(activeGroup.id)}
                    disabled={isProcessing || !stagedHexesForCurrentEdit || stagedHexesForCurrentEdit.size === 0}
                    className="text-xs bg-green-600 hover:bg-green-700 text-white font-medium py-1 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors duration-150 disabled:opacity-50"
                    title={stagedHexesForCurrentEdit && stagedHexesForCurrentEdit.size === 0 ? "Cannot save an empty group" : "Save changes to this group"}
                >
                    Save Changes
                </button>
                <button
                    onClick={handleStartSaveAsNew}
                    disabled={isProcessing || !stagedHexesForCurrentEdit || stagedHexesForCurrentEdit.size === 0}
                    className="text-xs bg-sky-600 hover:bg-sky-700 text-white font-medium py-1 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-sky-500 transition-colors duration-150 disabled:opacity-50"
                    title={stagedHexesForCurrentEdit && stagedHexesForCurrentEdit.size === 0 ? "Cannot save an empty group" : "Save these colors as a new group"}
                >
                    Save As New...
                </button>
                <button
                    onClick={() => onCancelEdit(activeGroup.id)}
                    disabled={isProcessing}
                    className="text-xs bg-slate-600 hover:bg-slate-500 text-slate-200 font-medium py-1 px-2 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors duration-150"
                >
                    Cancel
                </button>
                </div>
            ) : null /* "Save As New" sub-mode UI will be rendered below */ }
            </div>
        )}
      </div>

      {isEditingThisGroup && !isSavingAsNew && (
          <p className="text-xs text-yellow-300 mb-2">
              Editing mode: Click pixels on the image to add/remove their original colors from this group.
              Pixels not in this group (staged) will appear with 90% transparency.
          </p>
      )}

      {isEditingThisGroup && isSavingAsNew && (
        <div className="my-2 p-3 bg-slate-700/60 rounded-md shadow">
            <label htmlFor="save-as-new-group-name-input" className="block text-sm font-medium text-slate-200 mb-1">Enter name for new group:</label>
            <input
                type="text"
                id="save-as-new-group-name-input"
                value={newGroupNameForSaveAs}
                onChange={(e) => setNewGroupNameForSaveAs(e.target.value)}
                className="w-full bg-slate-600 border border-slate-500 text-slate-100 text-sm rounded p-1.5 focus:ring-sky-500 focus:border-sky-500 mb-2"
                placeholder={`e.g., Copy of ${activeGroup.name}`}
                disabled={isProcessing}
            />
            <div className="flex space-x-2">
                <button
                    onClick={handleConfirmSaveAsNew}
                    disabled={isProcessing || !stagedHexesForCurrentEdit || stagedHexesForCurrentEdit.size === 0 || !newGroupNameForSaveAs.trim()}
                    className="flex-1 text-xs bg-green-500 hover:bg-green-600 text-white font-medium py-1.5 px-2 rounded disabled:opacity-50"
                    title={!newGroupNameForSaveAs.trim() ? "Name cannot be empty" : (!stagedHexesForCurrentEdit || stagedHexesForCurrentEdit.size === 0 ? "Add colors first" : "Confirm Save As New")}
                >
                    Confirm Save As New
                </button>
                <button
                    onClick={handleCancelSaveAsNew}
                    disabled={isProcessing}
                    className="flex-1 text-xs bg-slate-500 hover:bg-slate-600 text-slate-200 font-medium py-1.5 px-2 rounded disabled:opacity-50"
                >
                    Cancel Save As New
                </button>
            </div>
        </div>
      )}

      {colorsToDisplaySet.size === 0 && <p className="text-sm text-slate-400">This group is empty. Add colors from the palette or pixel selection, or by editing in the image.</p>}
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-3 lg:grid-cols-4 gap-3 max-h-60 overflow-y-auto custom-scrollbar pr-2">
        {sortedGroupColors.map(hex => (
          <ColorSwatch
            key={hex}
            originalHex={hex}
            activeGroupId={activeGroup.id}
            isCurrentPrimary={hex === groupPrimaryHex && !isEditingThisGroup} 
            isProcessing={props.isProcessing}
            displayPalette={props.displayPalette}
            colorFinalOverrides={props.colorFinalOverrides}
            currentGroupSliderValues={props.currentGroupSliderValues}
            groupPrimaryColorHexesForTintCalc={props.groupPrimaryColorHexesForTintCalc}
            onSetPrimaryColor={props.onSetPrimaryColor}
            onOverrideColor={props.onOverrideColor}
            onClearColorOverride={props.onClearColorOverride}
            allColorGroups={props.allColorGroups}
            isEditingThisGroupSwatches={isEditingThisGroup}
            onToggleStagedColorForSwatch={onToggleStagedColor}
            isColorInStagedEditSet={isEditingThisGroup && stagedHexesForCurrentEdit ? stagedHexesForCurrentEdit.has(hex) : false}
          />
        ))}
      </div>
    </div>
  );
};

export default ActiveGroupDetails;
