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
    PIE: "Integración escolar (PIE)",
    SEP: "Subvención preferencial (SEP)",
    TECNICO_PROFESIONAL: "Técnico-profesional",
    _4MEDIO: "Hasta 4° medio",
  };
  return map[e] ?? e;
}

export function nivelEducativoLabel(n: string | null | undefined): string {
  const map: Record<string, string> = {
    Básica: "Enseñanza Básica",
    Media: "Enseñanza Media",
  };
  return n ? map[n] ?? n : "—";
}

export type GseVeredict = "alto" | "similar" | "bajo" | "sin-dato";

export function gseVeredict(glosa: string | null | undefined): GseVeredict {
  const g = (glosa ?? "").trim().toLowerCase();
  if (g.includes("más alto")) return "alto";
  if (g.includes("similar")) return "similar";
  if (g.includes("más bajo")) return "bajo";
  return "sin-dato";
}

export function gseLabel(glosa: string | null | undefined): string {
  switch (gseVeredict(glosa)) {
    case "alto":
      return "Mejor que colegios similares";
    case "similar":
      return "En la media de colegios similares";
    case "bajo":
      return "Más bajo que colegios similares";
    default:
      return "Sin comparación disponible";
  }
}

export function sanitizeText(s: string | null | undefined): string {
  if (!s) return "";
  return s
    // eslint-disable-next-line no-control-regex
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function normalizeUrl(url: string | null | undefined): string {
  if (!url) return "#";
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

export function indicadorDef(nombre: string): string {
  const defs: Record<string, string> = {
    "Autoestima académica y motivación escolar":
      "Percepción del estudiante sobre su capacidad de aprender y su motivación hacia el logro académico.",
    "Clima de convivencia escolar":
      "Percepción de un ambiente de respeto, organizado y seguro en el establecimiento.",
    "Participación y formación ciudadana":
      "Actitud hacia el colegio y cuánto se fomenta la participación y la vida democrática.",
    "Hábitos de vida saludable":
      "Conductas de autocuidado y cuánto el colegio promueve hábitos sanos.",
    Lenguaje: "Puntaje SIMCE de Lenguaje (lectura).",
    Matemática: "Puntaje SIMCE de Matemática.",
  };
  return defs[nombre] ?? "";
}

export function copagoResumen(cursos: { copago_valor?: number | null }[]): string {
  const valores = cursos
    .map((c) => c.copago_valor)
    .filter((v): v is number => v != null);
  if (valores.length === 0) return "Sin información de copago";
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  if (min === 0 && max === 0) return "Gratuito";
  if (min === max) return `${formatClp(min)} mensual`;
  return `Desde ${formatClp(min)} hasta ${formatClp(max)} mensual`;
}
