/**
 * AdminTemplateEditor — Main Tiptap-based legal document editor component.
 *
 * Features:
 * - A4 page-style editing canvas on grey workspace background
 * - Professional Word-like toolbar
 * - Gujarati/English tab switching
 * - Custom TemplateVariable and PageBreak nodes
 * - Table support
 * - AnekGujarati font for Gujarati content
 *
 * Web-only component (Tiptap requires DOM / ProseMirror).
 */
import React, { useCallback, useEffect, useImperativeHandle, forwardRef, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import TextAlign from "@tiptap/extension-text-align";
import { TextStyle } from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import FontFamily from "@tiptap/extension-font-family";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import Placeholder from "@tiptap/extension-placeholder";
import type { JSONContent } from "@tiptap/react";

import { TemplateVariable } from "./TemplateVariableNode";
import { PageBreak } from "./PageBreakNode";
import { EditorToolbar } from "./EditorToolbar";
import { plainTextToTiptapJSON, tiptapJSONToPlainText } from "./editorUtils";
import type { TemplateField } from "@/src/types/admin";

export interface AdminTemplateEditorRef {
  getJSON: () => JSONContent;
  getPlainText: () => string;
  setContent: (json: JSONContent) => void;
}

interface AdminTemplateEditorProps {
  initialContent?: JSONContent | null;
  initialPlainText?: string;
  language: "gu" | "en";
  fields: TemplateField[];
  onChange?: (json: JSONContent) => void;
}

const AdminTemplateEditorInner: React.ForwardRefRenderFunction<
  AdminTemplateEditorRef,
  AdminTemplateEditorProps
> = ({ initialContent, initialPlainText, language, fields, onChange }, ref) => {
  const [ready, setReady] = useState(false);

  // Determine initial content
  const getInitialDoc = useCallback((): JSONContent => {
    if (initialContent && initialContent.type === "doc") {
      return initialContent;
    }
    if (initialPlainText) {
      return plainTextToTiptapJSON(initialPlainText);
    }
    return { type: "doc", content: [{ type: "paragraph" }] };
  }, [initialContent, initialPlainText]);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        horizontalRule: {},
      }),
      Underline,
      TextAlign.configure({
        types: ["heading", "paragraph"],
        alignments: ["left", "center", "right", "justify"],
        defaultAlignment: "left",
      }),
      TextStyle,
      Color,
      FontFamily,
      Table.configure({
        resizable: true,
        allowTableNodeSelection: true,
      }),
      TableRow,
      TableCell,
      TableHeader,
      Placeholder.configure({
        placeholder: language === "gu"
          ? "અહીં ટેમ્પ્લેટ સામગ્રી લખો..."
          : "Start typing template content here...",
      }),
      TemplateVariable,
      PageBreak,
    ],
    content: getInitialDoc(),
    onUpdate: ({ editor: e }) => {
      if (onChange) {
        onChange(e.getJSON());
      }
    },
    onCreate: () => {
      setReady(true);
    },
    editorProps: {
      attributes: {
        class: "tiptap-legal-editor",
        spellcheck: "true",
      },
    },
  });

  // Expose imperative API
  useImperativeHandle(ref, () => ({
    getJSON: () => editor?.getJSON() || { type: "doc", content: [] },
    getPlainText: () => {
      const json = editor?.getJSON();
      return json ? tiptapJSONToPlainText(json) : "";
    },
    setContent: (json: JSONContent) => {
      editor?.commands.setContent(json);
    },
  }));

  // Determine font family based on language
  const fontFamily =
    language === "gu"
      ? "'AnekGujarati', 'Noto Sans Gujarati', serif"
      : "'Times New Roman', Times, serif";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#0B1B3D",
        borderRadius: 8,
        overflow: "hidden",
        border: "1px solid #1B2A49",
      }}
    >
      {/* Toolbar */}
      <EditorToolbar editor={editor} fields={fields} />

      {/* A4 page workspace */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          background: "#3A4050",
          padding: "32px 0",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: 794, // A4 at 96 DPI = 210mm
            minHeight: 1123, // A4 height at 96 DPI = 297mm
            background: "#FFFFFF",
            boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
            padding: "72px 64px", // ~2.5cm margins
            fontFamily,
            fontSize: 14,
            lineHeight: 1.6,
            color: "#1A1A1A",
            position: "relative",
          }}
        >
          {/* Editor styles injected via <style> tag */}
          <style
            dangerouslySetInnerHTML={{
              __html: `
                .tiptap-legal-editor {
                  outline: none;
                  min-height: 900px;
                  font-family: ${fontFamily};
                }
                .tiptap-legal-editor p {
                  margin: 0 0 4px 0;
                }
                .tiptap-legal-editor h1 {
                  font-size: 20px;
                  font-weight: 700;
                  text-align: center;
                  margin: 12px 0 8px;
                }
                .tiptap-legal-editor h2 {
                  font-size: 17px;
                  font-weight: 700;
                  margin: 10px 0 6px;
                }
                .tiptap-legal-editor h3 {
                  font-size: 15px;
                  font-weight: 700;
                  margin: 8px 0 4px;
                }
                .tiptap-legal-editor ul,
                .tiptap-legal-editor ol {
                  padding-left: 24px;
                  margin: 4px 0;
                }
                .tiptap-legal-editor li {
                  margin: 2px 0;
                }
                .tiptap-legal-editor hr {
                  border: none;
                  border-top: 1px solid #ccc;
                  margin: 12px 0;
                }
                .tiptap-legal-editor table {
                  border-collapse: collapse;
                  width: 100%;
                  margin: 8px 0;
                }
                .tiptap-legal-editor th,
                .tiptap-legal-editor td {
                  border: 1px solid #999;
                  padding: 6px 10px;
                  text-align: left;
                  vertical-align: top;
                  min-width: 60px;
                }
                .tiptap-legal-editor th {
                  background: #f0f0f0;
                  font-weight: 700;
                }
                .tiptap-legal-editor .selectedCell {
                  background: rgba(197, 160, 89, 0.15);
                }
                .tiptap-legal-editor .ProseMirror-gapcursor {
                  display: none;
                  pointer-events: none;
                  position: absolute;
                  margin: 0;
                }
                .tiptap-legal-editor .ProseMirror-gapcursor:after {
                  content: '';
                  display: block;
                  position: absolute;
                  top: -2px;
                  width: 20px;
                  border-top: 1px solid #1A1A1A;
                  animation: ProseMirror-cursor-blink 1.1s steps(2, start) infinite;
                }
                @keyframes ProseMirror-cursor-blink {
                  to { visibility: hidden; }
                }
                .tiptap-legal-editor p.is-editor-empty:first-child::before {
                  color: #adb5bd;
                  content: attr(data-placeholder);
                  float: left;
                  height: 0;
                  pointer-events: none;
                }
              `,
            }}
          />
          <EditorContent editor={editor} />
        </div>
      </div>
    </div>
  );
};

export const AdminTemplateEditor = forwardRef(AdminTemplateEditorInner);
