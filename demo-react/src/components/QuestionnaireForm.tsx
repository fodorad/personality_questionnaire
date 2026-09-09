import { ACCENT, INK, NEUTRAL, SUCCESS, UNANSWERED } from "../theme";
import type { Questionnaire, Responses } from "../types";

interface QuestionnaireFormProps {
  questionnaire: Questionnaire;
  responses: Responses;
  onAnswer: (itemNumber: number, value: number) => void;
}

/**
 * Render one form field per item: a radio group for a Likert item (choices
 * from the instrument's own labels), a slider for a visual-analogue item
 * (anchors shown as helper text) -- mirroring demo/form.py's field_specs
 * dispatch on scale exactly.
 */
export function QuestionnaireForm({ questionnaire, responses, onAnswer }: QuestionnaireFormProps) {
  const isLikert = questionnaire.scale === "likert";
  const labelEntries = Object.entries(questionnaire.labels);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      {questionnaire.items.map((item) => {
        const answered = item.number in responses;
        const borderColor = answered ? SUCCESS : UNANSWERED;

        return (
          <div
            key={item.number}
            style={{
              border: `1px solid ${borderColor}`,
              borderLeft: `4px solid ${borderColor}`,
              borderRadius: "10px",
              padding: "0.75rem 1rem",
              background: "white",
            }}
          >
            <div style={{ marginBottom: "0.5rem", color: INK, fontSize: "0.95rem" }}>
              {item.prompt}
            </div>

            {isLikert ? (
              <div
                style={{
                  display: "flex",
                  flexWrap: "nowrap",
                  justifyContent: "space-between",
                  gap: "0.75rem",
                }}
              >
                {labelEntries.map(([label, value]) => (
                  <label
                    key={label}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.35rem",
                      fontSize: "0.85rem",
                      color: INK,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    <input
                      type="radio"
                      name={`item-${item.number}`}
                      checked={responses[item.number] === value}
                      onChange={() => onAnswer(item.number, value)}
                      style={{ accentColor: ACCENT }}
                    />
                    {label}
                  </label>
                ))}
              </div>
            ) : (
              <div>
                <input
                  type="range"
                  min={questionnaire.minimum}
                  max={questionnaire.maximum}
                  step={1}
                  // App.tsx seeds every VAS item at the scale midpoint on
                  // mount/instrument-select, so this is always answered --
                  // the fallback only matters if a caller ever renders this
                  // form with a genuinely empty VAS responses map.
                  value={responses[item.number] ?? Math.round((questionnaire.minimum + questionnaire.maximum) / 2)}
                  onChange={(event) => onAnswer(item.number, Number(event.target.value))}
                  style={{ width: "100%", accentColor: ACCENT }}
                />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.75rem",
                    color: NEUTRAL,
                  }}
                >
                  <span>{item.lowAnchor}</span>
                  <span>{item.highAnchor}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
