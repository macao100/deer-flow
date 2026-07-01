import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCustomSkill,
  deleteCustomSkill,
  enableSkill,
  getCustomSkill,
  loadSkills,
  scanSkillContent,
  updateCustomSkill,
} from "./api";
import type { SkillScanResult } from "./type";

export function useSkills() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["skills"],
    queryFn: () => loadSkills(),
  });
  return { skills: data ?? [], isLoading, error };
}

export function useEnableSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ skillName, enabled }: { skillName: string; enabled: boolean }) => {
      await enableSkill(skillName, enabled);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useCustomSkill(name: string) {
  return useQuery({
    queryKey: ["skills", "custom", name],
    queryFn: () => getCustomSkill(name),
    enabled: !!name,
  });
}

export function useCreateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, content }: { name: string; content: string }) => {
      return createCustomSkill(name, content);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useUpdateSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ name, content }: { name: string; content: string }) => {
      return updateCustomSkill(name, content);
    },
    onSuccess: (_data, vars) => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["skills", "custom", vars.name] });
    },
  });
}

export function useDeleteSkill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      return deleteCustomSkill(name);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
    },
  });
}

export function useScanSkill() {
  return useMutation({
    mutationFn: async ({ content, skillName }: { content: string; skillName?: string }) => {
      return scanSkillContent(content, skillName);
    },
  });
}
