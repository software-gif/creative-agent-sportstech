"use client";

import { useState } from "react";
import { Creative, getImageUrl, downloadCreative, resolveProductHandle } from "./CreativeCard";
import { PRODUCT_LABELS } from "@/lib/constants";

type ImageOverlayProps = {
  creative: Creative | null;
  variants?: Creative[];
  onClose: () => void;
  onSelectVariant?: (creative: Creative) => void;
};

export default function ImageOverlay({ creative, variants = [], onClose, onSelectVariant }: ImageOverlayProps) {
  const [copied, setCopied] = useState<"path" | "id" | null>(null);

  if (!creative) return null;

  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return null;

  const productHandle = resolveProductHandle(creative);
  const product = PRODUCT_LABELS[productHandle] || productHandle;
  const env = creative.environment_style || creative.environment;

  const multishots = variants.filter((v) => v.creative_type === "multishot");
  const colorVariants = variants.filter((v) => v.creative_type === "color_variant");

  async function copy(value: string, kind: "path" | "id") {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      // Clipboard API unavailable — fall back to prompt so the user can
      // still grab the value manually instead of getting no feedback.
      window.prompt("Copy:", value);
    }
  }

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
      <div className="flex gap-6 max-w-[95vw] max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
        <img
          src={imageUrl}
          alt={product || "Lifestyle"}
          className="max-h-[85vh] object-contain rounded-xl shadow-2xl"
        />
        <div className="hidden lg:flex flex-col min-w-[360px] max-w-[440px] max-h-[85vh] overflow-y-auto space-y-3">
          {/* Variants first — bigger grid on top next to the image */}
          <VariantGroup
            label="Multishots"
            items={multishots}
            activeId={creative.id}
            onSelect={onSelectVariant}
          />
          <VariantGroup
            label="Color Variants"
            items={colorVariants}
            activeId={creative.id}
            onSelect={onSelectVariant}
          />

          {/* Compact metadata — below the variants */}
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3 text-white">
            <div className="flex items-baseline justify-between gap-2">
              {creative.short_id && (
                <span className="text-[10px] font-mono font-bold text-white/40">{creative.short_id}</span>
              )}
              <span className="text-[10px] text-white/30 tabular-nums">
                {new Date(creative.created_at).toLocaleDateString("de-DE")}
              </span>
            </div>
            {product && (
              <p className="text-sm font-bold text-primary-light leading-tight">{product}</p>
            )}
            {env && (
              <p className="text-white/70 text-xs capitalize">{env.replace(/_/g, " ")}</p>
            )}

            {(creative.shot_size || creative.camera_angle || creative.lens) && (
              <div className="mt-2 pt-2 border-t border-white/10 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                {creative.shot_size && <span className="text-white/40">Shot</span>}
                {creative.shot_size && <span className="text-white/80 text-right">{creative.shot_size}</span>}
                {creative.camera_angle && <span className="text-white/40">Angle</span>}
                {creative.camera_angle && <span className="text-white/80 text-right">{creative.camera_angle}</span>}
                {creative.character_angle && <span className="text-white/40">Position</span>}
                {creative.character_angle && (
                  <span
                    className="text-white/80 text-right line-clamp-1"
                    title={creative.character_angle}
                  >
                    {creative.character_angle}
                  </span>
                )}
                {creative.lens && <span className="text-white/40">Lens</span>}
                {creative.lens && <span className="text-white/80 text-right">{creative.lens}</span>}
                {creative.depth_of_field && <span className="text-white/40">DoF</span>}
                {creative.depth_of_field && <span className="text-white/80 text-right">{creative.depth_of_field}</span>}
                <span className="text-white/40">Format</span>
                <span className="text-white/80 text-right">{creative.format}</span>
                {creative.color_variant && <span className="text-white/40">Color</span>}
                {creative.color_variant && (
                  <span className="text-accent text-right capitalize">{creative.color_variant}</span>
                )}
                {typeof creative.rating === "number" && <span className="text-white/40">QC</span>}
                {typeof creative.rating === "number" && (
                  <span className={`text-right font-semibold ${creative.rating >= 8 ? "text-green-400" : creative.rating >= 7 ? "text-yellow-400" : "text-red-400"}`}>
                    {creative.rating}/10
                  </span>
                )}
              </div>
            )}

            {imageUrl && (
              <button
                onClick={() => downloadCreative(creative)}
                className="mt-2.5 w-full flex items-center justify-center gap-1.5 text-xs font-semibold bg-primary text-white py-1.5 rounded-md hover:bg-primary-light transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                  <path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
                  <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
                </svg>
                Download
              </button>
            )}

            <div className="mt-1.5 flex gap-1.5">
              {creative.storage_path && (
                <button
                  onClick={() => copy(creative.storage_path!, "path")}
                  className="flex-1 text-[10px] font-medium bg-white/10 hover:bg-white/20 text-white/80 py-1 rounded-md transition-colors"
                  title="Copy storage path — paste into Claude prompt for multishot/color-variant"
                >
                  {copied === "path" ? "Copied!" : "Copy path"}
                </button>
              )}
              <button
                onClick={() => copy(creative.id, "id")}
                className="flex-1 text-[10px] font-medium bg-white/10 hover:bg-white/20 text-white/80 py-1 rounded-md transition-colors"
                title="Copy creative ID"
              >
                {copied === "id" ? "Copied!" : "Copy ID"}
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* Mobile caption (right column is hidden below lg) */}
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

function VariantGroup({
  label,
  items,
  activeId,
  onSelect,
}: {
  label: string;
  items: Creative[];
  activeId: string;
  onSelect?: (c: Creative) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="bg-white/10 backdrop-blur-sm rounded-xl p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-white uppercase tracking-wide">{label}</span>
        <span className="text-[10px] text-white/40 tabular-nums">{items.length}</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {items.map((v) => {
          const vUrl = getImageUrl(v);
          const isActive = v.id === activeId;
          return (
            <button
              key={v.id}
              onClick={() => onSelect?.(v)}
              className={`relative aspect-[4/5] rounded-lg overflow-hidden border-2 transition-all ${
                isActive ? "border-primary scale-[1.03]" : "border-transparent hover:border-white/40"
              }`}
              title={v.camera_angle || v.color_variant || v.character_angle || v.short_id || undefined}
            >
              {vUrl ? (
                <img src={vUrl} alt={v.short_id || ""} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-white/10 flex items-center justify-center text-[8px] text-white/40">
                  {v.short_id}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
