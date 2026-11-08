
import React from 'react';
import { ColorGroup, AppliedGroupSettings, RGBColor, PaletteColor } from '../types';
import { hexToRgb, rgbToHex } from '../services/colorService';
import {
  DEFAULT_TINT_COLOR_HEX,
} from '../constants';

interface QuickRecolorControlsProps {
  colorGroups: ColorGroup[];
  appliedGroupSettings: Record<string, AppliedGroupSettings>;
  onSetGroupQuickTint: (groupId: string, tintColor: RGBColor) => void;
  isProcessing: boolean;
  initialGroupPrimaryColorHexes: Record<string, string>;
  displayPalette: PaletteColor[];
  onResetGroupToInitial: (groupId: string) => void;
  isGroupModifiedCheck: (settings: AppliedGroupSettings | undefined, initialPrimaryHex: string | undefined) => boolean;
}

const QuickRecolorControls: React.FC<QuickRecolorControlsProps> = ({
  colorGroups,
  appliedGroupSettings,
  onSetGroupQuickTint,
  isProcessing,
  initialGroupPrimaryColorHexes,
  onResetGroupToInitial,
  isGroupModifiedCheck,
}) => {
  if (colorGroups.length === 0) {
    return (
      <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg mt-4">
        <p className="text-slate-400 text-center">No color groups available for Quick Recolor. Create groups first (other than "All Colors").</p>
      </div>
    );
  }

  return (
    <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg space-y-3">
      <div className="text-center mb-3">
        <h3 className="text-lg font-semibold text-teal-400">Quick Recolor Tints</h3>
        <p className="text-xs text-slate-400">
          Set a group's tint color. Tint amount will be 100% and HSL/Contrast/Alpha will be reset for the group.
        </p>
      </div>
      <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar pr-2">
        {colorGroups.map(group => {
          const groupSettings = appliedGroupSettings[group.id];
          
          let displayPickerTintColor: RGBColor;
          if (groupSettings) {
            displayPickerTintColor = groupSettings.tintColor;
          } else {
            const primaryHex = initialGroupPrimaryColorHexes[group.id];
            displayPickerTintColor = primaryHex ? (hexToRgb(primaryHex) || hexToRgb(DEFAULT_TINT_COLOR_HEX)!) : hexToRgb(DEFAULT_TINT_COLOR_HEX)!;
          }
          
          const currentGroupTintColorHexForPicker = rgbToHex(displayPickerTintColor);

          const handleTintColorChange = (event: React.ChangeEvent<HTMLInputElement>) => {
            const newHexColor = event.target.value;
            const newRgbColor = hexToRgb(newHexColor);
            if (newRgbColor) {
              onSetGroupQuickTint(group.id, newRgbColor);
            }
          };

          const isModified = isGroupModifiedCheck(
            groupSettings,
            initialGroupPrimaryColorHexes[group.id]
          );

          return (
            <div
              key={group.id}
              className="flex items-center justify-between p-3 bg-slate-700/70 rounded-lg shadow"
              role="group"
              aria-labelledby={`group-name-${group.id}`}
            >
              {isModified && (
                <button
                  onClick={() => onResetGroupToInitial(group.id)}
                  disabled={isProcessing}
                  className="w-7 h-7 flex items-center justify-center mr-2 rounded-full bg-slate-600 hover:bg-slate-500 text-slate-100 font-bold text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 disabled:opacity-50 transition-colors"
                  title={`Reset ${group.name} to its initial settings`}
                  aria-label={`Reset group ${group.name}`}
                >
                  R
                </button>
              )}
              {!isModified && <div className="w-7 mr-2"></div>} 

              <span
                id={`group-name-${group.id}`}
                className="text-sm text-slate-100 font-medium truncate pr-2 flex-grow"
                title={`${group.name} (${group.colorHexes.size} colors)`}
              >
                {group.name} <span className="text-xs text-slate-400">({group.colorHexes.size})</span>
              </span>
              <div className="flex items-center space-x-2 flex-shrink-0">
                <input
                  type="color"
                  value={currentGroupTintColorHexForPicker}
                  onChange={handleTintColorChange}
                  disabled={isProcessing}
                  className="w-9 h-9 p-0 border-2 border-slate-500 rounded-md cursor-pointer disabled:opacity-50 focus:ring-2 focus:ring-teal-400 focus:outline-none"
                  aria-label={`Tint color for group ${group.name}`}
                  title={`Set tint color for ${group.name}`}
                />
                <span className="text-xs text-slate-300 tabular-nums">{currentGroupTintColorHexForPicker.toUpperCase()}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default QuickRecolorControls;
