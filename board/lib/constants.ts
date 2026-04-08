export const PRODUCTS = [
  { value: "walking_pad", label: "WoodPad Pro" },
  { value: "treadmill", label: "F37s Pro" },
  { value: "speedbike", label: "sBike" },
  { value: "ergometer", label: "X150" },
  { value: "crosstrainer", label: "sCross" },
  { value: "rowing_machine", label: "AquaElite" },
  { value: "power_station", label: "sGym Pro / HGX50" },
  { value: "smith_machine", label: "SXM200" },
  { value: "vibration_plate", label: "sVibe" },
] as const;

export const PRODUCT_LABELS: Record<string, string> = Object.fromEntries(
  PRODUCTS.map((p) => [p.value, p.label])
);

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

export const FORMATS = [
  { value: "9:16", label: "9:16 Story" },
  { value: "1:1", label: "1:1 Feed" },
  { value: "16:9", label: "16:9 Wide" },
] as const;

export const CREATIVE_TYPES = [
  { value: "lifestyle", label: "Lifestyle" },
  { value: "multishot", label: "Multishot" },
  { value: "color_variant", label: "Variant" },
] as const;
