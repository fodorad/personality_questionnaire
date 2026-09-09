import { INK, NEUTRAL, PRIMARY } from "../theme";
import type { InstrumentRegistry } from "../types";

interface InstrumentSelectorProps {
  registry: InstrumentRegistry;
  selectedKey: string;
  onSelect: (key: string) => void;
}

/** The instrument dropdown, labelled by each instrument's own abbreviation. */
export function InstrumentSelector({ registry, selectedKey, onSelect }: InstrumentSelectorProps) {
  const questionnaire = registry[selectedKey];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <select
        value={selectedKey}
        onChange={(event) => onSelect(event.target.value)}
        style={{
          padding: "0.5rem 0.75rem",
          borderRadius: "8px",
          border: `1px solid ${NEUTRAL}`,
          fontSize: "0.95rem",
          color: INK,
          background: "white",
          width: "100%",
          maxWidth: "32rem",
        }}
      >
        {Object.values(registry).map((q) => (
          <option key={q.key} value={q.key}>
            {q.abbreviation}: {q.name}
          </option>
        ))}
      </select>
      <p style={{ color: NEUTRAL, fontSize: "0.85rem", fontStyle: "italic", margin: 0 }}>
        {questionnaire.citation}
      </p>
      <p style={{ color: PRIMARY, fontSize: "0.8rem", margin: 0 }}>
        {questionnaire.items.length} items: {questionnaire.scale === "likert" ? "1-5 scale" : `${questionnaire.minimum}-${questionnaire.maximum} scale`}
      </p>
    </div>
  );
}
