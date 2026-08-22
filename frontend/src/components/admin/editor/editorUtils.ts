/**
 * Editor utilities for converting between legacy plain text (content_gu/content_en)
 * and Tiptap JSON documents. Ensures backward compatibility with the existing
 * document generation pipeline.
 */
import type { JSONContent } from "@tiptap/react";

// ── Auto-fill fields that are system-provided (never user-entered) ──
export const AUTO_FILL_FIELDS = [
  "advocate_name", "today", "district", "court", "case_number", "case_type",
  "party_name", "opposite_party", "police_station", "law", "section",
  "client_name", "client_mobile", "client_email", "client_address", "client_district",
  "case_status_clause", "tense", "selected_party_role", "taluka_place",
  "date_display", "party_role", "opposite_party_role", "party_line",
  "opposite_party_line", "case_or_crime",
];

/**
 * Convert legacy plain text content (with {{variable}} placeholders) into a
 * Tiptap-compatible JSON document.
 *
 * Each line becomes a paragraph. {{variable}} tokens become TemplateVariable
 * inline nodes. Empty lines become empty paragraphs (spacers).
 * [TABLE_START]...[TABLE_END] blocks become table nodes.
 * --- PAGE BREAK --- lines become pageBreak nodes.
 */
export function plainTextToTiptapJSON(text: string): JSONContent {
  if (!text || !text.trim()) {
    return { type: "doc", content: [{ type: "paragraph" }] };
  }

  const lines = text.split("\n");
  const content: JSONContent[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Page break marker
    if (trimmed === "--- PAGE BREAK ---") {
      content.push({ type: "pageBreak" });
      i++;
      continue;
    }

    // Table block
    if (trimmed === "[TABLE_START]") {
      i++;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim() !== "[TABLE_END]") {
        const cells = lines[i].split(" | ").map((c) => c.trim());
        rows.push(cells);
        i++;
      }
      if (i < lines.length) i++; // skip [TABLE_END]
      if (rows.length > 0) {
        const colCount = Math.max(...rows.map((r) => r.length));
        const tableContent: JSONContent[] = rows.map((row, ri) => ({
          type: ri === 0 ? "tableRow" : "tableRow",
          content: Array.from({ length: colCount }, (_, ci) => ({
            type: ri === 0 ? "tableHeader" : "tableCell",
            content: [
              {
                type: "paragraph",
                content: row[ci] ? parseLineIntoNodes(row[ci]) : [],
              },
            ],
          })),
        }));
        content.push({ type: "table", content: tableContent });
      }
      continue;
    }

    // Empty line → empty paragraph
    if (!trimmed) {
      content.push({ type: "paragraph" });
      i++;
      continue;
    }

    // Normal line → paragraph with inline nodes
    const inlineNodes = parseLineIntoNodes(trimmed);
    content.push({
      type: "paragraph",
      content: inlineNodes.length > 0 ? inlineNodes : undefined,
    });
    i++;
  }

  if (content.length === 0) {
    content.push({ type: "paragraph" });
  }

  return { type: "doc", content };
}

/**
 * Parse a single line into an array of Tiptap inline nodes.
 * Text segments become text nodes; {{key}} become templateVariable nodes.
 */
function parseLineIntoNodes(line: string): JSONContent[] {
  const nodes: JSONContent[] = [];
  const regex = /\{\{(\w+)\}\}/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(line)) !== null) {
    // Text before the variable
    if (match.index > lastIndex) {
      nodes.push({ type: "text", text: line.slice(lastIndex, match.index) });
    }
    // Variable node
    nodes.push({
      type: "templateVariable",
      attrs: { variableName: match[1] },
    });
    lastIndex = regex.lastIndex;
  }

  // Remaining text after last variable
  if (lastIndex < line.length) {
    nodes.push({ type: "text", text: line.slice(lastIndex) });
  }

  return nodes;
}

/**
 * Convert a Tiptap JSON document back to plain text.
 * TemplateVariable nodes → {{variableName}}
 * pageBreak nodes → --- PAGE BREAK ---
 * Table nodes → [TABLE_START]...[TABLE_END]
 * Paragraph nodes → one line per paragraph
 */
export function tiptapJSONToPlainText(doc: JSONContent): string {
  if (!doc || !doc.content) return "";

  const lines: string[] = [];

  for (const node of doc.content) {
    if (node.type === "pageBreak") {
      lines.push("--- PAGE BREAK ---");
      continue;
    }

    if (node.type === "table") {
      lines.push("[TABLE_START]");
      for (const row of node.content || []) {
        const cells: string[] = [];
        for (const cell of row.content || []) {
          const cellText = extractTextFromNode(cell);
          cells.push(cellText);
        }
        lines.push(cells.join(" | "));
      }
      lines.push("[TABLE_END]");
      continue;
    }

    if (node.type === "heading") {
      lines.push(extractTextFromNode(node));
      continue;
    }

    if (node.type === "bulletList" || node.type === "orderedList") {
      let idx = 1;
      for (const item of node.content || []) {
        const itemText = extractTextFromNode(item);
        if (node.type === "orderedList") {
          lines.push(`${idx}. ${itemText}`);
        } else {
          lines.push(`• ${itemText}`);
        }
        idx++;
      }
      continue;
    }

    if (node.type === "horizontalRule") {
      lines.push("---");
      continue;
    }

    if (node.type === "paragraph") {
      const text = extractTextFromNode(node);
      lines.push(text);
      continue;
    }

    // Fallback for unknown nodes
    lines.push(extractTextFromNode(node));
  }

  return lines.join("\n");
}

/**
 * Recursively extract text from a Tiptap node, converting templateVariable
 * nodes back to {{variableName}} placeholders.
 */
function extractTextFromNode(node: JSONContent): string {
  if (!node) return "";

  if (node.type === "text") {
    return node.text || "";
  }

  if (node.type === "templateVariable") {
    return `{{${node.attrs?.variableName || "unknown"}}}`;
  }

  if (node.type === "hardBreak") {
    return "\n";
  }

  if (!node.content) return "";

  return node.content.map(extractTextFromNode).join("");
}

/**
 * Extract all variable names referenced in a Tiptap JSON document.
 */
export function extractVariablesFromJSON(doc: JSONContent): string[] {
  const vars = new Set<string>();
  collectVariables(doc, vars);
  return Array.from(vars).sort();
}

function collectVariables(node: JSONContent, vars: Set<string>): void {
  if (node.type === "templateVariable" && node.attrs?.variableName) {
    vars.add(node.attrs.variableName);
  }
  if (node.content) {
    for (const child of node.content) {
      collectVariables(child, vars);
    }
  }
}
