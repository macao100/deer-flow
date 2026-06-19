"use client";

import { CheckCircle2Icon, ExternalLinkIcon, EyeIcon, EyeOffIcon, KeyRoundIcon, Loader2Icon, RotateCcwIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiKeys, useUpdateApiKey } from "@/core/api-keys/hooks";

import { SettingsSection } from "./settings-section";

type KeyRowProps = {
  entry: {
    env_var: string;
    label: string;
    provider: string;
    placeholder: string;
    docs_url: string;
    is_set: boolean;
    masked_value: string;
  };
};

function KeyRow({ entry }: KeyRowProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [showValue, setShowValue] = useState(false);
  const { mutateAsync: updateKey, isPending } = useUpdateApiKey();

  const handleSave = async () => {
    if (!value.trim()) return;
    try {
      await updateKey({ env_var: entry.env_var, value: value.trim() });
      toast.success(`${entry.label} saved`, {
        description: "Restart DeerFlow for the change to take effect.",
      });
      setEditing(false);
      setValue("");
    } catch {
      toast.error(`Failed to save ${entry.label}`);
    }
  };

  const handleCancel = () => {
    setEditing(false);
    setValue("");
    setShowValue(false);
  };

  return (
    <div className="border-border rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <KeyRoundIcon className="text-muted-foreground size-4 shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{entry.label}</span>
              {entry.is_set ? (
                <Badge variant="outline" className="text-green-600 border-green-300 bg-green-50 dark:bg-green-950 dark:border-green-800 dark:text-green-400 text-xs gap-1">
                  <CheckCircle2Icon className="size-3" />
                  Set
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground text-xs">
                  Not set
                </Badge>
              )}
            </div>
            <code className="text-muted-foreground text-xs">{entry.env_var}</code>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {entry.docs_url && (
            <Button variant="ghost" size="icon" className="size-7" asChild>
              <a href={entry.docs_url} target="_blank" rel="noopener noreferrer">
                <ExternalLinkIcon className="size-3.5" />
              </a>
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditing((e) => !e)}
            className="h-7 text-xs"
          >
            {editing ? (
              <><RotateCcwIcon className="size-3 mr-1" />Cancel</>
            ) : entry.is_set ? (
              "Change"
            ) : (
              "Set key"
            )}
          </Button>
        </div>
      </div>

      {entry.is_set && !editing && (
        <div className="bg-muted/50 rounded px-3 py-1.5 font-mono text-xs text-muted-foreground">
          {entry.masked_value}
        </div>
      )}

      {editing && (
        <div className="space-y-2">
          <label className="text-xs text-muted-foreground">New value</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type={showValue ? "text" : "password"}
                placeholder={entry.placeholder}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="pr-9 text-sm font-mono h-8"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSave();
                  if (e.key === "Escape") handleCancel();
                }}
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowValue((s) => !s)}
                className="text-muted-foreground hover:text-foreground absolute right-2 top-1/2 -translate-y-1/2"
              >
                {showValue ? <EyeOffIcon className="size-3.5" /> : <EyeIcon className="size-3.5" />}
              </button>
            </div>
            <Button size="sm" onClick={handleSave} disabled={!value.trim() || isPending} className="h-8">
              {isPending ? <Loader2Icon className="size-3.5 animate-spin" /> : "Save"}
            </Button>
          </div>
          <p className="text-muted-foreground text-xs">
            Saved to <code>.env</code> — restart DeerFlow after saving.
          </p>
        </div>
      )}
    </div>
  );
}

export function ApiKeysSettingsPage() {
  const { data, isLoading } = useApiKeys();

  return (
    <SettingsSection
      title="API Keys"
      description="Configure provider credentials. Keys are stored in your local .env file and never sent to any external server."
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2Icon className="text-muted-foreground size-5 animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {data?.keys.map((entry) => (
            <KeyRow key={entry.env_var} entry={entry} />
          ))}
        </div>
      )}
    </SettingsSection>
  );
}
