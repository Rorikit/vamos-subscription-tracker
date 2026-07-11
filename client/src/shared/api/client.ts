import { getAuthToken } from "./authToken";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ошибка API" }));
    throw new Error(error.detail ?? "Ошибка API");
  }

  return response.json() as Promise<T>;
}

export const toCurrency = (value: string | number) =>
  new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(Number(value));

export const toDate = (value?: string | null) => (value ? new Intl.DateTimeFormat("ru-RU").format(new Date(value)) : "—");
