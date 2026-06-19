import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type ConfigWriteResponse,
  type GeneralConfigPatch,
  type ModelCreateRequest,
  type ModelUpdateRequest,
  addModel,
  deleteModel,
  loadGeneralConfig,
  loadModelsConfig,
  patchGeneralConfig,
  updateModel,
} from "./api";

const GENERAL_KEY = ["app-config", "general"] as const;
const MODELS_KEY = ["app-config", "models"] as const;

export function useGeneralConfig() {
  return useQuery({ queryKey: GENERAL_KEY, queryFn: loadGeneralConfig, staleTime: 30_000 });
}

export function usePatchGeneralConfig() {
  const qc = useQueryClient();
  return useMutation<ConfigWriteResponse, Error, GeneralConfigPatch>({
    mutationFn: patchGeneralConfig,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: GENERAL_KEY }); },
  });
}

export function useModelsConfig() {
  return useQuery({ queryKey: MODELS_KEY, queryFn: loadModelsConfig, staleTime: 30_000 });
}

export function useAddModel() {
  const qc = useQueryClient();
  return useMutation<ConfigWriteResponse, Error, ModelCreateRequest>({
    mutationFn: addModel,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MODELS_KEY }); },
  });
}

export function useUpdateModel() {
  const qc = useQueryClient();
  return useMutation<ConfigWriteResponse, Error, { name: string; req: ModelUpdateRequest }>({
    mutationFn: ({ name, req }) => updateModel(name, req),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MODELS_KEY }); },
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation<ConfigWriteResponse, Error, string>({
    mutationFn: deleteModel,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: MODELS_KEY }); },
  });
}
