"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, {
  Creative,
  getImageUrl,
  downloadCreative,
} from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import SaveButton from "@/components/SaveButton";
import ClearBoardButton from "@/components/ClearBoardButton";
import { PRODUCTS, ENVIRONMENTS, CAMERA_ANGLES, FORMATS, CREATIVE_TYPES } from "@/lib/constants";

export default function Board() {
  const { brandId, loading: brandLoading } = useBrand();
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  // Filters
  const [productFilter, setProductFilter] = useState("all");
  const [envFilter, setEnvFilter] = useState("all");
  const [cameraFilter, setCameraFilter] = useState("all");
  const [formatFilter, setFormatFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

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

  const filtered = creatives
    .filter((c) => productFilter === "all" || c.product_category === productFilter)
    .filter((c) => envFilter === "all" || c.environment_style === envFilter || c.environment === envFilter)
    .filter((c) => cameraFilter === "all" || c.camera_angle === cameraFilter)
    .filter((c) => formatFilter === "all" || c.format === formatFilter)
    .filter((c) => typeFilter === "all" || c.creative_type === typeFilter);

  const doneCount = creatives.filter((c) => c.status === "done" || c.status === "generated").length;
  const generatingCount = creatives.filter((c) => c.status === "generating").length;

  async function deleteCreative(id: string) {
    await supabase.from("creatives").delete().eq("id", id);
    setCreatives((prev) => prev.filter((c) => c.id !== id));
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
        <p className="text-sm mt-1">Create a brand in the database first.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Filter Bar */}
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2.5">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Count + Status */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <span className="text-sm font-bold text-foreground tabular-nums">
              {filtered.length}
              <span className="text-muted font-normal text-xs ml-1">/ {doneCount}</span>
            </span>
            {generatingCount > 0 && (
              <span className="flex items-center gap-1.5 text-xs text-primary font-medium">
                <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
                {generatingCount}
              </span>
            )}
          </div>

          {/* Center: Filters */}
          <div className="flex items-center gap-2 flex-wrap justify-center flex-1">
            {/* Product */}
            <select
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              className="text-xs border border-border rounded-lg px-2.5 py-1.5 bg-surface text-foreground focus:outline-none focus:border-primary"
            >
              <option value="all">All Products</option>
              {PRODUCTS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>

            {/* Environment */}
            <select
              value={envFilter}
              onChange={(e) => setEnvFilter(e.target.value)}
              className="text-xs border border-border rounded-lg px-2.5 py-1.5 bg-surface text-foreground focus:outline-none focus:border-primary"
            >
              <option value="all">All Environments</option>
              {ENVIRONMENTS.map((e) => (
                <option key={e.value} value={e.value}>{e.label}</option>
              ))}
            </select>

            {/* Camera Angle */}
            <select
              value={cameraFilter}
              onChange={(e) => setCameraFilter(e.target.value)}
              className="text-xs border border-border rounded-lg px-2.5 py-1.5 bg-surface text-foreground focus:outline-none focus:border-primary"
            >
              <option value="all">All Angles</option>
              {CAMERA_ANGLES.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>

            {/* Format */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {[{ value: "all", label: "All" }, ...FORMATS].map((fmt) => (
                <button
                  key={fmt.value}
                  onClick={() => setFormatFilter(fmt.value)}
                  className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-all ${
                    formatFilter === fmt.value
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-foreground"
                  }`}
                >
                  {fmt.label}
                </button>
              ))}
            </div>

            {/* Type */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {[{ value: "all", label: "All" }, ...CREATIVE_TYPES].map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTypeFilter(t.value)}
                  className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-all ${
                    typeFilter === t.value
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-foreground"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Right: View Toggle */}
          <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5 flex-shrink-0">
            <button
              onClick={() => setViewMode("grid")}
              className={`p-1.5 rounded-md transition-all ${
                viewMode === "grid" ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-foreground"
              }`}
              title="Grid"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode("list")}
              className={`p-1.5 rounded-md transition-all ${
                viewMode === "list" ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-foreground"
              }`}
              title="List"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80 text-muted">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 text-primary">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-foreground">No lifestyle images yet</p>
            <p className="text-sm mt-1 max-w-sm text-center">
              Generate lifestyle shots via Claude Code Agent — they appear here in real-time.
            </p>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
            {filtered.map((creative) => (
              <CreativeCard
                key={creative.id}
                creative={creative}
                viewMode="grid"
                onImageClick={setSelectedImage}
                actions={
                  (creative.status === "done" || creative.status === "generated") && (
                    <>
                      <SaveButton creative={creative} />
                      {getImageUrl(creative) && (
                        <button
                          onClick={() => downloadCreative(creative)}
                          className="flex-1 text-center text-xs font-semibold bg-primary text-white py-1.5 rounded-lg hover:bg-primary-light transition-colors"
                        >
                          Download
                        </button>
                      )}
                      <button
                        onClick={() => deleteCreative(creative.id)}
                        className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                        title="Delete"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
                    </>
                  )
                }
              />
            ))}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {filtered.map((creative) => (
              <CreativeCard
                key={creative.id}
                creative={creative}
                viewMode="list"
                onImageClick={setSelectedImage}
                actions={
                  (creative.status === "done" || creative.status === "generated") && (
                    <>
                      <SaveButton creative={creative} />
                      {getImageUrl(creative) && (
                        <button
                          onClick={() => downloadCreative(creative)}
                          className="text-xs font-semibold bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary-light transition-colors"
                        >
                          Download
                        </button>
                      )}
                      <button
                        onClick={() => deleteCreative(creative.id)}
                        className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                        title="Delete"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </button>
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
