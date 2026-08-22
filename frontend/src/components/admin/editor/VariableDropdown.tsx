/**
 * Dropdown component for inserting template variables into the Tiptap editor.
 * Shows fields from the template's schema + system auto-fill variables.
 */
import React, { useState, useRef, useEffect } from "react";
import { AUTO_FILL_FIELDS } from "./editorUtils";
import type { Editor } from "@tiptap/react";
import type { TemplateField } from "@/src/types/admin";

interface VariableDropdownProps {
  editor: Editor | null;
  fields: TemplateField[];
}

export const VariableDropdown: React.FC<VariableDropdownProps> = ({
  editor,
  fields,
}) => {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const templateVars = (fields || []).map((f) => ({
    key: f.key,
    label: f.label_en || f.key,
    labelGu: f.label_gu || "",
    source: "template" as const,
  }));

  const systemVars = AUTO_FILL_FIELDS.map((key) => ({
    key,
    label: key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase()),
    labelGu: "",
    source: "system" as const,
  }));

  // Deduplicate: template fields take priority
  const templateKeys = new Set(templateVars.map((v) => v.key));
  const allVars = [
    ...templateVars,
    ...systemVars.filter((v) => !templateKeys.has(v.key)),
  ];

  const filtered = search
    ? allVars.filter(
        (v) =>
          v.key.toLowerCase().includes(search.toLowerCase()) ||
          v.label.toLowerCase().includes(search.toLowerCase())
      )
    : allVars;

  const insertVar = (key: string) => {
    if (editor) {
      editor.chain().focus().insertVariable(key).run();
    }
    setOpen(false);
    setSearch("");
  };

  return (
    <div ref={dropdownRef} style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        title="Insert Variable"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "4px 10px",
          background: open ? "rgba(197, 160, 89, 0.15)" : "transparent",
          border: "1px solid rgba(197, 160, 89, 0.4)",
          borderRadius: 4,
          color: "#C5A059",
          fontSize: 12,
          fontWeight: 700,
          cursor: "pointer",
          whiteSpace: "nowrap",
        }}
      >
        {"{{x}}"} Variable
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            marginTop: 4,
            width: 320,
            maxHeight: 400,
            background: "#0B1B3D",
            border: "1px solid #1B2A49",
            borderRadius: 8,
            boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            zIndex: 1000,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Search */}
          <div style={{ padding: 8, borderBottom: "1px solid #162544" }}>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search variables..."
              autoFocus
              style={{
                width: "100%",
                padding: "6px 10px",
                background: "#061024",
                border: "1px solid #1B2A49",
                borderRadius: 4,
                color: "#FDFDFD",
                fontSize: 13,
                outline: "none",
              }}
            />
          </div>

          {/* Scrollable list */}
          <div style={{ overflowY: "auto", maxHeight: 340 }}>
            {/* Template fields */}
            {filtered.filter((v) => v.source === "template").length > 0 && (
              <>
                <div
                  style={{
                    padding: "6px 12px",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#8B96A9",
                    textTransform: "uppercase",
                    letterSpacing: 1,
                    background: "#0A1630",
                  }}
                >
                  Template Fields
                </div>
                {filtered
                  .filter((v) => v.source === "template")
                  .map((v) => (
                    <button
                      type="button"
                      key={`t-${v.key}`}
                      onClick={() => insertVar(v.key)}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "6px 12px",
                        background: "transparent",
                        border: "none",
                        borderBottom: "1px solid #162544",
                        color: "#FDFDFD",
                        cursor: "pointer",
                        textAlign: "left",
                        fontSize: 13,
                      }}
                      onMouseEnter={(e) =>
                        ((e.target as HTMLElement).style.background =
                          "rgba(197, 160, 89, 0.08)")
                      }
                      onMouseLeave={(e) =>
                        ((e.target as HTMLElement).style.background =
                          "transparent")
                      }
                    >
                      <span>
                        <span
                          style={{
                            fontFamily: "monospace",
                            color: "#C5A059",
                            fontSize: 12,
                          }}
                        >
                          {`{{${v.key}}}`}
                        </span>
                        <span
                          style={{
                            marginLeft: 8,
                            color: "#8B96A9",
                            fontSize: 11,
                          }}
                        >
                          {v.label}
                        </span>
                      </span>
                    </button>
                  ))}
              </>
            )}

            {/* System auto-fill */}
            {filtered.filter((v) => v.source === "system").length > 0 && (
              <>
                <div
                  style={{
                    padding: "6px 12px",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "#8B96A9",
                    textTransform: "uppercase",
                    letterSpacing: 1,
                    background: "#0A1630",
                  }}
                >
                  System Variables (Auto-filled)
                </div>
                {filtered
                  .filter((v) => v.source === "system")
                  .map((v) => (
                    <button
                      type="button"
                      key={`s-${v.key}`}
                      onClick={() => insertVar(v.key)}
                      style={{
                        display: "flex",
                        width: "100%",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "6px 12px",
                        background: "transparent",
                        border: "none",
                        borderBottom: "1px solid #162544",
                        color: "#FDFDFD",
                        cursor: "pointer",
                        textAlign: "left",
                        fontSize: 13,
                      }}
                      onMouseEnter={(e) =>
                        ((e.target as HTMLElement).style.background =
                          "rgba(197, 160, 89, 0.08)")
                      }
                      onMouseLeave={(e) =>
                        ((e.target as HTMLElement).style.background =
                          "transparent")
                      }
                    >
                      <span
                        style={{
                          fontFamily: "monospace",
                          color: "#48BB78",
                          fontSize: 12,
                        }}
                      >
                        {`{{${v.key}}}`}
                      </span>
                      <span style={{ color: "#8B96A9", fontSize: 11 }}>
                        {v.label}
                      </span>
                    </button>
                  ))}
              </>
            )}

            {filtered.length === 0 && (
              <div
                style={{
                  padding: 16,
                  textAlign: "center",
                  color: "#8B96A9",
                  fontSize: 13,
                }}
              >
                No variables match "{search}"
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
