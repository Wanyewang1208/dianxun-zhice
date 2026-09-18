import { t } from "../../i18n";
import { CarFront, Recycle } from "lucide-react";
import { scenarios } from "../../data/demoBattery";
import type { ScenarioId } from "../../types/battery";
export default function ScenarioSwitch({
  value,
  onChange,
  disabled = false,
}: {
  value: ScenarioId;
  onChange: (id: ScenarioId) => void;
  disabled?: boolean;
}) {
  return (
    <div className="scenario-switch" role="group" aria-label={t("评估场景")}>
      {t((["used", "retired"] as const).map((id) => (
        <button
          disabled={disabled}
          type="button"
          aria-pressed={value === id}
          className={value === id ? "active" : ""}
          key={id}
          onClick={() => onChange(id)}
        >
          {t(id === "used" ? <CarFront size={18} /> : <Recycle size={18} />)}
          <span>{t(scenarios[id].name)}</span>
        </button>
      )))}
    </div>
  );
}
