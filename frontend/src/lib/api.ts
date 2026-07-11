const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}
