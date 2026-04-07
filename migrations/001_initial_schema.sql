-- ============================================
-- Sportstech Creative Agent — Initial Schema
-- ============================================

-- 1. Brands (multi-brand support)
CREATE TABLE brands (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  shop_url TEXT,
  config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Products
CREATE TABLE products (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  handle TEXT NOT NULL,
  name TEXT NOT NULL,
  category TEXT,
  price NUMERIC(10,2),
  colors JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(brand_id, handle)
);

-- 3. Product Images (reference images for AI generation)
CREATE TABLE product_images (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  storage_path TEXT NOT NULL,
  image_type TEXT DEFAULT 'reference',
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Characters (Character Builder output — consistent model identity)
CREATE TABLE characters (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT,
  gender TEXT,
  age INTEGER,
  height TEXT,
  physique TEXT,
  skin_type TEXT,
  hairstyle TEXT,
  expression TEXT,
  clothes TEXT,
  headshot_path TEXT,
  full_body_front_path TEXT,
  full_body_profile_path TEXT,
  prompt_data JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Environments (Room Creation output)
CREATE TABLE environments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  style TEXT,
  description TEXT,
  room_prompt TEXT,
  angle_prompts JSONB DEFAULT '[]',
  reference_images JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 6. Creatives (generated images — main output table)
CREATE TABLE creatives (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  batch_id UUID,
  product_id UUID REFERENCES products(id) ON DELETE SET NULL,
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  environment_id UUID REFERENCES environments(id) ON DELETE SET NULL,

  -- Image paths
  storage_path TEXT NOT NULL,
  thumbnail_path TEXT,

  -- Prompt & generation data
  prompt_text TEXT,
  prompt_json JSONB DEFAULT '{}',

  -- Camera settings (from Weavy multishots)
  shot_size TEXT,
  camera_angle TEXT,
  character_angle TEXT,
  lens TEXT,
  depth_of_field TEXT,

  -- Creative metadata
  creative_type TEXT DEFAULT 'lifestyle',
  creative_style TEXT DEFAULT 'on_brand',
  color_variant TEXT,
  format TEXT DEFAULT '9:16',
  resolution_width INTEGER,
  resolution_height INTEGER,

  -- Generation metadata
  generation_model TEXT,
  generation_mode TEXT DEFAULT 'raw',
  scene_type TEXT DEFAULT 'positive',
  season TEXT DEFAULT 'evergreen',
  environment_style TEXT,

  -- Status
  status TEXT DEFAULT 'generated',
  is_saved BOOLEAN DEFAULT FALSE,
  rating INTEGER,
  notes TEXT,

  created_at TIMESTAMPTZ DEFAULT now()
);

-- 7. Asset Folders (organize saved creatives)
CREATE TABLE asset_folders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  parent_folder_id UUID REFERENCES asset_folders(id) ON DELETE CASCADE,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 8. Saved Assets (creative → folder)
CREATE TABLE saved_assets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  creative_id UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
  folder_id UUID REFERENCES asset_folders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(creative_id)
);

-- ============================================
-- Row Level Security
-- ============================================
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE environments ENABLE ROW LEVEL SECURITY;
ALTER TABLE creatives ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public access" ON brands FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON product_images FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON characters FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON environments FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON creatives FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON asset_folders FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Public access" ON saved_assets FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- Realtime
-- ============================================
ALTER PUBLICATION supabase_realtime ADD TABLE creatives;
ALTER PUBLICATION supabase_realtime ADD TABLE saved_assets;

-- ============================================
-- Indexes
-- ============================================
CREATE INDEX idx_creatives_brand ON creatives(brand_id);
CREATE INDEX idx_creatives_batch ON creatives(batch_id);
CREATE INDEX idx_creatives_product ON creatives(product_id);
CREATE INDEX idx_creatives_status ON creatives(status);
CREATE INDEX idx_creatives_type ON creatives(creative_type);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_characters_brand ON characters(brand_id);
CREATE INDEX idx_environments_brand ON environments(brand_id);

-- ============================================
-- Seed: Sportstech brand
-- ============================================
INSERT INTO brands (name, slug, shop_url, config)
VALUES (
  'Sportstech',
  'sportstech',
  'https://www.sportstech.de',
  '{"platform": "shopware", "market": "DACH", "language": "de", "currency": "EUR"}'
);
