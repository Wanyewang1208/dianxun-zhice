import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import fixture from "../../../docs/examples/assessment.request.json?raw";
import manualFixture from "../../../docs/examples/manual_demo.request.json?raw";
import type { ManualRequest } from "../types/manual";
import type {
  AssessmentRequest,
  AssessmentResponse,
  Envelope,
  BMSValidationResponse,
} from "../types/api";
import type { ScenarioId } from "../types/battery";
import * as api from "../lib/api";
import {
  assessmentAdapter,
  normalizeAssessment,
} from "../lib/assessmentAdapter";
const sample = () => JSON.parse(fixture) as AssessmentRequest;
function useAssessmentState() {
  const [assessmentResult, setResult] =
    useState<Envelope<AssessmentResponse> | null>(null);
  const [assessmentStatus, setStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [backendStatus, setBackend] = useState<
    "checking" | "online" | "offline"
  >("checking");
  const [currentScenario, setScenario] = useState<ScenarioId>("used");
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<AssessmentRequest | ManualRequest>(
    sample,
  );
  const [validation, setValidation] = useState<BMSValidationResponse | null>(
    null,
  );
  const [validating, setValidating] = useState(false);
  const generation = useRef(0);
  const busy = useRef(false);
  const mounted = useRef(true);
  const checkBackend = async () => {
    try {
      await api.healthCheck();
      if (mounted.current) setBackend("online");
    } catch {
      if (mounted.current) setBackend("offline");
    }
  };
  useEffect(() => {
    mounted.current = true;
    void checkBackend();
    const timer = setInterval(checkBackend, 30000);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, []);
  const resetAssessment = () => {
    generation.current++;
    busy.current = false;
    setResult(null);
    setStatus("idle");
    setError(null);
    setValidation(null);
    setValidating(false);
  };
  const loadDemoAssessment = () => {
    resetAssessment();
    setRequest(sample());
  };
  const runAssessment = async () => {
    if (busy.current) return;
    busy.current = true;
    const id = ++generation.current;
    setStatus("loading");
    setError(null);
    try {
      const response = await api.runAssessment(request);
      const result = { ...response, data: normalizeAssessment(response.data) };
      assessmentAdapter(result.data);
      if (id !== generation.current) return;
      setResult(result);
      setStatus("success");
      setBackend("online");
      if (result.data.data_quality.status === "checked")
        setValidation(result.data.data_quality);
    } catch (e) {
      if (id !== generation.current) return;
      setError(
        e instanceof api.ApiError
          ? e.message
          : "评估返回不完整，请检查后端版本后重试。",
      );
      setStatus("error");
      if (e instanceof api.ApiError && e.kind === "offline")
        setBackend("offline");
    } finally {
      if (id === generation.current) busy.current = false;
    }
  };
  const validate = async () => {
    if (!request.bms || busy.current) return;
    busy.current = true;
    const id = ++generation.current;
    setValidating(true);
    setError(null);
    try {
      const r = await api.validateBMS(request.bms);
      if (id !== generation.current) return;
      if (
        r.data.status !== "checked" ||
        !r.data.summary ||
        !Array.isArray(r.data.issues)
      )
        throw new api.ApiError("incomplete", "数据检查返回不完整");
      setValidation(r.data);
      setBackend("online");
    } catch (e) {
      if (id === generation.current)
        setError(
          e instanceof api.ApiError
            ? e.message
            : "数据检查返回不完整，请重试。",
        );
    } finally {
      if (id === generation.current) {
        busy.current = false;
        setValidating(false);
      }
    }
  };
  return {
    assessmentResult,
    assessmentStatus,
    backendStatus,
    currentScenario,
    error,
    request,
    manualRequest: "input_mode" in request ? request : null,
    useManual: (demo = false) => {
      resetAssessment();
      setRequest(
        demo
          ? JSON.parse(manualFixture)
          : {
              input_mode: "manual",
              data_kind: "user_declared",
              manual_input: { rated_capacity_kwh: null },
            },
      );
    },
    setManualField: (key: string, value: string | number | boolean | null) => {
      resetAssessment();
      setRequest((r) =>
        "input_mode" in r
          ? { ...r, manual_input: { ...r.manual_input, [key]: value } }
          : r,
      );
    },
    validation,
    validating,
    dataSource: assessmentResult ? ("live" as const) : ("demo" as const),
    view: assessmentResult ? assessmentAdapter(assessmentResult.data) : null,
    runAssessment,
    resetAssessment,
    loadDemoAssessment,
    checkBackend,
    validate,
    setError,
    setScenario: (s: ScenarioId) => {
      if (!assessmentResult && !busy.current) setScenario(s);
    },
    setBMS: (key: "telemetry_csv" | "metadata_csv", value: string) => {
      resetAssessment();
      setRequest((r) => ({ ...r, bms: { ...r.bms!, [key]: value } }));
    },
    useTeamDataset: () => {
      loadDemoAssessment();
    },
  };
}
const Context = createContext<ReturnType<typeof useAssessmentState> | null>(
  null,
);
export function AssessmentProvider({ children }: { children: ReactNode }) {
  return (
    <Context.Provider value={useAssessmentState()}>{children}</Context.Provider>
  );
}
export function useAssessment() {
  const value = useContext(Context);
  if (!value) throw new Error("AssessmentProvider missing");
  return value;
}
