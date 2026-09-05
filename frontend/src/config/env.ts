function requiredUrl(name: string, value: string | undefined): string {
  if (!value) throw new Error(`${name} is not configured`);
  try {
    const url = new URL(value);
    const browserHost = window.location.hostname;
    const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1"]);
    if (loopbackHosts.has(url.hostname) && loopbackHosts.has(browserHost)) {
      url.hostname = browserHost;
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    throw new Error(`${name} must be an absolute URL`);
  }
}

export const env = Object.freeze({
  apiBaseUrl: requiredUrl("VITE_API_BASE_URL", import.meta.env.VITE_API_BASE_URL),
});
