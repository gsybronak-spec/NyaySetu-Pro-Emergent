/**
 * Professional Word-like toolbar for the Tiptap legal document editor.
 * Grouped sections: Text, Paragraph, Lists, Insert, History.
 */
import React from "react";
import type { Editor } from "@tiptap/react";
import { VariableDropdown } from "./VariableDropdown";
import type { TemplateField } from "@/src/types/admin";

interface EditorToolbarProps {
  editor: Editor | null;
  fields: TemplateField[];
}

/* ── Tiny toolbar button ── */
const TBtn: React.FC<{
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}> = ({ onClick, active, disabled, title, children }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    title={title}
    style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      width: 30,
      height: 28,
      padding: 0,
      border: "none",
      borderRadius: 3,
      background: active ? "rgba(197, 160, 89, 0.2)" : "transparent",
      color: active ? "#C5A059" : disabled ? "#4A5568" : "#D1D8E5",
      cursor: disabled ? "default" : "pointer",
      fontSize: 13,
      fontWeight: active ? 700 : 500,
      transition: "background 0.1s",
    }}
    onMouseEnter={(e) => {
      if (!disabled)
        (e.currentTarget as HTMLElement).style.background =
          "rgba(197, 160, 89, 0.12)";
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.background = active
        ? "rgba(197, 160, 89, 0.2)"
        : "transparent";
    }}
  >
    {children}
  </button>
);

/* ── Separator ── */
const Sep = () => (
  <div
    style={{
      width: 1,
      height: 20,
      background: "#1B2A49",
      margin: "0 6px",
      flexShrink: 0,
    }}
  />
);

/* ── Group label ── */
const GroupLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span
    style={{
      fontSize: 9,
      fontWeight: 700,
      color: "#5A6B88",
      textTransform: "uppercase",
      letterSpacing: 1,
      marginRight: 4,
      userSelect: "none",
    }}
  >
    {children}
  </span>
);

export const EditorToolbar: React.FC<EditorToolbarProps> = ({
  editor,
  fields,
}) => {
  if (!editor) return null;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 2,
        padding: "6px 12px",
        background: "#0A1630",
        borderBottom: "1px solid #162544",
        userSelect: "none",
        minHeight: 40,
      }}
    >
      {/* ── History ── */}
      <TBtn
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        title="Undo (Ctrl+Z)"
      >
        ↩
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        title="Redo (Ctrl+Y)"
      >
        ↪
      </TBtn>

      <Sep />

      {/* ── Text Formatting ── */}
      <TBtn
        onClick={() => editor.chain().focus().toggleBold().run()}
        active={editor.isActive("bold")}
        title="Bold (Ctrl+B)"
      >
        <b>B</b>
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().toggleItalic().run()}
        active={editor.isActive("italic")}
        title="Italic (Ctrl+I)"
      >
        <i>I</i>
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        active={editor.isActive("underline")}
        title="Underline (Ctrl+U)"
      >
        <u>U</u>
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().toggleStrike().run()}
        active={editor.isActive("strike")}
        title="Strikethrough"
      >
        <s>S</s>
      </TBtn>

      <Sep />

      {/* ── Headings ── */}
      <TBtn
        onClick={() =>
          editor.chain().focus().toggleHeading({ level: 1 }).run()
        }
        active={editor.isActive("heading", { level: 1 })}
        title="Heading 1"
      >
        H1
      </TBtn>
      <TBtn
        onClick={() =>
          editor.chain().focus().toggleHeading({ level: 2 }).run()
        }
        active={editor.isActive("heading", { level: 2 })}
        title="Heading 2"
      >
        H2
      </TBtn>
      <TBtn
        onClick={() =>
          editor.chain().focus().toggleHeading({ level: 3 }).run()
        }
        active={editor.isActive("heading", { level: 3 })}
        title="Heading 3"
      >
        H3
      </TBtn>

      <Sep />

      {/* ── Alignment ── */}
      <TBtn
        onClick={() => editor.chain().focus().setTextAlign("left").run()}
        active={editor.isActive({ textAlign: "left" })}
        title="Align Left"
      >
        ≡
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().setTextAlign("center").run()}
        active={editor.isActive({ textAlign: "center" })}
        title="Align Center"
      >
        ≡
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().setTextAlign("right").run()}
        active={editor.isActive({ textAlign: "right" })}
        title="Align Right"
      >
        ≡
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().setTextAlign("justify").run()}
        active={editor.isActive({ textAlign: "justify" })}
        title="Justify"
      >
        ≡
      </TBtn>

      <Sep />

      {/* ── Lists ── */}
      <TBtn
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        active={editor.isActive("bulletList")}
        title="Bullet List"
      >
        •≡
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        active={editor.isActive("orderedList")}
        title="Numbered List"
      >
        1.
      </TBtn>

      <Sep />

      {/* ── Table ── */}
      <TBtn
        onClick={() =>
          editor
            .chain()
            .focus()
            .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
            .run()
        }
        title="Insert Table"
      >
        ⊞
      </TBtn>

      {/* Show table controls only when inside a table */}
      {editor.isActive("table") && (
        <>
          <TBtn
            onClick={() => editor.chain().focus().addRowAfter().run()}
            title="Add Row"
          >
            +↓
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().deleteRow().run()}
            title="Delete Row"
          >
            −↓
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().addColumnAfter().run()}
            title="Add Column"
          >
            +→
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().deleteColumn().run()}
            title="Delete Column"
          >
            −→
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().mergeCells().run()}
            title="Merge Cells"
          >
            ⊟
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().splitCell().run()}
            title="Split Cell"
          >
            ⊞
          </TBtn>
          <TBtn
            onClick={() => editor.chain().focus().deleteTable().run()}
            title="Delete Table"
          >
            ✕⊞
          </TBtn>
        </>
      )}

      <Sep />

      {/* ── Insert ── */}
      <TBtn
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        title="Horizontal Rule"
      >
        ―
      </TBtn>
      <TBtn
        onClick={() => editor.chain().focus().insertPageBreak().run()}
        title="Page Break (Ctrl+Enter)"
      >
        ⎘
      </TBtn>

      <Sep />

      {/* ── Variable Dropdown ── */}
      <VariableDropdown editor={editor} fields={fields} />
    </div>
  );
};
