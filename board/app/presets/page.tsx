"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import PresetCard, { Preset } from "@/components/PresetCard";

export default function PresetsPage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (brandId) loadPresets(brandId);
  }, [brandId]);

  async function loadPresets(bid: string) {
    setLoading(true);
    const { data, error } = await supabase
      .from("creative_presets")
      .select("*")
      .eq("brand_id", bid)
      .order("created_at", { ascending: false });
    if (!error && data) {
      setPresets(data as Preset[]);
    }
    setLoading(false);
  }

  if (brandLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Loading...
      </div>
    );
  }

  if (!brandId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted">
        <p className="text-lg font-medium">No brand configured</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <main className="p-6">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-foreground">Presets</h1>
          <p className="text-sm text-muted mt-1">
            Reusable Product × Room × Character × Camera recipes. Read-only —
            manage them via the{" "}
            <code className="font-mono text-[11px] bg-tag-bg text-tag-text px-1.5 py-0.5 rounded">
              presets
            </code>{" "}
            CLI skill.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Loading...
          </div>
        ) : presets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted">
            <p className="text-lg font-medium">No presets yet</p>
            <p className="text-sm mt-1">
              Create one with{" "}
              <code className="font-mono text-[11px] bg-tag-bg text-tag-text px-1.5 py-0.5 rounded">
                python3 .claude/skills/presets/scripts/main.py create ...
              </code>
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {presets.map((preset) => (
              <PresetCard key={preset.id} preset={preset} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
