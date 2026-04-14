// Each product is its own entry keyed by the exact handle from
// product_knowledge.json. Two products can share a Shopware category
// (power_station is both sgym-pro AND hgx50) — we intentionally treat
// them as separate products so the filters, labels, and QC can all
// distinguish them.
export const PRODUCTS = [
  { value: "woodpad-pro",  label: "WoodPad Pro",  category: "walking_pad" },
  { value: "f37s-pro",     label: "F37s Pro",     category: "treadmill" },
  { value: "sbike",        label: "sBike",        category: "speedbike" },
  { value: "x150",         label: "X150",         category: "ergometer" },
  { value: "scross",       label: "sCross",       category: "crosstrainer" },
  { value: "aqua-elite",   label: "AquaElite",    category: "rowing_machine" },
  { value: "sgym-pro",     label: "sGym Pro",     category: "power_station" },
  { value: "hgx50",        label: "HGX50",        category: "power_station" },
  { value: "sxm200",       label: "SXM200",       category: "smith_machine" },
  { value: "svibe",        label: "sVibe",        category: "vibration_plate" },
] as const;

export const PRODUCT_LABELS: Record<string, string> = Object.fromEntries(
  PRODUCTS.map((p) => [p.value, p.label])
);

// Legacy category → default handle map, used when a creative only has
// `product_category` and no `prompt_json.product` (pre-dates the handle fix).
// For `power_station` we default to sgym-pro arbitrarily; the proper
// resolver in `resolveProductHandle` prefers `prompt_json.product` first.
export const CATEGORY_DEFAULT_HANDLE: Record<string, string> = {
  walking_pad:     "woodpad-pro",
  treadmill:       "f37s-pro",
  speedbike:       "sbike",
  ergometer:       "x150",
  crosstrainer:    "scross",
  rowing_machine:  "aqua-elite",
  power_station:   "sgym-pro",
  smith_machine:   "sxm200",
  vibration_plate: "svibe",
};

// Map room_preset IDs to display-friendly environment categories
export const ENVIRONMENTS = [
  { value: "scandinavian", label: "Scandinavian", presets: ["scandinavian", "scandi_minimal", "scandi_sunlit", "golden_hour_cozy"] },
  { value: "loft_industrial", label: "Industrial", presets: ["loft_industrial", "urban_loft_eclectic", "urban_loft_golden", "industrial_home_gym"] },
  { value: "contemporary_traditional", label: "Traditional", presets: ["contemporary_traditional", "terracotta_traditional"] },
  { value: "german_modern", label: "Modern", presets: ["german_modern", "indoor_outdoor_modern", "sunlit_walnut"] },
  { value: "japandi_wellness", label: "Japandi", presets: ["japandi_wellness", "japandi_sideboard", "japandi_media", "japandi_bookcase", "walnut_accent_study"] },
  { value: "home_office", label: "Home Office", presets: ["home_office"] },
  { value: "dark_evening", label: "Evening", presets: ["dark_evening", "moody_lounge", "eclectic_lounge"] },
  { value: "luxury", label: "Luxury", presets: ["luxury_penthouse", "villa_panorama", "penthouse_balcony"] },
] as const;

// Build a reverse map: preset_id → category value
export const PRESET_TO_ENV: Record<string, string> = {};
ENVIRONMENTS.forEach((env) => {
  env.presets.forEach((preset) => {
    PRESET_TO_ENV[preset] = env.value;
  });
});

export const ENV_LABELS: Record<string, string> = Object.fromEntries(
  ENVIRONMENTS.map((e) => [e.value, e.label])
);

export const CAMERA_ANGLES = [
  "Eye level",
  "Slightly above",
  "High angle",
  "Slightly below",
  "Low angle",
  "Ground level",
] as const;

export const CHARACTER_ANGLES = [
  "Front facing",
  "3/4 angle",
  "Profile",
  "Over the shoulder",
  "Back view",
  "Top View",
] as const;

export const FORMATS = [
  { value: "9:16", label: "9:16 Story" },
  { value: "1:1", label: "1:1 Feed" },
  { value: "16:9", label: "16:9 Wide" },
] as const;

export const CREATIVE_TYPES = [
  { value: "lifestyle", label: "Key Visuals" },
  { value: "multishot", label: "Angles" },
  { value: "color_variant", label: "Colors" },
] as const;
