import type { Message } from "@langchain/langgraph-sdk";

import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  hasContent,
  hasToolCalls,
  isHiddenFromUIMessage,
  stripInternalMarkers,
} from "../messages/utils";

import type { AgentThread } from "./types";
import { titleOfThread } from "./utils";

/**
 * Optional debug switches for advanced exports.
 *
 * Bytedance/deer-flow issue #3107 BUG-006 explicitly prescribes that the
 * default export includes only the user-visible transcript and excludes
 * thinking/reasoning content, tool calls, tool results, hidden messages,
 * memory injection, and `<system-reminder>` payloads. These options let a
 * future "debug export" surface re-include any of those categories without
 * forking the formatter. They are not currently wired to any UI control —
 * callers that want them must construct the options object explicitly.
 */
export interface ExportOptions {
  includeReasoning?: boolean;
  includeToolCalls?: boolean;
  includeToolMessages?: boolean;
  includeHidden?: boolean;
}

function visibleMessages(
  messages: Message[],
  options: ExportOptions,
): Message[] {
  return messages.filter((message) => {
    if (!options.includeHidden && isHiddenFromUIMessage(message)) {
      return false;
    }
    if (!options.includeToolMessages && message.type === "tool") {
      return false;
    }
    return true;
  });
}

function formatMessageContent(message: Message): string {
  const text = extractContentFromMessage(message);
  if (!text) return "";
  // Defence-in-depth: even if a middleware-injected marker slipped through
  // the `hide_from_ui` filter, scrub every known internal tag before the
  // content lands in a user-visible export file.
  return stripInternalMarkers(text);
}

function formatToolCalls(message: Message): string {
  if (message.type !== "ai" || !hasToolCalls(message)) return "";
  const calls = message.tool_calls ?? [];
  return calls.map((call) => `- **Tool:** \`${call.name}\``).join("\n");
}

export function formatThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): string {
  const title = titleOfThread(thread);
  const createdAt = thread.created_at
    ? new Date(thread.created_at).toLocaleString()
    : "Unknown";

  const lines: string[] = [
    `# ${title}`,
    "",
    `*Exported on ${new Date().toLocaleString()} · Created ${createdAt}*`,
    "",
    "---",
    "",
  ];

  for (const message of visibleMessages(messages, options)) {
    if (message.type === "human") {
      const content = formatMessageContent(message);
      if (content) {
        lines.push(`## 🧑 User`, "", content, "", "---", "");
      }
    } else if (message.type === "ai") {
      const reasoning = options.includeReasoning
        ? extractReasoningContentFromMessage(message)
        : undefined;
      const content = formatMessageContent(message);
      const toolCalls = options.includeToolCalls
        ? formatToolCalls(message)
        : "";

      if (!content && !toolCalls && !reasoning) continue;

      lines.push(`## 🤖 Assistant`);

      if (reasoning) {
        lines.push(
          "",
          "<details>",
          "<summary>Thinking</summary>",
          "",
          reasoning,
          "",
          "</details>",
        );
      }

      if (toolCalls) {
        lines.push("", toolCalls);
      }

      if (content && hasContent(message)) {
        lines.push("", content);
      }

      lines.push("", "---", "");
    }
  }

  return lines.join("\n").trimEnd() + "\n";
}

interface JSONExportMessage {
  type: Message["type"];
  id: string | undefined;
  content: string;
  reasoning?: string;
  tool_calls?: unknown;
}

function buildJSONMessage(
  msg: Message,
  options: ExportOptions,
): JSONExportMessage | null {
  // Run the same sanitiser the Markdown path uses so the JSON `content`
  // field never carries inline `<think>...</think>` wrappers, content-array
  // thinking blocks, `<uploaded_files>` markers, or other internal payloads.
  const content = formatMessageContent(msg);
  const reasoning =
    options.includeReasoning && msg.type === "ai"
      ? (extractReasoningContentFromMessage(msg) ?? undefined)
      : undefined;
  const toolCalls =
    options.includeToolCalls &&
    msg.type === "ai" &&
    "tool_calls" in msg &&
    msg.tool_calls?.length
      ? msg.tool_calls
      : undefined;

  // Drop rows with no exportable payload (empty content + no opted-in
  // reasoning / tool_calls). Uses falsy semantics so `reasoning: ""` (the
  // empty string ``extractReasoningContentFromMessage`` can hand back) is
  // treated the same way Markdown's `!reasoning` continue does — otherwise
  // an opted-in but empty reasoning field would leak as `{reasoning: ""}`.
  if (!content && !reasoning && !toolCalls) {
    return null;
  }

  return {
    type: msg.type,
    id: msg.id,
    content,
    ...(reasoning !== undefined ? { reasoning } : {}),
    ...(toolCalls !== undefined ? { tool_calls: toolCalls } : {}),
  };
}

export function formatThreadAsJSON(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): string {
  const exportData = {
    title: titleOfThread(thread),
    thread_id: thread.thread_id,
    created_at: thread.created_at,
    exported_at: new Date().toISOString(),
    messages: visibleMessages(messages, options)
      .map((msg) => buildJSONMessage(msg, options))
      .filter((m): m is JSONExportMessage => m !== null),
  };
  return JSON.stringify(exportData, null, 2);
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^\p{L}\p{N}_\- ]/gu, "").trim() || "conversation";
}

export function downloadAsFile(
  content: string,
  filename: string,
  mimeType: string,
) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Save content to a file chosen by the user via the File System Access API.
 *
 * On browsers that support {@link window.showSaveFilePicker} (Chromium-based),
 * the user is prompted to choose a destination folder and filename.
 * Falls back to the classic {@link downloadAsFile} mechanism on other browsers
 * (Firefox, Safari) or when the API is unavailable.
 *
 * @returns `true` if the file was saved, `false` if the user cancelled the picker.
 */
async function saveFileWithPicker(
  content: string,
  filename: string,
  mimeType: string,
): Promise<boolean> {
  const win = window as Window & {
    showSaveFilePicker?: (opts: {
      suggestedName?: string;
      types?: Array<{
        description: string;
        accept: Record<string, string[]>;
      }>;
    }) => Promise<{ createWritable: () => Promise<{ write: (data: string) => Promise<void>; close: () => Promise<void> }> }>;
  };

  if (win.showSaveFilePicker) {
    try {
      const ext = filename.endsWith(".json") ? ".json" : ".md";
      const handle = await win.showSaveFilePicker({
        suggestedName: filename,
        types: [
          {
            description: ext === ".json" ? "JSON" : "Markdown",
            accept: { [mimeType]: [ext] },
          },
        ],
      });
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();
      return true;
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return false;
      }
      // Other errors: fall through to fallback
    }
  }
  // Fallback: classic browser download (default download folder)
  downloadAsFile(content, filename, mimeType);
  return true;
}

export async function exportThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
): Promise<boolean> {
  const markdown = formatThreadAsMarkdown(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.md`;
  return saveFileWithPicker(markdown, filename, "text/markdown;charset=utf-8");
}

export async function exportThreadAsJSON(
  thread: AgentThread,
  messages: Message[],
): Promise<boolean> {
  const json = formatThreadAsJSON(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.json`;
  return saveFileWithPicker(json, filename, "application/json;charset=utf-8");
}
