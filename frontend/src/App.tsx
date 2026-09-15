import { useState } from "react";
import { Database, Info } from "lucide-react";
import { useAssessment } from "./context/AssessmentContext";
import AssessmentControls from "./components/AssessmentControls";
import Sidebar from "./components/layout/Sidebar";
import Overview from "./pages/Overview";
import ModuleDialog from "./components/ModuleDialog";
import { scenarios } from "./data/demoBattery";
import type { ModuleId } from "./types/battery";
export default function App() {
  const a = useAssessment();
  const [module, setModule] = useState<ModuleId | "assessment" | null>(null);
  const data = scenarios[a.currentScenario];
  const close = () => setModule(null);
  const assess = () => {
    void a.runAssessment();
  };
  return (
    <>
      <a className="skip-link" href="#workspace">
        跳到主要内容
      </a>
      <Sidebar onModule={setModule} />
      <div className="app-shell" id="overview">
        <header className="header">
          <div>
            <span>Overview</span>
            <i />
            <span className="header-subtitle">Lifecycle Intelligence</span>
          </div>
          <div className="dataset-badge">
            <Database size={13} />
            {a.dataSource === "live"
              ? "LIVE ANALYSIS / Live Backend"
              : "DEMO DATA / Local Demo"}
          </div>
        </header>
        <main id="workspace">
          <div className="workspace-context">
            <span>BATTERY LIFECYCLE INTELLIGENCE & GREEN DECISION</span>
            <span>
              <Info size={12} />
              公开电芯模型 · 情景决策 · 数据可追溯
            </span>
          </div>
          <AssessmentControls />
          <Overview
            data={data}
            onScenario={a.setScenario}
            onAssess={assess}
            onModule={setModule}
            busy={a.assessmentStatus === "loading" || a.validating}
          />
        </main>
      </div>
      <ModuleDialog module={module} data={data} onClose={close} progress={5} />
    </>
  );
}
