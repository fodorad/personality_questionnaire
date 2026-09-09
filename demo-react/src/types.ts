/**
 * Types matching the JSON shape scripts/export_instruments.py generates from
 * personality_questionnaire's registry.py. Field names are camelCase here
 * (lowAnchor, not low_anchor) since the export script already renames them;
 * everything else mirrors registry.py's Questionnaire/Item/Subscale exactly.
 */

export type ScaleType = "likert" | "vas";
export type Aggregation = "mean" | "sum";

export interface Item {
  number: number;
  text: string;
  prompt: string;
  lowAnchor: string;
  highAnchor: string;
  sourceNumber: number | null;
}

export interface Subscale {
  name: string;
  items: number[];
  reverse: number[];
  level: string;
  parent: string | null;
  higherIs: string;
  aggregation: Aggregation;
}

export interface Questionnaire {
  key: string;
  name: string;
  abbreviation: string;
  scale: ScaleType;
  minimum: number;
  maximum: number;
  citation: string;
  labels: Record<string, number>;
  paired: boolean;
  normalize: boolean;
  items: Item[];
  subscales: Subscale[];
}

export type InstrumentRegistry = Record<string, Questionnaire>;

/** Item number to response value, exactly as demo/form.py's responses dict. */
export type Responses = Record<number, number>;
