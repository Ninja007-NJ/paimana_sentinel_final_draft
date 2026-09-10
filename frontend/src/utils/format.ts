export const percent = (value: number | null | undefined, digits = 1) => value == null ? "Not available" : `${(value * 100).toFixed(digits)}%`;
export const number = (value: number | null | undefined, digits = 0) => value == null ? "Not available" : value.toLocaleString("en-IN", { maximumFractionDigits: digits });
export const crore = (value: number | null | undefined) => value == null ? "Not available" : `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })} Cr`;
export const month = (value: string | null | undefined) => value ? new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric" }).format(new Date(`${value}-01T00:00:00`)) : "Not available";
export const text = (value: unknown) => value == null ? "Not available" : String(value).trim() || "Not available";
