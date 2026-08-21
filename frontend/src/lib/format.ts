export const DEPENDENCIAS = [
  "PUBLICO",
  "PARTICULAR SUBVENCIONADO",
  "SERVICIO LOCAL DE EDUCACIÓN",
] as const;

export const REGIMENES = ["Mixto", "Hombres", "Mujeres"] as const;

export const NIVELES = ["PARVULARIO", "BASICA", "MEDIA"] as const;

export const ETIQUETAS = [
  "GRATUITO",
  "INTERNADO",
  "PIE",
  "SEP",
  "TECNICO_PROFESIONAL",
  "_4MEDIO",
] as const;

export function formatClp(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  }).format(value);
}

export function dependenciaLabel(dep: string): string {
  const map: Record<string, string> = {
    PUBLICO: "Público",
    "PARTICULAR SUBVENCIONADO": "Particular Subvencionado",
    "SERVICIO LOCAL DE EDUCACIÓN": "Servicio Local de Educación",
  };
  return map[dep] ?? dep;
}

export function regimenLabel(r: string): string {
  return r ?? "—";
}

export function nivelLabel(n: string): string {
  const map: Record<string, string> = {
    PARVULARIO: "Parvulario",
    BASICA: "Básica",
    MEDIA: "Media",
  };
  return map[n] ?? n;
}

export function etiquetaLabel(e: string): string {
  const map: Record<string, string> = {
    GRATUITO: "Gratuito",
    INTERNADO: "Internado",
    PIE: "PIE",
    SEP: "SEP",
    TECNICO_PROFESIONAL: "Técnico Profesional",
    _4MEDIO: "Hasta 4º Medio",
  };
  return map[e] ?? e;
}
