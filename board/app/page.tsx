"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, {
  Creative,
  ANGLE_EMOJI,
  getImageUrl,
  downloadCreative,
} from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import SaveButton from "@/components/SaveButton";
import ClearBoardButton from "@/components/ClearBoardButton";

export default function Board() {
  const { brandId, loading: brandLoading } = useBrand();
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [filter, setFilter] = useState("all");
  const [styleFilter, setStyleFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [seasonFilter, setSeasonFilter] = useState("all");
  const [envFilter, setEnvFilter] = useState("all");
  const [productCatFilter, setProductCatFilter] = useState("all");
  const [formatFilter, setFormatFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);

  useEffect(() => {
    if (!brandId) return;

    setLoading(true);
    loadCreatives(brandId);

    const channel = supabase
      .channel(`creatives-board-${brandId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "creatives",
          filter: `brand_id=eq.${brandId}`,
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            const c = payload.new as Creative;
            if (!c.is_saved) {
              setCreatives((prev) => [c, ...prev]);
            }
          } else if (payload.eventType === "UPDATE") {
            const c = payload.new as Creative;
            if (c.is_saved) {
              // Saved → remove from board
              setCreatives((prev) => prev.filter((x) => x.id !== c.id));
            } else {
              setCreatives((prev) =>
                prev.map((x) => (x.id === c.id ? c : x))
              );
            }
          } else if (payload.eventType === "DELETE") {
            setCreatives((prev) =>
              prev.filter((c) => c.id !== (payload.old as Creative).id)
            );
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [brandId]);

  async function loadCreatives(bid: string) {
    const { data, error } = await supabase
      .from("creatives")
      .select("*")
      .eq("brand_id", bid)
      .eq("is_saved", false)
      .order("created_at", { ascending: false });

    if (!error && data) {
      setCreatives(data);
    }
    setLoading(false);
  }

  const angles = [...new Set(creatives.map((c) => c.angle))];
  const seasons = [...new Set(creatives.map((c) => c.season).filter(Boolean))];
  const filtered = creatives
    .filter((c) => filter === "all" || c.angle === filter)
    .filter((c) => styleFilter === "all" || c.creative_style === styleFilter)
    .filter((c) => typeFilter === "all" || c.creative_type === typeFilter)
    .filter((c) => seasonFilter === "all" || c.season === seasonFilter)
    .filter((c) => envFilter === "all" || c.environment === envFilter)
    .filter((c) => productCatFilter === "all" || c.product_category === productCatFilter)
    .filter((c) => formatFilter === "all" || c.format === formatFilter);
  const doneCount = creatives.filter((c) => c.status === "done").length;
  const generatingCount = creatives.filter((c) => c.status === "generating").length;

  if (brandLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Laden...
      </div>
    );
  }

  if (!brandId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted">
        <p className="text-lg font-medium">Keine Brand konfiguriert</p>
        <p className="text-sm mt-1">
          Lege zuerst eine Brand in der Datenbank an.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Filter Bar */}
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-accent tabular-nums">
              {filtered.length}
              <span className="text-muted font-normal"> / {doneCount}</span>
            </span>
            {generatingCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-primary">
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                {generatingCount} generiert...
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            {/* Format toggle */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {(["all", "4:5", "9:16"] as const).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setFormatFilter(fmt)}
                  className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                    formatFilter === fmt ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-accent"
                  }`}
                >
                  {fmt === "all" ? "Alle" : fmt === "4:5" ? "Feed" : "Story"}
                </button>
              ))}
            </div>
            {/* Type toggle */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {(["all", "lifestyle", "product_static"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setTypeFilter(type)}
                  className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                    typeFilter === type ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-accent"
                  }`}
                >
                  {type === "all" ? "Alle" : type === "lifestyle" ? "Lifestyle" : "Product"}
                </button>
              ))}
            </div>
            {/* Style toggle */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {(["all", "on_brand", "off_brand"] as const).map((style) => (
                <button
                  key={style}
                  onClick={() => setStyleFilter(style)}
                  className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                    styleFilter === style ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-accent"
                  }`}
                >
                  {style === "all" ? "Alle" : style === "on_brand" ? "On" : "Off"}
                </button>
              ))}
            </div>
            {/* Dropdowns */}
            <select value={productCatFilter} onChange={(e) => setProductCatFilter(e.target.value)} className="text-[11px] border border-border rounded-lg px-2 py-1.5 text-accent bg-surface focus:outline-none focus:border-primary">
              <option value="all">Alle Produkte</option>
              {/* TODO: Sportstech Produkte hier eintragen */}
            </select>
            <select value={envFilter} onChange={(e) => setEnvFilter(e.target.value)} className="text-[11px] border border-border rounded-lg px-2 py-1.5 text-accent bg-surface focus:outline-none focus:border-primary">
              <option value="all">Alle Environments</option>
              <option value="wohnzimmer">Wohnzimmer</option>
              <option value="garten">Garten</option>
              <option value="schlafzimmer">Schlafzimmer</option>
              <option value="studio">Studio</option>
            </select>
            <select value={seasonFilter} onChange={(e) => setSeasonFilter(e.target.value)} className="text-[11px] border border-border rounded-lg px-2 py-1.5 text-accent bg-surface focus:outline-none focus:border-primary">
              <option value="all">Season</option>
              <option value="evergreen">Evergreen</option>
              <option value="sommer">Sommer</option>
              <option value="frühling">Frühling</option>
              <option value="herbst">Herbst</option>
              <option value="winter">Winter</option>
            </select>
            <select value={filter} onChange={(e) => setFilter(e.target.value)} className="text-[11px] border border-border rounded-lg px-2 py-1.5 text-accent bg-surface focus:outline-none focus:border-primary">
              <option value="all">Angle</option>
              {angles.map((a) => (
                <option key={a} value={a}>{ANGLE_EMOJI[a] || ""} {a} ({creatives.filter((c) => c.angle === a).length})</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Grid */}
      <main className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80 text-muted">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 text-primary">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-accent">Noch keine Creatives</p>
            <p className="text-sm mt-1 max-w-xs text-center">
              Generiere Ads per Claude Code — sie erscheinen hier live in Echtzeit.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-5">
            {filtered.map((creative) => (
              <CreativeCard
                key={creative.id}
                creative={creative}
                onImageClick={setSelectedImage}
                actions={
                  creative.status === "done" && (
                    <>
                      <SaveButton creative={creative} />
                      {getImageUrl(creative) && (
                        <button
                          onClick={() => downloadCreative(creative)}
                          className="flex-1 text-center text-xs font-semibold bg-primary text-white py-1.5 rounded-lg hover:bg-primary/80 transition-colors"
                        >
                          Download
                        </button>
                      )}
                    </>
                  )
                }
              />
            ))}
          </div>
        )}
      </main>

      <ImageOverlay
        creative={selectedImage}
        onClose={() => setSelectedImage(null)}
      />

      <ClearBoardButton />
    </div>
  );
}
