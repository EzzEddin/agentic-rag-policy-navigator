import { Scale, Activity } from "lucide-react";

interface HeaderProps {
  agentReady: boolean;
}

export const Header = ({ agentReady }: HeaderProps) => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-brand">
          <div className="header-icon">
            <Scale size={24} />
          </div>
          <div>
            <h1 className="header-title">Policy Navigator</h1>
            <p className="header-subtitle">
              AI-powered government regulation research
            </p>
          </div>
        </div>
        <div className="header-status">
          <Activity
            size={14}
            className={agentReady ? "status-icon-ready" : "status-icon-loading"}
          />
          <span className={agentReady ? "status-text-ready" : "status-text-loading"}>
            {agentReady ? "Agent Ready" : "Initialising…"}
          </span>
        </div>
      </div>
    </header>
  );
};
