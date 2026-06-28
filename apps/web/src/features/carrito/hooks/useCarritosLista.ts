import { useQuery } from "@tanstack/react-query";

import { getCarritos } from "@/lib/api";

import { carritoQueryKeys } from "../lib/queryKeys";

export function useCarritosLista() {
  return useQuery({
    queryKey: carritoQueryKeys.lista(),
    queryFn: getCarritos,
    retry: 1,
  });
}
