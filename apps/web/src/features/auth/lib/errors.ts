import { ApiError } from "@/lib/api";

interface ApiErrorBody {
  error?: { codigo?: string; mensaje?: string };
}

function isApiErrorBody(body: unknown): body is ApiErrorBody {
  if (typeof body !== "object" || body === null) {
    return false;
  }

  const record = body as Record<string, unknown>;
  const error = record.error;
  return error === undefined || typeof error === "object";
}

export function mensajeDesdeError(error: unknown, fallback: string): string {
  if (error instanceof ApiError && isApiErrorBody(error.body)) {
    return error.body.error?.mensaje ?? fallback;
  }

  return fallback;
}

export function esErrorCorreoDuplicado(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}
