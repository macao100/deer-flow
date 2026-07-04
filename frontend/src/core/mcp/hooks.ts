import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { loadMCPConfig, MCPConfigRequestError, scanMCPServer, updateMCPConfig } from "./api";
import type { MCPConfig, MCPServerConfig } from "./types";

export function useMCPConfig() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["mcpConfig"],
    queryFn: () => loadMCPConfig(),
    retry: (count, error) =>
      !(error instanceof MCPConfigRequestError) && count < 3,
  });
  return { config: data, isLoading, error };
}

export function useEnableMCPServer() {
  const queryClient = useQueryClient();
  const { config } = useMCPConfig();
  return useMutation({
    mutationFn: async ({
      serverName,
      enabled,
    }: {
      serverName: string;
      enabled: boolean;
    }) => {
      if (!config) {
        throw new Error("MCP config not found");
      }
      if (!config.mcp_servers[serverName]) {
        throw new Error(`MCP server ${serverName} not found`);
      }
      await updateMCPConfig({
        mcp_servers: {
          ...config.mcp_servers,
          [serverName]: {
            ...config.mcp_servers[serverName],
            enabled,
          },
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcpConfig"] });
    },
  });
}

export function useAddMCPServer() {
  const queryClient = useQueryClient();
  const { config } = useMCPConfig();
  return useMutation({
    mutationFn: async ({
      name,
      server,
    }: {
      name: string;
      server: MCPServerConfig;
    }) => {
      if (!config) throw new Error("MCP config not loaded");
      await updateMCPConfig({
        mcp_servers: {
          ...config.mcp_servers,
          [name]: server,
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcpConfig"] });
    },
  });
}

export function useDeleteMCPServer() {
  const queryClient = useQueryClient();
  const { config } = useMCPConfig();
  return useMutation({
    mutationFn: async (name: string) => {
      if (!config) throw new Error("MCP config not loaded");
      const next = { ...config.mcp_servers };
      delete next[name];
      await updateMCPConfig({ mcp_servers: next });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcpConfig"] });
    },
  });
}

export function useScanMCP() {
  return useMutation({
    mutationFn: async (server: MCPServerConfig) => {
      return scanMCPServer(server);
    },
  });
}
