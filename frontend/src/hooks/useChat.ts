import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { sendMessage } from "../api/client";
import type { Message } from "../types";

export const useChat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const sessionId = useRef<string>(uuidv4());

  const addMessage = useCallback((msg: Omit<Message, "id" | "timestamp">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: uuidv4(), timestamp: new Date() },
    ]);
  }, []);

  const submit = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      addMessage({ role: "user", content: text });
      setIsLoading(true);

      try {
        const response = await sendMessage({
          message: text,
          session_id: sessionId.current,
        });

        sessionId.current = response.session_id;

        addMessage({
          role: "assistant",
          content: response.answer,
          steps: response.intermediate_steps,
          error: response.error,
        });
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        addMessage({
          role: "assistant",
          content:
            "I'm sorry, I couldn't process your request. Please try again.",
          error: message,
        });
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, addMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    sessionId.current = uuidv4();
  }, []);

  return { messages, isLoading, submit, clearMessages };
};
