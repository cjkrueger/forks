import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Dangerous URL schemes that must never appear in href or src.
const DANGEROUS_URI = /^(?:javascript|data|vbscript):/i;

// Register a one-time hook that strips dangerous URI schemes from any
// attribute that holds a URL.  DOMPurify's built-in ALLOWED_URI_REGEXP is
// browser-environment-dependent; this hook provides a reliable fallback.
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  for (const attr of ['href', 'src', 'action', 'formaction', 'xlink:href'] as const) {
    if (node.hasAttribute(attr)) {
      const value = node.getAttribute(attr) ?? '';
      if (DANGEROUS_URI.test(value.trim())) {
        node.removeAttribute(attr);
      }
    }
  }
});

/**
 * Render Markdown to sanitized HTML.
 *
 * marked.parse() converts Markdown to HTML, then DOMPurify strips any
 * tags or attributes that could be used for XSS (e.g. <script>, event
 * handlers, javascript: and data: URLs).  This provides defense-in-depth
 * on top of the escapeHtml() calls that already protect individual text
 * values built inline in the recipe-detail page.
 */
export function renderMarkdown(content: string): string {
  const raw = marked.parse(content, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    // Allow standard block/inline HTML produced by marked.
    // Restrict to a known-safe subset so unexpected tags can't sneak through.
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'strong', 'em', 'del', 'code', 'pre', 'blockquote',
      'ul', 'ol', 'li',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'a',
      'img',
      // diff-highlight spans added by the recipe-detail page
      'span',
    ],
    ALLOWED_ATTR: [
      // Hyperlinks
      'href', 'target', 'rel',
      // Images
      'src', 'alt', 'title', 'width', 'height',
      // Tables
      'colspan', 'rowspan',
      // diff-highlight classes used by the recipe page CSS
      'class',
      // Ordered-list step numbering (value="N" on <li>)
      'value',
    ],
    FORCE_BODY: false,
  });
}
