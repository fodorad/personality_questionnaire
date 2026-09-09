/**
 * Ported from personality_questionnaire/scoring.py -- see that file for the
 * canonical implementation and docs/design.md for why this port exists at
 * all (Gradio Lite, the alternative to a second implementation, turned out
 * to be broken and unmaintained upstream).
 *
 * Kept free of any React import, mirroring demo/form.py's own discipline, so
 * it can be unit-tested directly against the same fixtures scoring.py's own
 * tests use (see scoring.test.ts).
 */

import type { Questionnaire, Responses } from "./types";

const BIG_FIVE_DOMAINS = [
  "openness",
  "conscientiousness",
  "extraversion",
  "agreeableness",
  "neuroticism",
];

/**
 * One subscale's raw (unnormalized) score for a single participant.
 *
 * Mirrors scoring.py's _weight_matrix() + subscale_means(), collapsed to a
 * single participant since there is no cohort to vectorize over in the
 * browser: `share = 1/len(items)` for a mean aggregation, `1` for sum. A
 * reverse-keyed item contributes `-share * value + (minimum + maximum) *
 * share`; a forward item contributes `share * value`.
 */
function rawSubscaleScore(
  questionnaire: Questionnaire,
  subscale: Questionnaire["subscales"][number],
  responses: Responses,
): number {
  const share = subscale.aggregation === "sum" ? 1 : 1 / subscale.items.length;
  const reflection = questionnaire.minimum + questionnaire.maximum;
  const reverseSet = new Set(subscale.reverse);

  let total = 0;
  for (const itemNumber of subscale.items) {
    const value = responses[itemNumber];
    if (reverseSet.has(itemNumber)) {
      total += -share * value + reflection * share;
    } else {
      total += share * value;
    }
  }
  return total;
}

/**
 * Round floating-point noise near zero to exactly 0, matching scoring.py's
 * own rounding step (a value like -2.8e-17 must not print as "-0.000").
 */
function snapToZero(value: number): number {
  const rounded = Math.round(value * 1e12) / 1e12;
  return rounded === 0 ? 0 : rounded;
}

/**
 * Score a complete set of responses to one instrument, for one participant.
 *
 * Mirrors scoring.py's score(): every subscale's raw score, then linear
 * normalization to [0, 1] for mean-aggregated subscales only -- a
 * sum-aggregated subscale (a published total, like PANAS's 10-50 range) is
 * never rescaled, matching scoring.py's exemption exactly.
 *
 * @param questionnaire - The instrument being scored.
 * @param responses - Item number to response value; must cover every item.
 * @returns Subscale name to its (possibly normalized) score.
 */
export function scoreQuestionnaire(
  questionnaire: Questionnaire,
  responses: Responses,
): Record<string, number> {
  const result: Record<string, number> = {};

  for (const subscale of questionnaire.subscales) {
    const raw = rawSubscaleScore(questionnaire, subscale, responses);
    const shouldNormalize = questionnaire.normalize && subscale.aggregation !== "sum";
    const value = shouldNormalize
      ? snapToZero(
          (raw - questionnaire.minimum) / (questionnaire.maximum - questionnaire.minimum),
        )
      : raw;
    result[subscale.name] = value;
  }

  return result;
}

/**
 * Whether an instrument's top-level subscales are exactly the five Big Five
 * domains, in any order. Ported verbatim from demo/plots.py::is_big_five --
 * generic over instrument key, not a hardcoded list of which keys match.
 *
 * @param questionnaire - The instrument to check.
 * @returns True if its first level is exactly the five Big Five domains.
 */
export function isBigFive(questionnaire: Questionnaire): boolean {
  const firstLevel = questionnaire.subscales[0]?.level;
  const topLevelNames = questionnaire.subscales
    .filter((s) => s.level === firstLevel)
    .map((s) => s.name);

  if (topLevelNames.length !== BIG_FIVE_DOMAINS.length) return false;
  const names = new Set(topLevelNames);
  return BIG_FIVE_DOMAINS.every((domain) => names.has(domain));
}

/**
 * Report which items of an instrument have no response yet.
 *
 * Mirrors demo/form.py::missing_items(): an item is answered if its number
 * is a key in responses; unanswered numbers are reported in administration
 * order.
 *
 * @param questionnaire - The instrument being answered.
 * @param responses - Item number to response value, for whatever is answered.
 * @returns Unanswered item numbers, in administration order.
 */
export function missingItems(questionnaire: Questionnaire, responses: Responses): number[] {
  return questionnaire.items
    .map((item) => item.number)
    .filter((number) => !(number in responses));
}

/**
 * The instrument's top-level subscales, in declaration order -- what a bar
 * chart or the pentagon radar plots one axis/bar per.
 *
 * @param questionnaire - The instrument to inspect.
 * @returns Subscales at the first level that appears in questionnaire.subscales.
 */
export function topLevelSubscales(questionnaire: Questionnaire) {
  const firstLevel = questionnaire.subscales[0]?.level;
  return questionnaire.subscales.filter((s) => s.level === firstLevel);
}
