"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import PresetCard, { Preset } from "@/components/PresetCard";

export default function PresetsPage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showGuide, setShowGuide] = useState(false);

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
      <main className="p-6 max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 mb-5">
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Presets</h1>
            <p className="text-sm text-muted mt-1 max-w-2xl">
              Reusable recipes — pair a product with a room, character, and camera setup so
              every team member generates the same look with a single command.
            </p>
          </div>
          <button
            onClick={() => setShowGuide((v) => !v)}
            className="text-xs font-semibold px-3 py-2 rounded-lg border border-border text-foreground hover:border-primary/50 hover:text-primary-light transition-colors flex items-center gap-1.5"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-3.5 h-3.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
            </svg>
            {showGuide ? "Hide guide" : "How presets work"}
          </button>
        </div>

        {/* Collapsible guide */}
        {showGuide && <Guide />}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Loading presets...
          </div>
        ) : presets.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
            {presets.map((preset) => (
              <PresetCard key={preset.id} preset={preset} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function Cmd({ children }: { children: React.ReactNode }) {
  return (
    <code className="font-mono text-[11px] bg-background text-primary-light px-1.5 py-0.5 rounded">
      {children}
    </code>
  );
}

function Guide() {
  return (
    <div className="mb-6 bg-surface rounded-xl border border-border p-4 text-sm">
      <p className="text-xs text-muted mb-3">
        A preset = a named recipe of <span className="text-foreground">Product + Room + Character + Camera</span>. Run it from Claude with a slash command to generate images with those settings.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
        <div className="flex items-baseline gap-2">
          <Cmd>/presets list</Cmd>
          <span className="text-muted">show all presets</span>
        </div>
        <div className="flex items-baseline gap-2">
          <Cmd>/presets show &lt;slug&gt;</Cmd>
          <span className="text-muted">inspect one in detail</span>
        </div>
        <div className="flex items-baseline gap-2">
          <Cmd>/presets run &lt;slug&gt;</Cmd>
          <span className="text-muted">generate images with it</span>
        </div>
        <div className="flex items-baseline gap-2">
          <Cmd>/presets run &lt;slug&gt; --count 10</Cmd>
          <span className="text-muted">override batch size</span>
        </div>
        <div className="flex items-baseline gap-2">
          <Cmd>/presets create ...</Cmd>
          <span className="text-muted">add a new recipe</span>
        </div>
        <div className="flex items-baseline gap-2">
          <Cmd>/presets delete &lt;slug&gt;</Cmd>
          <span className="text-muted">remove a recipe</span>
        </div>
      </div>

      <p className="text-[11px] text-muted/70 mt-3 pt-3 border-t border-border">
        Full flag reference lives in{" "}
        <code className="font-mono text-[10px] bg-tag-bg text-foreground/80 px-1 py-0.5 rounded">
          .claude/skills/presets/SKILL.md
        </code>
        .
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 text-primary">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      </div>
      <p className="text-base font-semibold text-foreground">No presets yet</p>
      <p className="text-sm text-muted mt-1 max-w-md">
        Create your first preset with the{" "}
        <code className="font-mono text-[11px] bg-tag-bg text-foreground px-1.5 py-0.5 rounded">
          presets create
        </code>{" "}
        CLI command — click <b>How presets work</b> above for a full example.
      </p>
    </div>
  );
}
