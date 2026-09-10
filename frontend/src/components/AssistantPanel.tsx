import { Bot, Send } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import type { AssistantResponse } from "../types";

function renderInline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

function AssistantAnswer({ answer }: { answer: string }) {
  const blocks = answer.split(/\n\s*\n/).filter(Boolean);
  return <div className="assistant-answer-text">
    {blocks.map((block, blockIndex) => {
      const lines = block.split("\n");
      const bullets = lines.filter(line => /^\s*[-*]\s+/.test(line));
      if (bullets.length === lines.length && bullets.length > 0) {
        return <ul key={blockIndex}>{bullets.map((line, index) => <li key={index}>{renderInline(line.replace(/^\s*[-*]\s+/, ""))}</li>)}</ul>;
      }
      return <p key={blockIndex}>{lines.map((line, index) => <span key={index}>{index > 0 && <br />}{renderInline(line.replace(/^#{1,6}\s+/, ""))}</span>)}</p>;
    })}
  </div>;
}

const PROJECT_QUESTIONS = [
  "Why is this project high risk?",
  "How has its risk changed recently?",
  "Compare this project with similar projects.",
  "Explain the active warnings.",
  "How reliable is this prediction?",
  "What model-based scenarios should officials review?",
  "Compare the 3-month and 6-month risks.",
  "Why is this project prioritized for intervention?",
];

const PORTFOLIO_QUESTIONS = [
  "Which sectors need the most attention?",
  "Which ministries have the highest risk?",
  "What are the major portfolio warning patterns?",
  "Which projects should officials review first and why?",
];

export function AssistantPanel({ projectId }: { projectId?: string }) {
  const suggestions = projectId ? PROJECT_QUESTIONS : PORTFOLIO_QUESTIONS;
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function ask() {
    const clean = question.trim();
    if (!clean || loading) return;
    setLoading(true); setError(null); setResult(null);
    try {
      setResult(await api.askAssistant(clean, projectId));
    } catch {
      setError("The assistant response could not be loaded. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel assistant-panel" aria-label="Project Intelligence Assistant">
      <div className="panel-heading assistant-panel-heading">
        <div className="assistant-heading-left">
          <span className="eyebrow assistant-eyebrow">Grounded decision support</span>
          <h2 className="assistant-title">
            <span className="assistant-icon-wrap">
              <Bot size={18} />
            </span>
            <span>Project Intelligence Assistant</span>
          </h2>
        </div>
        {result && (
          <span className="assistant-provider">
            {result.provider === "openrouter" ? "Gemma via OpenRouter" : "Offline grounded summary"}
          </span>
        )}
      </div>

      <div className="assistant-suggestions">
        {suggestions.map(item => (
          <button type="button" key={item} onClick={() => setQuestion(item)}>
            {item}
          </button>
        ))}
      </div>

      <label className="assistant-input">
        <span className="assistant-input-label">Question</span>
        <div className="textarea-wrapper">
          <textarea 
            aria-label="Assistant question" 
            maxLength={1500} 
            rows={3} 
            value={question} 
            placeholder={projectId ? "Ask about this project's risk, trend, drivers, peers, warnings, or scenarios" : "Ask about portfolio risk, sectors, ministries, warnings, or review priorities"} 
            onChange={event => setQuestion(event.target.value)} 
          />
          <small className="assistant-counter">{question.length} / 1500</small>
        </div>
      </label>

      <div className="assistant-actions-row">
        <button 
          type="button" 
          className="primary-button assistant-submit" 
          disabled={!question.trim() || loading} 
          onClick={ask}
        >
          <Send size={15} /> 
          <span>{loading ? "Preparing grounded answer…" : "Ask"}</span>
        </button>
      </div>

      {error && <p className="inline-error" role="alert">{error}</p>}

      {result && (
        <div className="assistant-answer" aria-live="polite">
          <AssistantAnswer answer={result.answer} />
          <small className="assistant-sources">Sources: {result.sources_used.join(" · ")}</small>
        </div>
      )}

      <div className="assistant-transparency">
        <strong>Grounding notice</strong>
        <span>Answers are generated from PAIMANA Sentinel's structured analytics and model outputs. The assistant does not independently calculate project risk.</span>
        <span>Scenario estimates are model-based and do not establish causal impact.</span>
      </div>
    </section>
  );
}
