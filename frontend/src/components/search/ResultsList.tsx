import type { SearchResponse } from "../../lib/api";
import SchoolCard from "../SchoolCard";

type Props = {
  data: SearchResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
};

export default function ResultsList({
  data,
  isLoading,
  isError,
  isFetching,
  page,
  totalPages,
  onPageChange,
}: Props) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-40 animate-pulse rounded-lg bg-slate-200" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="font-medium text-red-700">No pudimos consultar el buscador.</p>
        <p className="mt-1 text-sm text-red-600">
          Revisa que el backend esté corriendo en el puerto 8000.
        </p>
      </div>
    );
  }

  if (!data || data.results.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
        <p className="font-medium text-slate-700">Sin resultados.</p>
        <p className="mt-1 text-sm text-slate-500">
          Prueba con otros términos de búsqueda o quita filtros.
        </p>
      </div>
    );
  }

  return (
    <div
      className={`space-y-4 transition-opacity ${isFetching ? "opacity-60" : "opacity-100"}`}
    >
      <p className="text-sm text-slate-600">
        <strong className="text-slate-900">{data.total.toLocaleString("es-CL")}</strong>{" "}
        {data.total === 1 ? "colegio encontrado" : "colegios encontrados"}
      </p>

      {data.results.map((school) => (
        <SchoolCard key={school.rbd} school={school} />
      ))}

      {totalPages > 1 && (
        <nav className="flex items-center justify-between pt-2" aria-label="Paginación">
          <button
            type="button"
            onClick={() => onPageChange(Math.max(0, page - 1))}
            disabled={page === 0}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-100 disabled:opacity-40"
          >
            Anterior
          </button>
          <span className="text-sm text-slate-600">
            Página {page + 1} de {totalPages}
          </span>
          <button
            type="button"
            onClick={() => onPageChange(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-100 disabled:opacity-40"
          >
            Siguiente
          </button>
        </nav>
      )}
    </div>
  );
}
