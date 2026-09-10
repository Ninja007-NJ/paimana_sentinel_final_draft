export type DisplayKind = "state" | "sector" | "ministry" | "agency" | "regime" | "identity" | "project";

const STATE_LABELS: Record<string, string> = {
  "andaman and": "Andaman and Nicobar Islands",
  "andaman & nicobar": "Andaman and Nicobar Islands",
  "andaman and nicobar": "Andaman and Nicobar Islands",
  chhattisgarh: "Chhattisgarh",
  goa: "Goa",
  ladakh: "Ladakh",
  "west bengal": "West Bengal",
  "pan india": "Pan-India",
};

const SECTOR_LABELS: Record<string, string> = {
  "civil aviation": "Civil Aviation",
  coal: "Coal",
  "department of higher education": "Higher Education",
  dpiit: "Industry and Internal Trade",
  finance: "Finance",
  "health and family welfare": "Health and Family Welfare",
  "higher education": "Higher Education",
  "home affairs": "Home Affairs",
  petroleum: "Petroleum and Natural Gas",
  power: "Power",
  railways: "Railways",
  "road transport": "Road Transport",
  "road transport and": "Road Transport and Highways",
  "road transport and highways": "Road Transport and Highways",
  "social justice": "Social Justice",
  steel: "Steel",
  "telecommuni cations": "Telecommunications",
  telecommunication: "Telecommunications",
  "urban development": "Urban Development",
  "water resources": "Water Resources",
};

const MINISTRY_LABELS: Record<string, string> = {
  "department for promotion of industry & internal trade": "Department for Promotion of Industry and Internal Trade",
  "department of water resources, river development & gr": "Department of Water Resources, River Development and Ganga Rejuvenation",
  "ministry of health & family welfare": "Ministry of Health and Family Welfare",
  "ministry of housing & urban affairs": "Ministry of Housing and Urban Affairs",
  "ministry of petroleum & natural gas": "Ministry of Petroleum and Natural Gas",
  "ministry of road transport & highways": "Ministry of Road Transport and Highways",
};

const REGIME_LABELS: Record<string, string> = {
  ocms_legacy: "Legacy OCMS",
  paimana: "PAIMANA",
  paimana_transition: "PAIMANA Transition",
};

const IDENTITY_LABELS: Record<string, string> = {
  fallback_generated: "Generated Fallback ID",
  legacy_ocms_id: "Legacy OCMS ID",
  paimana_id: "PAIMANA ID",
};

const ALERT_LABELS: Record<string, string> = {
  CRITICAL_RISK: "Critical Risk",
  RAPIDLY_RISING_RISK: "Rapidly Rising Risk",
  NEW_HIGH_RISK: "New High-Risk Project",
  LOW_CONFIDENCE_HIGH_RISK: "High Risk / Low Data Reliability",
  STAGNATING_PROJECT: "Project Progress Stagnating",
  REPEATED_TARGET_REVISION: "Repeated Completion-Date Revision",
};

export function collapseWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function displayValue(value: unknown, kind: DisplayKind = "project"): string {
  if (value == null) return "Not available";
  const cleaned = collapseWhitespace(String(value));
  if (!cleaned) return "Not available";
  const key = cleaned.toLocaleLowerCase("en-IN");
  const labels = kind === "state" ? STATE_LABELS
    : kind === "sector" ? SECTOR_LABELS
      : kind === "ministry" ? MINISTRY_LABELS
        : kind === "regime" ? REGIME_LABELS
          : kind === "identity" ? IDENTITY_LABELS
            : undefined;
  return labels?.[key] ?? cleaned;
}

export function alertTypeLabel(value: string): string {
  return ALERT_LABELS[value] ?? collapseWhitespace(value.replaceAll("_", " ").toLocaleLowerCase("en-IN").replace(/\b\w/g, letter => letter.toLocaleUpperCase("en-IN")));
}

export function peerFieldLabel(value: string): string {
  const labels: Record<string, string> = {
    sector: "Sector",
    state: "State",
    ministry_department: "Ministry / Department",
    cost_bucket: "Cost Range",
    age_bucket: "Project Age",
    progress_stage: "Progress Stage",
  };
  return labels[value] ?? collapseWhitespace(value.replaceAll("_", " "));
}

export function peerFieldValue(key: string, value: unknown): string {
  if (key === "sector" || key === "state") return displayValue(value, key);
  if (key === "ministry_department") return displayValue(value, "ministry");
  return displayValue(value);
}
