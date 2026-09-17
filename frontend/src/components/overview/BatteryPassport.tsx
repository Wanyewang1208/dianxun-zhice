import { t } from "../../i18n";
import { ScanLine, ShieldCheck, ShieldAlert } from "lucide-react";
import type { BatteryScenario } from "../../types/battery";
import { getBatteryModel } from "../../lib/batteryMath";
import { calculateLifecycleCarbon } from "../../lib/carbonMath";
import CountUp from "../CountUp";
export default function BatteryPassport({ data }: { data: BatteryScenario }) {
  const { soh, rul } = getBatteryModel(data);
  return (
    <section className="passport surface" aria-label={t("电池数字护照")}>
      <div className="passport-heading">
        <h2>{t("Battery Digital Passport")}</h2>
        <ScanLine size={22} />
      </div>
      <div className="passport-id">
        <span className="micro-label">{t("BATTERY ID")}</span>
        <strong>{data.batteryId}</strong>
        <span className={`risk-tag ${data.id === "retired" ? "amber" : ""}`}>
          {t(data.risk === "LOW" ? (
            <ShieldCheck size={13} />
          ) : (
            <ShieldAlert size={13} />
          ))}{t(" ")}
          {t(data.risk)}{t(" RISK")}</span>
      </div>
      <div className="passport-body">
        <div className="passport-readings">
          <div>
            <span>{t("State of Health")}</span>
            <strong className="mint">
              <CountUp value={soh} decimals={1} />
              <small>{t("%")}</small>
            </strong>
            <progress aria-label={t("电池健康度")} value={soh} max={100} />
          </div>
          <div>
            <span>{t("Remaining Useful Life")}</span>
            <strong className="cyan">
              <CountUp value={rul} />
              <small>{t(" cycles")}</small>
            </strong>
          </div>
          <div>
            <span>{t("Lifecycle Carbon")}</span>
            <strong>
              <CountUp
                value={calculateLifecycleCarbon(data.carbon)}
                decimals={2}
              />
              <small>{t(" tCO₂e")}</small>
            </strong>
          </div>
        </div>
        <figure>
          <img
            src="/assets/battery-pack.png"
            alt={t("石墨黑动力电池包概念渲染")}
            width="1024"
            height="1024"
          />
          <figcaption>{t("ONE IDENTITY.")}<br />{t("A LIFETIME OF INTELLIGENCE.")}</figcaption>
        </figure>
      </div>
      <dl className="passport-specs">
        <div>
          <dt>{t("Battery Type")}</dt>
          <dd>{t(data.batteryType)}</dd>
        </div>
        <div>
          <dt>{t("Capacity")}</dt>
          <dd>
            {t(data.initialCapacity)} <small>{t("kWh")}</small>
          </dd>
        </div>
        <div>
          <dt>{t("Mileage")}</dt>
          <dd>
            {t(data.mileage.toLocaleString("en-US"))} <small>{t("km")}</small>
          </dd>
        </div>
        <div>
          <dt>{t("Cycle Count")}</dt>
          <dd>{t(data.cycles.toLocaleString("en-US"))}</dd>
        </div>
      </dl>
      <div className="passport-bottom">
        <span>{t("数字身份 · 全程可溯")}</span>
        <span>{t("DEMO DATASET / 2026")}</span>
      </div>
    </section>
  );
}
