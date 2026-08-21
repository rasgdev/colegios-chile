import type { EstablecimientoListItem } from "../lib/api";
import { dependenciaLabel, etiquetaLabel, regimenLabel } from "../lib/format";

export default function SchoolCard({ school }: { school: EstablecimientoListItem }) {
  return (
    <a
      href={`/colegio/${school.rbd}`}
      className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-600 hover:shadow-md"
    >
      <h3 className="text-lg font-semibold text-slate-900">{school.nombre}</h3>
      <p className="mt-1 text-sm text-slate-600">
        {dependenciaLabel(school.dependencia)}
        {school.regimen ? ` · ${regimenLabel(school.regimen)}` : ""}
      </p>

      {school.etiquetas.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {school.etiquetas.map((et) => (
            <span
              key={et}
              className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700"
            >
              {etiquetaLabel(et)}
            </span>
          ))}
        </div>
      )}

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-slate-500">Niveles</dt>
          <dd className="font-medium">
            {school.nivel_minimo ?? "—"} a {school.nivel_maximo ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500">Estudiantes matriculados</dt>
          <dd className="font-medium">
            {school.alumnos_matriculados != null
              ? school.alumnos_matriculados.toLocaleString("es-CL")
              : "—"}
          </dd>
        </div>
      </dl>
    </a>
  );
}
