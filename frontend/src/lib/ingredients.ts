export interface ParsedIngredient {
  quantity: number | null;
  unit: string | null;
  name: string;
  displayText: string;
  original: string;
}

const UNIT_MAP: Record<string, string> = {
  cup: 'cup', cups: 'cup', c: 'cup',
  tablespoon: 'tbsp', tablespoons: 'tbsp', tbsp: 'tbsp', tbs: 'tbsp',
  teaspoon: 'tsp', teaspoons: 'tsp', tsp: 'tsp',
  ounce: 'oz', ounces: 'oz', oz: 'oz',
  pound: 'lb', pounds: 'lb', lb: 'lb', lbs: 'lb',
  gram: 'g', grams: 'g', g: 'g',
  kilogram: 'kg', kilograms: 'kg', kg: 'kg',
  liter: 'l', liters: 'l', l: 'l',
  milliliter: 'ml', milliliters: 'ml', ml: 'ml',
  pint: 'pint', pints: 'pint',
  quart: 'quart', quarts: 'quart',
  gallon: 'gallon', gallons: 'gallon',
  can: 'can', cans: 'can',
  clove: 'clove', cloves: 'clove',
  slice: 'slice', slices: 'slice',
  piece: 'piece', pieces: 'piece',
  bunch: 'bunch', bunches: 'bunch',
  head: 'head', heads: 'head',
  sprig: 'sprig', sprigs: 'sprig',
  pinch: 'pinch',
  dash: 'dash',
  stick: 'stick', sticks: 'stick',
};

const WORD_NUMBERS: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  half: 0.5, a: 1, an: 1,
};

const UNICODE_FRACTIONS: Record<string, number> = {
  '\u00BC': 0.25, '\u00BD': 0.5, '\u00BE': 0.75,
  '\u2153': 1/3, '\u2154': 2/3, '\u2155': 1/5,
  '\u2156': 2/5, '\u2157': 3/5, '\u2158': 4/5,
  '\u2159': 1/6, '\u215A': 5/6, '\u215B': 1/8,
  '\u215C': 3/8, '\u215D': 5/8, '\u215E': 7/8,
};

const PREP_WORDS = /,?\s*\b(diced|minced|chopped|sliced|thinly sliced|grated|shredded|crushed|ground|melted|softened|warmed|cooled|room temperature|to taste|for garnish|for serving|optional|divided|packed|sifted|peeled|seeded|trimmed|halved|quartered|cubed|julienned|roughly chopped|finely chopped|finely diced|finely minced)\b.*$/i;

const PARENTHETICAL = /\s*\([^)]*\)\s*/g;

function parseFraction(s: string): number | null {
  // Unicode fractions
  for (const [char, val] of Object.entries(UNICODE_FRACTIONS)) {
    if (s.includes(char)) {
      const prefix = s.replace(char, '').trim();
      const whole = prefix ? parseFloat(prefix) : 0;
      return isNaN(whole) ? val : whole + val;
    }
  }

  // Mixed number: "2 1/2"
  const mixedMatch = s.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixedMatch) {
    return parseInt(mixedMatch[1]) + parseInt(mixedMatch[2]) / parseInt(mixedMatch[3]);
  }

  // Simple fraction: "1/2"
  const fracMatch = s.match(/^(\d+)\/(\d+)$/);
  if (fracMatch) {
    return parseInt(fracMatch[1]) / parseInt(fracMatch[2]);
  }

  // Range: "2-3"
  const rangeMatch = s.match(/^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$/);
  if (rangeMatch) {
    return parseFloat(rangeMatch[2]);
  }

  // Plain number
  const num = parseFloat(s);
  return isNaN(num) ? null : num;
}

export function parseIngredient(line: string): ParsedIngredient {
  const original = line.trim();
  let text = original;

  // Strip leading "- "
  text = text.replace(/^-\s*/, '');

  // Strip parentheticals like "(14 oz)" for parsing only
  let parseText = text.replace(PARENTHETICAL, ' ').trim();

  // Try to extract quantity
  let quantity: number | null = null;
  let rest = parseText;

  // Check for word numbers first: "one large onion", "half a lemon"
  const wordMatch = parseText.match(/^(one|two|three|four|five|six|seven|eight|nine|ten|half|a|an)\b\s*/i);
  if (wordMatch) {
    const word = wordMatch[1].toLowerCase();
    if (word in WORD_NUMBERS) {
      quantity = WORD_NUMBERS[word];
      rest = parseText.slice(wordMatch[0].length);
    }
  }

  if (quantity === null) {
    // Try numeric patterns: "2 1/2", "1/3", "2-3", "2.5", unicode fractions
    const numMatch = parseText.match(/^(\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?|[^\x00-\x7F])/);
    if (numMatch) {
      const parsed = parseFraction(numMatch[1].trim());
      if (parsed !== null) {
        quantity = parsed;
        rest = parseText.slice(numMatch[0].length).trim();
      }
    }
  }

  // Try to extract unit
  let unit: string | null = null;
  const unitMatch = rest.match(/^(\S+)\s+/);
  if (unitMatch) {
    const candidate = unitMatch[1].toLowerCase().replace(/\.$/, '');
    if (candidate in UNIT_MAP) {
      unit = UNIT_MAP[candidate];
      rest = rest.slice(unitMatch[0].length);
    }
  }

  // Strip "of " after unit
  rest = rest.replace(/^of\s+/i, '');

  // displayText: full text after qty/unit (preserves prep words, parentheticals in rest)
  const displayText = rest.trim();

  // name: stripped of prep words for grocery aggregation
  const strippedRest = rest.replace(PREP_WORDS, '').replace(/[\s,\-–—]+$/, '').trim();
  const name = strippedRest.toLowerCase() || displayText.toLowerCase();

  return { quantity, unit, name, displayText, original };
}

export function formatQuantity(qty: number): string {
  if (qty === Math.floor(qty)) return String(qty);

  const fractions: [number, string][] = [
    [0.125, '1/8'], [0.25, '1/4'], [0.333, '1/3'], [0.375, '3/8'],
    [0.5, '1/2'], [0.625, '5/8'], [0.667, '2/3'], [0.75, '3/4'], [0.875, '7/8'],
  ];

  const whole = Math.floor(qty);
  const frac = qty - whole;

  for (const [val, str] of fractions) {
    if (Math.abs(frac - val) < 0.05) {
      return whole > 0 ? `${whole} ${str}` : str;
    }
  }

  return qty.toFixed(1).replace(/\.0$/, '');
}

export function formatIngredient(parsed: ParsedIngredient, scaleFactor: number = 1): string {
  if (parsed.quantity === null) return parsed.original;

  const scaled = parsed.quantity * scaleFactor;
  const qtyStr = formatQuantity(scaled);
  const unit = parsed.unit || '';

  // Pluralize unit if quantity > 1 and unit is singular
  let displayUnit = unit;
  if (scaled > 1 && unit && !unit.endsWith('s') && unit !== 'oz' && unit !== 'tsp' && unit !== 'tbsp') {
    displayUnit = unit + 's';
  }

  return [qtyStr, displayUnit, parsed.displayText].filter(Boolean).join(' ');
}

export function ingredientKey(parsed: ParsedIngredient): string {
  return `${parsed.unit || '_'}:${parsed.name}`;
}
