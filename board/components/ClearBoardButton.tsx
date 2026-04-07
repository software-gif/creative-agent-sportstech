"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";

export default function ClearBoardButton() {
  const { brandId } = useBrand();
  const [confirming, setConfirming] = useState(false);
  const [clearing, setClearing] = useState(false);

  async function handleClear() {
    if (!brandId || clearing) return;
    setClearing(true);

    const { error } = await supabase
      .from("creatives")
      .delete()
      .eq("brand_id", brandId)
      .eq("is_saved", false);

    if (!error) {
      // Force reload — bulk deletes don't always trigger realtime events
      window.location.reload();
    }

    setClearing(false);
    setConfirming(false);
  }

  if (confirming) {
    return (
      <div className="fixed bottom-6 right-6 z-50 bg-surface rounded-xl shadow-lg border border-border p-4 flex flex-col gap-3">
        <p className="text-sm text-accent font-medium">
          Alle ungespeicherten Creatives löschen?
        </p>
        <div className="flex gap-2">
          <button
            onClick={handleClear}
            disabled={clearing}
            className="flex-1 text-sm font-semibold bg-red-500 text-white py-2 rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {clearing ? "Lösche..." : "Ja, löschen"}
          </button>
          <button
            onClick={() => setConfirming(false)}
            className="flex-1 text-sm font-semibold bg-background text-accent py-2 rounded-lg hover:bg-border transition-colors"
          >
            Abbrechen
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={() => setConfirming(true)}
      className="fixed bottom-6 right-6 z-50 w-12 h-12 bg-surface rounded-full shadow-lg border border-border flex items-center justify-center text-muted hover:text-red-500 hover:border-red-200 transition-colors"
      title="Board leeren"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        className="w-5 h-5"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
        />
      </svg>
    </button>
  );
}
