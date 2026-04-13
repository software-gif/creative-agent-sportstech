-- ============================================
-- Sportstech Creative Agent — Creative Presets
-- ============================================
--
-- Stores reusable building-block combinations for lifestyle image generation.
-- A preset bundles Product × Room × Character × Camera settings into a named
-- recipe that can be recalled and executed via the `presets` skill.
--
-- Design driven by the Randomizer/Bausteine idea from the 2026-04-09 Sportstech
-- weekly call: Environment × Product × Person × Camera → reusable recipe.

CREATE TABLE creative_presets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,

  -- Identity
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,

  -- Generation building blocks — these map 1:1 onto the key-visual skill args
  product_handle TEXT NOT NULL,
  room_preset TEXT,           -- id from branding/room_prompts.json
  room_description TEXT,      -- free-text override (optional)
  character_mode TEXT NOT NULL DEFAULT 'auto_rotate'
    CHECK (character_mode IN ('auto_rotate', 'fixed', 'description', 'model_pool')),
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  character_description TEXT, -- used when mode = 'description'
  model_pool_id TEXT,         -- id from lifestyle_variance.json models (when mode = 'model_pool')
  pose TEXT,

  -- Camera settings (defaults match key-visual defaults)
  shot_size TEXT DEFAULT 'Wide',
  camera_angle TEXT DEFAULT 'Eye level',
  character_angle TEXT DEFAULT '3/4 angle',
  lens TEXT DEFAULT '50mm',
  depth_of_field TEXT DEFAULT 'f/4',
  format TEXT DEFAULT '9:16',

  default_count INTEGER DEFAULT 3 CHECK (default_count > 0 AND default_count <= 50),

  -- Filtering and metadata
  tags TEXT[] DEFAULT '{}',
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),

  -- Execution tracking
  last_run_at TIMESTAMPTZ,
  run_count INTEGER DEFAULT 0,

  UNIQUE(brand_id, slug)
);

-- RLS (matches rest of schema — public access for now)
ALTER TABLE creative_presets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public access" ON creative_presets FOR ALL USING (true) WITH CHECK (true);

-- Indexes
CREATE INDEX idx_creative_presets_brand ON creative_presets(brand_id);
CREATE INDEX idx_creative_presets_slug ON creative_presets(brand_id, slug);
CREATE INDEX idx_creative_presets_product ON creative_presets(product_handle);
CREATE INDEX idx_creative_presets_tags ON creative_presets USING gin(tags);

-- Auto-update updated_at on change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER creative_presets_set_updated_at
  BEFORE UPDATE ON creative_presets
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
