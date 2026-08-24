function requiredUrl(name: string, value: string | undefined): string {
  if (!value) throw new Error(`${name} is not configured`);
  try {
    return new URL(value).toString().replace(/\/$/, "");
  } catch {
    throw new Error(`${name} must be an absolute URL`);
  }
}

export const env = Object.freeze({
  apiBaseUrl: requiredUrl("VITE_API_BASE_URL", import.meta.env.VITE_API_BASE_URL),
});
