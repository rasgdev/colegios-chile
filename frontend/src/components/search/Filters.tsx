import { useQuery } from "@tanstack/react-query";
import Combobox from "./Combobox";
import { EMPTY_FILTERS, getComunas, getRegiones, queryKeys, type FiltersState } from "../../lib/api";
import {
  DEPENDENCIAS,
  ETIQUETAS,
  NIVELES,
  REGIMENES,
  dependenciaLabel,
  etiquetaLabel,
  nivelLabel,
  regimenLabel,
} from "../../lib/format";

type Props = {
  filters: FiltersState;
  onChange: (f: FiltersState) => void;
};

const selectCls =
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/30 disabled:bg-slate-100 disabled:text-slate-400";

const COPAGO_OPTIONS = [
  { value: "", label: "Cualquier valor" },
  { value: "0", label: "Gratuito" },
  { value: "50000", label: "Hasta $50.000" },
  { value: "100000", label: "Hasta $100.000" },
  { value: "200000", label: "Hasta $200.000" },
];

export default function Filters({ filters, onChange }: Props) {
  const { data: regiones, isLoading: regionesLoading } = useQuery({
    queryKey: queryKeys.regiones,
    queryFn: getRegiones,
  });

  const { data: comunas, isLoading: comunasLoading } = useQuery({
    queryKey: queryKeys.comunas(filters.region as number),
    queryFn: () => getComunas(filters.region as number),
    enabled: filters.region != null,
  });

  const set = (patch: Partial<FiltersState>) => onChange({ ...filters, ...patch });

  const handleRegion = (value: string) => {
    const code = value === "" ? null : Number(value);
    onChange({ ...filters, region: code, comuna: "" });
  };

  const toggleEtiqueta = (et: string) => {
    const has = filters.etiquetas.includes(et);
    set({
      etiquetas: has
        ? filters.etiquetas.filter((x) => x !== et)
        : [...filters.etiquetas, et],
    });
  };

  const comunaOptions = [
    { value: "", label: "Todas las comunas" },
    ...(comunas ?? []).map((c) => ({ value: c.nombre, label: c.nombre })),
  ];

  return (
    <aside className="h-fit space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:sticky lg:top-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        Filtros
      </h2>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-region">
          Región
        </label>
        <select
          id="f-region"
          className={selectCls}
          value={filters.region ?? ""}
          onChange={(e) => handleRegion(e.target.value)}
          disabled={regionesLoading}
        >
          <option value="">Todas las regiones</option>
          {regiones?.map((r) => (
            <option key={r.codigo} value={r.codigo}>
              {r.nombre}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-comuna">
          Comuna
        </label>
        <Combobox
          id="f-comuna"
          value={filters.comuna}
          onChange={(v) => set({ comuna: v })}
          options={comunaOptions}
          placeholder="Busca una comuna…"
          disabled={filters.region == null || comunasLoading}
        />
        {filters.region == null && (
          <p className="mt-1 text-xs text-slate-400">Elige una región para filtrar por comuna.</p>
        )}
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-dependencia">
          Dependencia
        </label>
        <select
          id="f-dependencia"
          className={selectCls}
          value={filters.dependencia}
          onChange={(e) => set({ dependencia: e.target.value })}
        >
          <option value="">Todas</option>
          {DEPENDENCIAS.map((d) => (
            <option key={d} value={d}>
              {dependenciaLabel(d)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-regimen">
          Régimen
        </label>
        <select
          id="f-regimen"
          className={selectCls}
          value={filters.regimen}
          onChange={(e) => set({ regimen: e.target.value })}
        >
          <option value="">Todos</option>
          {REGIMENES.map((r) => (
            <option key={r} value={r}>
              {regimenLabel(r)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-nivel">
          Nivel
        </label>
        <select
          id="f-nivel"
          className={selectCls}
          value={filters.nivel}
          onChange={(e) => set({ nivel: e.target.value })}
        >
          <option value="">Todos</option>
          {NIVELES.map((n) => (
            <option key={n} value={n}>
              {nivelLabel(n)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="f-copago">
          Copago máximo
        </label>
        <select
          id="f-copago"
          className={selectCls}
          value={filters.copago_max ?? ""}
          onChange={(e) =>
            set({ copago_max: e.target.value === "" ? null : Number(e.target.value) })
          }
        >
          {COPAGO_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <fieldset>
        <legend className="mb-2 text-sm font-medium text-slate-700">Características</legend>
        <div className="flex flex-wrap gap-2">
          {ETIQUETAS.map((et) => (
            <button
              key={et}
              type="button"
              onClick={() => toggleEtiqueta(et)}
              aria-pressed={filters.etiquetas.includes(et)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                filters.etiquetas.includes(et)
                  ? "border-brand-600 bg-brand-600 text-white"
                  : "border-slate-300 bg-white text-slate-700 hover:border-brand-600"
              }`}
            >
              {etiquetaLabel(et)}
            </button>
          ))}
        </div>
      </fieldset>

      <button
        type="button"
        onClick={() => onChange(EMPTY_FILTERS)}
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100"
      >
        Limpiar filtros
      </button>
    </aside>
  );
}
