
import { RGBColor, HSLValue, PaletteColor, ColorGroup } from '../types';

export const rgbToHsl = (rgb: RGBColor): HSLValue => {
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0, s = 0, l = (max + min) / 2;

  if (max === min) {
    h = s = 0; // achromatic
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return { h: h * 360, s, l };
};

export const hslToRgb = (hsl: HSLValue, alpha: number): RGBColor => {
  const h = hsl.h / 360;
  const s = hsl.s;
  const l = hsl.l;
  let r: number, g: number, b: number;

  if (s === 0) {
    r = g = b = l; // achromatic
  } else {
    const hue2rgb = (p: number, q: number, t: number): number => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  return { 
    r: Math.round(r * 255), 
    g: Math.round(g * 255), 
    b: Math.round(b * 255), 
    a: alpha 
  };
};

export const rgbToHex = (rgb: RGBColor): string => {
  const toHex = (c: number) => c.toString(16).padStart(2, '0');
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
};

export const hexToRgb = (hex: string): RGBColor | null => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) return null;
  return {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
    a: 255, 
  };
};

export const getUniqueColorsFromImageData = (imageData: ImageData): RGBColor[] => {
  const uniqueColorsMap = new Map<string, RGBColor>();
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    const a = data[i + 3];
    if (a === 0) continue; 
    const key = `${r}-${g}-${b}-${a}`; 
    if (!uniqueColorsMap.has(key)) {
      uniqueColorsMap.set(key, { r, g, b, a });
    }
  }
  return Array.from(uniqueColorsMap.values());
};

/**
 * Applies a tint to a base color by interpolating HSL values towards the tint source color.
 * Used for "All Colors" group tinting.
 */
export const applyPixelTint = (baseColorRgb: RGBColor, tintSourceRgb: RGBColor, amountFraction: number): RGBColor => {
  const t = Math.max(0, Math.min(1, amountFraction));

  const baseHsl = rgbToHsl(baseColorRgb);
  const tintSourceHsl = rgbToHsl(tintSourceRgb);

  // Hue interpolation (shortest path)
  let h1 = baseHsl.h;
  let h2 = tintSourceHsl.h;
  
  let finalHue = h1;

  // Only apply hue shift if tint source is not grayscale and amount is significant
  // and base color is not grayscale (or if it is, allow it to take on hue)
  if (tintSourceHsl.s > 0.01 && t > 0.001 ) { 
      let hueDiff = h2 - h1;
      if (hueDiff > 180) hueDiff -= 360;
      if (hueDiff < -180) hueDiff += 360;
      finalHue = (h1 + hueDiff * t + 360) % 360;
  } else if (t >= 0.999 && tintSourceHsl.s > 0.01) { // If tint is 100% and source has hue, take source hue
      finalHue = tintSourceHsl.h;
  } else if (baseHsl.s < 0.01 && tintSourceHsl.s > 0.01 && t > 0.001) { // If base is grayscale and source has hue, take source hue
      finalHue = tintSourceHsl.h;
  }


  // Saturation and Lightness interpolation
  const finalSaturation = baseHsl.s + (tintSourceHsl.s - baseHsl.s) * t;
  const finalLightness = baseHsl.l + (tintSourceHsl.l - baseHsl.l) * t;

  const newHslValue: HSLValue = {
    h: finalHue,
    s: Math.max(0, Math.min(1, finalSaturation)), // Clamp S
    l: Math.max(0, Math.min(1, finalLightness)),  // Clamp L
  };

  return hslToRgb(newHslValue, baseColorRgb.a);
};

export const imageDataToDataUrl = (imageData: ImageData): string => {
  const canvas = document.createElement('canvas');
  canvas.width = imageData.width;
  canvas.height = imageData.height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Could not get canvas context');
  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL();
};

// --- Automatic Color Grouping ---
interface ColorCategoryDefinition {
    name: string;
    condition: (hsl: HSLValue) => boolean;
    hexes: Set<string>;
}

const colorCategoryDefinitions: ColorCategoryDefinition[] = [
    { name: "Blacks", condition: ({s, l}) => l < 0.15 && s < 0.25, hexes: new Set() },
    { name: "Whites", condition: ({s, l}) => l > 0.85 && s < 0.25, hexes: new Set() },
    { name: "Grays", condition: ({s, l}) => s < 0.15 && !(l < 0.15 && s < 0.25) && !(l > 0.85 && s < 0.25), hexes: new Set() },
    { name: "Reds", condition: ({h, s, l}) => (h >= 335 || h < 15) && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Oranges", condition: ({h, s, l}) => h >= 15 && h < 45 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Yellows", condition: ({h, s, l}) => h >= 45 && h < 70 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Greens", condition: ({h, s, l}) => h >= 70 && h < 165 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Cyans", condition: ({h, s, l}) => h >= 165 && h < 195 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Blues", condition: ({h, s, l}) => h >= 195 && h < 255 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Purples", condition: ({h, s, l}) => h >= 255 && h < 295 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
    { name: "Magentas/Pinks", condition: ({h, s, l}) => h >= 295 && h < 335 && s >= 0.15 && !(l < 0.15 && s < 0.25), hexes: new Set() },
];

export const autoGroupColorsFromPalette = (palette: PaletteColor[]): ColorGroup[] => {
  colorCategoryDefinitions.forEach(cat => cat.hexes.clear());
  palette.forEach(pColor => {
    if (pColor.original.a === 0) return;
    const hsl = rgbToHsl(pColor.original);
    for (const category of colorCategoryDefinitions) {
      if (category.condition(hsl)) {
        category.hexes.add(pColor.hex);
        break; 
      }
    }
  });

  return colorCategoryDefinitions
    .filter(cat => cat.hexes.size > 0) 
    .map((cat, index) => ({
      id: `auto_${cat.name.toLowerCase().replace(/[\s/]+/g, '_')}_${index}`,
      name: cat.name, 
      colorHexes: cat.hexes
    }));
};

// --- New Tint Logic for Group-based Relative Shading ---

const PROTOTYPICAL_HSL_VALUES: Record<string, HSLValue> = {
  "Blacks": { h: 0, s: 0, l: 0.05 },
  "Whites": { h: 0, s: 0, l: 0.95 },
  "Grays": { h: 0, s: 0, l: 0.5 },
  "Reds": { h: 0, s: 1, l: 0.5 },
  "Oranges": { h: 30, s: 1, l: 0.5 },
  "Yellows": { h: 60, s: 1, l: 0.5 },
  "Greens": { h: 120, s: 1, l: 0.5 },
  "Cyans": { h: 180, s: 1, l: 0.5 },
  "Blues": { h: 240, s: 1, l: 0.5 },
  "Purples": { h: 270, s: 1, l: 0.5 },
  "Magentas/Pinks": { h: 300, s: 1, l: 0.5 },
};

// Helper to calculate "distance" between HSL values (simplified, weighted for perception)
// Considers hue wrap-around. Lower is closer.
const hslDistance = (hsl1: HSLValue, hsl2: HSLValue): number => {
  let h1 = hsl1.h;
  let h2 = hsl2.h;
  const deltaH = Math.min(Math.abs(h1 - h2), 360 - Math.abs(h1 - h2)) / 180; // Normalized 0-1
  const deltaS = Math.abs(hsl1.s - hsl2.s); // 0-1
  const deltaL = Math.abs(hsl1.l - hsl2.l); // 0-1
  // Weight lightness and saturation more than hue for "similarity" in this context
  return deltaH * 0.5 + deltaS * 1.5 + deltaL * 2.0;
};

export const getGroupPrimaryColorOriginalRgb = (
  group: ColorGroup,
  palette: PaletteColor[]
): RGBColor | null => {
  if (group.colorHexes.size === 0) return null;

  let primaryHex: string | undefined;

  if (group.id.startsWith('auto_')) {
    const categoryName = group.name;
    const prototypeHsl = PROTOTYPICAL_HSL_VALUES[categoryName];
    if (prototypeHsl) {
      let closestHex: string | undefined;
      let minDistance = Infinity;

      group.colorHexes.forEach(hex => {
        const pColor = palette.find(pc => pc.hex === hex);
        if (pColor) {
          const colorHsl = rgbToHsl(pColor.original);
          const distance = hslDistance(colorHsl, prototypeHsl);
          if (distance < minDistance) {
            minDistance = distance;
            closestHex = hex;
          }
        }
      });
      primaryHex = closestHex;
    }
  }
  
  // Fallback for user groups or if auto-group prototype logic fails
  if (!primaryHex) {
    // Try to find a color that is actually in the palette
    const availableHexes = Array.from(group.colorHexes).filter(hex => palette.some(p => p.hex === hex));
    if (availableHexes.length > 0) {
        primaryHex = availableHexes[0];
    } else if (group.colorHexes.size > 0) { // Absolute fallback if no palette match (should be rare)
        primaryHex = Array.from(group.colorHexes)[0];
    }
  }


  const paletteColor = palette.find(p => p.hex === primaryHex);
  return paletteColor ? paletteColor.original : null;
};


/**
 * Calculates the tinted color for a member of a group, relative to the group's primary color transformation.
 */
export const calculateTintedColorForGroupMember = (
  memberOriginalRgb: RGBColor,
  groupPrimaryOriginalRgb: RGBColor,
  tintTargetRgb: RGBColor, // This is the color the group's primary should become at 100% tint
  tintAmountFraction: number
): RGBColor => {
  // Check if memberOriginalRgb is the same as groupPrimaryOriginalRgb (ignoring alpha for this check initially)
  const isMemberThePrimaryColorStructurally =
    memberOriginalRgb.r === groupPrimaryOriginalRgb.r &&
    memberOriginalRgb.g === groupPrimaryOriginalRgb.g &&
    memberOriginalRgb.b === groupPrimaryOriginalRgb.b;

  // Check if tintTargetRgb is the same as groupPrimaryOriginalRgb (ignoring alpha)
  const isTintTargetThePrimaryColorStructurally =
    tintTargetRgb.r === groupPrimaryOriginalRgb.r &&
    tintTargetRgb.g === groupPrimaryOriginalRgb.g &&
    tintTargetRgb.b === groupPrimaryOriginalRgb.b;

  if (tintAmountFraction >= 0.999) { // Effectively 100%
    if (isMemberThePrimaryColorStructurally) {
      // If the member IS the primary, it becomes the tintTargetRgb exactly, but preserves its original alpha.
      return { ...tintTargetRgb, a: memberOriginalRgb.a };
    } else {
      // If the member is NOT the primary:
      if (isTintTargetThePrimaryColorStructurally) {
        // And the tint target IS the primary color itself (e.g. user picked primary as tint and set to 100%)
        // Then this non-primary member should NOT change.
        return { ...memberOriginalRgb };
      }
      // Otherwise (tint target is some other color), proceed with relative shading for non-primary members.
      // The member will adopt the hue and saturation of the (tinted) primary.
      // Its lightness will be the (tinted) primary's lightness, adjusted by its original relative lightness.
      const primaryEffectiveTintedHsl = rgbToHsl(tintTargetRgb); // HSL of what the primary becomes
      const memberOriginalHsl = rgbToHsl(memberOriginalRgb);
      const groupPrimaryOriginalHsl = rgbToHsl(groupPrimaryOriginalRgb);
      
      const originalLightnessDifference = memberOriginalHsl.l - groupPrimaryOriginalHsl.l;
      
      const memberTargetHslAtFullTint: HSLValue = {
        h: primaryEffectiveTintedHsl.h,
        s: primaryEffectiveTintedHsl.s,
        l: Math.max(0, Math.min(1, primaryEffectiveTintedHsl.l + originalLightnessDifference)),
      };
      return hslToRgb(memberTargetHslAtFullTint, memberOriginalRgb.a); // Preserve original member's alpha
    }
  }

  // For tintAmountFraction < 1.0, use the existing interpolation logic.
  const memberOriginalHsl = rgbToHsl(memberOriginalRgb);
  const groupPrimaryOriginalHsl = rgbToHsl(groupPrimaryOriginalRgb);
  
  // Determine the HSL of the primary color IF IT WERE fully tinted to tintTargetRgb
  const primaryTargetHslAtFullTint = rgbToHsl(tintTargetRgb);

  // Calculate the member's target HSL if tintAmount were 100%, relative to this primaryTargetHslAtFullTint
  const originalLightnessDifference = memberOriginalHsl.l - groupPrimaryOriginalHsl.l;
  
  const memberTargetHslAtFullTint: HSLValue = {
    h: primaryTargetHslAtFullTint.h,
    s: primaryTargetHslAtFullTint.s,
    l: Math.max(0, Math.min(1, primaryTargetHslAtFullTint.l + originalLightnessDifference)),
  };

  // Convert the member's fully tinted target HSL back to RGB
  const memberTargetRgbAtFullTint = hslToRgb(memberTargetHslAtFullTint, memberOriginalRgb.a);

  // Interpolate between the member's original RGB and its fully tinted target RGB
  const finalR = memberOriginalRgb.r + (memberTargetRgbAtFullTint.r - memberOriginalRgb.r) * tintAmountFraction;
  const finalG = memberOriginalRgb.g + (memberTargetRgbAtFullTint.g - memberOriginalRgb.g) * tintAmountFraction;
  const finalB = memberOriginalRgb.b + (memberTargetRgbAtFullTint.b - memberOriginalRgb.b) * tintAmountFraction;

  return {
    r: Math.round(Math.max(0, Math.min(255, finalR))),
    g: Math.round(Math.max(0, Math.min(255, finalG))),
    b: Math.round(Math.max(0, Math.min(255, finalB))),
    a: memberOriginalRgb.a, // Preserve original alpha throughout interpolation
  };
};
