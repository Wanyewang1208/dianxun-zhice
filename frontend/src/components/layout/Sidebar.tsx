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
  return (
    <aside className="sidebar">
      <a className="brand" href="#overview" aria-label="电循智策首页">
        <Leaf size={37} strokeWidth={1.6} />
        <span>
          <strong>电循智策</strong>
          <small>DianXun ZhiCe</small>
        </span>
      </a>
      <nav aria-label="主导航">
        <a className="nav-item selected" href="#overview" aria-current="page">
          <House size={20} />
          Overview
        </a>
        {items.map(({ id, name, Icon }) => (
          <button className="nav-item" key={id} onClick={() => onModule(id)}>
            <Icon size={20} />
            <span>{name}</span>
          </button>
        ))}
      </nav>
      <div className="engine">
        <ChartNoAxesCombined size={18} />
        <span>Battery Intelligence Engine</span>
        <div>
          <i className="status-dot" />
          Online <span className="muted">· Demo v1.0</span>
        </div>
      </div>
    </aside>
  );
}
