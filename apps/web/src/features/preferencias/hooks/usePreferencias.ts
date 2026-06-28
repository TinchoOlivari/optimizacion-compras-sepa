import { useQuery } from "@tanstack/react-query";

import type { PreferenciasResponse } from "@/lib/api";
import { getPreferencias } from "@/lib/api";

import { preferenciasQueryKeys } from "../lib/queryKeys";

export function usePreferencias(enabled = true) {
  return useQuery<PreferenciasResponse>({
    queryKey: preferenciasQueryKeys.actuales(),
    queryFn: getPreferencias,
    enabled,
    retry: 1,
  });
}
