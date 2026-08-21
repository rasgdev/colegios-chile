import { useEffect, useRef, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { compareSchools, queryKeys, searchSchools } from "../../lib/api";
import { dependenciaLabel, regimenLabel } from "../../lib/format";

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
  const indicadorKeys = Array.from(
    new Set(
      (data ? Object.values(data.indicadores).flat() : []).map((i) => i.nombre_indicador),
    ),
  );

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
                    {dependenciaLabel(s.dependencia)} · RBD {s.rbd}
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
                {est?.nombre ?? `RBD ${rbd}`}
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
              <tr>
                <td className="px-4 py-2 font-medium text-slate-500">RBD</td>
                {establecimientos.map((e) => (
                  <td key={e.rbd} className="px-4 py-2">{e.rbd}</td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium text-slate-500">Dependencia</td>
                {establecimientos.map((e) => (
                  <td key={e.rbd} className="px-4 py-2">{dependenciaLabel(e.dependencia)}</td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium text-slate-500">Régimen</td>
                {establecimientos.map((e) => (
                  <td key={e.rbd} className="px-4 py-2">
                    {e.regimen ? regimenLabel(e.regimen) : "—"}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium text-slate-500">Niveles</td>
                {establecimientos.map((e) => (
                  <td key={e.rbd} className="px-4 py-2">
                    {e.nivel_minimo ?? "—"} a {e.nivel_maximo ?? "—"}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="px-4 py-2 font-medium text-slate-500">Matrícula</td>
                {establecimientos.map((e) => (
                  <td key={e.rbd} className="px-4 py-2">
                    {e.alumnos_matriculados != null
                      ? e.alumnos_matriculados.toLocaleString("es-CL")
                      : "—"}
                  </td>
                ))}
              </tr>
              {indicadorKeys.map((key) => (
                <tr key={key}>
                  <td className="px-4 py-2 font-medium text-slate-500">{key}</td>
                  {establecimientos.map((e) => {
                    const ind = data.indicadores[String(e.rbd)]?.find(
                      (i) => i.nombre_indicador === key,
                    );
                    return (
                      <td key={e.rbd} className="px-4 py-2">
                        {ind?.puntaje != null ? ind.puntaje : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
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
