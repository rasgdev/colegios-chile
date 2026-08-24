import type { components } from "./types";

export type EstablecimientoListItem = components["schemas"]["EstablecimientoListItem"];
export type EstablecimientoOut = components["schemas"]["EstablecimientoOut"];
export type SearchResponse = components["schemas"]["SearchResponse"];
export type FichaOut = components["schemas"]["FichaOut"];
export type CompareResponse = components["schemas"]["CompareResponse"];
export type RegionOut = components["schemas"]["RegionOut"];
export type ComunaOut = components["schemas"]["ComunaOut"];
export type SedeOut = components["schemas"]["SedeOut"];
export type CursoResumenOut = components["schemas"]["CursoResumenOut"];
export type IndicadorOut = components["schemas"]["IndicadorOut"];
export type ActividadOut = components["schemas"]["ActividadOut"];
export type ImagenOut = components["schemas"]["ImagenOut"];

const getApiBase = (): string => {
  if (import.meta.env.PUBLIC_API_BASE_URL) {
    return import.meta.env.PUBLIC_API_BASE_URL;
  }
  if (import.meta.env.PROD) {
    return "/api/v1";
  }
  return "http://localhost:8000/api/v1";
};

export const API_BASE = getApiBase();

export type SearchParams = {
  q?: string;
  comuna?: string;
  region?: number | null;
  dependencia?: string;
  regimen?: string;
  nivel?: string;
  copago_max?: number | null;
  etiquetas?: string[];
  limit?: number;
  offset?: number;
};

export type FiltersState = {
  comuna: string;
  region: number | null;
  dependencia: string;
  regimen: string;
  nivel: string;
  copago_max: number | null;
  etiquetas: string[];
};

export const EMPTY_FILTERS: FiltersState = {
  comuna: "",
  region: null,
  dependencia: "",
  regimen: "",
  nivel: "",
  copago_max: null,
  etiquetas: [],
};

function buildQuery(
  params: Record<string, string | number | string[] | undefined | null>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value == null || value === "") continue;
    if (Array.isArray(value)) {
      value.forEach((v) => search.append(key, v));
    } else {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} al consultar ${path}`);
  }
  return res.json() as Promise<T>;
}

export function searchSchools(params: SearchParams): Promise<SearchResponse> {
  return fetchJson<SearchResponse>(
    `/search${buildQuery({ ...params, limit: params.limit ?? 20, offset: params.offset ?? 0 })}`,
  );
}

export function getFicha(rbd: number): Promise<FichaOut> {
  return fetchJson<FichaOut>(`/establecimientos/${rbd}`);
}

export function getRegiones(): Promise<RegionOut[]> {
  return fetchJson<RegionOut[]>("/regiones");
}

export function getComunas(region: number): Promise<ComunaOut[]> {
  return fetchJson<ComunaOut[]>(`/comunas?region=${region}`);
}

export function compareSchools(rbds: number[]): Promise<CompareResponse> {
  return fetchJson<CompareResponse>(`/compare?rbds=${rbds.join(",")}`);
}

export const queryKeys = {
  search: (params: SearchParams) => ["search", params] as const,
  regiones: ["regiones"] as const,
  comunas: (region: number) => ["comunas", region] as const,
  compare: (rbds: number[]) => ["compare", rbds] as const,
};
