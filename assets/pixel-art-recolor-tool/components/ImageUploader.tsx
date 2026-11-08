
import React, { ChangeEvent, useRef } from 'react';
import { SPINNER_SVG } from '../constants';
import { PredefinedImage } from '../types';

interface ImageUploaderProps {
  onImageUpload: (file: File) => void;
  isLoading: boolean;
  currentFileName: string | null;
  
  predefinedImages: PredefinedImage[];
  selectedPredefinedImageUrl: string;
  onSelectPredefinedImage: (url: string) => void;
  isFetchingPredefinedImages: boolean;

  baseCostumes: PredefinedImage[];
  selectedBaseCostumeUrl: string;
  onSelectBaseCostume: (url: string) => void;
  isFetchingBaseCostumes: boolean;
}


const ImageUploader: React.FC<ImageUploaderProps> = (props) => {
  const { 
    onImageUpload, 
    isLoading, 
    currentFileName,
    predefinedImages,
    selectedPredefinedImageUrl,
    onSelectPredefinedImage,
    isFetchingPredefinedImages,
    baseCostumes,
    selectedBaseCostumeUrl,
    onSelectBaseCostume,
    isFetchingBaseCostumes,
  } = props;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onImageUpload(file);
    }
    if (event.target) {
      event.target.value = ""; // Reset file input
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handlePredefinedImageChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onSelectPredefinedImage(event.target.value);
  };

  const handleBaseCostumeChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onSelectBaseCostume(event.target.value);
  };

  return (
    <div className="p-4 border border-slate-700 rounded-lg bg-slate-800 shadow-lg">
      <h3 className="text-lg font-semibold mb-3 text-sky-400">Upload Pixel Art</h3>
      <input
        type="file"
        accept="image/png, image/jpeg, image/gif"
        onChange={handleFileChange}
        className="hidden"
        ref={fileInputRef}
        disabled={isLoading}
      />
      <button
        onClick={handleButtonClick}
        disabled={isLoading}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors duration-150 flex items-center justify-center disabled:opacity-50"
      >
        {isLoading && !currentFileName ? (
          <>
            {SPINNER_SVG}
            <span className="ml-2">Processing...</span>
          </>
        ) : currentFileName && isLoading ? (
          <>
            {SPINNER_SVG}
            <span className="ml-2">Loading New...</span>
          </>
        )
        : (
          currentFileName ? "Choose Different Image" : "Choose Image from Device"
        )}
      </button>
      
      <div className="mt-4 pt-4 border-t border-slate-700/50">
        <label htmlFor="predefined-image-select" className="block text-sm font-medium text-slate-300 mb-1">
          Original color costumes:
        </label>
        {isFetchingPredefinedImages && (
          <div className="flex items-center text-sm text-slate-400">
            {SPINNER_SVG}
            <span className="ml-2">Fetching original costumes...</span>
          </div>
        )}
        {!isFetchingPredefinedImages && predefinedImages.length === 0 && (
          <p className="text-sm text-slate-500">Could not load original costumes.</p>
        )}
        {!isFetchingPredefinedImages && predefinedImages.length > 0 && (
          <select
            id="predefined-image-select"
            value={selectedPredefinedImageUrl}
            onChange={handlePredefinedImageChange}
            disabled={isLoading || isFetchingPredefinedImages}
            className="w-full bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded-md p-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-50 custom-scrollbar"
          >
            <option value="">-- Select an original costume --</option>
            {predefinedImages.map((image) => (
              <option key={image.download_url} value={image.download_url}>
                {image.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-700/50">
        <label htmlFor="base-costume-select" className="block text-sm font-medium text-slate-300 mb-1">
          Base costumes:
        </label>
        {isFetchingBaseCostumes && (
          <div className="flex items-center text-sm text-slate-400">
            {SPINNER_SVG}
            <span className="ml-2">Fetching base costumes...</span>
          </div>
        )}
        {!isFetchingBaseCostumes && baseCostumes.length === 0 && (
          <p className="text-sm text-slate-500">Could not load base costumes.</p>
        )}
        {!isFetchingBaseCostumes && baseCostumes.length > 0 && (
          <select
            id="base-costume-select"
            value={selectedBaseCostumeUrl}
            onChange={handleBaseCostumeChange}
            disabled={isLoading || isFetchingBaseCostumes}
            className="w-full bg-slate-700 border border-slate-600 text-slate-200 text-sm rounded-md p-2 focus:ring-sky-500 focus:border-sky-500 disabled:opacity-50 custom-scrollbar"
          >
            <option value="">-- Select a base costume --</option>
            {baseCostumes.map((image) => (
              <option key={image.download_url} value={image.download_url}>
                {image.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {currentFileName && (
        <p className="text-sm text-slate-400 mt-3 pt-3 border-t border-slate-700/50 truncate" title={currentFileName}>
          Current: {currentFileName}
        </p>
      )}
       {!currentFileName && !isLoading && (
        <p className="text-sm text-slate-500 mt-2">No image selected.</p>
      )}
    </div>
  );
};

export default ImageUploader;
