import { useState } from "react";
import { InstrumentSelector } from "./components/InstrumentSelector";
import { QuestionnaireForm } from "./components/QuestionnaireForm";
import { ResultsChart } from "./components/ResultsChart";
import { missingItems, scoreQuestionnaire } from "./scoring";
import { ACCENT, DANGER, INK, PAPER, PRIMARY } from "./theme";
import instrumentsData from "./instruments.json";
import type { InstrumentRegistry, Questionnaire, Responses } from "./types";

const registry = instrumentsData as InstrumentRegistry;
const firstKey = Object.keys(registry)[0];

/**
 * Seed a VAS instrument's items at the scale midpoint, mirroring the
 * default value demo/app.py's gr.Slider mounts with. A visual-analogue item
 * (fatigue, mood) has no "correct" starting point the way a Likert item's
 * unset state does -- the midpoint is a deliberate default, not a filled-in
 * answer, so a participant is free to leave it and still submit. A Likert
 * item still starts genuinely unanswered: it renders no radio pre-selected,
 * matching demo/app.py's radios there too.
 */
function initialResponses(questionnaire: Questionnaire): Responses {
  if (questionnaire.scale !== "vas") return {};
  const midpoint = Math.round((questionnaire.minimum + questionnaire.maximum) / 2);
  const responses: Responses = {};
  for (const item of questionnaire.items) responses[item.number] = midpoint;
  return responses;
}

/**
 * The public demo: pick an instrument, answer it, see the scores plotted.
 *
 * Mirrors demo/app.py::build()'s flow -- select instrument, fill form,
 * Evaluate, validate-or-plot -- but reimplemented in React/TypeScript rather
 * than importing that Python. No storage anywhere: responses live only in
 * this component's own state and are gone on refresh, same guarantee as the
 * Gradio demo's own "nothing you enter is stored anywhere."
 */
function App() {
  const [selectedKey, setSelectedKey] = useState(firstKey);
  const [responses, setResponses] = useState<Responses>(() => initialResponses(registry[firstKey]));
  const [scores, setScores] = useState<Record<string, number> | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const questionnaire = registry[selectedKey];

  function handleSelect(key: string) {
    setSelectedKey(key);
    setResponses(initialResponses(registry[key]));
    setScores(null);
    setWarning(null);
  }

  function handleAnswer(itemNumber: number, value: number) {
    setResponses((prev) => ({ ...prev, [itemNumber]: value }));
  }

  function handleEvaluate() {
    const missing = missingItems(questionnaire, responses);
    if (missing.length > 0) {
      setWarning(
        `${missing.length} item(s) still unanswered (item ${missing[0]}${
          missing.length > 1 ? ", …" : ""
        }).`,
      );
      setScores(null);
      return;
    }
    setWarning(null);
    setScores(scoreQuestionnaire(questionnaire, responses));
  }

  return (
    <div style={{ background: PAPER, minHeight: "100vh" }}>
      <div style={{ maxWidth: "64rem", margin: "0 auto", padding: "2rem 1.5rem" }}>
        <h1 style={{ color: PRIMARY, fontSize: "1.75rem", marginBottom: "0.25rem" }}>
          Personality Questionnaire Demo
        </h1>
        <p style={{ color: INK, marginTop: 0 }}>
          Pick an instrument, answer every item, then evaluate.
          <br />
          <strong>This is a demo: nothing you enter is stored anywhere.</strong> Runs entirely
          in your browser.
        </p>

        <div style={{ marginBottom: "1.5rem" }}>
          <InstrumentSelector registry={registry} selectedKey={selectedKey} onSelect={handleSelect} />
        </div>

        <QuestionnaireForm questionnaire={questionnaire} responses={responses} onAnswer={handleAnswer} />

        <div
          style={{
            marginTop: "1.5rem",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "1rem",
          }}
        >
          <button
            type="button"
            onClick={handleEvaluate}
            style={{
              background: ACCENT,
              color: "white",
              border: "none",
              borderRadius: "8px",
              padding: "0.75rem 1.5rem",
              fontSize: "1rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Evaluate
          </button>

          {warning && (
            <p style={{ color: DANGER, fontWeight: 600, margin: 0 }}>{warning}</p>
          )}

          {scores && (
            <div style={{ maxWidth: "28rem", width: "100%" }}>
              <ResultsChart questionnaire={questionnaire} scores={scores} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
