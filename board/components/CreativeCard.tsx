"use client";

import { supabase } from "@/lib/supabase";
import { PRODUCT_LABELS, ENV_LABELS, PRESET_TO_ENV } from "@/lib/constants";

export type Creative = {
  id: string;
  short_id: string | null;
  brand_id: string;
  batch_id: string | null;
  product_id: string | null;
  character_id: string | null;
  environment_id: string | null;
  storage_path: string | null;
  thumbnail_path: string | null;
  prompt_text: string | null;
  prompt_json: Record<string, unknown> | null;
  shot_size: string | null;
  camera_angle: string | null;
  character_angle: string | null;
  lens: string | null;
  depth_of_field: string | null;
  creative_type: string;
  creative_style: string;
  color_variant: string | null;
  format: string;
  resolution_width: number | null;
  resolution_height: number | null;
  generation_model: string | null;
  generation_mode: string | null;
  scene_type: string | null;
  season: string | null;
  environment_style: string | null;
  status: string;
  is_saved: boolean;
  rating: number | null;
  notes: string | null;
  created_at: string;
  tags: string[] | null;
  parent_id: string | null;
  // Legacy fields for compatibility
  image_url?: string | null;
  angle?: string;
  sub_angle?: string;
  hook_text?: string;
  product_category?: string | null;
  environment?: string | null;
};


export function getImageUrl(creative: Creative): string | null {
  if (creative.image_url) return creative.image_url;
  if (creative.storage_path) {
    const { data } = supabase.storage
      .from("creatives")
      .getPublicUrl(creative.storage_path);
    return data.publicUrl;
  }
  return null;
}

export function getDownloadFilename(creative: Creative): string {
  const product = creative.product_category || creative.creative_type;
  const env = creative.environment_style || creative.environment || "lifestyle";
  const cam = creative.camera_angle || "";
  const ts = new Date(creative.created_at).toISOString().slice(0, 10);
  return `${product}_${env}_${cam}_${ts}.png`.replace(/\s+/g, "_").replace(/[^a-zA-Z0-9._-]/g, "");
}

export async function downloadCreative(creative: Creative) {
  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return;
  try {
    const resp = await fetch(`/api/download?url=${encodeURIComponent(imageUrl)}&filename=img`);
    const blob = await resp.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = getDownloadFilename(creative);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
  } catch {
    window.open(imageUrl, "_blank");
  }
}

function Tag({ children, color = "default" }: { children: React.ReactNode; color?: "default" | "primary" | "accent" | "muted" }) {
  const colors = {
    default: "bg-tag-bg text-tag-text",
    primary: "bg-primary/15 text-primary-light",
    accent: "bg-accent/15 text-accent",
    muted: "bg-tag-bg text-muted",
  };
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${colors[color]}`}>
      {children}
    </span>
  );
}

type CreativeCardProps = {
  creative: Creative;
  onImageClick?: (creative: Creative) => void;
  actions?: React.ReactNode;
  viewMode?: "grid" | "list";
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent, creative: Creative) => void;
  variants?: Creative[];
};

function VariantDot({
  letter,
  count,
  label,
}: {
  letter: string;
  count: number;
  label: string;
}) {
  const active = count > 0;
  return (
    <span
      title={`${label}: ${count}`}
      className="inline-flex items-center gap-1"
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          active
            ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.9)]"
            : "bg-red-500/70 shadow-[0_0_4px_rgba(239,68,68,0.5)]"
        }`}
      />
      <span
        className={`text-[10px] font-semibold leading-none ${
          active ? "text-green-400" : "text-red-400/80"
        }`}
      >
        {letter}
        {active && <span className="ml-0.5 tabular-nums">{count}</span>}
      </span>
    </span>
  );
}

function VariantDots({
  multishotCount,
  colorCount,
}: {
  multishotCount: number;
  colorCount: number;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <VariantDot letter="M" count={multishotCount} label="Multishots" />
      <VariantDot letter="C" count={colorCount} label="Color Variants" />
    </div>
  );
}

export default function CreativeCard({
  creative,
  onImageClick,
  actions,
  viewMode = "grid",
  draggable,
  onDragStart,
  variants = [],
}: CreativeCardProps) {
  const imageUrl = getImageUrl(creative);
  const productLabel = PRODUCT_LABELS[creative.product_category || ""] || creative.product_category;
  const envStyle = creative.environment_style || creative.environment || "";
  const envCategory = PRESET_TO_ENV[envStyle] || envStyle;
  const envLabel = ENV_LABELS[envCategory] || ENV_LABELS[envStyle] || envStyle;
  const multishots = variants.filter((v) => v.creative_type === "multishot");
  const colors = variants.filter((v) => v.creative_type === "color_variant");

  if (viewMode === "list") {
    return (
      <div
        className={`group flex items-center gap-4 bg-surface rounded-xl border border-border p-2 hover:border-primary/30 hover:bg-surface-hover transition-all ${
          draggable ? "active:cursor-grabbing cursor-grab" : "cursor-pointer"
        }`}
        draggable={draggable}
        onDragStart={(e) => onDragStart?.(e, creative)}
        onClick={() => imageUrl && onImageClick?.(creative)}
      >
        {/* Thumbnail */}
        <div
          className="relative w-20 h-20 rounded-lg bg-background overflow-hidden flex-shrink-0"
        >
          {creative.status === "generating" ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : imageUrl ? (
            <img
              src={imageUrl}
              alt=""
              className="w-full h-full object-cover"
              loading="lazy"
              draggable={false}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-muted">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5 opacity-40">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {creative.short_id && (
              <span className="text-[10px] font-mono font-bold text-foreground bg-border/50 px-1.5 py-0.5 rounded">
                {creative.short_id}
              </span>
            )}
            {productLabel && <Tag color="primary">{productLabel}</Tag>}
            {envLabel && <Tag>{envLabel}</Tag>}
            {creative.camera_angle && <Tag color="muted">{creative.camera_angle}</Tag>}
            {creative.lens && <Tag color="muted">{creative.lens}</Tag>}
            {creative.color_variant && <Tag color="accent">{creative.color_variant}</Tag>}
            <Tag color="muted">{creative.format}</Tag>
            <VariantDots multishotCount={multishots.length} colorCount={colors.length} />
          </div>
          <p className="text-xs text-muted mt-1 truncate">
            {new Date(creative.created_at).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
            {creative.shot_size && ` \u00B7 ${creative.shot_size}`}
            {creative.depth_of_field && ` \u00B7 ${creative.depth_of_field}`}
          </p>
        </div>

        {/* Actions — stop row-click propagation so Download/Delete don't open overlay */}
        {actions && (
          <div
            className="flex items-center gap-2 flex-shrink-0"
            onClick={(e) => e.stopPropagation()}
          >
            {actions}
          </div>
        )}
      </div>
    );
  }

  // Grid view
  return (
    <div
      className={`group bg-surface rounded-xl border border-border overflow-hidden hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30 transition-all ${
        draggable ? "active:cursor-grabbing cursor-grab" : ""
      }`}
      draggable={draggable}
      onDragStart={(e) => onDragStart?.(e, creative)}
    >
      {/* Image */}
      <div
        className="relative aspect-[4/5] bg-background cursor-pointer overflow-hidden"
        onClick={() => imageUrl && onImageClick?.(creative)}
      >
        {creative.status === "generating" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-muted">Generating...</span>
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt=""
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
            loading="lazy"
            draggable={false}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 opacity-40">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
            </svg>
            <span className="text-xs">No image</span>
          </div>
        )}
        {/* Badges */}
        <div className="absolute top-2 left-2">
          {creative.short_id && (
            <span className="bg-black/70 backdrop-blur-sm text-white/90 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded">
              {creative.short_id}
            </span>
          )}
        </div>
        <div className="absolute top-2 right-2">
          <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-semibold px-1.5 py-0.5 rounded">
            {creative.format}
          </span>
        </div>
      </div>

      {/* Tags & Meta */}
      <div className="p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 flex-wrap flex-1 min-w-0">
            {productLabel && <Tag color="primary">{productLabel}</Tag>}
            {envLabel && <Tag>{envLabel}</Tag>}
            {creative.camera_angle && <Tag color="muted">{creative.camera_angle}</Tag>}
            {creative.color_variant && <Tag color="accent">{creative.color_variant}</Tag>}
          </div>
          <VariantDots multishotCount={multishots.length} colorCount={colors.length} />
        </div>
        {(creative.lens || creative.shot_size) && (
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            {creative.shot_size && <Tag color="muted">{creative.shot_size}</Tag>}
            {creative.lens && <Tag color="muted">{creative.lens}</Tag>}
            {creative.depth_of_field && <Tag color="muted">{creative.depth_of_field}</Tag>}
          </div>
        )}
        {actions && <div className="mt-2.5 flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
