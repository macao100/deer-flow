import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type UpdateApiKeyRequest,
  type UpdateApiKeyResponse,
  loadApiKeys,
  updateApiKey,
} from "./api";

const QUERY_KEY = ["api-keys"] as const;

export function useApiKeys() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: loadApiKeys,
    staleTime: 30_000,
  });
}

export function useUpdateApiKey() {
  const queryClient = useQueryClient();
  return useMutation<UpdateApiKeyResponse, Error, UpdateApiKeyRequest>({
    mutationFn: updateApiKey,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
