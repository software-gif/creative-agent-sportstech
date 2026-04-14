-- Backfill parent_id on orphaned multishot and color_variant creatives.
--
-- The multishot and color-variant skills used to not populate the
-- creatives.parent_id column. They did however stash the source image
-- path under prompt_json.source_image. We can recover the lineage by
-- joining that back to the parent lifestyle creative via storage_path.
--
-- Safe to run repeatedly — only touches rows where parent_id is still NULL.

UPDATE creatives c
SET parent_id = p.id
FROM creatives p
WHERE c.parent_id IS NULL
  AND c.creative_type IN ('multishot', 'color_variant')
  AND p.creative_type = 'lifestyle'
  AND p.storage_path = c.prompt_json->>'source_image';
