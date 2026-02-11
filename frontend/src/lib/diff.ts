import { parseIngredient, ingredientKey, formatQuantity } from './ingredients';
import { parseSections } from './sections';

export type LineDiffStatus = 'unchanged' | 'added' | 'removed' | 'modified';

export interface LineDiff {
  status: LineDiffStatus;
  forkLine: string | null;
  baseLine: string | null;
  annotation?: string;
}

export interface SectionDiff {
  sectionName: string;
  lines: LineDiff[];
  hasChanges: boolean;
}

/**
 * Diff ingredients by matching on ingredient key (unit:name).
 * Handles duplicates by consuming matches greedily in order.
 */
export function diffIngredients(baseContent: string, forkContent: string): LineDiff[] {
  const baseLines = baseContent.split('\n').map(l => l.trim()).filter(l => l.startsWith('- '));
  const forkLines = forkContent.split('\n').map(l => l.trim()).filter(l => l.startsWith('- '));

  const baseParsed = baseLines.map(l => ({ line: l, parsed: parseIngredient(l) }));
  const forkParsed = forkLines.map(l => ({ line: l, parsed: parseIngredient(l) }));

  const baseUsed = new Array(baseParsed.length).fill(false);

  // Greedy match: for each fork line, find first unused base line with same key
  const forkToBase = new Map<number, number>();
  for (let fi = 0; fi < forkParsed.length; fi++) {
    const fKey = ingredientKey(forkParsed[fi].parsed);
    for (let bi = 0; bi < baseParsed.length; bi++) {
      if (baseUsed[bi]) continue;
      if (ingredientKey(baseParsed[bi].parsed) === fKey) {
        baseUsed[bi] = true;
        forkToBase.set(fi, bi);
        break;
      }
    }
  }

  // Walk fork lines in order, interleaving removed base lines at their original positions
  const result: LineDiff[] = [];
  let prevBaseIdx = -1;

  for (let fi = 0; fi < forkParsed.length; fi++) {
    const bi = forkToBase.get(fi);
    if (bi !== undefined) {
      // Emit removed base lines between prevBaseIdx and bi
      for (let ri = prevBaseIdx + 1; ri < bi; ri++) {
        if (!baseUsed[ri]) {
          result.push({ status: 'removed', forkLine: null, baseLine: baseParsed[ri].line });
        }
      }
      prevBaseIdx = bi;

      // Emit the matched line
      const bQty = baseParsed[bi].parsed.quantity;
      const fQty = forkParsed[fi].parsed.quantity;
      if (bQty === fQty) {
        result.push({ status: 'unchanged', forkLine: forkParsed[fi].line, baseLine: baseParsed[bi].line });
      } else {
        const annotation = bQty !== null
          ? `was ${formatQuantity(bQty)}${baseParsed[bi].parsed.unit ? ' ' + baseParsed[bi].parsed.unit : ''}`
          : undefined;
        result.push({ status: 'modified', forkLine: forkParsed[fi].line, baseLine: baseParsed[bi].line, annotation });
      }
    } else {
      result.push({ status: 'added', forkLine: forkParsed[fi].line, baseLine: null });
    }
  }

  // Emit any remaining removed base lines after the last matched base index
  for (let ri = prevBaseIdx + 1; ri < baseParsed.length; ri++) {
    if (!baseUsed[ri]) {
      result.push({ status: 'removed', forkLine: null, baseLine: baseParsed[ri].line });
    }
  }

  return result;
}

/**
 * LCS-based positional diff for instructions/notes.
 */
export function diffPositional(baseContent: string, forkContent: string): LineDiff[] {
  const baseLines = baseContent.split('\n').map(l => l.trim()).filter(l => l.length > 0);
  const forkLines = forkContent.split('\n').map(l => l.trim()).filter(l => l.length > 0);

  // Strip numbering for comparison (e.g., "1. Preheat" -> "Preheat")
  const normalize = (line: string) => line.replace(/^\d+\.\s*/, '').replace(/^-\s*/, '');

  // Build LCS table
  const m = baseLines.length;
  const n = forkLines.length;
  const dp: number[][] = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (normalize(baseLines[i - 1]) === normalize(forkLines[j - 1])) {
        dp[i][j] = dp[i - 1][j - 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
      }
    }
  }

  // Backtrack to find the diff
  const result: LineDiff[] = [];
  let i = m, j = n;

  const temp: LineDiff[] = [];
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && normalize(baseLines[i - 1]) === normalize(forkLines[j - 1])) {
      temp.push({ status: 'unchanged', forkLine: forkLines[j - 1], baseLine: baseLines[i - 1] });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      temp.push({ status: 'added', forkLine: forkLines[j - 1], baseLine: null });
      j--;
    } else {
      temp.push({ status: 'removed', forkLine: null, baseLine: baseLines[i - 1] });
      i--;
    }
  }

  // Reverse since we backtracked from the end
  return temp.reverse();
}

/**
 * Orchestrator: compute diffs for all sections the fork overrides.
 */
export function computeSectionDiffs(baseMarkdown: string, forkMarkdown: string): Map<string, SectionDiff> {
  const baseSections = parseSections(baseMarkdown);
  const forkSections = parseSections(forkMarkdown);

  const baseMap = new Map(baseSections.map(s => [s.name, s.content]));
  const forkMap = new Map(forkSections.map(s => [s.name, s.content]));

  const result = new Map<string, SectionDiff>();

  for (const [name, forkContent] of forkMap) {
    if (name === '_preamble') continue;

    const baseContent = baseMap.get(name);

    let lines: LineDiff[];
    if (!baseContent) {
      // Fork-only section: all lines added
      lines = forkContent.split('\n').map(l => l.trim()).filter(l => l.length > 0)
        .map(l => ({ status: 'added' as LineDiffStatus, forkLine: l, baseLine: null }));
    } else if (name.toLowerCase() === 'ingredients') {
      lines = diffIngredients(baseContent, forkContent);
    } else {
      lines = diffPositional(baseContent, forkContent);
    }

    const hasChanges = lines.some(l => l.status !== 'unchanged');
    result.set(name, { sectionName: name, lines, hasChanges });
  }

  return result;
}
