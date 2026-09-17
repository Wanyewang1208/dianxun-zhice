import { t } from "./i18n";
import { useLanguage } from "./i18n/useLanguage";
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
  const { language, setLanguage } = useLanguage();
  const a = useAssessment();
  const [module, setModule] = useState<ModuleId | "assessment" | null>(null);
  const data = scenarios[a.currentScenario];
  const close = () => setModule(null);
  const assess = () => {
    void a.runAssessment();
  };
  return (
    <>
      <a className="skip-link" href="#workspace">{t("跳到主要内容")}</a>
      <Sidebar onModule={setModule} />
      <div className="app-shell" id="overview">
        <header className="header">
          <div>
            <span>{t("Overview")}</span>
            <i />
            <span className="header-subtitle">{t("Lifecycle Intelligence")}</span>
          </div>
          <div className="header-actions">
          <div className="language-switch" role="group" aria-label={language === 'zh' ? '界面语言' : 'Interface language'}>
            <button type="button" lang="zh-CN" aria-pressed={language === 'zh'} onClick={() => setLanguage('zh')}>中文</button>
            <button type="button" lang="en" aria-pressed={language === 'en'} onClick={() => setLanguage('en')}>English</button>
          </div>
          <div className="dataset-badge">
            <Database size={13} />
            {t(a.dataSource === "live"
              ? "LIVE ANALYSIS / Live Backend"
              : "DEMO DATA / Local Demo")}
          </div>
          </div>
        </header>
        <main id="workspace">
          <div className="workspace-context">
            <span>{t("BATTERY LIFECYCLE INTELLIGENCE & GREEN DECISION")}</span>
            <span>
              <Info size={12} />{t("公开电芯模型 · 情景决策 · 数据可追溯")}</span>
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
