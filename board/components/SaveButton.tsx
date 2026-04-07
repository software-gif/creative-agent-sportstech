"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import type { Creative } from "./CreativeCard";

type SaveButtonProps = {
  creative: Creative;
  onSaved?: () => void;
};

export default function SaveButton({ creative, onSaved }: SaveButtonProps) {
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (saving || creative.is_saved) return;
    setSaving(true);

    // Insert into saved_assets and mark creative as saved
    const { error: insertError } = await supabase
      .from("saved_assets")
      .insert({
        brand_id: creative.brand_id,
        creative_id: creative.id,
      });

    if (!insertError) {
      await supabase
        .from("creatives")
        .update({ is_saved: true })
        .eq("id", creative.id);
      onSaved?.();
    }

    setSaving(false);
  }

  return (
    <button
      onClick={handleSave}
      disabled={saving || creative.is_saved}
      className={`p-1.5 rounded-lg transition-colors ${
        creative.is_saved
          ? "text-primary bg-primary/10"
          : "text-muted hover:text-primary hover:bg-primary/10"
      }`}
      title={creative.is_saved ? "Gespeichert" : "Speichern"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill={creative.is_saved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={2}
        className="w-4 h-4"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z"
        />
      </svg>
    </button>
  );
}
