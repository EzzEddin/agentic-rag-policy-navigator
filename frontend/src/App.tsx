import { useState, useEffect } from "react";
import { Trash2 } from "lucide-react";
import { Header } from "./components/Header";
import { ChatWindow } from "./components/ChatWindow";
import { ChatInput } from "./components/ChatInput";
import { useChat } from "./hooks/useChat";
import { getAgentStatus } from "./api/client";
import "./App.css";

function App() {
  const { messages, isLoading, submit, clearMessages } = useChat();
  const [agentReady, setAgentReady] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await getAgentStatus();
        setAgentReady(status.agent_ready);
      } catch {
        setAgentReady(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <Header agentReady={agentReady} />

      <main className="main">
        <div className="toolbar">
          {messages.length > 0 && (
            <button
              className="toolbar-btn toolbar-btn-danger"
              onClick={clearMessages}
              title="Clear conversation"
            >
              <Trash2 size={16} />
              <span>Clear Chat</span>
            </button>
          )}
        </div>

        <ChatWindow messages={messages} isLoading={isLoading} />
        <ChatInput onSubmit={submit} isLoading={isLoading} />
      </main>

    </div>
  );
}

export default App;
