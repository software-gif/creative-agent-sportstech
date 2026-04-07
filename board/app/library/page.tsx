"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, { Creative, getImageUrl, downloadCreative } from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import FolderSidebar from "@/components/FolderSidebar";

type SavedAsset = {
  id: string;
  creative_id: string;
  folder_id: string | null;
  creative: Creative;
};

export default function Library() {
  const { brandId, loading: brandLoading } = useBrand();
  const [assets, setAssets] = useState<SavedAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);

  useEffect(() => {
    if (brandId) loadAssets(brandId);
  }, [brandId]);

  async function loadAssets(bid: string) {
    setLoading(true);
    const { data, error } = await supabase
      .from("saved_assets")
      .select("*, creative:creatives(*)")
      .eq("brand_id", bid)
      .order("created_at", { ascending: false });

    if (!error && data) {
      // Flatten the join result
      const mapped = data.map((row: Record<string, unknown>) => ({
        id: row.id as string,
        creative_id: row.creative_id as string,
        folder_id: row.folder_id as string | null,
        creative: row.creative as Creative,
      }));
      setAssets(mapped);
    }
    setLoading(false);
  }

  async function removeFromLibrary(creativeId: string) {
    const { error: deleteError } = await supabase
      .from("saved_assets")
      .delete()
      .eq("creative_id", creativeId);
    if (deleteError) return;

    await supabase
      .from("creatives")
      .update({ is_saved: false })
      .eq("id", creativeId);
    setAssets((prev) => prev.filter((a) => a.creative_id !== creativeId));
  }

  async function moveToFolder(folderId: string, creativeId: string) {
    const { error } = await supabase
      .from("saved_assets")
      .update({ folder_id: folderId })
      .eq("creative_id", creativeId);
    if (error) return;

    setAssets((prev) =>
      prev.map((a) =>
        a.creative_id === creativeId ? { ...a, folder_id: folderId } : a
      )
    );
  }

  function handleDragStart(e: React.DragEvent, creative: Creative) {
    e.dataTransfer.setData("creative-id", creative.id);
  }

  const filtered = selectedFolder
    ? assets.filter((a) => a.folder_id === selectedFolder)
    : assets;

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
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <FolderSidebar
        selectedFolderId={selectedFolder}
        onSelectFolder={setSelectedFolder}
        onDrop={moveToFolder}
      />

      <main className="flex-1 p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted">
            <p className="text-lg font-medium">
              {selectedFolder ? "Keine Assets in diesem Ordner" : "Noch keine gespeicherten Assets"}
            </p>
            <p className="text-sm mt-1">
              Speichere Creatives vom Board, um sie hier zu organisieren.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
            {filtered.map((asset) => (
              <CreativeCard
                key={asset.id}
                creative={asset.creative}
                onImageClick={setSelectedImage}
                draggable
                onDragStart={handleDragStart}
                actions={
                  <>
                    {getImageUrl(asset.creative) && (
                      <button
                        onClick={() => downloadCreative(asset.creative)}
                        className="flex-1 text-center text-xs font-semibold bg-primary text-white py-1.5 rounded-lg hover:bg-primary/80 transition-colors"
                      >
                        Download
                      </button>
                    )}
                    <button
                      onClick={() => removeFromLibrary(asset.creative_id)}
                      className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="Aus Library entfernen"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        className="w-4 h-4"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </>
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
    </div>
  );
}
