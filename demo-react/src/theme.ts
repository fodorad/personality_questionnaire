/**
 * Colour tokens mirrored from personality_questionnaire/core/theme.py, so
 * this demo reads as the same application as the Lab UI and the Gradio demo.
 * Kept in sync by hand (a small, stable palette) rather than generated,
 * unlike instruments.json.
 */

export const PRIMARY = "#12294B";
export const ACCENT = "#B84C14";
export const SUCCESS = "#2E6E5E";
export const WARNING = "#8A5A00";
export const DANGER = "#A6303B";
export const NEUTRAL = "#565F6E";
export const PAPER = "#FAF8F5";
export const INK = "#151B26";
export const UNANSWERED = "#DDD8D0";

export const DOMAIN_COLORS: Record<string, string> = {
  openness: "#3E4C8A",
  conscientiousness: "#2E6E5E",
  extraversion: "#B84C14",
  agreeableness: "#7A4A82",
  neuroticism: "#A6303B",
};

const FALLBACK_PALETTE = [PRIMARY, ACCENT, SUCCESS, DANGER, NEUTRAL];

/**
 * Resolve a subscale's colour, mirroring theme.py::domain_color: a Big Five
 * domain resolves through its own name; anything else falls back to a fixed
 * palette cycled by position, matching demo/plots.py's bar-chart behaviour.
 *
 * @param name - The subscale's name.
 * @param index - Its position among the subscales being plotted, for the fallback palette.
 * @returns A hex colour.
 */
export function domainColor(name: string, index: number): string {
  const lower = name.toLowerCase();
  if (lower in DOMAIN_COLORS) return DOMAIN_COLORS[lower];
  return FALLBACK_PALETTE[index % FALLBACK_PALETTE.length];
}
