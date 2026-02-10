export interface Section {
  name: string;
  content: string;
}

/**
 * Parse markdown body into sections.
 * Returns array of {name, content} preserving order.
 */
export function parseSections(markdown: string): Section[] {
  const sections: Section[] = [];
  let currentName = '_preamble';
  let currentLines: string[] = [];

  for (const line of markdown.split('\n')) {
    const match = line.match(/^##\s+(.+)$/);
    if (match) {
      const content = currentLines.join('\n').trim();
      if (content) {
        sections.push({ name: currentName, content });
      }
      currentName = match[1].trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  const content = currentLines.join('\n').trim();
  if (content) {
    sections.push({ name: currentName, content });
  }

  return sections;
}

/**
 * Merge base content with fork content.
 * Fork sections replace base sections; unmodified sections inherited.
 */
export function mergeContent(baseMarkdown: string, forkMarkdown: string): string {
  const baseSections = parseSections(baseMarkdown);
  const forkSections = parseSections(forkMarkdown);
  const forkMap = new Map(forkSections.map(s => [s.name, s.content]));

  const lines: string[] = [];
  for (const section of baseSections) {
    const content = forkMap.get(section.name) ?? section.content;
    if (section.name === '_preamble') {
      lines.push(content);
    } else {
      lines.push('');
      lines.push(`## ${section.name}`);
      lines.push('');
      lines.push(content);
    }
  }

  return lines.join('\n');
}

/**
 * Get set of section names that the fork modifies.
 */
export function getModifiedSections(forkMarkdown: string): Set<string> {
  const sections = parseSections(forkMarkdown);
  return new Set(sections.filter(s => s.name !== '_preamble').map(s => s.name));
}
