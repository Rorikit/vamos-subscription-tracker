const basePath = (import.meta.env.VITE_BASE_PATH ?? "/").replace(/[^a-zA-Z0-9_-]+/g, "_");
const TOKEN_KEY = `vamos_access_token_${basePath || "_"}`;

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuthToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
}
