// Shared motion grammar. One curve family for the whole page: a strong ease-out for anything
// entering, so the first frames move and the end settles.
export const EASE_OUT: [number, number, number, number] = [0.23, 1, 0.32, 1];

const PAPER = [241, 236, 226];
const WARM = [255, 90, 60];
const COOL = [95, 212, 177];

/**
 * Blend the paper text colour toward warm (raises risk) or cool (lowers it) by model weight.
 * Returns a plain rgb() string so it can be interpolated by the animation library.
 */
export function heatColor(weight: number | undefined): string | undefined {
  if (weight === undefined || Math.abs(weight) < 0.1) return undefined;
  const t = 0.4 + 0.6 * Math.min(1, Math.abs(weight) / 0.5);
  const target = weight > 0 ? WARM : COOL;
  const [r, g, b] = PAPER.map((p, i) => Math.round(p + (target[i] - p) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

/** Split text into word and non-word tokens, keeping everything so it can be re-joined. */
export function tokenize(text: string): { text: string; word: boolean }[] {
  const out: { text: string; word: boolean }[] = [];
  const re = /([A-Za-z0-9]+)|([^A-Za-z0-9]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    out.push({ text: m[0], word: m[1] !== undefined });
  }
  return out;
}
