/**
 * Custom Tiptap Node for explicit page breaks.
 * Renders as a visual dashed separator in the editor.
 * Serializes to "--- PAGE BREAK ---" in plain text export.
 */
import { Node } from "@tiptap/react";

declare module "@tiptap/react" {
  interface Commands<ReturnType> {
    pageBreak: {
      insertPageBreak: () => ReturnType;
    };
  }
}

export const PageBreak = Node.create({
  name: "pageBreak",
  group: "block",
  atom: true,
  selectable: true,
  draggable: false,

  parseHTML() {
    return [
      {
        tag: 'div[data-type="page-break"]',
      },
    ];
  },

  renderHTML() {
    return [
      "div",
      {
        "data-type": "page-break",
        class: "page-break-node",
        contenteditable: "false",
        style: [
          "display: flex",
          "align-items: center",
          "justify-content: center",
          "margin: 16px 0",
          "padding: 8px 0",
          "border-top: 2px dashed #8B96A9",
          "border-bottom: 2px dashed #8B96A9",
          "color: #8B96A9",
          "font-size: 11px",
          "font-weight: 700",
          "letter-spacing: 2px",
          "text-transform: uppercase",
          "user-select: none",
          "cursor: default",
          "background: rgba(139, 150, 169, 0.05)",
        ].join(";"),
      },
      "— PAGE BREAK —",
    ];
  },

  addCommands() {
    return {
      insertPageBreak:
        () =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
          });
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      "Mod-Enter": () => this.editor.commands.insertPageBreak(),
    };
  },

  renderText() {
    return "--- PAGE BREAK ---";
  },
});
