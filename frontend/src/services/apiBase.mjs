export function normalizeApiBase(configuredBase) {
  return (configuredBase?.trim() || "/api").replace(/\/+$/, "");
}
