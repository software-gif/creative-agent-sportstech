"use client";

import { PRODUCT_LABELS, ENV_LABELS, PRESET_TO_ENV } from "@/lib/constants";

export type Preset = {
  id: string;
  brand_id: string;
  slug: string;
  name: string;
  description: string | null;
  product_handle: string;
  room_preset: string | null;
  room_description: string | null;
  character_mode: string;
  character_id: string | null;
  character_description: string | null;
  model_pool_id: string | null;
  pose: string | null;
  shot_size: string | null;
  camera_angle: string | null;
  character_angle: string | null;
  lens: string | null;
  depth_of_field: string | null;
  format: string;
  default_count: number;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
  last_run_at: string | null;
  run_count: number;
};

function humanize(slug: string | null | undefined): string {
  if (!slug) return "—";
  return slug
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function characterModeLabel(mode: string): string {
  switch (mode) {
    case "auto_rotate":
      return "Auto-Rotate (Model Pool)";
    case "fixed":
      return "Fixed Character";
    case "description":
      return "Free-Text Description";
    case "model_pool":
      return "Specific Model Pool";
    default:
      return humanize(mode);
  }
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3 text-xs leading-tight">
      <span className="text-muted/80 uppercase tracking-wide text-[10px] font-semibold w-20 flex-shrink-0">
        {label}
      </span>
      <span className="text-foreground truncate">{value}</span>
    </div>
  );
}

export default function PresetCard({ preset }: { preset: Preset }) {
  const productLabel = PRODUCT_LABELS[preset.product_handle] || humanize(preset.product_handle);
  const envCategory = preset.room_preset ? PRESET_TO_ENV[preset.room_preset] || preset.room_preset : "";
  const envLabel = ENV_LABELS[envCategory] || humanize(preset.room_preset);

  const cameraParts = [
    preset.shot_size,
    preset.camera_angle,
    preset.character_angle,
    preset.lens,
    preset.depth_of_field,
  ].filter(Boolean);

  return (
    <div className="bg-surface rounded-xl border border-border p-5 flex flex-col gap-4 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 transition-all">
      {/* Header: name + slug + runs */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-bold text-foreground leading-tight">{preset.name}</h3>
          <code className="text-[10px] font-mono text-muted/70 mt-0.5 block truncate">
            {preset.slug}
          </code>
        </div>
        <div className="flex flex-col items-end gap-1 flex-shrink-0">
          {preset.run_count > 0 ? (
            <span className="text-[10px] font-semibold text-primary-light bg-primary/10 px-2 py-0.5 rounded-full">
              {preset.run_count} {preset.run_count === 1 ? "run" : "runs"}
            </span>
          ) : (
            <span className="text-[10px] font-medium text-muted/60 bg-tag-bg px-2 py-0.5 rounded-full">
              unused
            </span>
          )}
          <span className="text-[10px] font-semibold text-muted bg-tag-bg px-2 py-0.5 rounded-full">
            {preset.format}
          </span>
        </div>
      </div>

      {preset.description && (
        <p className="text-xs text-muted leading-relaxed line-clamp-2 -mt-2">
          {preset.description}
        </p>
      )}

      {/* Recipe */}
      <div className="flex flex-col gap-1.5 bg-background/50 rounded-lg p-3">
        <Row label="Product" value={<span className="font-semibold text-primary-light">{productLabel}</span>} />
        <Row label="Room" value={envLabel} />
        <Row label="Character" value={characterModeLabel(preset.character_mode)} />
        {cameraParts.length > 0 && (
          <Row label="Camera" value={<span className="text-muted">{cameraParts.join(" · ")}</span>} />
        )}
        {preset.pose && (
          <Row label="Pose" value={<span className="text-muted line-clamp-1">{preset.pose}</span>} />
        )}
        <Row
          label="Batch"
          value={
            <span className="text-muted">
              {preset.default_count} {preset.default_count === 1 ? "image" : "images"} per run
            </span>
          }
        />
      </div>

      {/* Tags */}
      {preset.tags && preset.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {preset.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] font-medium text-muted bg-tag-bg px-1.5 py-0.5 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer: run command hint + last run */}
      <div className="flex items-center justify-between gap-2 pt-2 border-t border-border text-[10px]">
        <code className="font-mono text-muted/80 truncate">
          presets run {preset.slug}
        </code>
        {preset.last_run_at && (
          <span className="text-muted/50 flex-shrink-0 tabular-nums">
            {new Date(preset.last_run_at).toLocaleDateString("de-DE", {
              day: "2-digit",
              month: "2-digit",
            })}
          </span>
        )}
      </div>
    </div>
  );
}
