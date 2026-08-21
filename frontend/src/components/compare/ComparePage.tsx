import { useEffect, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import {
  compareSchools,
  queryKeys,
  searchSchools,
  type IndicadorOut,
  type SedeOut,
} from "../../lib/api";
import {
  copagoResumen,
  dependenciaLabel,
  gseLabel,
  gseVeredict,
  indicadorDef,
  nivelEducativoLabel,
  regimenLabel,
} from "../../lib/format";

const MAX = 10;

function readInitialRbds(): number[] {
  if (typeof window === "undefined") return [];
  const raw = new URLSearchParams(window.location.search).get("rbds");
  if (!raw) return [];
  return raw
    .split(",")
    .map(Number)
    .filter((n) => Number.isInteger(n) && n > 0)
    .slice(0, MAX);
}

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

type IndKey = { nombre: string; nivel: string | null };

function collectKeys(
  indicadores: Record<string, IndicadorOut[]>,
  tipo: string,
): IndKey[] {
  const map = new Map<string, IndKey>();
  for (const list of Object.values(indicadores)) {
    for (const ind of list) {
      if (ind.tipo_indicador !== tipo) continue;
      const key = `${ind.nombre_indicador}|${ind.nivel_indicador ?? ""}`;
      if (!map.has(key)) {
        map.set(key, { nombre: ind.nombre_indicador, nivel: ind.nivel_indicador ?? null });
      }
    }
  }
  return Array.from(map.values());
}

function dotClass(glosa: string | null | undefined): string {
  switch (gseVeredict(glosa)) {
    case "alto":
      return "bg-green-500";
    case "similar":
      return "bg-slate-400";
    case "bajo":
      return "bg-red-500";
    default:
      return "bg-slate-300";
  }
}

function ubicacionSedes(sedes: SedeOut[]): string {
  return sedes
    .map((s) => [s.calle, s.comuna, s.region].filter((v) => !!v).join(", "))
    .join("\n");
}

function CompareExperience() {
  const [rbds, setRbds] = useState<number[]>(readInitialRbds);
  const [term, setTerm] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  const debouncedTerm = useDebouncedValue(term.trim(), 300);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const qs = rbds.length ? `?rbds=${rbds.join(",")}` : window.location.pathname;
    window.history.replaceState(null, "", qs);
  }, [rbds]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const { data: suggestions } = useQuery({
    queryKey: ["picker", debouncedTerm],
    queryFn: () => searchSchools({ q: debouncedTerm, limit: 8 }),
    enabled: debouncedTerm.length >= 2,
  });

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.compare(rbds),
    queryFn: () => compareSchools(rbds),
    enabled: rbds.length > 0,
  });

  const addRbd = (rbd: number) => {
    if (rbds.length >= MAX) return;
    if (rbds.includes(rbd)) return;
    setRbds([...rbds, rbd]);
    setTerm("");
    setPickerOpen(false);
  };

  const removeRbd = (rbd: number) => setRbds(rbds.filter((r) => r !== rbd));

  const establecimientos = data?.establecimientos ?? [];
  const simceKeys = data ? collectKeys(data.indicadores, "SIMCE") : [];
  const desarrolloKeys = data ? collectKeys(data.indicadores, "DESARROLLO_PERSONAL") : [];

  const sectionRow = (title: string) => (
    <tr className="border-b border-slate-200 bg-slate-50">
      <td colSpan={establecimientos.length + 1} className="px-4 py-2 text-sm font-semibold text-slate-600">
        {title}
      </td>
    </tr>
  );

  const indicatorRow = (key: IndKey) => {
    const label = key.nivel
      ? `${key.nombre} · ${nivelEducativoLabel(key.nivel)}`
      : key.nombre;
    return (
      <tr key={`${key.nombre}-${key.nivel}`}>
        <td className="px-4 py-2 text-slate-600">
          <span title={indicadorDef(key.nombre)}>{label}</span>
        </td>
        {establecimientos.map((e) => {
          const ind = data?.indicadores[String(e.rbd)]?.find(
            (i) => i.nombre_indicador === key.nombre && i.nivel_indicador === key.nivel,
          );
          return (
            <td key={e.rbd} className="px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{ind?.puntaje != null ? ind.puntaje : "—"}</span>
                <span
                  title={gseLabel(ind?.comparacion_gse_glosa)}
                  className={`h-2.5 w-2.5 rounded-full ${dotClass(ind?.comparacion_gse_glosa)}`}
                ></span>
              </div>
            </td>
          );
        })}
      </tr>
    );
  };

  return (
    <div className="space-y-6">
      <div ref={pickerRef} className="relative max-w-xl">
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="picker">
          Agrega colegios para comparar (hasta {MAX})
        </label>
        <input
          id="picker"
          type="search"
          value={term}
          onChange={(e) => {
            setTerm(e.target.value);
            setPickerOpen(true);
          }}
          onFocus={() => setPickerOpen(true)}
          placeholder="Busca por nombre…"
          className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-base shadow-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/30"
        />
        {pickerOpen && suggestions && suggestions.results.length > 0 && (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg">
            {suggestions.results.map((s) => (
              <li key={s.rbd}>
                <button
                  type="button"
                  onClick={() => addRbd(s.rbd)}
                  disabled={rbds.includes(s.rbd)}
                  className="flex w-full items-center justify-between px-4 py-2 text-left text-sm hover:bg-brand-50 disabled:opacity-40"
                >
                  <span className="truncate">{s.nombre}</span>
                  <span className="ml-2 shrink-0 text-xs text-slate-400">
                    {dependenciaLabel(s.dependencia)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {rbds.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {rbds.map((rbd) => {
            const est = establecimientos.find((e) => e.rbd === rbd);
            return (
              <span
                key={rbd}
                className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-sm text-brand-800"
              >
                {est?.nombre ?? `Colegio ${rbd}`}
                <button
                  type="button"
                  onClick={() => removeRbd(rbd)}
                  aria-label={`Quitar ${est?.nombre ?? rbd}`}
                  className="text-brand-600 hover:text-brand-800"
                >
                  ×
                </button>
              </span>
            );
          })}
        </div>
      )}

      {isLoading && <p className="text-slate-500">Cargando comparación…</p>}
      {isError && (
        <p className="text-red-600">No se pudo cargar la comparación. Revisa el backend.</p>
      )}

      {data && establecimientos.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">
            El puntaje es comparable entre colegios. El color compara cada colegio con su propio
            grupo socioeconómico, no con los otros colegios de esta tabla.
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[600px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Atributo</th>
                  {establecimientos.map((e) => (
                    <th key={e.rbd} className="px-4 py-3 text-left font-semibold text-slate-900">
                      <a href={`/colegio/${e.rbd}`} className="hover:text-brand-600">
                        {e.nombre}
                      </a>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sectionRow("Datos generales")}
                <tr>
                  <td className="px-4 py-2 text-slate-600">Dependencia</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2">{dependenciaLabel(e.dependencia)}</td>
                  ))}
                </tr>
                <tr>
                  <td className="px-4 py-2 text-slate-600">Régimen</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2">
                      {e.regimen ? regimenLabel(e.regimen) : "—"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-4 py-2 text-slate-600">Ubicación</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2 whitespace-pre-line">
                      {ubicacionSedes(data.sedes[String(e.rbd)] ?? []) || "—"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-4 py-2 text-slate-600">Niveles</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2">
                      {e.nivel_minimo ?? "—"} a {e.nivel_maximo ?? "—"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <td className="px-4 py-2 text-slate-600">Estudiantes matriculados</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2">
                      {e.alumnos_matriculados != null
                        ? e.alumnos_matriculados.toLocaleString("es-CL")
                        : "—"}
                    </td>
                  ))}
                </tr>

                {sectionRow("Copago")}
                <tr>
                  <td className="px-4 py-2 text-slate-600">Copago mensual</td>
                  {establecimientos.map((e) => (
                    <td key={e.rbd} className="px-4 py-2">
                      {copagoResumen(data.cursos_resumen[String(e.rbd)] ?? [])}
                    </td>
                  ))}
                </tr>

                {simceKeys.length > 0 && (
                  <>
                    {sectionRow("SIMCE")}
                    {simceKeys.map(indicatorRow)}
                  </>
                )}

                {desarrolloKeys.length > 0 && (
                  <>
                    {sectionRow("Desarrollo personal")}
                    {desarrolloKeys.map(indicatorRow)}
                  </>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <CompareExperience />
    </QueryClientProvider>
  );
}
