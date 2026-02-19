/**
 * Tests for renderMarkdown() — verifies that DOMPurify sanitization is applied
 * on top of marked's HTML output, providing defense-in-depth against XSS.
 *
 * Run with: npx vitest run
 */

import { describe, it, expect } from 'vitest';
import { renderMarkdown } from './markdown';

describe('renderMarkdown', () => {
  // -----------------------------------------------------------------
  // Basic Markdown rendering
  // -----------------------------------------------------------------

  it('renders headings', () => {
    const html = renderMarkdown('## Ingredients');
    expect(html).toContain('<h2>');
    expect(html).toContain('Ingredients');
  });

  it('renders an unordered list', () => {
    const html = renderMarkdown('- 1 cup flour\n- 2 eggs');
    expect(html).toContain('<ul>');
    expect(html).toContain('<li>');
    expect(html).toContain('1 cup flour');
    expect(html).toContain('2 eggs');
  });

  it('renders an ordered list', () => {
    const html = renderMarkdown('1. Preheat oven\n2. Mix ingredients');
    expect(html).toContain('<ol>');
    expect(html).toContain('<li>');
    expect(html).toContain('Preheat oven');
  });

  it('renders bold and italic text', () => {
    const html = renderMarkdown('**bold** and _italic_');
    expect(html).toContain('<strong>bold</strong>');
    expect(html).toContain('<em>italic</em>');
  });

  it('renders a safe hyperlink', () => {
    const html = renderMarkdown('[Source](https://example.com)');
    expect(html).toContain('<a');
    expect(html).toContain('href="https://example.com"');
    expect(html).toContain('Source');
  });

  // -----------------------------------------------------------------
  // XSS sanitization — these payloads must be stripped or neutralised
  // -----------------------------------------------------------------

  it('strips <script> tags', () => {
    const html = renderMarkdown('<script>alert("xss")</script>');
    expect(html).not.toContain('<script');
    expect(html).not.toContain('alert(');
  });

  it('strips inline event handlers (onerror)', () => {
    const html = renderMarkdown('<img src="x" onerror="alert(1)">');
    expect(html).not.toContain('onerror');
  });

  it('strips inline event handlers (onload)', () => {
    const html = renderMarkdown('<div onload="stealCookies()">hi</div>');
    expect(html).not.toContain('onload');
  });

  it('strips javascript: URLs in links', () => {
    // Markdown link with javascript: href
    const html = renderMarkdown('[click me](javascript:alert(1))');
    expect(html).not.toContain('javascript:');
  });

  it('strips javascript: URLs in raw anchor tags', () => {
    const html = renderMarkdown('<a href="javascript:alert(1)">xss</a>');
    expect(html).not.toContain('javascript:');
  });

  it('strips <iframe> elements', () => {
    const html = renderMarkdown('<iframe src="https://evil.com"></iframe>');
    expect(html).not.toContain('<iframe');
  });

  it('strips <object> elements', () => {
    const html = renderMarkdown('<object data="evil.swf"></object>');
    expect(html).not.toContain('<object');
  });

  it('strips <embed> elements', () => {
    const html = renderMarkdown('<embed src="evil.swf">');
    expect(html).not.toContain('<embed');
  });

  it('strips <form> elements', () => {
    const html = renderMarkdown('<form action="https://evil.com"><input name="data"></form>');
    expect(html).not.toContain('<form');
  });

  it('strips style attributes that could be used for clickjacking', () => {
    const html = renderMarkdown('<div style="position:fixed;top:0;left:0;width:100%;height:100%">overlay</div>');
    expect(html).not.toContain('style=');
  });

  it('strips data: URLs in image src', () => {
    const html = renderMarkdown('<img src="data:text/html,<script>alert(1)</script>">');
    // The afterSanitizeAttributes hook removes the src when it contains a data: URI.
    expect(html).not.toContain('data:text/html');
    // The img tag itself may remain but the dangerous src must be gone.
    expect(html).not.toContain('data:');
  });

  it('allows safe image tags with http src', () => {
    const html = renderMarkdown('![alt text](https://example.com/img.jpg)');
    expect(html).toContain('<img');
    expect(html).toContain('src="https://example.com/img.jpg"');
  });

  it('preserves diff-highlight class attributes used by recipe page', () => {
    // The recipe-detail page injects spans with diff classes via escapeHtml()
    // Those span elements are NOT produced by renderMarkdown, but we still
    // want to confirm that class= is in the allowed attribute list so that
    // any future use from Markdown won't be stripped unexpectedly.
    const html = renderMarkdown('<span class="diff-added">extra garlic</span>');
    expect(html).toContain('class="diff-added"');
    expect(html).toContain('extra garlic');
  });

  // -----------------------------------------------------------------
  // Edge cases
  // -----------------------------------------------------------------

  it('returns empty string for empty input', () => {
    const html = renderMarkdown('');
    // marked produces '\n' for empty input; after sanitization it stays minimal
    expect(html.trim()).toBe('');
  });

  it('handles plain text without Markdown formatting', () => {
    const html = renderMarkdown('Just a plain sentence.');
    expect(html).toContain('Just a plain sentence.');
  });
});
