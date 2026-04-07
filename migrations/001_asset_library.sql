-- Migration: Asset Library + Multi-Brand support
-- Run this in the Supabase SQL Editor for project uftxyftpsdvgtlowrpel

-- 1. Add new columns to creatives
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id) ON DELETE CASCADE;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS batch_id UUID;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS is_saved BOOLEAN DEFAULT FALSE;

-- 2. Asset Folders
CREATE TABLE IF NOT EXISTS asset_folders (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  parent_folder_id UUID REFERENCES asset_folders(id) ON DELETE CASCADE,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Saved Assets (join table: creative → folder)
CREATE TABLE IF NOT EXISTS saved_assets (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  creative_id UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
  folder_id UUID REFERENCES asset_folders(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(creative_id)
);

-- 4. RLS Policies
ALTER TABLE asset_folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_assets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read asset_folders" ON asset_folders
  FOR SELECT USING (true);

CREATE POLICY "Public insert asset_folders" ON asset_folders
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Public update asset_folders" ON asset_folders
  FOR UPDATE USING (true);

CREATE POLICY "Public delete asset_folders" ON asset_folders
  FOR DELETE USING (true);

CREATE POLICY "Public read saved_assets" ON saved_assets
  FOR SELECT USING (true);

CREATE POLICY "Public insert saved_assets" ON saved_assets
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Public update saved_assets" ON saved_assets
  FOR UPDATE USING (true);

CREATE POLICY "Public delete saved_assets" ON saved_assets
  FOR DELETE USING (true);

-- 5. Enable Realtime for saved_assets
ALTER PUBLICATION supabase_realtime ADD TABLE saved_assets;

-- 6. Backfill brand_id for any existing rows, then enforce NOT NULL
-- UPDATE creatives SET brand_id = (SELECT id FROM brands LIMIT 1) WHERE brand_id IS NULL;
-- ALTER TABLE creatives ALTER COLUMN brand_id SET NOT NULL;
-- NOTE: Run the above manually after inserting your brand, if needed.
