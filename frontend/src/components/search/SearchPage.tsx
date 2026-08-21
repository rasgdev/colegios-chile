import { useEffect, useState } from "react";
import {
  keepPreviousData,
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import SearchBox from "./SearchBox";
import Filters from "./Filters";
import ResultsList from "./ResultsList";
import {
  EMPTY_FILTERS,
  queryKeys,
  searchSchools,
  type FiltersState,
  type SearchParams,
} from "../../lib/api";

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

const LIMIT = 20;

function SearchExperience() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<FiltersState>(EMPTY_FILTERS);
  const [page, setPage] = useState(0);

  const debouncedQ = useDebouncedValue(q, 300);

  const params: SearchParams = {
    q: debouncedQ.trim() || undefined,
    ...filters,
    limit: LIMIT,
    offset: page * LIMIT,
  };

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: queryKeys.search(params),
    queryFn: () => searchSchools(params),
    placeholderData: keepPreviousData,
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / LIMIT)) : 1;

  return (
    <div className="flex flex-col gap-6">
      <SearchBox
        value={q}
        onChange={(v) => {
          setQ(v);
          setPage(0);
        }}
      />
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Filters
          filters={filters}
          onChange={(f) => {
            setFilters(f);
            setPage(0);
          }}
        />
        <ResultsList
          data={data}
          isLoading={isLoading}
          isError={isError}
          isFetching={isFetching}
          page={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </div>
    </div>
  );
}

export default function SearchPage() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <SearchExperience />
    </QueryClientProvider>
  );
}
