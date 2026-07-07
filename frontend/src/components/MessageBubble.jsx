import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import PieChart from "./PieChart";

// GFM only parses a table when there's a BLANK LINE before it. The model
// sometimes glues a table directly under a heading/paragraph, which makes
// react-markdown fall back to paragraph rendering (the "| --- | --- |" soup).
// This inserts the missing blank line before any run of table rows.
function normalizeMarkdown(md) {
  const lines = String(md ?? "").split("\n");
  const isRow = (l) => /^\s*\|.*\|\s*$/.test(l);
  const out = [];
  for (const line of lines) {
    const prev = out.length ? out[out.length - 1] : "";
    if (isRow(line) && prev.trim() !== "" && !isRow(prev)) {
      out.push(""); // blank line so GFM recognises the table block
    }
    out.push(line);
  }
  return out.join("\n");
}

// Wrap tables so wide ones scroll horizontally instead of overflowing the bubble.
const mdComponents = {
  table: (props) => (
    <div className="table-wrap">
      <table {...props} />
    </div>
  ),
};

// One Insight row = one exchange: the user's prompt and the AI's response.
// The AI response is Markdown (rendered) and may carry chart_data (-> pie).
export default function MessageBubble({ message }) {
  const { user_prompt, conversational_response, chart_bool, chart_data } = message;

  const hasChart =
    chart_bool &&
    chart_data &&
    Array.isArray(chart_data.labels) &&
    Array.isArray(chart_data.values) &&
    chart_data.values.some((v) => Number(v) > 0);

  return (
    <>
      <div className="bubble user">{user_prompt}</div>

      <div className="bubble ai">
        <div className="markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
            {normalizeMarkdown(conversational_response)}
          </ReactMarkdown>
        </div>

        {hasChart && (
          <div className="chart-card">
            <div className="chart-card-title">
              {chart_data.title || "Allocation"}
            </div>
            <PieChart labels={chart_data.labels} values={chart_data.values} />
          </div>
        )}
      </div>
    </>
  );
}
