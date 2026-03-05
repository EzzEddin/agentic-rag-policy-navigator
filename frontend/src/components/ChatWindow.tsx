import { useEffect, useRef } from "react";
import { Bot, Loader2 } from "lucide-react";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
}

const WelcomeScreen = () => (
  <div className="welcome">
    <div className="welcome-icon">
      <Bot size={40} />
    </div>
    <h2 className="welcome-title">Policy Navigator</h2>
    <p className="welcome-subtitle">
      Ask questions about government regulations, executive orders, compliance
      requirements, or case law. I'll search indexed policy documents, the
      Federal Register, and CourtListener to give you accurate, sourced answers.
    </p>
    <div className="welcome-capabilities">
      <div className="capability-card">
        <span className="capability-emoji">📄</span>
        <span>Policy document search</span>
      </div>
      <div className="capability-card">
        <span className="capability-emoji">🏛️</span>
        <span>Federal Register lookup</span>
      </div>
      <div className="capability-card">
        <span className="capability-emoji">⚖️</span>
        <span>Case law research</span>
      </div>
    </div>
  </div>
);

export const ChatWindow = ({ messages, isLoading }: ChatWindowProps) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.length === 0 ? (
        <WelcomeScreen />
      ) : (
        <div className="messages-list">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div className="message-wrapper message-wrapper-assistant">
              <div className="avatar avatar-assistant">
                <Bot size={16} />
              </div>
              <div className="typing-indicator">
                <Loader2 size={16} className="spin" />
                <span>Researching your question…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};
