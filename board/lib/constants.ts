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

export const ENVIRONMENTS = [
  { value: "scandinavian", label: "Scandinavian" },
  { value: "loft_industrial", label: "Industrial" },
  { value: "contemporary_traditional", label: "Traditional" },
  { value: "german_modern", label: "Modern" },
  { value: "japandi_wellness", label: "Japandi" },
  { value: "home_office", label: "Home Office" },
  { value: "dark_evening", label: "Evening" },
] as const;

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
