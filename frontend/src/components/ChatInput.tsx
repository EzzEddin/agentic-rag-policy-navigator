import { useState, useRef, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
}

const EXAMPLE_QUESTIONS = [
  "Does GDPR apply to manual paper files?",
  "What does the Clean Air Act say about emission standards?",
  "Is Executive Order 14067 still in effect?",
  "Has Section 230 ever been challenged in court?",
];

export const ChatInput = ({ onSubmit, isLoading }: ChatInputProps) => {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = () => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    }
  };

  return (
    <div className="chat-input-area">
      {/* Example questions */}
      <div className="example-chips">
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            className="chip"
            onClick={() => {
              setValue(q);
              textareaRef.current?.focus();
            }}
            disabled={isLoading}
          >
            {q}
          </button>
        ))}
      </div>

      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask about government regulations, policies, or compliance requirements…"
          rows={1}
          disabled={isLoading}
        />
        <button
          className={`send-btn ${isLoading ? "send-btn-loading" : ""}`}
          onClick={handleSubmit}
          disabled={isLoading || !value.trim()}
          aria-label="Send message"
        >
          {isLoading ? <Loader2 size={20} className="spin" /> : <Send size={20} />}
        </button>
      </div>
      <p className="input-hint">Press Enter to send · Shift+Enter for new line</p>
    </div>
  );
};
