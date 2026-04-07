"use client";

import { Creative, getImageUrl, downloadCreative } from "./CreativeCard";

type ImageOverlayProps = {
  creative: Creative | null;
  onClose: () => void;
};

export default function ImageOverlay({ creative, onClose }: ImageOverlayProps) {
  if (!creative) return null;

  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return null;

  const pixelSizes: Record<string, string> = {
    "4:5": "1440 × 1800 px",
    "9:16": "1440 × 2560 px",
    "1:1": "1440 × 1440 px",
    "16:9": "2560 × 1440 px",
  };
  const pixelSize = pixelSizes[creative.format] || creative.format;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-md flex items-center justify-center p-6"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 text-white/60 hover:text-white hover:bg-white/20 transition-colors text-xl"
        onClick={onClose}
      >
        ×
      </button>
      <div className="flex gap-6 max-w-[90vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
        <img
          src={imageUrl}
          alt={creative.sub_angle}
          className="max-h-[85vh] object-contain rounded-xl shadow-2xl"
        />
        <div className="hidden lg:flex flex-col justify-end min-w-[220px] max-w-[280px] pb-4">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 text-white">
            <p className="text-xs text-white/50 uppercase tracking-wide font-semibold">{creative.angle}</p>
            <p className="font-semibold mt-1">{creative.sub_angle}</p>
            {creative.hook_text && (
              <p className="text-sm text-white/70 mt-2 italic">&ldquo;{creative.hook_text}&rdquo;</p>
            )}
            <div className="mt-3 pt-3 border-t border-white/10">
              <p className="text-xs font-mono text-white/80 mb-2">{pixelSize}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-white/50">
              <span>{creative.format}</span>
              <span>·</span>
              <span>{creative.creative_style === "off_brand" ? "Off-Brand" : "On-Brand"}</span>
              <span>·</span>
              <span>{creative.creative_type === "lifestyle" ? "Lifestyle" : "Product"}</span>
              {creative.season && creative.season !== "evergreen" && (
                <>
                  <span>·</span>
                  <span className="text-white/70 capitalize">{creative.season}</span>
                </>
              )}
            </div>
            {imageUrl && (
              <button
                onClick={() => downloadCreative(creative)}
                className="mt-3 flex items-center justify-center gap-1.5 text-sm font-semibold bg-white text-black py-2 rounded-lg hover:bg-white/90 transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
                  <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
                </svg>
                Download
              </button>
            )}
          </div>
        </div>
      </div>
      {/* Mobile bottom info */}
      <div className="lg:hidden absolute bottom-6 left-6 right-6 text-center text-white">
        <p className="font-semibold">{creative.sub_angle}</p>
        <p className="text-sm text-white/60">
          {creative.angle} — {creative.format}
        </p>
      </div>
    </div>
  );
}
