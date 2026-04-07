"use client";

import { Creative, getImageUrl, downloadCreative } from "./CreativeCard";
import { PRODUCT_LABELS } from "@/lib/constants";

type ImageOverlayProps = {
  creative: Creative | null;
  onClose: () => void;
};

export default function ImageOverlay({ creative, onClose }: ImageOverlayProps) {
  if (!creative) return null;

  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return null;

  const product = PRODUCT_LABELS[creative.product_category || ""] || creative.product_category;
  const env = creative.environment_style || creative.environment;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-md flex items-center justify-center p-6"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 text-white/60 hover:text-white hover:bg-white/20 transition-colors text-xl"
        onClick={onClose}
      >
        x
      </button>
      <div className="flex gap-6 max-w-[90vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
        <img
          src={imageUrl}
          alt={product || "Lifestyle"}
          className="max-h-[85vh] object-contain rounded-xl shadow-2xl"
        />
        <div className="hidden lg:flex flex-col justify-end min-w-[240px] max-w-[300px] pb-4">
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-5 text-white">
            {product && (
              <p className="text-sm font-bold text-primary-light">{product}</p>
            )}
            {env && (
              <p className="text-white/80 text-sm mt-1 capitalize">{env.replace(/_/g, " ")}</p>
            )}

            {/* Camera Settings */}
            {(creative.camera_angle || creative.shot_size || creative.lens) && (
              <div className="mt-3 pt-3 border-t border-white/10 space-y-1">
                {creative.shot_size && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">Shot</span>
                    <span className="text-white/80">{creative.shot_size}</span>
                  </div>
                )}
                {creative.camera_angle && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">Angle</span>
                    <span className="text-white/80">{creative.camera_angle}</span>
                  </div>
                )}
                {creative.character_angle && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">Position</span>
                    <span className="text-white/80">{creative.character_angle}</span>
                  </div>
                )}
                {creative.lens && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">Lens</span>
                    <span className="text-white/80">{creative.lens}</span>
                  </div>
                )}
                {creative.depth_of_field && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">DoF</span>
                    <span className="text-white/80">{creative.depth_of_field}</span>
                  </div>
                )}
              </div>
            )}

            {/* Meta */}
            <div className="mt-3 pt-3 border-t border-white/10">
              <div className="flex flex-wrap items-center gap-2 text-xs text-white/50">
                <span>{creative.format}</span>
                {creative.color_variant && (
                  <>
                    <span>·</span>
                    <span className="text-accent capitalize">{creative.color_variant}</span>
                  </>
                )}
                {creative.creative_type && (
                  <>
                    <span>·</span>
                    <span className="capitalize">{creative.creative_type.replace(/_/g, " ")}</span>
                  </>
                )}
              </div>
              <p className="text-[10px] text-white/30 mt-1">
                {new Date(creative.created_at).toLocaleString("de-DE")}
              </p>
            </div>

            {imageUrl && (
              <button
                onClick={() => downloadCreative(creative)}
                className="mt-3 w-full flex items-center justify-center gap-1.5 text-sm font-semibold bg-primary text-white py-2 rounded-lg hover:bg-primary-light transition-colors"
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
      {/* Mobile */}
      <div className="lg:hidden absolute bottom-6 left-6 right-6 text-center text-white">
        <p className="font-semibold">{product || "Lifestyle"}</p>
        <p className="text-sm text-white/60">
          {env && <span className="capitalize">{env.replace(/_/g, " ")} — </span>}
          {creative.format}
        </p>
      </div>
    </div>
  );
}
