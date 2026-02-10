export interface TimerMatch {
  startIndex: number;
  endIndex: number;
  originalText: string;
  totalSeconds: number;
  label: string;
}

const TIME_PATTERN = /(\d+(?:[./]\d+)?)\s*(?:-\s*(\d+(?:[./]\d+)?)\s*)?(seconds?|secs?|minutes?|mins?|hours?|hrs?)(?:\s+and\s+(\d+(?:[./]\d+)?)\s*(minutes?|mins?|seconds?|secs?))?/gi;

function parseNumber(s: string): number {
  if (s.includes('/')) {
    const [num, den] = s.split('/');
    return parseFloat(num) / parseFloat(den);
  }
  return parseFloat(s);
}

function unitToSeconds(unit: string): number {
  const u = unit.toLowerCase().replace(/s$/, '');
  if (u === 'hour' || u === 'hr') return 3600;
  if (u === 'minute' || u === 'min') return 60;
  if (u === 'second' || u === 'sec') return 1;
  return 60;
}

function formatLabel(totalSeconds: number): string {
  if (totalSeconds >= 3600) {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.round((totalSeconds % 3600) / 60);
    return m > 0 ? `${h} hr ${m} min` : `${h} hr`;
  }
  if (totalSeconds >= 60) {
    const m = Math.round(totalSeconds / 60);
    return `${m} min`;
  }
  return `${Math.round(totalSeconds)} sec`;
}

export function parseTimers(text: string): TimerMatch[] {
  const matches: TimerMatch[] = [];
  let match: RegExpExecArray | null;

  TIME_PATTERN.lastIndex = 0;

  while ((match = TIME_PATTERN.exec(text)) !== null) {
    const num1 = parseNumber(match[1]);
    const num2 = match[2] ? parseNumber(match[2]) : null;
    const unit1 = match[3];
    const andNum = match[4] ? parseNumber(match[4]) : null;
    const andUnit = match[5] || null;

    const primaryValue = num2 !== null ? num2 : num1;
    let totalSeconds = primaryValue * unitToSeconds(unit1);

    if (andNum !== null && andUnit !== null) {
      totalSeconds += andNum * unitToSeconds(andUnit);
    }

    totalSeconds = Math.round(totalSeconds);
    if (totalSeconds <= 0) continue;

    matches.push({
      startIndex: match.index,
      endIndex: match.index + match[0].length,
      originalText: match[0],
      totalSeconds,
      label: formatLabel(totalSeconds),
    });
  }

  return matches;
}
