/**
 * Custom Tiptap Node for template variables ({{variable_name}}).
 * Renders as an inline atomic pill/chip that cannot be partially edited.
 * Serializes back to {{variableName}} in plain text export.
 */
import { Node, mergeAttributes } from "@tiptap/react";

export interface TemplateVariableOptions {
  HTMLAttributes: Record<string, any>;
}

declare module "@tiptap/react" {
  interface Commands<ReturnType> {
    templateVariable: {
      insertVariable: (variableName: string) => ReturnType;
    };
  }
}

export const TemplateVariable = Node.create<TemplateVariableOptions>({
  name: "templateVariable",
  group: "inline",
  inline: true,
  atom: true, // Cannot be edited internally — acts as a single unit
  selectable: true,
  draggable: true,

  addOptions() {
    return {
      HTMLAttributes: {},
    };
  },

  addAttributes() {
    return {
      variableName: {
        default: "unknown",
        parseHTML: (element) =>
          element.getAttribute("data-variable-name") || "unknown",
        renderHTML: (attributes) => ({
          "data-variable-name": attributes.variableName,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-type="template-variable"]',
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(
        {
          "data-type": "template-variable",
          "data-variable-name": node.attrs.variableName,
          class: "template-variable-node",
          style: [
            "display: inline-block",
            "background: rgba(197, 160, 89, 0.15)",
            "border: 1px solid rgba(197, 160, 89, 0.4)",
            "border-radius: 4px",
            "padding: 1px 6px",
            "margin: 0 1px",
            "font-family: monospace",
            "font-size: 0.9em",
            "color: #C5A059",
            "font-weight: 600",
            "cursor: default",
            "user-select: all",
            "white-space: nowrap",
          ].join(";"),
        },
        this.options.HTMLAttributes,
        HTMLAttributes
      ),
      `{{${node.attrs.variableName}}}`,
    ];
  },

  addCommands() {
    return {
      insertVariable:
        (variableName: string) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: { variableName },
          });
        },
    };
  },

  // Serialize to plain text as {{variableName}}
  renderText({ node }) {
    return `{{${node.attrs.variableName}}}`;
  },
});
