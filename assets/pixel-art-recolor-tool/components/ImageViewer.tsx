


import React, { useRef, useState, useEffect } from 'react';
import { RGBColor } from '../types';
import { rgbToHex, imageDataToDataUrl } from '../services/colorService';

interface ImageViewerProps {
  imageDataUrl: string | null;
  isLoading?: boolean;
  onPixelClick?: (originalX: number, originalY: number) => void;
  processedOriginalImageData?: ImageData | null;
  editingGroupActiveId?: string | null;
  editingGroupHexes?: Set<string> | null;
}

const LOUPE_SIZE_PX = 100; // Square size for the loupe
const LOUPE_ZOOM_LEVEL = 10; // Each original pixel will be 10x10 in the loupe
const LOUPE_BORDER_COLOR = 'rgba(50, 50, 50, 0.9)'; // Darker border for the loupe box
const LOUPE_BORDER_WIDTH_PX = 2;
const LOUPE_OFFSET_X_FROM_CURSOR_PX = 20;
const LOUPE_OFFSET_Y_FROM_CURSOR_PX = -LOUPE_SIZE_PX - 20 - LOUPE_BORDER_WIDTH_PX * 2; // Adjust for border

const LOUPE_GRID_COLOR = 'rgba(150, 150, 150, 0.3)';
const LOUPE_CENTER_INDICATOR_BORDER_COLOR = 'rgba(255, 0, 0, 0.9)';
const LOUPE_TEXT_BG_COLOR = 'rgba(0, 0, 0, 0.75)';
const LOUPE_TEXT_COLOR = 'white';
const LOUPE_TEXT_FONT = '10px monospace';
const LOUPE_TEXT_AREA_HEIGHT = 22;


const ImageViewer: React.FC<ImageViewerProps> = ({
    imageDataUrl,
    isLoading,
    onPixelClick,
    processedOriginalImageData,
    editingGroupActiveId,
    editingGroupHexes
}) => {
  const imgRef = useRef<HTMLImageElement>(null);
  const imageWrapperRef = useRef<HTMLDivElement>(null);
  const internalCanvasRef = useRef<HTMLCanvasElement | null>(null); // For edit mode previews
  const loupeCanvasRef = useRef<HTMLCanvasElement | null>(null); // For the loupe itself
  const offscreenLoupeReadCanvasRef = useRef<HTMLCanvasElement | null>(null); // For reading pixel color for loupe

  const [isMouseOverWrapper, setIsMouseOverWrapper] = useState<boolean>(false);
  const [loupeTargetPixel, setLoupeTargetPixel] = useState<{ naturalX: number; naturalY: number } | null>(null);
  const [loupeDivPosition, setLoupeDivPosition] = useState<{ x: number; y: number } | null>(null);
  const [loupePixelColor, setLoupePixelColor] = useState<RGBColor | null>(null);

  const [effectiveImageDataUrl, setEffectiveImageDataUrl] = useState<string | null>(null);

  // FIX: Moved currentDisplayUrl declaration here, before its use in useEffect dependency array.
  const currentDisplayUrl = effectiveImageDataUrl || imageDataUrl;

  useEffect(() => {
    if (!imageDataUrl) {
      setEffectiveImageDataUrl(null);
      return;
    }

    if (!editingGroupActiveId || !editingGroupHexes || !processedOriginalImageData || !imgRef.current) {
      setEffectiveImageDataUrl(imageDataUrl);
      return;
    }

    const baseImg = new Image();
    baseImg.onload = () => {
      const canvas = internalCanvasRef.current || document.createElement('canvas');
      canvas.width = baseImg.naturalWidth;
      canvas.height = baseImg.naturalHeight;

      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) {
        setEffectiveImageDataUrl(imageDataUrl);
        return;
      }
      ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height);

      let currentViewImageData: globalThis.ImageData;
      try {
        currentViewImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      } catch (e) {
        console.error("Error getting image data from canvas for edit preview:", e);
        setEffectiveImageDataUrl(imageDataUrl);
        return;
      }

      const newPreviewImageData = new globalThis.ImageData(new Uint8ClampedArray(currentViewImageData.data), canvas.width, canvas.height);
      const originalImgData = processedOriginalImageData.data;
      const originalWidth = processedOriginalImageData.width;
      const originalHeight = processedOriginalImageData.height;

      if (canvas.width !== originalWidth || canvas.height !== originalHeight) {
        console.warn("ImageViewer: Mismatched dimensions between current view and original image data for edit mode. Alpha blending might be inaccurate.");
        setEffectiveImageDataUrl(imageDataUrl);
        return;
      }

      for (let i = 0; i < originalImgData.length; i += 4) {
        const r = originalImgData[i];
        const g = originalImgData[i + 1];
        const b = originalImgData[i + 2];
        const a = originalImgData[i + 3];
        const originalHex = rgbToHex({ r, g, b, a });

        if (a > 0 && !editingGroupHexes.has(originalHex)) {
          newPreviewImageData.data[i + 3] = Math.round(currentViewImageData.data[i + 3] * 0.1);
        }
      }
      setEffectiveImageDataUrl(imageDataToDataUrl(newPreviewImageData));
    };
    baseImg.onerror = () => {
      setEffectiveImageDataUrl(imageDataUrl);
    };
    baseImg.src = imageDataUrl;

  }, [imageDataUrl, editingGroupActiveId, editingGroupHexes, processedOriginalImageData]);

  // Loupe Drawing Effect
  useEffect(() => {
    if (!isMouseOverWrapper || !loupeTargetPixel || !loupeCanvasRef.current || !imgRef.current || !imgRef.current.complete || imgRef.current.naturalWidth === 0 || isLoading) {
      setLoupePixelColor(null);
      return;
    }

    const loupeCtx = loupeCanvasRef.current.getContext('2d');
    if (!loupeCtx) return;

    // --- Setup Offscreen Canvas for Color Picking ---
    const offscreenCanvas = offscreenLoupeReadCanvasRef.current || document.createElement('canvas');
    if (!offscreenLoupeReadCanvasRef.current) { // only assign if newly created
        // offscreenLoupeReadCanvasRef.current = offscreenCanvas; // This would be problematic if called every time. Better to ensure it's in JSX.
    }
    const mainImage = imgRef.current;
    if (offscreenCanvas.width !== mainImage.naturalWidth || offscreenCanvas.height !== mainImage.naturalHeight) {
        offscreenCanvas.width = mainImage.naturalWidth;
        offscreenCanvas.height = mainImage.naturalHeight;
    }
    const offscreenCtx = offscreenCanvas.getContext('2d', { willReadFrequently: true });
    if (!offscreenCtx) return;
    
    offscreenCtx.clearRect(0,0, offscreenCanvas.width, offscreenCanvas.height); // Clear before drawing
    offscreenCtx.drawImage(mainImage, 0, 0, mainImage.naturalWidth, mainImage.naturalHeight);

    // Get color of the target pixel from the *currently displayed* image
    try {
        const pixelData = offscreenCtx.getImageData(loupeTargetPixel.naturalX, loupeTargetPixel.naturalY, 1, 1).data;
        setLoupePixelColor({ r: pixelData[0], g: pixelData[1], b: pixelData[2], a: pixelData[3] });
    } catch (e) {
        // console.warn("Could not get pixel data for loupe, possibly due to cross-origin or image not fully ready.", e);
        setLoupePixelColor(null); // Reset if error
    }


    // --- Draw Magnified Image onto Loupe Canvas ---
    loupeCtx.imageSmoothingEnabled = false;
    // @ts-ignore
    loupeCtx.mozImageSmoothingEnabled = false;
    // @ts-ignore
    loupeCtx.webkitImageSmoothingEnabled = false;
    // @ts-ignore
    loupeCtx.msImageSmoothingEnabled = false;

    loupeCtx.clearRect(0, 0, LOUPE_SIZE_PX, LOUPE_SIZE_PX);

    const numPixelsPerDim = LOUPE_SIZE_PX / LOUPE_ZOOM_LEVEL; // e.g., 100px / 10x zoom = 10 pixels
    const halfNumPixelsFloored = Math.floor(numPixelsPerDim / 2);

    const sx = loupeTargetPixel.naturalX - halfNumPixelsFloored;
    const sy = loupeTargetPixel.naturalY - halfNumPixelsFloored;
    const sWidth = numPixelsPerDim;
    const sHeight = numPixelsPerDim;

    loupeCtx.drawImage(
      mainImage,
      sx, sy, sWidth, sHeight, // Source rectangle in original image
      0, 0, LOUPE_SIZE_PX, LOUPE_SIZE_PX // Destination rectangle in loupe canvas
    );

    // --- Draw Grid ---
    loupeCtx.strokeStyle = LOUPE_GRID_COLOR;
    loupeCtx.lineWidth = 1;
    for (let i = 0; i <= numPixelsPerDim; i++) {
      const pos = i * LOUPE_ZOOM_LEVEL;
      loupeCtx.beginPath();
      loupeCtx.moveTo(pos + 0.5, 0);
      loupeCtx.lineTo(pos + 0.5, LOUPE_SIZE_PX);
      loupeCtx.stroke();
      loupeCtx.beginPath();
      loupeCtx.moveTo(0, pos + 0.5);
      loupeCtx.lineTo(LOUPE_SIZE_PX, pos + 0.5);
      loupeCtx.stroke();
    }

    // --- Highlight Central Pixel ---
    const centralCellCanvasX = halfNumPixelsFloored * LOUPE_ZOOM_LEVEL;
    const centralCellCanvasY = halfNumPixelsFloored * LOUPE_ZOOM_LEVEL;
    loupeCtx.strokeStyle = LOUPE_CENTER_INDICATOR_BORDER_COLOR;
    loupeCtx.lineWidth = 2; // Thicker border for center
    loupeCtx.strokeRect(
      centralCellCanvasX + 1, // Offset by half line width for crispness inside cell
      centralCellCanvasY + 1,
      LOUPE_ZOOM_LEVEL - 2, // Adjust size to be inside cell lines
      LOUPE_ZOOM_LEVEL - 2
    );

  }, [isMouseOverWrapper, loupeTargetPixel, imageDataUrl, currentDisplayUrl, isLoading]);

  // Effect for drawing text, depends on loupePixelColor
  useEffect(()=> {
    if (!loupeCanvasRef.current || !loupePixelColor || !isMouseOverWrapper) return;
    const loupeCtx = loupeCanvasRef.current.getContext('2d');
    if (!loupeCtx) return;

     // --- Draw Color Info Text ---
    const hex = rgbToHex(loupePixelColor);
    const rgbStr = `R:${loupePixelColor.r} G:${loupePixelColor.g} B:${loupePixelColor.b} A:${loupePixelColor.a}`;

    loupeCtx.fillStyle = LOUPE_TEXT_BG_COLOR;
    loupeCtx.fillRect(0, LOUPE_SIZE_PX - LOUPE_TEXT_AREA_HEIGHT, LOUPE_SIZE_PX, LOUPE_TEXT_AREA_HEIGHT);

    loupeCtx.fillStyle = LOUPE_TEXT_COLOR;
    loupeCtx.font = LOUPE_TEXT_FONT;
    loupeCtx.textAlign = 'center';
    loupeCtx.textBaseline = 'middle';
    loupeCtx.fillText(hex.toUpperCase(), LOUPE_SIZE_PX / 2, LOUPE_SIZE_PX - LOUPE_TEXT_AREA_HEIGHT + 7);
    loupeCtx.fillText(rgbStr, LOUPE_SIZE_PX / 2, LOUPE_SIZE_PX - LOUPE_TEXT_AREA_HEIGHT + 16);


  }, [loupePixelColor, isMouseOverWrapper]);


  const handleClick = (event: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current || !onPixelClick || (!imageDataUrl && !effectiveImageDataUrl)) return;

    const imgElement = imgRef.current;
    const rect = imgElement.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    const { naturalWidth, naturalHeight } = imgElement;
    if (naturalWidth === 0 || naturalHeight === 0) return;

    const displayWidth = imgElement.offsetWidth;
    const displayHeight = imgElement.offsetHeight;
    let visibleImageActualWidth = displayWidth, visibleImageActualHeight = displayHeight;
    let imgContentOffsetX = 0, imgContentOffsetY = 0;
    const naturalAspectRatio = naturalWidth / naturalHeight;
    const displayAspectRatio = displayWidth / displayHeight;

    if (naturalAspectRatio > displayAspectRatio) {
      visibleImageActualHeight = displayWidth / naturalAspectRatio;
      imgContentOffsetY = (displayHeight - visibleImageActualHeight) / 2;
    } else {
      visibleImageActualWidth = displayHeight * naturalAspectRatio;
      imgContentOffsetX = (displayWidth - visibleImageActualWidth) / 2;
    }

    const contentClickX = clickX - imgContentOffsetX;
    const contentClickY = clickY - imgContentOffsetY;

    if (contentClickX < 0 || contentClickX >= visibleImageActualWidth || contentClickY < 0 || contentClickY >= visibleImageActualHeight) return;

    const originalX = Math.floor((contentClickX / visibleImageActualWidth) * naturalWidth);
    const originalY = Math.floor((contentClickY / visibleImageActualHeight) * naturalHeight);
    onPixelClick(originalX, originalY);
  };

  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!imgRef.current || !imageWrapperRef.current || (!imageDataUrl && !effectiveImageDataUrl) || isLoading) {
      setLoupeTargetPixel(null);
      setLoupeDivPosition(null);
      return;
    }

    const wrapperRect = imageWrapperRef.current.getBoundingClientRect();
    const mouseXInWrapper = event.clientX - wrapperRect.left;
    const mouseYInWrapper = event.clientY - wrapperRect.top;

    let newLoupeX = mouseXInWrapper + LOUPE_OFFSET_X_FROM_CURSOR_PX;
    let newLoupeY = mouseYInWrapper + LOUPE_OFFSET_Y_FROM_CURSOR_PX;

    newLoupeX = Math.max(0, Math.min(newLoupeX, wrapperRect.width - LOUPE_SIZE_PX - LOUPE_BORDER_WIDTH_PX * 2));
    newLoupeY = Math.max(0, Math.min(newLoupeY, wrapperRect.height - LOUPE_SIZE_PX - LOUPE_BORDER_WIDTH_PX * 2 - LOUPE_TEXT_AREA_HEIGHT));


    setLoupeDivPosition({ x: newLoupeX, y: newLoupeY });

    const imgElement = imgRef.current;
    const imgRect = imgElement.getBoundingClientRect();
    const mouseXRelToImgTag = event.clientX - imgRect.left;
    const mouseYRelToImgTag = event.clientY - imgRect.top;

    const { naturalWidth, naturalHeight } = imgElement;
    if (naturalWidth === 0 || naturalHeight === 0) {
      setLoupeTargetPixel(null); return;
    }

    const displayWidth = imgElement.offsetWidth, displayHeight = imgElement.offsetHeight;
    let visibleImageActualWidth = displayWidth, visibleImageActualHeight = displayHeight;
    let imgContentOffsetX = 0, imgContentOffsetY = 0;
    const naturalAspectRatio = naturalWidth / naturalHeight;
    const displayAspectRatio = displayWidth / displayHeight;

    if (naturalAspectRatio > displayAspectRatio) {
        visibleImageActualHeight = displayWidth / naturalAspectRatio;
        imgContentOffsetY = (displayHeight - visibleImageActualHeight) / 2;
    } else {
        visibleImageActualWidth = displayHeight * naturalAspectRatio;
        imgContentOffsetX = (displayWidth - visibleImageActualWidth) / 2;
    }

    const contentMouseX = mouseXRelToImgTag - imgContentOffsetX;
    const contentMouseY = mouseYRelToImgTag - imgContentOffsetY;

    if (contentMouseX < 0 || contentMouseX >= visibleImageActualWidth || contentMouseY < 0 || contentMouseY >= visibleImageActualHeight) {
      setLoupeTargetPixel(null);
      return;
    }

    const naturalX = Math.min(naturalWidth -1, Math.max(0, Math.floor((contentMouseX / visibleImageActualWidth) * naturalWidth)));
    const naturalY = Math.min(naturalHeight -1, Math.max(0, Math.floor((contentMouseY / visibleImageActualHeight) * naturalHeight)));
    setLoupeTargetPixel({ naturalX, naturalY });
  };

  const handleMouseEnterWrapper = () => {
    if ((imageDataUrl || effectiveImageDataUrl) && !isLoading) {
      setIsMouseOverWrapper(true);
    }
  };
  const handleMouseLeaveWrapper = () => {
    setIsMouseOverWrapper(false);
    setLoupeTargetPixel(null);
    setLoupeDivPosition(null);
    setLoupePixelColor(null);
  };


  return (
    <div
      ref={imageWrapperRef}
      className="relative w-full h-full flex items-center justify-center"
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnterWrapper}
      onMouseLeave={handleMouseLeaveWrapper}
    >
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-800/50 z-10">
          {/* Spinner could go here */}
        </div>
      )}
      {currentDisplayUrl ? (
        <img
          ref={imgRef}
          src={currentDisplayUrl}
          alt="Pixel art preview"
          onClick={handleClick}
          className={`max-w-full max-h-full object-contain ${onPixelClick ? 'cursor-crosshair' : 'cursor-default'}`}
          style={{
            imageRendering: 'pixelated',
            // @ts-ignore
            MsImageRendering: 'pixelated',
            // @ts-ignore
            MozImageRendering: 'pixelated'
          }}
          draggable={false}
          crossOrigin="anonymous"
          onLoad={() => { // Force redraw loupe on image load, e.g. when URL changes
            if (loupeTargetPixel && imgRef.current && imgRef.current.complete && imgRef.current.naturalWidth > 0) {
                 // Trigger loupe update logic, e.g. by nudging a dependency or calling a draw function directly
                 // For now, the existing useEffect for loupe drawing should re-run if `currentDisplayUrl` is a dep indirectly (via imageDataUrl)
            }
          }}
        />
      ) : (
        <div className="w-full h-64 bg-slate-700/50 rounded-lg flex items-center justify-center text-slate-400">
          <p>Upload an image to begin.</p>
        </div>
      )}
      
      {/* Hidden canvases for processing */}
      <canvas ref={internalCanvasRef} style={{ display: 'none' }}></canvas>
      <canvas ref={offscreenLoupeReadCanvasRef} style={{ display: 'none' }}></canvas>


      {isMouseOverWrapper && loupeTargetPixel && loupeDivPosition && currentDisplayUrl && !isLoading && imgRef.current && (
        <div
          style={{
            position: 'absolute',
            left: `${loupeDivPosition.x}px`,
            top: `${loupeDivPosition.y}px`,
            width: `${LOUPE_SIZE_PX}px`,
            height: `${LOUPE_SIZE_PX}px`,
            border: `${LOUPE_BORDER_WIDTH_PX}px solid ${LOUPE_BORDER_COLOR}`,
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            pointerEvents: 'none',
            zIndex: 20,
            backgroundColor: '#1e293b', // bg-slate-800 as fallback
            overflow: 'hidden', // Ensure canvas doesn't spill
          }}
          aria-hidden="true"
        >
          <canvas
            ref={loupeCanvasRef}
            width={LOUPE_SIZE_PX}
            height={LOUPE_SIZE_PX}
            style={{ imageRendering: 'pixelated' }}
          />
        </div>
      )}
    </div>
  );
};

export default ImageViewer;