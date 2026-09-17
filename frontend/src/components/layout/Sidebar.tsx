import { t } from "../../i18n";
import { useAssessment } from "../../context/AssessmentContext";
import {
  Activity,
  ChartNoAxesCombined,
  CircleCheck,
  FileText,
  House,
  Leaf,
  Clock3,
} from "lucide-react";
import type { ModuleId } from "../../types/battery";
const items = [
  { id: "health", name: "Battery Health", Icon: Activity },
  { id: "life", name: "Remaining Life", Icon: Clock3 },
  { id: "carbon", name: "Carbon Passport", Icon: Leaf },
  { id: "decision", name: "Green Decision", Icon: CircleCheck },
  { id: "report", name: "Assessment Report", Icon: FileText },
] as const;
export default function Sidebar({
  onModule,
}: {
  onModule: (id: ModuleId) => void;
}) {
  const { backendStatus } = useAssessment();
  return (
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label={t("电循智策首页")}>
        <Leaf size={37} strokeWidth={1.6} />
        <span>
          <strong>{t("电循智策")}</strong>
          <small>{t("Lifecycle Intelligence")}</small>
        </span>
      </a>
      <nav aria-label={t("主导航")}>
        <a className="nav-item selected" href="#overview" aria-current="page">
          <House size={20} />{t("Overview")}</a>
        {t(items.map(({ id, name, Icon }) => (
          <button
            className="nav-item"
            key={id}
            aria-label={t(name)}
            onClick={() => onModule(id)}
          >
            <Icon size={20} />
            <span>{t(name)}</span>
          </button>
        )))}
      </nav>
      <div className="engine">
        <ChartNoAxesCombined size={18} />
        <span>{t("Battery Intelligence Engine")}</span>
        <div>
          <i
            className="status-dot"
            style={{
              background: backendStatus === "online" ? undefined : "#999",
            }}
          />
          {t(backendStatus === "online"
            ? "Online"
            : backendStatus === "checking"
              ? "Checking…"
              : "Offline")}{t(" ")}
          <span className="muted">{t("· API v1")}</span>
        </div>
      </div>
    </aside>
  );
}
