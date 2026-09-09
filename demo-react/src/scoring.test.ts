/**
 * Tests scoring.ts against the same fixtures scoring.py's own tests use
 * (tests/fixtures.py, tests/test_scoring.py, tests/instruments/test_panas.py),
 * so a transcription error in the TypeScript port is caught the same way a
 * mistake in the Python arithmetic would be -- against a hand-computed or
 * published-since-1.0.0 expected value, not a value invented for this port.
 */

import { describe, expect, it } from "vitest";
import instruments from "./instruments.json";
import { isBigFive, missingItems, scoreQuestionnaire } from "./scoring";
import type { InstrumentRegistry, Responses } from "./types";

const registry = instruments as InstrumentRegistry;

function constantResponses(nItems: number, value: number): Responses {
  const responses: Responses = {};
  for (let n = 1; n <= nItems; n++) responses[n] = value;
  return responses;
}

describe("isBigFive", () => {
  it("is true for the three Big Five forms", () => {
    expect(isBigFive(registry["bfi10"])).toBe(true);
    expect(isBigFive(registry["bfi2"])).toBe(true);
    expect(isBigFive(registry["bfi2-xs"])).toBe(true);
  });

  it("is false for PANAS and VAS-F", () => {
    expect(isBigFive(registry["panas"])).toBe(false);
    expect(isBigFive(registry["vasf"])).toBe(false);
  });
});

describe("missingItems", () => {
  it("reports every item when nothing has been answered", () => {
    const bfi10 = registry["bfi10"];
    expect(missingItems(bfi10, {})).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });

  it("reports nothing once every item is answered", () => {
    const bfi10 = registry["bfi10"];
    expect(missingItems(bfi10, constantResponses(10, 3))).toEqual([]);
  });

  it("reports only the gaps, in order", () => {
    const bfi10 = registry["bfi10"];
    const responses = constantResponses(10, 3);
    delete responses[2];
    delete responses[7];
    expect(missingItems(bfi10, responses)).toEqual([2, 7]);
  });
});

describe("scoreQuestionnaire: BFI-2 midpoint invariant", () => {
  it("answering every item 3 lands every subscale at exactly 0.5", () => {
    const bfi2 = registry["bfi2"];
    const scores = scoreQuestionnaire(bfi2, constantResponses(60, 3));
    for (const subscale of bfi2.subscales) {
      expect(scores[subscale.name]).toBeCloseTo(0.5, 10);
    }
  });

  it("answering every item 1 or 5 still lands every domain at 0.5 (half reverse-keyed)", () => {
    const bfi2 = registry["bfi2"];
    for (const value of [1, 5]) {
      const scores = scoreQuestionnaire(bfi2, constantResponses(60, value));
      const domains = bfi2.subscales.filter((s) => s.level === "domain");
      for (const domain of domains) {
        expect(scores[domain.name]).toBeCloseTo(0.5, 10);
      }
    }
  });
});

describe("scoreQuestionnaire: BFI-2 published fixture", () => {
  // tests/data/test_bfi2_answers.npy, raw answers for two participants,
  // dumped from the current scorer this session and cross-checked to
  // reproduce tests/fixtures.py::PUBLISHED_OCEAN exactly.
  const participant1 = [
    2, 3, 4, 4, 1, 4, 5, 3, 3, 4, 2, 1, 3, 2, 4, 4, 3, 2, 2, 1, 1, 1, 2, 4, 3, 4, 2, 2, 3, 2, 4, 3,
    4, 2, 1, 2, 1, 4, 2, 4, 2, 4, 5, 5, 1, 2, 4, 2, 3, 5, 3, 4, 4, 1, 4, 4, 2, 2, 1, 3,
  ];
  const participant2 = [
    4, 3, 5, 4, 5, 5, 3, 5, 1, 5, 1, 4, 2, 3, 3, 1, 3, 2, 1, 3, 2, 5, 5, 4, 1, 4, 3, 5, 2, 5, 3, 3,
    2, 4, 4, 3, 4, 2, 3, 4, 5, 1, 2, 1, 1, 5, 3, 1, 2, 4, 3, 2, 1, 4, 1, 5, 3, 4, 4, 2,
  ];

  // Published domain scores, in OCEAN order, since 1.0.0 -- themselves
  // rounded to 3 decimals for display, so assertions below check to 2
  // decimals: the actual Python value (e.g. agreeableness for participant 2)
  // is 0.4375 exactly, which rounds to the published 0.438 but sits right at
  // the edge of a 3-decimal toBeCloseTo tolerance.
  const published = {
    p1: {
      openness: 0.521,
      conscientiousness: 0.646,
      extraversion: 0.417,
      agreeableness: 0.604,
      neuroticism: 0.25,
    },
    p2: {
      openness: 0.583,
      conscientiousness: 0.208,
      extraversion: 0.729,
      agreeableness: 0.438,
      neuroticism: 0.604,
    },
  };

  function toResponses(answers: number[]): Responses {
    const responses: Responses = {};
    answers.forEach((value, index) => {
      responses[index + 1] = value;
    });
    return responses;
  }

  it("matches the published OCEAN domain scores for participant 1", () => {
    const bfi2 = registry["bfi2"];
    const scores = scoreQuestionnaire(bfi2, toResponses(participant1));
    for (const [domain, expected] of Object.entries(published.p1)) {
      expect(scores[domain]).toBeCloseTo(expected, 2);
    }
  });

  it("matches the published OCEAN domain scores for participant 2", () => {
    const bfi2 = registry["bfi2"];
    const scores = scoreQuestionnaire(bfi2, toResponses(participant2));
    for (const [domain, expected] of Object.entries(published.p2)) {
      expect(scores[domain]).toBeCloseTo(expected, 2);
    }
  });
});

describe("scoreQuestionnaire: PANAS sum vs mean", () => {
  it("matches the hand-computed vector: positive=4, negative=2", () => {
    const panas = registry["panas"];
    const positiveItems = [1, 3, 5, 9, 10, 12, 14, 16, 17, 19];
    const negativeItems = [2, 4, 6, 7, 8, 11, 13, 15, 18, 20];

    const responses: Responses = {};
    for (const n of positiveItems) responses[n] = 4;
    for (const n of negativeItems) responses[n] = 2;

    const scores = scoreQuestionnaire(panas, responses);
    expect(scores["Positive Affect"]).toBeCloseTo(0.75, 10);
    expect(scores["Negative Affect"]).toBeCloseTo(0.25, 10);
    expect(scores["Positive Affect (sum)"]).toBeCloseTo(40, 10);
    expect(scores["Negative Affect (sum)"]).toBeCloseTo(20, 10);
  });

  it("sum equals mean times item count, and sum subscales are never rescaled", () => {
    const panas = registry["panas"];
    const scores = scoreQuestionnaire(panas, constantResponses(20, 5));
    expect(scores["Positive Affect"]).toBeCloseTo(1.0, 10);
    expect(scores["Positive Affect (sum)"]).toBeCloseTo(50, 10);
    expect(scores["Negative Affect (sum)"]).toBeCloseTo(50, 10);
  });

  it("all-1 answers give sum totals of exactly 10 for both scales", () => {
    const panas = registry["panas"];
    const scores = scoreQuestionnaire(panas, constantResponses(20, 1));
    expect(scores["Positive Affect (sum)"]).toBe(10);
    expect(scores["Negative Affect (sum)"]).toBe(10);
  });
});

describe("scoreQuestionnaire: VAS-F normalization bounds", () => {
  it("all-zero answers score Fatigue at exactly 0", () => {
    const vasf = registry["vasf"];
    const scores = scoreQuestionnaire(vasf, constantResponses(18, 0));
    expect(scores["Fatigue"]).toBeCloseTo(0.0, 10);
  });

  it("all-max answers score Fatigue at exactly 1", () => {
    const vasf = registry["vasf"];
    const scores = scoreQuestionnaire(vasf, constantResponses(18, 10));
    expect(scores["Fatigue"]).toBeCloseTo(1.0, 10);
  });
});
