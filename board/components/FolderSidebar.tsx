"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";

type Folder = {
  id: string;
  name: string;
  parent_folder_id: string | null;
  sort_order: number;
};

type FolderSidebarProps = {
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onDrop?: (folderId: string, creativeId: string) => void;
};

export default function FolderSidebar({
  selectedFolderId,
  onSelectFolder,
  onDrop,
}: FolderSidebarProps) {
  const { brandId } = useBrand();
  const [folders, setFolders] = useState<Folder[]>([]);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [dragOver, setDragOver] = useState<string | null>(null);

  useEffect(() => {
    if (brandId) loadFolders();
  }, [brandId]);

  async function loadFolders() {
    const { data } = await supabase
      .from("asset_folders")
      .select("*")
      .eq("brand_id", brandId!)
      .order("sort_order")
      .order("name");

    if (data) setFolders(data);
  }

  async function createFolder() {
    if (!newName.trim() || !brandId) return;
    const { error } = await supabase.from("asset_folders").insert({
      brand_id: brandId,
      name: newName.trim(),
    });
    if (error) return;
    setNewName("");
    setCreating(false);
    loadFolders();
  }

  async function deleteFolder(folderId: string) {
    const { error } = await supabase.from("asset_folders").delete().eq("id", folderId);
    if (error) return;
    if (selectedFolderId === folderId) onSelectFolder(null);
    loadFolders();
  }

  function handleDragOver(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    setDragOver(folderId);
  }

  function handleDragLeave() {
    setDragOver(null);
  }

  function handleDrop(e: React.DragEvent, folderId: string) {
    e.preventDefault();
    setDragOver(null);
    const creativeId = e.dataTransfer.getData("creative-id");
    if (creativeId && onDrop) {
      onDrop(folderId, creativeId);
    }
  }

  return (
    <div className="w-56 border-r border-border bg-surface p-4 flex flex-col gap-1">
      <h2 className="text-xs font-semibold text-muted uppercase tracking-wide mb-2">
        Ordner
      </h2>

      {/* All Assets */}
      <button
        onClick={() => onSelectFolder(null)}
        className={`text-left text-sm px-3 py-2 rounded-lg transition-colors ${
          selectedFolderId === null
            ? "bg-primary/10 text-primary font-medium"
            : "text-accent hover:bg-background"
        }`}
      >
        Alle Assets
      </button>

      {/* Folders */}
      {folders.map((folder) => (
        <div
          key={folder.id}
          className={`group flex items-center rounded-lg transition-colors ${
            dragOver === folder.id ? "bg-primary-light/20 ring-2 ring-primary-light" : ""
          } ${
            selectedFolderId === folder.id
              ? "bg-primary/10"
              : "hover:bg-background"
          }`}
          onDragOver={(e) => handleDragOver(e, folder.id)}
          onDragLeave={handleDragLeave}
          onDrop={(e) => handleDrop(e, folder.id)}
        >
          <button
            onClick={() => onSelectFolder(folder.id)}
            className={`flex-1 text-left text-sm px-3 py-2 ${
              selectedFolderId === folder.id
                ? "text-primary font-medium"
                : "text-accent"
            }`}
          >
            {folder.name}
          </button>
          <button
            onClick={() => deleteFolder(folder.id)}
            className="hidden group-hover:block text-muted hover:text-red-400 pr-2 text-xs"
            title="Ordner löschen"
          >
            ×
          </button>
        </div>
      ))}

      {/* Create folder */}
      {creating ? (
        <div className="mt-2 flex gap-1">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createFolder()}
            placeholder="Ordnername"
            className="flex-1 text-sm border border-border rounded-lg px-2 py-1 focus:outline-none focus:border-primary"
            autoFocus
          />
          <button
            onClick={createFolder}
            className="text-xs text-gray-500 hover:text-gray-700 px-1"
          >
            OK
          </button>
        </div>
      ) : (
        <button
          onClick={() => setCreating(true)}
          className="mt-2 text-left text-sm text-muted hover:text-primary px-3 py-2"
        >
          + Neuer Ordner
        </button>
      )}
    </div>
  );
}
