import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  RadialLinearScale,
  Title,
  Tooltip,
} from "chart.js";
import { Bar, Radar } from "react-chartjs-2";
import { domainColor, INK, NEUTRAL, PAPER } from "../theme";
import { isBigFive, topLevelSubscales } from "../scoring";
import type { Questionnaire } from "../types";

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
);

interface ResultsChartProps {
  questionnaire: Questionnaire;
  scores: Record<string, number>;
}

/**
 * Render the right chart for one instrument's computed scores: a radar for
 * the Big Five forms (five equal, comparable domains), a bar chart otherwise
 * -- mirroring demo/plots.py::plot_for's dispatch exactly.
 */
export function ResultsChart({ questionnaire, scores }: ResultsChartProps) {
  const subscales = topLevelSubscales(questionnaire);
  const labels = subscales.map((s) => s.name);
  const values = subscales.map((s) => scores[s.name]);
  const colors = subscales.map((s, i) => domainColor(s.name, i));

  if (isBigFive(questionnaire)) {
    return (
      <Radar
        data={{
          labels: labels.map((l) => l.charAt(0).toUpperCase() + l.slice(1)),
          datasets: [
            {
              data: values,
              backgroundColor: "#B84C1440",
              borderColor: "#12294B",
              borderWidth: 2,
              pointBackgroundColor: colors,
              pointRadius: 4,
            },
          ],
        }}
        options={{
          scales: {
            r: {
              min: 0,
              max: 1,
              ticks: { stepSize: 0.25, color: NEUTRAL, backdropColor: PAPER },
              pointLabels: { color: INK, font: { size: 13 } },
              grid: { color: `${NEUTRAL}4D` },
              angleLines: { color: `${NEUTRAL}4D` },
            },
          },
          plugins: { legend: { display: false } },
        }}
      />
    );
  }

  const normalized = questionnaire.normalize;
  const scaleLabel = normalized
    ? "Score [0, 1]"
    : `Score [${questionnaire.minimum}, ${questionnaire.maximum}]`;

  return (
    <Bar
      data={{
        labels,
        datasets: [
          {
            data: values,
            backgroundColor: colors,
            borderRadius: 4,
          },
        ],
      }}
      options={{
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: scaleLabel, color: INK },
            ticks: { color: INK },
            grid: { color: `${NEUTRAL}33` },
          },
          x: { ticks: { color: INK }, grid: { display: false } },
        },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => ctx.formattedValue } },
        },
      }}
    />
  );
}
