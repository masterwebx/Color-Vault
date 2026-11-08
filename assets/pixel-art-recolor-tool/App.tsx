
import React, { useState, useEffect, useCallback, useRef } from 'react';
import ImageUploader from './components/ImageUploader';
import ColorPalette from './components/ColorPalette';
import ColorControls from './components/ColorControls';
import ImageViewer from './components/ImageViewer';
import ColorGroupControls from './components/ColorGroupControls';
import ActiveGroupDetails from './components/ActiveGroupDetails';
import QuickRecolorControls from './components/QuickRecolorControls';
import { RGBColor, PaletteColor, HSLValue, ColorGroup, PredefinedImage, AppliedGroupSettings } from './types';
import {
  rgbToHsl,
  hslToRgb,
  rgbToHex,
  hexToRgb,
  getUniqueColorsFromImageData,
  applyPixelTint,
  imageDataToDataUrl,
  autoGroupColorsFromPalette,
  getGroupPrimaryColorOriginalRgb,
  calculateTintedColorForGroupMember,
} from './services/colorService';
import {
  SPINNER_SVG,
  DEFAULT_TINT_COLOR_HEX,
  INITIAL_HUE_DELTA,
  INITIAL_SATURATION_DELTA,
  INITIAL_LIGHTNESS_DELTA,
  INITIAL_CONTRAST_DELTA,
  INITIAL_ALPHA_DELTA, 
  INITIAL_TINT_AMOUNT,
  ALL_COLORS_GROUP_ID,
  MAX_UNIQUE_COLORS_PROCESSING, 
} from './constants';

interface LastClickedPixelInfo {
  hex: string;
  matchingGroupIds: string[];
  cycleIndex: number;
}

const getInitialAppliedSettings = (): AppliedGroupSettings => ({
  hueDelta: INITIAL_HUE_DELTA,
  saturationDelta: INITIAL_SATURATION_DELTA,
  lightnessDelta: INITIAL_LIGHTNESS_DELTA,
  contrastDelta: INITIAL_CONTRAST_DELTA,
  alphaDelta: INITIAL_ALPHA_DELTA, 
  tintColor: hexToRgb(DEFAULT_TINT_COLOR_HEX)!, 
  tintAmount: INITIAL_TINT_AMOUNT,
});

const isGroupModified = (
  settings: AppliedGroupSettings | undefined,
  initialPrimaryHex: string | undefined,
  defaultGlobalTintColorRgb: RGBColor
): boolean => {
  if (!settings) return false;

  const effectiveInitialGroupTintColorRgb = initialPrimaryHex
    ? hexToRgb(initialPrimaryHex)
    : defaultGlobalTintColorRgb;

  if (!effectiveInitialGroupTintColorRgb) return true; 

  const settingsTintColorHex = rgbToHex(settings.tintColor).toLowerCase();
  const initialEffectiveTintColorHex = rgbToHex(effectiveInitialGroupTintColorRgb).toLowerCase();
  
  const isPureQuickRecolorState = 
        settings.hueDelta === INITIAL_HUE_DELTA &&
        settings.saturationDelta === INITIAL_SATURATION_DELTA &&
        settings.lightnessDelta === INITIAL_LIGHTNESS_DELTA &&
        settings.contrastDelta === INITIAL_CONTRAST_DELTA &&
        settings.alphaDelta === INITIAL_ALPHA_DELTA &&
        settings.tintAmount === 100;

  if (isPureQuickRecolorState) {
    return settingsTintColorHex !== initialEffectiveTintColorHex;
  }

  return (
    settings.hueDelta !== INITIAL_HUE_DELTA ||
    settings.saturationDelta !== INITIAL_SATURATION_DELTA ||
    settings.lightnessDelta !== INITIAL_LIGHTNESS_DELTA ||
    settings.contrastDelta !== INITIAL_CONTRAST_DELTA ||
    settings.alphaDelta !== INITIAL_ALPHA_DELTA ||
    settings.tintAmount !== INITIAL_TINT_AMOUNT ||
    settingsTintColorHex !== initialEffectiveTintColorHex
  );
};


const App: React.FC = () => {
  const [originalImageFile, setOriginalImageFile] = useState<File | null>(null);
  const [originalImageDataUrl, setOriginalImageDataUrl] = useState<string | null>(null);

  const [processedOriginalImageData, setProcessedOriginalImageData] = useState<ImageData | null>(null);
  const [cumulativeAlteredImageData, setCumulativeAlteredImageData] = useState<ImageData | null>(null);

  const [displayPalette, setDisplayPalette] = useState<PaletteColor[]>([]);
  const [recoloredImageDataUrl, setRecoloredImageDataUrl] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRecoloring, setIsRecoloring] = useState<boolean>(false);

  const [hueDelta, setHueDelta] = useState<number>(INITIAL_HUE_DELTA);
  const [saturationDelta, setSaturationDelta] = useState<number>(INITIAL_SATURATION_DELTA);
  const [lightnessDelta, setLightnessDelta] = useState<number>(INITIAL_LIGHTNESS_DELTA);
  const [contrastDelta, setContrastDelta] = useState<number>(INITIAL_CONTRAST_DELTA);
  const [alphaDelta, setAlphaDelta] = useState<number>(INITIAL_ALPHA_DELTA); 
  const [tintColor, setTintColor] = useState<RGBColor>(hexToRgb(DEFAULT_TINT_COLOR_HEX)!);
  const [tintAmount, setTintAmount] = useState<number>(INITIAL_TINT_AMOUNT);

  const [selectedPaletteColors, setSelectedPaletteColors] = useState<Set<string>>(new Set());
  const [colorGroups, setColorGroups] = useState<ColorGroup[]>([]);
  const [activeColorGroupId, setActiveColorGroupId] = useState<string>(ALL_COLORS_GROUP_ID);
  const [newGroupName, setNewGroupName] = useState<string>("");

  const [groupPrimaryColorHexes, setGroupPrimaryColorHexes] = useState<Record<string, string>>({});
  const [initialGroupPrimaryColorHexes, setInitialGroupPrimaryColorHexes] = useState<Record<string, string>>({});
  const [appliedGroupSettings, setAppliedGroupSettings] = useState<Record<string, AppliedGroupSettings>>({
     [ALL_COLORS_GROUP_ID]: getInitialAppliedSettings(),
  });

  const [isPixelHopperModeActive, setIsPixelHopperModeActive] = useState<boolean>(false);
  const [pixelHopperSelectedColors, setPixelHopperSelectedColors] = useState<Set<string>>(new Set());
  const [hopperPreviewUrl, setHopperPreviewUrl] = useState<string | null>(null);

  const [colorFinalOverrides, setColorFinalOverrides] = useState<Record<string, RGBColor>>({});

  const [predefinedImages, setPredefinedImages] = useState<PredefinedImage[]>([]);
  const [selectedPredefinedImageUrl, setSelectedPredefinedImageUrl] = useState<string>('');
  const [isFetchingPredefinedImages, setIsFetchingPredefinedImages] = useState<boolean>(false);

  const [baseCostumes, setBaseCostumes] = useState<PredefinedImage[]>([]);
  const [selectedBaseCostumeUrl, setSelectedBaseCostumeUrl] = useState<string>('');
  const [isFetchingBaseCostumes, setIsFetchingBaseCostumes] = useState<boolean>(false);

  const [lastClickedPixelInfo, setLastClickedPixelInfo] = useState<LastClickedPixelInfo | null>(null);
  const [isQuickRecolorModeActive, setIsQuickRecolorModeActive] = useState<boolean>(false);

  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [stagedHexesForGroupEdit, setStagedHexesForGroupEdit] = useState<Set<string> | null>(null);

  // --- NEW: Discord Submission State ---
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState<boolean>(false);
  const [discordUsername, setDiscordUsername] = useState<string>('');
  const [costumeName, setCostumeName] = useState<string>('');
  const [isSendingToDiscord, setIsSendingToDiscord] = useState<boolean>(false);
  // ------------------------------------
  const latestPreviewImageDataRef = useRef<ImageData | null>(null);
  const previousActiveColorGroupIdRef = useRef<string>(ALL_COLORS_GROUP_ID);

  const resetColorGroupsState = useCallback(() => {
    setSelectedPaletteColors(new Set());
    setColorGroups([]);
    setActiveColorGroupId(ALL_COLORS_GROUP_ID);
    setNewGroupName("");
    setGroupPrimaryColorHexes({});
    setInitialGroupPrimaryColorHexes({});
    setAppliedGroupSettings(prev => ({ [ALL_COLORS_GROUP_ID]: prev[ALL_COLORS_GROUP_ID] || getInitialAppliedSettings() }));
    previousActiveColorGroupIdRef.current = ALL_COLORS_GROUP_ID;
    setLastClickedPixelInfo(null);
    setPixelHopperSelectedColors(new Set());
    setIsPixelHopperModeActive(false);
    setHopperPreviewUrl(null);
    setColorFinalOverrides({});
    setIsQuickRecolorModeActive(false);
    setEditingGroupId(null); 
    setStagedHexesForGroupEdit(null); 
  }, []);

  const resetSlidersAndTint = useCallback((forGroupId: string) => {
    const newSettings = getInitialAppliedSettings(); 

    if (forGroupId !== ALL_COLORS_GROUP_ID) {
        const initialPrimary = initialGroupPrimaryColorHexes[forGroupId];
        if (initialPrimary) {
            const primaryRgb = hexToRgb(initialPrimary);
            if (primaryRgb) {
                newSettings.tintColor = primaryRgb; 
            }
        }
    }
    
    setHueDelta(newSettings.hueDelta);
    setSaturationDelta(newSettings.saturationDelta);
    setLightnessDelta(newSettings.lightnessDelta);
    setContrastDelta(newSettings.contrastDelta);
    setAlphaDelta(newSettings.alphaDelta);
    setTintColor(newSettings.tintColor);
    setTintAmount(newSettings.tintAmount);

    setAppliedGroupSettings(prev => ({
        ...prev,
        [forGroupId]: newSettings
    }));

    if (forGroupId !== ALL_COLORS_GROUP_ID) {
        const initialPrimary = initialGroupPrimaryColorHexes[forGroupId];
        if (initialPrimary) {
            setGroupPrimaryColorHexes(prev => ({ ...prev, [forGroupId]: initialPrimary }));
        }
    }
  }, [initialGroupPrimaryColorHexes]);


  const fullResetLogic = useCallback(() => {
    setOriginalImageDataUrl(null); 
    setRecoloredImageDataUrl(null);
    setProcessedOriginalImageData(null);
    setCumulativeAlteredImageData(null);
    latestPreviewImageDataRef.current = null;
    setDisplayPalette([]);
    resetColorGroupsState();
    resetSlidersAndTint(ALL_COLORS_GROUP_ID); 
    setLastClickedPixelInfo(null);
  }, [resetColorGroupsState, resetSlidersAndTint]);


  const processNewImageFile = useCallback((file: File, source: 'device' | 'predefined' | 'base') => {
    fullResetLogic(); 
    setOriginalImageFile(file); 

    if (source === 'device') {
        setSelectedPredefinedImageUrl('');
        setSelectedBaseCostumeUrl('');
    } else if (source === 'predefined') {
        setSelectedBaseCostumeUrl('');
    } else if (source === 'base') {
        setSelectedPredefinedImageUrl('');
    }
  }, [fullResetLogic]); 

  const processNewImageFileRef = useRef(processNewImageFile);
  useEffect(() => {
    processNewImageFileRef.current = processNewImageFile;
  }, [processNewImageFile]);


  const setHueDeltaWrapped = (value: number) => {
    setHueDelta(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), hueDelta: value }}));
  };
  const setSaturationDeltaWrapped = (value: number) => {
    setSaturationDelta(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), saturationDelta: value }}));
  };
  const setLightnessDeltaWrapped = (value: number) => {
    setLightnessDelta(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), lightnessDelta: value }}));
  };
  const setContrastDeltaWrapped = (value: number) => {
    setContrastDelta(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), contrastDelta: value }}));
  };
  const setAlphaDeltaWrapped = (value: number) => { 
    setAlphaDelta(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), alphaDelta: value }}));
  };
  const setTintColorWrapped = (color: RGBColor) => {
    setTintColor(color);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), tintColor: color }}));
  };
  const setTintAmountWrapped = (value: number) => {
    setTintAmount(value);
    setAppliedGroupSettings(prev => ({...prev, [activeColorGroupId]: {...(prev[activeColorGroupId] || getInitialAppliedSettings()), tintAmount: value }}));
  };


  useEffect(() => {
    const fetchOriginalColorCostumes = async () => {
      setIsFetchingPredefinedImages(true);
      try {
        const response = await fetch('https://api.github.com/repos/masterwebx/Color-Vault/contents/other/color%20sheets');
        if (!response.ok) {
          throw new Error(`GitHub API for original costumes responded with ${response.status}`);
        }
        const data = await response.json();
        if (Array.isArray(data)) {
          const imageFiles = data
            .filter((item: any) => item.type === 'file' && /\.(png|jpe?g|gif)$/i.test(item.name))
            .map((item: any) => ({ name: item.name, download_url: item.download_url }));
          setPredefinedImages(imageFiles);
        } else {
          console.error("Unexpected data format from GitHub API for original costumes:", data);
          setPredefinedImages([]);
        }
      } catch (error) {
        console.error("Failed to fetch original color costumes:", error);
        setPredefinedImages([]);
      } finally {
        setIsFetchingPredefinedImages(false);
      }
    };
    fetchOriginalColorCostumes();
  }, []);

  useEffect(() => {
    const fetchBaseCostumes = async () => {
      setIsFetchingBaseCostumes(true);
      try {
        const response = await fetch('https://api.github.com/repos/masterwebx/Color-Vault/contents/other/color%20sheets/OG%20sheets');
        if (!response.ok) {
          throw new Error(`GitHub API for base costumes responded with ${response.status}`);
        }
        const data = await response.json();
        if (Array.isArray(data)) {
          const imageFiles = data
            .filter((item: any) => item.type === 'file' && /\.(png|jpe?g|gif)$/i.test(item.name))
            .map((item: any) => ({ name: item.name, download_url: item.download_url }));
          setBaseCostumes(imageFiles);
        } else {
          console.error("Unexpected data format from GitHub API for base costumes:", data);
          setBaseCostumes([]);
        }
      } catch (error) {
        console.error("Failed to fetch base costumes:", error);
        setBaseCostumes([]);
      } finally {
        setIsFetchingBaseCostumes(false);
      }
    };
    fetchBaseCostumes();
  }, []);


   useEffect(() => {
    if (!selectedPredefinedImageUrl) return;

    const loadPredefined = async () => {
      setIsLoading(true); 
      try {
        const response = await fetch(selectedPredefinedImageUrl);
        if (!response.ok) throw new Error(`Failed to fetch image: ${response.status}`);
        const blob = await response.blob();
        const selectedImage = predefinedImages.find(img => img.download_url === selectedPredefinedImageUrl);
        const fileName = selectedImage ? selectedImage.name : `predefined_image.${blob.type.split('/')[1] || 'png'}`;

        const file = new File([blob], fileName, { type: blob.type });
        processNewImageFileRef.current(file, 'predefined');
      } catch (error) {
        console.error("Error loading predefined image:", error);
        alert(`Error loading predefined image: ${error instanceof Error ? error.message : String(error)}`);
        setIsLoading(false); 
      } 
    };
    loadPredefined();
  // eslint-disable-next-line react-hooks/exhaustive-deps 
  }, [selectedPredefinedImageUrl, predefinedImages]); 

  useEffect(() => {
    if (!selectedBaseCostumeUrl) return;

    const loadBaseCostume = async () => {
      setIsLoading(true); 
      try {
        const response = await fetch(selectedBaseCostumeUrl);
        if (!response.ok) throw new Error(`Failed to fetch base costume image: ${response.status}`);
        const blob = await response.blob();
        const selectedImage = baseCostumes.find(img => img.download_url === selectedBaseCostumeUrl);
        const fileName = selectedImage ? selectedImage.name : `base_costume.${blob.type.split('/')[1] || 'png'}`;
        const file = new File([blob], fileName, { type: blob.type });
        processNewImageFileRef.current(file, 'base');
      } catch (error) {
        console.error("Error loading base costume image:", error);
        alert(`Error loading base costume: ${error instanceof Error ? error.message : String(error)}`);
        setIsLoading(false); 
      }
    };
    loadBaseCostume();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBaseCostumeUrl, baseCostumes]); 


  useEffect(() => {
    if (!originalImageFile) {
      setIsLoading(false); 
      return;
    }

    setIsLoading(true);
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
      const img = new Image();
      img.onload = () => {
        setOriginalImageDataUrl(dataUrl); 
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (!ctx) {
          setIsLoading(false); return;
        }
        ctx.drawImage(img, 0, 0);
        try {
          const imageData = ctx.getImageData(0, 0, img.width, img.height);
          
          const uniqueRgbs = getUniqueColorsFromImageData(imageData);
          if (uniqueRgbs.length > MAX_UNIQUE_COLORS_PROCESSING) {
            alert(`Image has too many unique colors (${uniqueRgbs.length}). Maximum allowed is ${MAX_UNIQUE_COLORS_PROCESSING}. Please simplify the image or choose a different one.`);
            fullResetLogic();
            setOriginalImageFile(null); 
            setIsLoading(false);
            return;
          }

          setProcessedOriginalImageData(imageData);
          const initialCai = new ImageData(new Uint8ClampedArray(imageData.data), imageData.width, imageData.height);
          setCumulativeAlteredImageData(initialCai);
          latestPreviewImageDataRef.current = new ImageData(new Uint8ClampedArray(initialCai.data), initialCai.width, initialCai.height);

          const newPalette = uniqueRgbs.map(rgb => ({
            original: rgb, hex: rgbToHex(rgb),
          })).sort((a,b) => {
            const hslA = rgbToHsl(a.original); const hslB = rgbToHsl(b.original);
            if(hslA.l !== hslB.l) return hslA.l - hslB.l;
            if(hslA.s !== hslB.s) return hslA.s - hslB.s;
            return hslA.h - hslB.h;
          });
          setDisplayPalette(newPalette);
          
          const autoGroups = autoGroupColorsFromPalette(newPalette);
          setColorGroups(autoGroups);

          const initialPrimaryHexesRecord: Record<string, string> = {};
          const currentPrimaryHexesRecord: Record<string, string> = {};
          const newAppliedSettingsUpdate: Record<string, AppliedGroupSettings> = {};

          autoGroups.forEach(group => {
              const groupInitialSettings = getInitialAppliedSettings();
              const primaryRgbForGroup = getGroupPrimaryColorOriginalRgb(group, newPalette);
              let primaryHexForGroup: string | undefined;

              if (primaryRgbForGroup) {
                  primaryHexForGroup = rgbToHex(primaryRgbForGroup);
                  groupInitialSettings.tintColor = primaryRgbForGroup;
              } else if (group.colorHexes.size > 0) { 
                  primaryHexForGroup = Array.from(group.colorHexes)[0];
                  const fallbackPrimaryRgb = hexToRgb(primaryHexForGroup);
                  if (fallbackPrimaryRgb) groupInitialSettings.tintColor = fallbackPrimaryRgb;
              }
              
              newAppliedSettingsUpdate[group.id] = groupInitialSettings;

              if (primaryHexForGroup) {
                  initialPrimaryHexesRecord[group.id] = primaryHexForGroup;
                  currentPrimaryHexesRecord[group.id] = primaryHexForGroup;
              }
          });
          setInitialGroupPrimaryColorHexes(initialPrimaryHexesRecord);
          setGroupPrimaryColorHexes(currentPrimaryHexesRecord);
          setAppliedGroupSettings(prev => ({ ...prev, ...newAppliedSettingsUpdate })); 
          setRecoloredImageDataUrl(imageDataToDataUrl(initialCai)); 
        } catch (error) { 
            console.error("Error processing image data:", error); 
            alert(`Error processing image: ${error instanceof Error ? error.message : String(error)}`);
            fullResetLogic();
            setOriginalImageFile(null);
        }
        finally { setIsLoading(false); }
      };
      img.onerror = () => { 
        setIsLoading(false); 
        setOriginalImageDataUrl(null); 
        alert("Could not load the image. It might be corrupted or in an unsupported format.");
        fullResetLogic();
        setOriginalImageFile(null);
      };
      img.src = dataUrl;
    };
    reader.onerror = () => { 
        setIsLoading(false); 
        alert("Failed to read the image file.");
        fullResetLogic();
        setOriginalImageFile(null);
    };
    reader.readAsDataURL(originalImageFile);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [originalImageFile]);


  useEffect(() => {
    if (activeColorGroupId !== previousActiveColorGroupIdRef.current) {
        if (editingGroupId && editingGroupId !== activeColorGroupId) {
          setEditingGroupId(null);
          setStagedHexesForGroupEdit(null);
        }

        if (latestPreviewImageDataRef.current) {
            setCumulativeAlteredImageData(
                new ImageData(
                    new Uint8ClampedArray(latestPreviewImageDataRef.current.data),
                    latestPreviewImageDataRef.current.width,
                    latestPreviewImageDataRef.current.height
                )
            );
        }

        const settingsToLoad = appliedGroupSettings[activeColorGroupId];
        if (settingsToLoad) {
            setHueDelta(settingsToLoad.hueDelta);
            setSaturationDelta(settingsToLoad.saturationDelta);
            setLightnessDelta(settingsToLoad.lightnessDelta);
            setContrastDelta(settingsToLoad.contrastDelta);
            setAlphaDelta(settingsToLoad.alphaDelta);
            
            const groupPrimaryHex = groupPrimaryColorHexes[activeColorGroupId] || initialGroupPrimaryColorHexes[activeColorGroupId];
            let tintToLoad = settingsToLoad.tintColor;

            if (activeColorGroupId !== ALL_COLORS_GROUP_ID) {
                const initialForGroup = initialGroupPrimaryColorHexes[activeColorGroupId];
                const defaultTintForGroup = initialForGroup ? hexToRgb(initialForGroup) : hexToRgb(DEFAULT_TINT_COLOR_HEX)!;

                if (rgbToHex(settingsToLoad.tintColor) === DEFAULT_TINT_COLOR_HEX && defaultTintForGroup) {
                    tintToLoad = defaultTintForGroup;
                }
            }
            setTintColor(tintToLoad); 
            setTintAmount(settingsToLoad.tintAmount);
        } else { 
            resetSlidersAndTint(activeColorGroupId);
        }
        previousActiveColorGroupIdRef.current = activeColorGroupId;
    }
  }, [activeColorGroupId, appliedGroupSettings, resetSlidersAndTint, groupPrimaryColorHexes, initialGroupPrimaryColorHexes, editingGroupId]);


  const handleManualGroupChange = (newGroupId: string) => {
    setActiveColorGroupId(newGroupId);
    setLastClickedPixelInfo(null); 
  };

  useEffect(() => {
    if (isPixelHopperModeActive && latestPreviewImageDataRef.current && processedOriginalImageData) {
      const baseImage = latestPreviewImageDataRef.current;
      const previewHopperImageData = new ImageData(
        new Uint8ClampedArray(baseImage.data), // Copy RGB values from current preview
        baseImage.width,
        baseImage.height
      );
  
      // Ensure dimensions match for safety
      if (baseImage.width !== processedOriginalImageData.width || baseImage.height !== processedOriginalImageData.height) {
        console.warn("Pixel Hopper: Mismatched dimensions between latest preview and original image data. Alpha blending might be inaccurate.");
        setHopperPreviewUrl(imageDataToDataUrl(baseImage)); // Fallback
        return;
      }
  
      for (let i = 0; i < processedOriginalImageData.data.length; i += 4) {
        const originalR = processedOriginalImageData.data[i];
        const originalG = processedOriginalImageData.data[i + 1];
        const originalB = processedOriginalImageData.data[i + 2];
        const originalA = processedOriginalImageData.data[i + 3]; // Alpha from the *original* processed image data
  
        const currentVisibleAlpha = baseImage.data[i + 3]; // Alpha from the *latest recolored* preview
  
        if (originalA === 0) { // If pixel was originally transparent, keep it transparent
          previewHopperImageData.data[i + 3] = 0;
          continue;
        }
  
        const originalHex = rgbToHex({ r: originalR, g: originalG, b: originalB, a: originalA });
  
        if (pixelHopperSelectedColors.has(originalHex)) {
          // Selected: 100% of its current visible alpha
          previewHopperImageData.data[i + 3] = currentVisibleAlpha;
        } else {
          // Not selected: 10% of its current visible alpha
          previewHopperImageData.data[i + 3] = Math.round(currentVisibleAlpha * 0.1);
        }
      }
      setHopperPreviewUrl(imageDataToDataUrl(previewHopperImageData));
    } else {
      setHopperPreviewUrl(null); // Not in hopper mode, or no base image/original data
    }
  }, [isPixelHopperModeActive, pixelHopperSelectedColors, latestPreviewImageDataRef, processedOriginalImageData]);


  useEffect(() => {
    if (!processedOriginalImageData || !cumulativeAlteredImageData) {
      if (recoloredImageDataUrl !== null) setRecoloredImageDataUrl(null);
      if (latestPreviewImageDataRef.current !== null) latestPreviewImageDataRef.current = null;
      if (isRecoloring) setIsRecoloring(false);
      return;
    }

    if (displayPalette.length === 0) { 
        if (isRecoloring) setIsRecoloring(false);
        return;
    }
    
    if (!recoloredImageDataUrl && cumulativeAlteredImageData) {
        const initialDisplayUrl = imageDataToDataUrl(cumulativeAlteredImageData);
        setRecoloredImageDataUrl(initialDisplayUrl);
        latestPreviewImageDataRef.current = new ImageData(
            new Uint8ClampedArray(cumulativeAlteredImageData.data),
            cumulativeAlteredImageData.width,
            cumulativeAlteredImageData.height
        );
        if (isRecoloring) setIsRecoloring(false);
        return; 
    }

    const currentActiveGroupSettings = appliedGroupSettings[activeColorGroupId] || getInitialAppliedSettings();
    const activeGroupInitialPrimaryHex = activeColorGroupId === ALL_COLORS_GROUP_ID ? undefined : initialGroupPrimaryColorHexes[activeColorGroupId];
    
    const noSliderChangesOrOverrides = 
        currentActiveGroupSettings.hueDelta === INITIAL_HUE_DELTA &&
        currentActiveGroupSettings.saturationDelta === INITIAL_SATURATION_DELTA &&
        currentActiveGroupSettings.lightnessDelta === INITIAL_LIGHTNESS_DELTA &&
        currentActiveGroupSettings.contrastDelta === INITIAL_CONTRAST_DELTA &&
        currentActiveGroupSettings.alphaDelta === INITIAL_ALPHA_DELTA &&
        currentActiveGroupSettings.tintAmount === INITIAL_TINT_AMOUNT &&
        (activeColorGroupId === ALL_COLORS_GROUP_ID 
            ? rgbToHex(currentActiveGroupSettings.tintColor) === DEFAULT_TINT_COLOR_HEX
            : (activeGroupInitialPrimaryHex 
                ? rgbToHex(currentActiveGroupSettings.tintColor).toLowerCase() === activeGroupInitialPrimaryHex.toLowerCase()
                : rgbToHex(currentActiveGroupSettings.tintColor) === DEFAULT_TINT_COLOR_HEX 
              )
        );

    const noOverridesExist = Object.keys(colorFinalOverrides).length === 0;

    if (noSliderChangesOrOverrides && noOverridesExist && !isQuickRecolorModeActive && !editingGroupId) { 
      const caiUrl = imageDataToDataUrl(cumulativeAlteredImageData);
      if (recoloredImageDataUrl !== caiUrl) {
        setRecoloredImageDataUrl(caiUrl);
      }
      latestPreviewImageDataRef.current = new ImageData(
          new Uint8ClampedArray(cumulativeAlteredImageData.data),
          cumulativeAlteredImageData.width,
          cumulativeAlteredImageData.height
      );
      if (isRecoloring) setIsRecoloring(false);
      return;
    }


    setIsRecoloring(true);

    const recolorTimeout = setTimeout(() => {
      try {
        const baseImageDataForRecolor = new ImageData(
          new Uint8ClampedArray(cumulativeAlteredImageData.data), 
          cumulativeAlteredImageData.width,
          cumulativeAlteredImageData.height
        );
        const displayImageData = new ImageData( 
          new Uint8ClampedArray(baseImageDataForRecolor.data), 
          baseImageDataForRecolor.width,
          baseImageDataForRecolor.height
        );
        
        const groupsToProcess = isQuickRecolorModeActive && !editingGroupId
          ? colorGroups 
          : [colorGroups.find(g => g.id === activeColorGroupId) || { id: ALL_COLORS_GROUP_ID, name: "All Colors", colorHexes: new Set(displayPalette.map(p => p.hex)) } ];


        for (const group of groupsToProcess) {
          if (!group) continue;
          const groupId = group.id;

          const groupSettingsToApply = appliedGroupSettings[groupId] || getInitialAppliedSettings();
          
          let targetHexesThisGroup = new Set<string>();
          if (groupId === ALL_COLORS_GROUP_ID) {
            displayPalette.forEach(pColor => targetHexesThisGroup.add(pColor.hex));
          } else {

            targetHexesThisGroup = (editingGroupId === groupId && stagedHexesForGroupEdit) 
                                    ? stagedHexesForGroupEdit 
                                    : group.colorHexes;
          }

          if (targetHexesThisGroup.size === 0) continue;

          let groupPrimaryOriginalRgbForTint: RGBColor | null = null;
          if (groupId !== ALL_COLORS_GROUP_ID) {
              const primaryHex = groupPrimaryColorHexes[groupId] || initialGroupPrimaryColorHexes[groupId];
              if (primaryHex) {
                  const pColor = displayPalette.find(p => p.hex === primaryHex);
                  if (pColor) groupPrimaryOriginalRgbForTint = pColor.original;
              }
              if (!groupPrimaryOriginalRgbForTint) {
                  groupPrimaryOriginalRgbForTint = getGroupPrimaryColorOriginalRgb(group, displayPalette);
              }
          }
          
          const { hueDelta: gh, saturationDelta: gs, lightnessDelta: gl, contrastDelta: gc, alphaDelta: ga, tintColor: gtc, tintAmount: gta } = groupSettingsToApply;

          for (let i = 0; i < processedOriginalImageData.data.length; i += 4) {
            const pogiR = processedOriginalImageData.data[i];
            const pogiG = processedOriginalImageData.data[i + 1];
            const pogiB = processedOriginalImageData.data[i + 2];
            const pogiA = processedOriginalImageData.data[i + 3];

            if (pogiA === 0 && ga === INITIAL_ALPHA_DELTA) { 
                displayImageData.data[i+3] = 0; 
                continue;
            }

            const currentPixelOriginalPogiRgb: RGBColor = { r: pogiR, g: pogiG, b: pogiB, a: pogiA };
            const currentPixelOriginalPogiHex = rgbToHex(currentPixelOriginalPogiRgb);
            
            if (colorFinalOverrides[currentPixelOriginalPogiHex]) {
              const finalRgb = colorFinalOverrides[currentPixelOriginalPogiHex];
              displayImageData.data[i] = finalRgb.r;
              displayImageData.data[i + 1] = finalRgb.g;
              displayImageData.data[i + 2] = finalRgb.b;
              displayImageData.data[i + 3] = finalRgb.a; 
              continue; 
            }

            if (targetHexesThisGroup.has(currentPixelOriginalPogiHex)) {
              const baseR = baseImageDataForRecolor.data[i];
              const baseG = baseImageDataForRecolor.data[i+1];
              const baseB = baseImageDataForRecolor.data[i+2];
              const baseA = baseImageDataForRecolor.data[i+3]; 

              let baseForHslSliders: RGBColor = { r: baseR, g: baseG, b: baseB, a: baseA };
              
              let finalAlphaValue = pogiA; 
              if (ga !== INITIAL_ALPHA_DELTA) { 
                  const factor = 1 + (ga / 100.0); 
                  finalAlphaValue = pogiA * factor; 
              }
              finalAlphaValue = Math.round(Math.max(0, Math.min(255, finalAlphaValue)));
              baseForHslSliders.a = finalAlphaValue;


              if (gta > 0) {
                if (groupId !== ALL_COLORS_GROUP_ID && groupPrimaryOriginalRgbForTint) {
                    baseForHslSliders = calculateTintedColorForGroupMember(
                      {...currentPixelOriginalPogiRgb, a: baseForHslSliders.a}, 
                      groupPrimaryOriginalRgbForTint, 
                      gtc, 
                      gta / 100
                    );
                } else if (groupId === ALL_COLORS_GROUP_ID) { 
                  baseForHslSliders = applyPixelTint(baseForHslSliders, gtc, gta / 100);
                }
              }

              const currentHsl = rgbToHsl(baseForHslSliders); 
              let adjustedH = (currentHsl.h + gh);
              adjustedH = ((adjustedH % 360) + 360) % 360;
              let adjustedS = currentHsl.s + (gs / 100);
              adjustedS = Math.max(0, Math.min(1, adjustedS));
              let adjustedL = currentHsl.l + (gl / 100);

              if (gc !== 0) {
                const contrastFactor = 1 + gc / 100;
                adjustedL = 0.5 + (adjustedL - 0.5) * contrastFactor;
              }
              adjustedL = Math.max(0, Math.min(1, adjustedL));

              const finalTransformedRgb = hslToRgb({ h: adjustedH, s: adjustedS, l: adjustedL }, baseForHslSliders.a);

              displayImageData.data[i] = finalTransformedRgb.r;
              displayImageData.data[i + 1] = finalTransformedRgb.g;
              displayImageData.data[i + 2] = finalTransformedRgb.b;
              displayImageData.data[i + 3] = finalTransformedRgb.a;
            } else if (pogiA === 0 && !colorFinalOverrides[currentPixelOriginalPogiHex]) { 
                displayImageData.data[i+3] = 0;
            }
          }
        }
        setRecoloredImageDataUrl(imageDataToDataUrl(displayImageData));
        latestPreviewImageDataRef.current = displayImageData; 
      } catch(error) {
        console.error("Error during recoloring:", error);
        if (cumulativeAlteredImageData) setRecoloredImageDataUrl(imageDataToDataUrl(cumulativeAlteredImageData));
      } finally {
        setIsRecoloring(false);
      }
    }, 50); 

    return () => clearTimeout(recolorTimeout);
  }, [
    processedOriginalImageData, cumulativeAlteredImageData, 
    hueDelta, saturationDelta, lightnessDelta, contrastDelta, alphaDelta, tintColor, tintAmount,
    displayPalette, activeColorGroupId, colorGroups, groupPrimaryColorHexes, initialGroupPrimaryColorHexes,
    colorFinalOverrides, appliedGroupSettings, isQuickRecolorModeActive, 
    editingGroupId, stagedHexesForGroupEdit 
  ]);

  const handleTogglePaletteColorSelection = useCallback((hex: string) => {
    setSelectedPaletteColors(prev => {
      const newSelected = new Set(prev);
      if (newSelected.has(hex)) newSelected.delete(hex);
      else newSelected.add(hex);
      return newSelected;
    });
  }, []);

  const handleCreateColorGroup = useCallback(() => {
    if (newGroupName.trim() === "" || selectedPaletteColors.size === 0) return;
    const newGroupId = Date.now().toString() + "_" + newGroupName.trim().replace(/\s+/g, '_');
    const newGroup: ColorGroup = {
      id: newGroupId,
      name: newGroupName.trim(),
      colorHexes: new Set(selectedPaletteColors),
    };
    setColorGroups(prev => [newGroup, ...prev]); // Prepend new group
    
    const newGroupInitialSettings = getInitialAppliedSettings();
    let primaryHexForNewGroup: string | undefined = undefined;

    if (newGroup.colorHexes.size > 0) {
        const tempPrimaryRgb = getGroupPrimaryColorOriginalRgb(newGroup, displayPalette);
        primaryHexForNewGroup = tempPrimaryRgb ? rgbToHex(tempPrimaryRgb) : Array.from(newGroup.colorHexes)[0];
    }

    if (primaryHexForNewGroup) {
        const primaryRgb = hexToRgb(primaryHexForNewGroup);
        if (primaryRgb) {
            newGroupInitialSettings.tintColor = primaryRgb;
        }
        setInitialGroupPrimaryColorHexes(prev => ({ ...prev, [newGroup.id]: primaryHexForNewGroup! }));
        setGroupPrimaryColorHexes(prevHexes => ({...prevHexes, [newGroup.id]: primaryHexForNewGroup! }));
    }
    setAppliedGroupSettings(prev => ({...prev, [newGroupId]: newGroupInitialSettings }));

    setNewGroupName("");
    setSelectedPaletteColors(new Set());
    setActiveColorGroupId(newGroup.id); 
    setLastClickedPixelInfo(null);

    // Turn off Pixel Hopper mode and clear related states
    setIsPixelHopperModeActive(false);
    setPixelHopperSelectedColors(new Set());
    setHopperPreviewUrl(null);

  }, [newGroupName, selectedPaletteColors, displayPalette]);

  const handleClearPaletteSelection = useCallback(() => setSelectedPaletteColors(new Set()), []);

  const handleSetGroupPrimaryColor = useCallback((groupId: string, colorHex: string) => {
    setGroupPrimaryColorHexes(prev => ({ ...prev, [groupId]: colorHex }));
    
    setAppliedGroupSettings(prevSettings => {
        const currentGroupSettings = prevSettings[groupId] || getInitialAppliedSettings();
        const initialPrimaryForGroupHex = initialGroupPrimaryColorHexes[groupId];
        let currentTintColorIsDefaultOrOldPrimary = rgbToHex(currentGroupSettings.tintColor) === DEFAULT_TINT_COLOR_HEX;
        if (initialPrimaryForGroupHex) {
            currentTintColorIsDefaultOrOldPrimary = currentTintColorIsDefaultOrOldPrimary || 
                                                   rgbToHex(currentGroupSettings.tintColor).toLowerCase() === initialPrimaryForGroupHex.toLowerCase();
        }

        if (currentTintColorIsDefaultOrOldPrimary) {
            const newPrimaryRgb = hexToRgb(colorHex);
            if (newPrimaryRgb) {
                const updatedSettings = { ...currentGroupSettings, tintColor: newPrimaryRgb };
                if (groupId === activeColorGroupId) {
                    setTintColor(newPrimaryRgb); 
                }
                return { ...prevSettings, [groupId]: updatedSettings };
            }
        }
        return prevSettings; 
    });

  }, [activeColorGroupId, initialGroupPrimaryColorHexes]);


  const handleToggleStagedHexForEdit = useCallback((hex: string) => {
    if (!stagedHexesForGroupEdit || !editingGroupId) return;
    const newStaged = new Set(stagedHexesForGroupEdit);
    if (newStaged.has(hex)) {
      newStaged.delete(hex);
    } else {
      if (displayPalette.some(p => p.hex === hex)) {
          newStaged.add(hex);
      }
    }
    setStagedHexesForGroupEdit(newStaged);
  }, [stagedHexesForGroupEdit, editingGroupId, displayPalette]);


  const handleImagePixelClick = useCallback((originalX: number, originalY: number) => {
    if (!processedOriginalImageData) return;

    const data = processedOriginalImageData.data;
    const width = processedOriginalImageData.width;
    const index = (originalY * width + originalX) * 4;

    const r = data[index];
    const g = data[index + 1];
    const b = data[index + 2];
    const a = data[index + 3];
    const clickedOriginalHex = rgbToHex({ r, g, b, a });

    if (editingGroupId) { 
      if (a === 0 && !displayPalette.some(p => p.hex === clickedOriginalHex)) { 
        if (!displayPalette.some(p => p.original.a === 0 && p.hex === clickedOriginalHex)) return;
      }
      if (displayPalette.some(p => p.hex === clickedOriginalHex)) {
        handleToggleStagedHexForEdit(clickedOriginalHex);
      }
      return; 
    }
    
    if (isPixelHopperModeActive) { 
      if (a === 0 && !displayPalette.some(p => p.hex === clickedOriginalHex)) return;
      if (!displayPalette.some(p => p.hex === clickedOriginalHex)) return;
      
      setPixelHopperSelectedColors(prev => {
        const newSelected = new Set(prev);
        if (newSelected.has(clickedOriginalHex)) newSelected.delete(clickedOriginalHex);
        else newSelected.add(clickedOriginalHex);
        return newSelected;
      });
      return; 
    }

    if (a === 0) { 
      setLastClickedPixelInfo(null); 
      return;
    }
    const currentMatchingGroupIds = colorGroups
      .filter(group => group.colorHexes.has(clickedOriginalHex))
      .map(group => group.id);

    if (!displayPalette.some(p => p.hex === clickedOriginalHex)) {
        setLastClickedPixelInfo(null);
        setActiveColorGroupId(ALL_COLORS_GROUP_ID); 
        return;
    }

    if (lastClickedPixelInfo && lastClickedPixelInfo.hex === clickedOriginalHex) {
      const numMatchingGroups = lastClickedPixelInfo.matchingGroupIds.length;
      let nextGroupId = ALL_COLORS_GROUP_ID;
      let nextCycleIndex = lastClickedPixelInfo.cycleIndex;

      if (numMatchingGroups > 0) {
        if (activeColorGroupId === ALL_COLORS_GROUP_ID) { 
            nextGroupId = lastClickedPixelInfo.matchingGroupIds[0];
            nextCycleIndex = 0;
        } else { 
            nextCycleIndex = (lastClickedPixelInfo.cycleIndex + 1);
            if (nextCycleIndex < numMatchingGroups) { 
                nextGroupId = lastClickedPixelInfo.matchingGroupIds[nextCycleIndex];
            } else { 
                nextGroupId = ALL_COLORS_GROUP_ID;
                nextCycleIndex = -1; 
            }
        }
      } else { 
        nextGroupId = ALL_COLORS_GROUP_ID;
        nextCycleIndex = 0; 
      }
      setActiveColorGroupId(nextGroupId);
      setLastClickedPixelInfo(prev => prev ? { ...prev, cycleIndex: nextCycleIndex } : null);

    } else { 
      if (currentMatchingGroupIds.length > 0) {
        setActiveColorGroupId(currentMatchingGroupIds[0]);
        setLastClickedPixelInfo({ hex: clickedOriginalHex, matchingGroupIds: currentMatchingGroupIds, cycleIndex: 0 });
      } else {
        setActiveColorGroupId(ALL_COLORS_GROUP_ID);
        setLastClickedPixelInfo({ hex: clickedOriginalHex, matchingGroupIds: [], cycleIndex: 0 }); 
      }
    }
  }, [processedOriginalImageData, colorGroups, lastClickedPixelInfo, displayPalette, activeColorGroupId, editingGroupId, isPixelHopperModeActive, handleToggleStagedHexForEdit]);


  const handleSaveImage = useCallback(() => {
    const urlToSave = hopperPreviewUrl || recoloredImageDataUrl; 
    if (urlToSave && originalImageFile) {
      const link = document.createElement('a');
      link.href = urlToSave;
      const originalNameParts = originalImageFile.name.split('.');
      const extension = originalNameParts.pop();
      const nameWithoutExtension = originalNameParts.join('.');
      link.download = `${nameWithoutExtension}_recolored.${extension || 'png'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [hopperPreviewUrl, recoloredImageDataUrl, originalImageFile]);

  // --- NEW: Helper to convert DataURL to Blob ---
  const dataURItoBlob = (dataURI: string) => {
    const byteString = atob(dataURI.split(',')[1]);
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ab], { type: mimeString });
  };

  // --- NEW: Handle Submission to Cloudflare/Discord ---
  const handleSubmitToDiscord = async () => {
    if (!discordUsername.trim() || !costumeName.trim()) {
      alert("Please enter both a Costume Name and your Discord Username.");
      return;
    }

    const imageSource = hopperPreviewUrl || recoloredImageDataUrl;
    if (!imageSource) {
      alert("No image data found to upload.");
      return;
    }

    setIsSendingToDiscord(true);

    try {
      const imageBlob = dataURItoBlob(imageSource);
      
      const formData = new FormData();
      formData.append('image', imageBlob, 'costume.png');
      formData.append('username', discordUsername);
      formData.append('costumeName', costumeName);
      // Optional: Pass original filename as character hint if needed
      if(originalImageFile) {
        formData.append('character', originalImageFile.name); 
      }

      const response = await fetch('https://color-vault-relay.glwplex-7c2.workers.dev/', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (result.success) {
        alert("Success! Sent to the Discord vault queue.");
        setIsSubmitModalOpen(false);
        setCostumeName(''); // Clear specific fields after success, but keep username for convenience? 
        // setDiscordUsername(''); // Optional: clear username too
      } else {
        alert("Failed to send: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("Error communicating with the server.");
    } finally {
      setIsSendingToDiscord(false);
    }
  };

  const handleCopySettingsFromGroup = useCallback((sourceGroupId: string) => {
    if (!sourceGroupId || sourceGroupId === activeColorGroupId || sourceGroupId === ALL_COLORS_GROUP_ID) return;

    const settingsToCopy = appliedGroupSettings[sourceGroupId] || getInitialAppliedSettings();
    const primaryColorToCopy = groupPrimaryColorHexes[sourceGroupId] || initialGroupPrimaryColorHexes[sourceGroupId];

    setHueDelta(settingsToCopy.hueDelta);
    setSaturationDelta(settingsToCopy.saturationDelta);
    setLightnessDelta(settingsToCopy.lightnessDelta);
    setContrastDelta(settingsToCopy.contrastDelta);
    setAlphaDelta(settingsToCopy.alphaDelta); 
    setTintColor(settingsToCopy.tintColor); 
    setTintAmount(settingsToCopy.tintAmount);

    if (activeColorGroupId !== ALL_COLORS_GROUP_ID) {
      setAppliedGroupSettings(prev => ({
        ...prev,
        [activeColorGroupId]: { ...settingsToCopy }
      }));
      if (primaryColorToCopy) { 
        handleSetGroupPrimaryColor(activeColorGroupId, primaryColorToCopy);
      }
    }
  }, [activeColorGroupId, appliedGroupSettings, groupPrimaryColorHexes, initialGroupPrimaryColorHexes, handleSetGroupPrimaryColor]);

  const togglePixelHopperMode = useCallback(() => {
    setIsPixelHopperModeActive(prev => {
      const newMode = !prev;
      if (newMode && editingGroupId) { 
        setEditingGroupId(null);
        setStagedHexesForGroupEdit(null);
      }
      if (!newMode) { 
        setPixelHopperSelectedColors(new Set()); 
        setHopperPreviewUrl(null);
      }
      return newMode;
    });
  }, [editingGroupId]); 

  const addHopperColorsToStaging = useCallback(() => {
    setSelectedPaletteColors(prevStaging => {
      const newStaging = new Set(prevStaging);
      pixelHopperSelectedColors.forEach(hex => newStaging.add(hex));
      return newStaging;
    });
    setPixelHopperSelectedColors(new Set()); 
  }, [pixelHopperSelectedColors]);

  const handleStartEditGroupColors = useCallback((groupId: string) => {
    const group = colorGroups.find(g => g.id === groupId);
    if (group && group.id !== ALL_COLORS_GROUP_ID) {
        setEditingGroupId(groupId);
        setStagedHexesForGroupEdit(new Set(group.colorHexes));
        if (isPixelHopperModeActive) { // Turn off hopper mode if it's on
            setIsPixelHopperModeActive(false);
            setPixelHopperSelectedColors(new Set());
            setHopperPreviewUrl(null);
        }
    }
  }, [colorGroups, isPixelHopperModeActive]);

  const handleSaveEditedGroupColors = useCallback((groupIdToUpdate: string) => {
    if (!stagedHexesForGroupEdit || groupIdToUpdate === ALL_COLORS_GROUP_ID || stagedHexesForGroupEdit.size === 0) {
        if (stagedHexesForGroupEdit && stagedHexesForGroupEdit.size === 0) {
            alert("Cannot save an empty group. Please add at least one color or cancel the edit.");
        }
        return;
    }
    
    setColorGroups(prevGroups => {
        const newGroups = prevGroups.map(g => 
            g.id === groupIdToUpdate ? { ...g, colorHexes: new Set(stagedHexesForGroupEdit) } : g
        );
        
        const updatedGroup = newGroups.find(g => g.id === groupIdToUpdate);
        if (updatedGroup) {
            const oldPrimary = groupPrimaryColorHexes[groupIdToUpdate] || initialGroupPrimaryColorHexes[groupIdToUpdate];
            if (oldPrimary && !updatedGroup.colorHexes.has(oldPrimary) && updatedGroup.colorHexes.size > 0) {
                const newPrimary = Array.from(updatedGroup.colorHexes)[0]; 
                handleSetGroupPrimaryColor(groupIdToUpdate, newPrimary);
            } else if (updatedGroup.colorHexes.size === 0 && oldPrimary) { 
                 setGroupPrimaryColorHexes(prev => { const newState = {...prev}; delete newState[groupIdToUpdate]; return newState; });
                 setInitialGroupPrimaryColorHexes(prev => { const newState = {...prev}; delete newState[groupIdToUpdate]; return newState; });
            } else if (updatedGroup.colorHexes.size > 0 && !oldPrimary) { 
                const newPrimary = Array.from(updatedGroup.colorHexes)[0];
                handleSetGroupPrimaryColor(groupIdToUpdate, newPrimary);
                setInitialGroupPrimaryColorHexes(prev => ({...prev, [groupIdToUpdate]: newPrimary}));
            }
        }
        return newGroups; 
    });

    setEditingGroupId(null);
    setStagedHexesForGroupEdit(null);
  }, [stagedHexesForGroupEdit, colorGroups, groupPrimaryColorHexes, initialGroupPrimaryColorHexes, handleSetGroupPrimaryColor]);


  const handleSaveAsNewGroup = useCallback((originalGroupId: string, newGroupNameProvided: string) => {
    if (!stagedHexesForGroupEdit || stagedHexesForGroupEdit.size === 0) {
        alert("Cannot save an empty group. Please add at least one color.");
        return;
    }

    const finalNewGroupName = newGroupNameProvided.trim(); 

    if (finalNewGroupName === "") {
      alert("New group name cannot be empty."); 
      return;
    }

    const newGroupId = Date.now().toString() + "_" + finalNewGroupName.replace(/\s+/g, '_');
    
    const newGroup: ColorGroup = {
      id: newGroupId,
      name: finalNewGroupName,
      colorHexes: new Set(stagedHexesForGroupEdit),
    };

    setColorGroups(prev => [newGroup, ...prev]); // Prepend new group
    
    const newGroupInitialSettings = getInitialAppliedSettings();
    let primaryHexForNewGroup: string | undefined = undefined;

    if (newGroup.colorHexes.size > 0) {
        const tempPrimaryRgb = getGroupPrimaryColorOriginalRgb(newGroup, displayPalette);
        primaryHexForNewGroup = tempPrimaryRgb ? rgbToHex(tempPrimaryRgb) : Array.from(newGroup.colorHexes)[0];
    }

    if (primaryHexForNewGroup) {
        const primaryRgb = hexToRgb(primaryHexForNewGroup);
        if (primaryRgb) {
            newGroupInitialSettings.tintColor = primaryRgb;
        }
        setInitialGroupPrimaryColorHexes(prev => ({ ...prev, [newGroup.id]: primaryHexForNewGroup! }));
        setGroupPrimaryColorHexes(prevHexes => ({...prevHexes, [newGroup.id]: primaryHexForNewGroup! }));
    }
    setAppliedGroupSettings(prev => ({...prev, [newGroupId]: newGroupInitialSettings }));

    setEditingGroupId(null);
    setStagedHexesForGroupEdit(null);
    setActiveColorGroupId(newGroup.id); 
    setLastClickedPixelInfo(null);

  }, [stagedHexesForGroupEdit, displayPalette, getGroupPrimaryColorOriginalRgb]);


  const handleCancelEditGroupColors = useCallback(() => {
    setEditingGroupId(null);
    setStagedHexesForGroupEdit(null);
  }, []);


  const handleRemoveColorFromGroup = useCallback((groupIdToRemoveFrom: string, colorHexToRemove: string) => {
    if (editingGroupId === groupIdToRemoveFrom && stagedHexesForGroupEdit) {
        handleToggleStagedHexForEdit(colorHexToRemove); 
        return;
    }
    let wasPrimaryRemoved = false;
    let newPrimaryForGroup: string | undefined = undefined;

    setColorGroups(prevGroups =>
      prevGroups.map(group => {
        if (group.id === groupIdToRemoveFrom) {
          const newColorHexes = new Set(group.colorHexes);
          const removed = newColorHexes.delete(colorHexToRemove);
          if (removed && (groupPrimaryColorHexes[groupIdToRemoveFrom] === colorHexToRemove || initialGroupPrimaryColorHexes[groupIdToRemoveFrom] === colorHexToRemove)) {
            wasPrimaryRemoved = true;
            if (newColorHexes.size > 0) {
              newPrimaryForGroup = Array.from(newColorHexes)[0]; 
            }
          }
          return { ...group, colorHexes: newColorHexes };
        }
        return group;
      }).filter(group => group.id === ALL_COLORS_GROUP_ID || group.id.startsWith('auto_') || group.colorHexes.size > 0) 
    );

    if (wasPrimaryRemoved) {
      const updatePrimaries = (prevPrimaries: Record<string, string>) => {
        const updatedPrimaries = { ...prevPrimaries };
        if (newPrimaryForGroup) {
          updatedPrimaries[groupIdToRemoveFrom] = newPrimaryForGroup;
        } else {
          delete updatedPrimaries[groupIdToRemoveFrom]; 
        }
        return updatedPrimaries;
      };
      setGroupPrimaryColorHexes(updatePrimaries);
      setInitialGroupPrimaryColorHexes(updatePrimaries); 

      if (activeColorGroupId === groupIdToRemoveFrom) {
          const currentSettings = appliedGroupSettings[groupIdToRemoveFrom] || getInitialAppliedSettings();
          let newTintColor = hexToRgb(DEFAULT_TINT_COLOR_HEX)!; 
          if (newPrimaryForGroup) {
              const newPrimaryRgb = hexToRgb(newPrimaryForGroup);
              if (newPrimaryRgb) newTintColor = newPrimaryRgb;
          }
          setAppliedGroupSettings(prev => ({
              ...prev,
              [groupIdToRemoveFrom]: { ...currentSettings, tintColor: newTintColor }
          }));
          setTintColor(newTintColor); 
      }
    }
  }, [groupPrimaryColorHexes, initialGroupPrimaryColorHexes, activeColorGroupId, appliedGroupSettings, editingGroupId, stagedHexesForGroupEdit, handleToggleStagedHexForEdit]);

  const handleOverrideColor = useCallback((originalHex: string, newPickedHex: string) => {
    const originalPaletteEntry = displayPalette.find(p => p.hex === originalHex);
    const originalAlpha = originalPaletteEntry ? originalPaletteEntry.original.a : 255;
    const newRgbFromPicker = hexToRgb(newPickedHex);

    if (newRgbFromPicker) {
      setColorFinalOverrides(prev => ({
        ...prev,
        [originalHex]: { ...newRgbFromPicker, a: originalAlpha }
      }));
    }
  }, [displayPalette]);

  const handleClearColorOverride = useCallback((originalHex: string) => {
    setColorFinalOverrides(prev => {
      const { [originalHex]: _, ...rest } = prev;
      return rest;
    });
  }, []);

  const toggleQuickRecolorMode = useCallback(() => {
    setIsQuickRecolorModeActive(prevIsActive => {
      const newMode = !prevIsActive;
      if (newMode && editingGroupId) { 
        setEditingGroupId(null);
        setStagedHexesForGroupEdit(null);
      }
      if (!newMode && appliedGroupSettings[activeColorGroupId]) { 
        const currentActiveSettings = appliedGroupSettings[activeColorGroupId];
        setHueDelta(currentActiveSettings.hueDelta);
        setSaturationDelta(currentActiveSettings.saturationDelta);
        setLightnessDelta(currentActiveSettings.lightnessDelta);
        setContrastDelta(currentActiveSettings.contrastDelta);
        setAlphaDelta(currentActiveSettings.alphaDelta);
        setTintColor(currentActiveSettings.tintColor);
        setTintAmount(currentActiveSettings.tintAmount);
      } else if (newMode && activeColorGroupId !== ALL_COLORS_GROUP_ID && appliedGroupSettings[activeColorGroupId]) { 
        const activeGroupCurrentSettings = appliedGroupSettings[activeColorGroupId];
        setTintColor(activeGroupCurrentSettings.tintColor);
      }
      return newMode;
    });
  }, [activeColorGroupId, appliedGroupSettings, editingGroupId]); 

  const handleSetGroupQuickTint = useCallback((groupId: string, newTintColor: RGBColor) => {
    const newSettingsForGroup: AppliedGroupSettings = {
      hueDelta: INITIAL_HUE_DELTA,
      saturationDelta: INITIAL_SATURATION_DELTA,
      lightnessDelta: INITIAL_LIGHTNESS_DELTA,
      contrastDelta: INITIAL_CONTRAST_DELTA,
      alphaDelta: INITIAL_ALPHA_DELTA,
      tintColor: newTintColor,
      tintAmount: 100, 
    };

    setAppliedGroupSettings(prev => ({
      ...prev,
      [groupId]: newSettingsForGroup
    }));
    
    setActiveColorGroupId(groupId); 
    
    setHueDelta(newSettingsForGroup.hueDelta);
    setSaturationDelta(newSettingsForGroup.saturationDelta);
    setLightnessDelta(newSettingsForGroup.lightnessDelta);
    setContrastDelta(newSettingsForGroup.contrastDelta);
    setAlphaDelta(newSettingsForGroup.alphaDelta);
    setTintColor(newSettingsForGroup.tintColor);
    setTintAmount(newSettingsForGroup.tintAmount);

  }, []); 

  const handleResetGroupToInitial = useCallback((groupIdToReset: string) => {
    if (groupIdToReset === ALL_COLORS_GROUP_ID) return; 

    const pristineSettings = getInitialAppliedSettings(); 
    const groupInitialPrimaryHex = initialGroupPrimaryColorHexes[groupIdToReset];

    if (groupInitialPrimaryHex) {
        const primaryRgb = hexToRgb(groupInitialPrimaryHex);
        if (primaryRgb) {
            pristineSettings.tintColor = primaryRgb; 
        }
    }
    
    setAppliedGroupSettings(prev => ({
        ...prev,
        [groupIdToReset]: pristineSettings
    }));

    if (activeColorGroupId === groupIdToReset) {
        setHueDelta(pristineSettings.hueDelta);
        setSaturationDelta(pristineSettings.saturationDelta);
        setLightnessDelta(pristineSettings.lightnessDelta);
        setContrastDelta(pristineSettings.contrastDelta);
        setAlphaDelta(pristineSettings.alphaDelta);
        setTintColor(pristineSettings.tintColor);
        setTintAmount(pristineSettings.tintAmount);
    }
  }, [initialGroupPrimaryColorHexes, activeColorGroupId]);


  const currentActiveGroupObject = colorGroups.find(g => g.id === activeColorGroupId);
  const overallAppIsBusy = isLoading || isRecoloring;
  const canUseQuickRecolor = colorGroups.filter(g => g.id !== ALL_COLORS_GROUP_ID).length > 0;
  const defaultGlobalTintRGB = hexToRgb(DEFAULT_TINT_COLOR_HEX)!;

  const isSpecialModeActiveWithImage = (isPixelHopperModeActive || !!editingGroupId) && !!processedOriginalImageData;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      <main className="flex flex-col md:flex-row flex-grow overflow-hidden">
        <div className="w-full md:w-[380px] p-4 md:p-6 bg-slate-800 md:h-screen md:overflow-y-auto custom-scrollbar flex-shrink-0 flex flex-col">
          <div className="mb-4">
            <ImageUploader
              onImageUpload={(file) => processNewImageFileRef.current(file, 'device')}
              isLoading={isLoading} 
              currentFileName={originalImageFile?.name || null}
              predefinedImages={predefinedImages}
              selectedPredefinedImageUrl={selectedPredefinedImageUrl}
              onSelectPredefinedImage={setSelectedPredefinedImageUrl}
              isFetchingPredefinedImages={isFetchingPredefinedImages}
              baseCostumes={baseCostumes}
              selectedBaseCostumeUrl={selectedBaseCostumeUrl}
              onSelectBaseCostume={setSelectedBaseCostumeUrl}
              isFetchingBaseCostumes={isFetchingBaseCostumes}
            />
          </div>
          
          <div className="space-y-4 flex-grow">
            <ColorGroupControls
              newGroupName={newGroupName}
              setNewGroupName={setNewGroupName}
              selectedPaletteColorsCount={selectedPaletteColors.size}
              onCreateGroup={handleCreateColorGroup}
              onClearSelection={handleClearPaletteSelection}
              paletteExists={displayPalette.length > 0}
              isProcessing={overallAppIsBusy}
              isPixelHopperModeActive={isPixelHopperModeActive}
              togglePixelHopperMode={togglePixelHopperMode}
              pixelHopperSelectedColorsCount={pixelHopperSelectedColors.size}
              onAddHopperColorsToStaging={addHopperColorsToStaging}
              isEditingAnyGroup={!!editingGroupId}
            />
            {activeColorGroupId !== ALL_COLORS_GROUP_ID && currentActiveGroupObject && processedOriginalImageData && (
                <ActiveGroupDetails
                  activeGroup={currentActiveGroupObject}
                  displayPalette={displayPalette}
                  groupPrimaryHex={groupPrimaryColorHexes[activeColorGroupId] || initialGroupPrimaryColorHexes[activeColorGroupId] || null}
                  onSetPrimaryColor={handleSetGroupPrimaryColor}
                  currentGroupSliderValues={{ hueDelta, saturationDelta, lightnessDelta, contrastDelta, alphaDelta, tintColor, tintAmount }}
                  isProcessing={overallAppIsBusy}
                  allColorGroups={colorGroups}
                  groupPrimaryColorHexesForTintCalc={groupPrimaryColorHexes} 
                  onRemoveColorFromGroup={handleRemoveColorFromGroup} 
                  colorFinalOverrides={colorFinalOverrides}
                  onOverrideColor={handleOverrideColor}
                  onClearColorOverride={handleClearColorOverride}
                  isEditingThisGroup={editingGroupId === activeColorGroupId}
                  stagedHexesForCurrentEdit={editingGroupId === activeColorGroupId ? stagedHexesForGroupEdit : null}
                  onStartEdit={handleStartEditGroupColors}
                  onSaveEdit={handleSaveEditedGroupColors}
                  onCancelEdit={handleCancelEditGroupColors}
                  onToggleStagedColor={handleToggleStagedHexForEdit}
                  onSaveAsNewGroup={handleSaveAsNewGroup} 
                />
              )}
            <ColorPalette
              palette={displayPalette}
              selectedPaletteColors={selectedPaletteColors}
              onColorSelect={handleTogglePaletteColorSelection}
            />
          </div>
        </div>

        <div className={`flex-grow p-4 md:p-6 lg:p-10 flex flex-col items-start justify-start relative overflow-y-auto custom-scrollbar ${isSpecialModeActiveWithImage ? 'bg-white' : 'bg-slate-850'}`}>
          { !processedOriginalImageData && !isLoading && ( 
            <div className="absolute top-4 left-4 md:top-6 md:left-10 text-left z-10 pointer-events-none">
              <h1 className="text-2xl md:text-3xl font-bold text-sky-400">Pixel Art Recolor Tool</h1>
              <p className="text-slate-400 mt-1 text-sm md:text-base">Recolor your pixel art with fine-tuned controls.</p>
            </div>
          )}

          <div className="w-full flex items-start justify-start min-h-[200px] md:min-h-[300px] lg:min-h-[400px]">
             <ImageViewer
              imageDataUrl={hopperPreviewUrl || recoloredImageDataUrl}
              isLoading={isRecoloring || (isLoading && !recoloredImageDataUrl)} 
              onPixelClick={handleImagePixelClick}
              processedOriginalImageData={processedOriginalImageData}
              editingGroupActiveId={editingGroupId}
              editingGroupHexes={stagedHexesForGroupEdit}
            />
          </div>

          {processedOriginalImageData && (displayPalette.length > 0 || colorGroups.length > 0) && (
            <div className="w-full max-w-3xl mt-2 p-4 bg-slate-800 rounded-lg shadow-lg">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-4 items-end gap-x-6 gap-y-4 mb-4">
                <div>
                  <label htmlFor="active-group-select-main" className="block text-sm font-medium text-slate-300 mb-1">
                    Active Color Group
                  </label>
                  <select
                    id="active-group-select-main"
                    value={activeColorGroupId}
                    onChange={(e) => handleManualGroupChange(e.target.value)}
                    disabled={overallAppIsBusy || !!editingGroupId} 
                    className="w-full bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded-md p-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-50 custom-scrollbar"
                  >
                    <option value={ALL_COLORS_GROUP_ID}>
                       {isGroupModified(appliedGroupSettings[ALL_COLORS_GROUP_ID], undefined, defaultGlobalTintRGB) ? '*' : ''}
                       All Colors ({displayPalette.length > 0 ? 'Entire Palette' : 'N/A'})
                    </option>
                    {colorGroups.map(group => {
                       const modified = isGroupModified(
                                appliedGroupSettings[group.id],
                                initialGroupPrimaryColorHexes[group.id],
                                defaultGlobalTintRGB
                              );
                      return (
                        <option key={group.id} value={group.id}>
                          {modified ? '*' : ''}{group.name} ({group.colorHexes.size} colors)
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div>
                  <label htmlFor="copy-settings-select" className="block text-sm font-medium text-slate-300 mb-1">
                    Copy Settings From:
                  </label>
                  <select
                    id="copy-settings-select"
                    value="" 
                    onChange={(e) => {
                      if (e.target.value) handleCopySettingsFromGroup(e.target.value);
                      e.target.value = ""; 
                    }}
                    disabled={overallAppIsBusy || !!editingGroupId || colorGroups.filter(g => g.id !== activeColorGroupId && g.id !== ALL_COLORS_GROUP_ID).length === 0}
                    className="w-full bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded-md p-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-50 custom-scrollbar"
                  >
                    <option value="">-- Select Group --</option>
                    {colorGroups
                      .filter(group => group.id !== activeColorGroupId && group.id !== ALL_COLORS_GROUP_ID)
                      .map(group => (
                        <option key={group.id} value={group.id}>
                          {group.name}
                        </option>
                      ))}
                  </select>
                </div>
                
                <div>
                  <label htmlFor="quick-recolor-toggle" className="block text-sm font-medium text-slate-300 mb-1">
                    Quick Recolor
                  </label>
                  <button
                    id="quick-recolor-toggle"
                    onClick={toggleQuickRecolorMode}
                    disabled={overallAppIsBusy || !canUseQuickRecolor || !!editingGroupId}
                    className={`w-full px-3 py-2 text-sm rounded-md transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-opacity-50 disabled:opacity-50
                      ${isQuickRecolorModeActive ? 'bg-teal-500 hover:bg-teal-600 text-white focus:ring-teal-400' : 'bg-slate-600 hover:bg-slate-500 text-slate-200 focus:ring-slate-400'}`}
                    aria-pressed={isQuickRecolorModeActive}
                    title={isQuickRecolorModeActive ? "Disable Quick Recolor Mode" : "Enable Quick Recolor Mode"}
                  >
                    {isQuickRecolorModeActive ? 'Mode: ON' : 'Mode: OFF'}
                  </button>
                </div>

                {(hopperPreviewUrl || recoloredImageDataUrl) && originalImageFile && (
                  <div className="lg:justify-self-end flex flex-col sm:flex-row gap-2"> 
                    {/* Option 1: Download Locally */}
                    <button
                        onClick={handleSaveImage}
                        disabled={overallAppIsBusy}
                        className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
                    >
                        Download
                    </button>
                    
                    {/* Option 2: Open Discord Modal */}
                    <button
                        onClick={() => setIsSubmitModalOpen(true)}
                        disabled={overallAppIsBusy}
                        className="flex-1 bg-[#5865F2] hover:bg-[#4752C4] text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50 transition-colors duration-150 disabled:opacity-50"
                    >
                        Submit to Vault
                    </button>
                  </div>
                )}
              </div>

               {processedOriginalImageData && (
                 <div className="mt-2">
                    {isQuickRecolorModeActive && !editingGroupId ? (
                        <QuickRecolorControls
                            colorGroups={colorGroups.filter(g => g.id !== ALL_COLORS_GROUP_ID)}
                            appliedGroupSettings={appliedGroupSettings}
                            onSetGroupQuickTint={handleSetGroupQuickTint}
                            isProcessing={overallAppIsBusy}
                            initialGroupPrimaryColorHexes={initialGroupPrimaryColorHexes}
                            displayPalette={displayPalette}
                            onResetGroupToInitial={handleResetGroupToInitial}
                            isGroupModifiedCheck={(settings, initialPrimaryHex) => 
                                isGroupModified(settings, initialPrimaryHex, defaultGlobalTintRGB)
                            }
                        />
                    ) : (
                        <ColorControls
                        hueDelta={hueDelta} setHueDelta={setHueDeltaWrapped}
                        saturationDelta={saturationDelta} setSaturationDelta={setSaturationDeltaWrapped}
                        lightnessDelta={lightnessDelta} setLightnessDelta={setLightnessDeltaWrapped}
                        contrastDelta={contrastDelta} setContrastDelta={setContrastDeltaWrapped}
                        alphaDelta={alphaDelta} setAlphaDelta={setAlphaDeltaWrapped} 
                        tintColor={tintColor} setTintColor={setTintColorWrapped}
                        tintAmount={tintAmount} setTintAmount={setTintAmountWrapped}
                        onResetControls={() => resetSlidersAndTint(activeColorGroupId)}
                        isProcessing={overallAppIsBusy || !!editingGroupId} 
                        />
                    )}
                 </div>
                )}
            </div>
          )}
        </div>
      </main>

      {overallAppIsBusy && (
        <div className="fixed bottom-4 right-4 bg-blue-600 text-white p-3 rounded-lg shadow-xl flex items-center z-50">
          {SPINNER_SVG}
          <span className="ml-2">
            {isLoading && !processedOriginalImageData && !originalImageFile ? "Loading image..." : 
             isLoading && originalImageFile && !processedOriginalImageData ? "Processing image..." : 
             isRecoloring ? "Recoloring..." :
             isLoading ? "Loading..." : "" 
            }
          </span>
        </div>
      )}
      {/* --- NEW: Submission Modal --- */}
      {isSubmitModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-[100] p-4">
          <div className="bg-slate-800 rounded-lg shadow-2xl p-6 w-full max-w-md border border-slate-600">
            <h2 className="text-xl font-bold text-white mb-4">Submit to Color Vault</h2>
            <p className="text-slate-400 text-sm mb-4">
              Upload your creation directly to the Discord queue.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Costume Name</label>
                <input
                  type="text"
                  value={costumeName}
                  onChange={(e) => setCostumeName(e.target.value)}
                  placeholder="e.g. Fire Mario"
                  className="w-full bg-slate-700 border border-slate-600 text-white rounded p-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Discord Username</label>
                <input
                  type="text"
                  value={discordUsername}
                  onChange={(e) => setDiscordUsername(e.target.value)}
                  placeholder="e.g. User#1234"
                  className="w-full bg-slate-700 border border-slate-600 text-white rounded p-2 focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setIsSubmitModalOpen(false)}
                disabled={isSendingToDiscord}
                className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitToDiscord}
                disabled={isSendingToDiscord}
                className="px-4 py-2 bg-[#5865F2] hover:bg-[#4752C4] text-white rounded font-medium flex items-center transition-colors disabled:opacity-50"
              >
                {isSendingToDiscord ? (
                  <>
                    <span className="mr-2 animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                    Sending...
                  </>
                ) : (
                  'Send'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
       <footer className="text-center py-4 border-t border-slate-700 text-slate-500 flex-shrink-0 bg-slate-900">
        <p className="text-sm">Crafted with React, TypeScript, and Tailwind CSS.</p>
      </footer>
    </div>
  );
};

export default App;
