import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, Bot, User, Wrench, AlertTriangle } from "lucide-react";
import type { Message } from "../types";

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble = ({ message }: MessageBubbleProps) => {
  const [stepsOpen, setStepsOpen] = useState(false);
  const isUser = message.role === "user";
  const hasSteps = (message.steps?.length ?? 0) > 0;

  return (
    <div className={`message-wrapper ${isUser ? "message-wrapper-user" : "message-wrapper-assistant"}`}>
      {/* Avatar */}
      <div className={`avatar ${isUser ? "avatar-user" : "avatar-assistant"}`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={`bubble-container ${isUser ? "bubble-container-user" : ""}`}>
        {/* Bubble */}
        <div className={`bubble ${isUser ? "bubble-user" : "bubble-assistant"}`}>
          {isUser ? (
            <p className="bubble-user-text">{message.content}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}

          {message.error && (
            <div className="error-notice">
              <AlertTriangle size={14} />
              <span>Something went wrong. Please try again.</span>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className={`timestamp ${isUser ? "timestamp-user" : ""}`}>
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>

        {/* Intermediate Steps Accordion */}
        {hasSteps && (
          <div className="steps-container">
            <button
              className="steps-toggle"
              onClick={() => setStepsOpen((o) => !o)}
            >
              <Wrench size={13} />
              <span>
                {message.steps!.length} tool call
                {message.steps!.length !== 1 ? "s" : ""}
              </span>
              {stepsOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {stepsOpen && (
              <div className="steps-list">
                {message.steps!.map((step, idx) => (
                  <div key={idx} className="step-item">
                    <div className="step-tool">
                      <Wrench size={11} />
                      <span>{step.tool}</span>
                    </div>
                    <div className="step-input">
                      <span className="step-label">Input:</span>
                      <code>{step.input}</code>
                    </div>
                    {step.output && (
                      <div className="step-output">
                        <span className="step-label">Output:</span>
                        <code>{step.output}</code>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
