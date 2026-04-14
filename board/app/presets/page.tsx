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

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="font-mono text-[11px] bg-background text-foreground px-1.5 py-0.5 rounded border border-border">
      {children}
    </code>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="bg-background border border-border rounded-lg p-3 text-[11px] font-mono text-foreground overflow-x-auto leading-relaxed">
      {children}
    </pre>
  );
}

function Guide() {
  return (
    <div className="mb-6 bg-surface rounded-xl border border-border p-5 space-y-5">
      {/* Mental model */}
      <div>
        <h2 className="text-sm font-bold text-foreground mb-1.5">What a preset is</h2>
        <p className="text-xs text-muted leading-relaxed">
          A preset is a named recipe of four ingredients:{" "}
          <span className="text-primary-light font-semibold">Product</span> ×{" "}
          <span className="text-primary-light font-semibold">Room</span> ×{" "}
          <span className="text-primary-light font-semibold">Character</span> ×{" "}
          <span className="text-primary-light font-semibold">Camera</span>. Running a preset
          fires up the key-visual pipeline with those exact ingredients pre-filled, so you skip
          re-typing ten flags every time and everyone on the team gets the same consistent look.
        </p>
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Create */}
        <div>
          <h2 className="text-sm font-bold text-foreground mb-1.5">Create a preset</h2>
          <p className="text-xs text-muted leading-relaxed mb-2">
            Presets are created from the CLI — this page is read-only so nobody can accidentally
            delete a good recipe from the browser. Minimum you need is a slug, name, and product;
            everything else inherits sensible defaults.
          </p>
          <CodeBlock>{`python3 .claude/skills/presets/scripts/main.py create \\
  --slug woodpad-scandi-morning \\
  --name "WoodPad Pro – Scandi Morning" \\
  --product woodpad-pro \\
  --room-preset scandi_minimal \\
  --character-mode auto_rotate \\
  --shot-size Wide \\
  --camera-angle "Eye level" \\
  --format 9:16 \\
  --tags walking_pad,scandi,morning \\
  --default-count 3`}</CodeBlock>
        </div>

        {/* Run */}
        <div>
          <h2 className="text-sm font-bold text-foreground mb-1.5">Run a preset</h2>
          <p className="text-xs text-muted leading-relaxed mb-2">
            Running spawns the key-visual skill with all the stored flags, increments{" "}
            <Code>run_count</Code>, and stamps <Code>last_run_at</Code>. Override{" "}
            <Code>--count</Code> to generate more than the preset default.
          </p>
          <CodeBlock>{`# run with stored default_count
python3 .claude/skills/presets/scripts/main.py run woodpad-scandi-morning

# override batch size
python3 .claude/skills/presets/scripts/main.py run woodpad-scandi-morning --count 10

# dry run (print the command without executing)
python3 .claude/skills/presets/scripts/main.py run woodpad-scandi-morning --dry-run`}</CodeBlock>
        </div>
      </div>

      {/* Variable reference */}
      <div>
        <h2 className="text-sm font-bold text-foreground mb-2">Variable reference</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left text-muted">
                <th className="py-1.5 pr-4 font-semibold">Variable</th>
                <th className="py-1.5 pr-4 font-semibold">What it does</th>
                <th className="py-1.5 pr-4 font-semibold">Values / default</th>
              </tr>
            </thead>
            <tbody className="text-foreground/80">
              <GuideRow
                name="--product"
                desc="Product handle, matches branding/product_knowledge.json"
                values="f37s-pro, woodpad-pro, sbike, scross, aqua-elite, …"
                required
              />
              <GuideRow
                name="--room-preset"
                desc="Room recipe ID from branding/room_prompts.json"
                values="scandi_minimal, japandi_bookcase, urban_loft_golden, …"
              />
              <GuideRow
                name="--character-mode"
                desc="How the model/person is chosen at run time"
                values={
                  <>
                    <Code>auto_rotate</Code> (default), <Code>fixed</Code>,{" "}
                    <Code>description</Code>, <Code>model_pool</Code>
                  </>
                }
              />
              <GuideRow
                name="--pose"
                desc="Free-text pose override. Empty = first correct-usage pose from product_knowledge"
                values="e.g. 'Walking on the pad while checking phone'"
              />
              <GuideRow
                name="--shot-size"
                desc="How much frame the subject fills"
                values="Wide (default), Medium Shot, Close Up, Extreme Wide, Bird's Eye"
              />
              <GuideRow
                name="--camera-angle"
                desc="Camera pitch relative to subject (vertical)"
                values="Eye level (default), Slightly above, High, Slightly below, Low, Ground"
              />
              <GuideRow
                name="--character-angle"
                desc="Subject rotation relative to camera (horizontal)"
                values="3/4 angle (default), Front facing, Profile, Over the shoulder, Back view"
              />
              <GuideRow
                name="--lens"
                desc="Focal length — wider = more room, longer = compressed"
                values="14mm, 24mm, 35mm, 50mm (default), 85mm, 135mm, 200mm"
              />
              <GuideRow
                name="--depth-of-field"
                desc="Aperture / background blur"
                values="f/1.2 – f/16 (default f/4)"
              />
              <GuideRow
                name="--format"
                desc="Output aspect ratio"
                values="9:16 (default), 1:1, 16:9, 4:5"
              />
              <GuideRow
                name="--default-count"
                desc="How many images to generate per run when --count is not passed"
                values="int (default 3)"
              />
              <GuideRow
                name="--tags"
                desc="Comma-separated searchable labels"
                values="e.g. walking_pad,scandi,morning"
              />
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-[11px] text-muted/70 pt-2 border-t border-border">
        Full documentation lives in{" "}
        <Code>creative generator/.claude/skills/presets/SKILL.md</Code>. Every preset gets
        validated against <Code>product_knowledge.json</Code> and <Code>room_prompts.json</Code>{" "}
        before it's saved.
      </p>
    </div>
  );
}

function GuideRow({
  name,
  desc,
  values,
  required,
}: {
  name: string;
  desc: string;
  values: React.ReactNode;
  required?: boolean;
}) {
  return (
    <tr className="border-b border-border/50 last:border-0">
      <td className="py-1.5 pr-4 align-top">
        <code className="font-mono text-[11px] text-primary-light">{name}</code>
        {required && <span className="text-[9px] text-accent ml-1 font-bold">required</span>}
      </td>
      <td className="py-1.5 pr-4 align-top text-muted leading-tight">{desc}</td>
      <td className="py-1.5 pr-4 align-top leading-tight">{values}</td>
    </tr>
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
