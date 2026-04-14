"use client";

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

function Tag({
  children,
  color = "default",
}: {
  children: React.ReactNode;
  color?: "default" | "primary" | "accent" | "muted";
}) {
  const colors = {
    default: "bg-tag-bg text-tag-text",
    primary: "bg-primary/15 text-primary-light",
    accent: "bg-accent/15 text-accent",
    muted: "bg-tag-bg text-muted",
  };
  return (
    <span
      className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${colors[color]}`}
    >
      {children}
    </span>
  );
}

export default function PresetCard({ preset }: { preset: Preset }) {
  return (
    <div className="bg-surface rounded-xl border border-border p-4 flex flex-col gap-3 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-foreground truncate">
            {preset.name}
          </h3>
          <p className="text-[11px] font-mono text-muted truncate mt-0.5">
            {preset.slug}
          </p>
        </div>
        {preset.run_count > 0 && (
          <Tag color="muted">
            {preset.run_count} {preset.run_count === 1 ? "run" : "runs"}
          </Tag>
        )}
      </div>

      {preset.description && (
        <p className="text-xs text-muted line-clamp-2">{preset.description}</p>
      )}

      <div className="flex flex-wrap gap-1.5">
        <Tag color="primary">{preset.product_handle}</Tag>
        {preset.room_preset && <Tag color="accent">{preset.room_preset}</Tag>}
        <Tag color="default">{preset.character_mode}</Tag>
        <Tag color="muted">{preset.format}</Tag>
      </div>

      {(preset.shot_size || preset.lens || preset.camera_angle) && (
        <div className="text-[10px] text-muted border-t border-border pt-2">
          <div className="flex flex-wrap gap-x-3 gap-y-0.5">
            {preset.shot_size && (
              <span>
                <span className="opacity-60">Shot:</span> {preset.shot_size}
              </span>
            )}
            {preset.camera_angle && (
              <span>
                <span className="opacity-60">Cam:</span> {preset.camera_angle}
              </span>
            )}
            {preset.lens && (
              <span>
                <span className="opacity-60">Lens:</span> {preset.lens}
              </span>
            )}
            {preset.depth_of_field && (
              <span>
                <span className="opacity-60">DoF:</span> {preset.depth_of_field}
              </span>
            )}
          </div>
        </div>
      )}

      {preset.tags && preset.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {preset.tags.map((tag) => (
            <span key={tag} className="text-[9px] font-medium text-muted">
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
