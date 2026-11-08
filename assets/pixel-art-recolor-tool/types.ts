export interface RGBColor {
  r: number;
  g: number;
  b: number;
  a: number;
}

export interface HSLValue { // Renamed from HSLColor to avoid confusion with RGBColor type name pattern
  h: number;
  s: number;
  l: number;
}

export interface PaletteColor {
  original: RGBColor;
  hex: string;
}

export interface ColorGroup {
  id: string;
  name: string;
  colorHexes: Set<string>;
}

export interface PredefinedImage {
  name: string;
  download_url: string;
}

export interface AppliedGroupSettings {
  hueDelta: number;
  saturationDelta: number;
  lightnessDelta: number;
  contrastDelta: number;
  tintColor: RGBColor;
  tintAmount: number;
  alphaDelta: number; // Added for alpha adjustment
}
