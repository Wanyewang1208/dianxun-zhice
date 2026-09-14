import { useEffect, useRef, useState } from "react";
import { Database, Info } from "lucide-react";
import Sidebar from "./components/layout/Sidebar";
import Overview from "./pages/Overview";
import ModuleDialog from "./components/ModuleDialog";
import { scenarios } from "./data/demoBattery";
import type { ModuleId, ScenarioId } from "./types/battery";
export default function App() {
  const [scenario, setScenario] = useState<ScenarioId>("used");
  const [module, setModule] = useState<ModuleId | "assessment" | null>(null);
  const [progress, setProgress] = useState(5);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const data = scenarios[scenario];
  const close = () => {
    if (timer.current) clearInterval(timer.current);
    setProgress(5);
    setModule(null);
  };
  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    [],
  );
  const assess = () => {
    setProgress(0);
    setModule("assessment");
    let step = 0;
    timer.current = setInterval(() => {
      step++;
      setProgress(step);
      if (step === 5 && timer.current) clearInterval(timer.current);
    }, 180);
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
            示例数据 <span>/ Demo Dataset</span>
          </div>
        </header>
        <main id="workspace">
          <div className="workspace-context">
            <span>BATTERY LIFECYCLE INTELLIGENCE & GREEN DECISION</span>
            <span>
              <Info size={12} />
              情景模拟 · 数据可追溯
            </span>
          </div>
          <Overview
            data={data}
            onScenario={setScenario}
            onAssess={assess}
            onModule={setModule}
            busy={progress < 5}
          />
        </main>
      </div>
      <ModuleDialog
        module={module}
        data={data}
        onClose={close}
        progress={progress}
      />
    </>
  );
}
