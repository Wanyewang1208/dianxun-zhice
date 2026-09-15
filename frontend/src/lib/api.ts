import type {
  Envelope,
  HealthResponse,
  BMSRequest,
  BMSValidationResponse,
  ModelCase,
  SOHResult,
  RULResult,
  ExplainabilityResult,
  AssessmentRequest,
  AssessmentResponse,
} from "../types/api";
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8013";
export class ApiError extends Error {
  constructor(
    public kind: "offline" | "timeout" | "invalid" | "failed" | "incomplete",
    message: string,
  ) {
    super(message);
  }
}
export async function request<T>(
  path: string,
  body?: unknown,
  timeout = 120000,
): Promise<Envelope<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    let payload: Envelope<T>;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError("incomplete", "返回数据格式异常，请检查后端版本。");
    }
    if (!payload || typeof payload !== 'object')
      throw new ApiError('incomplete', '后端返回不完整，未替换当前结果。');
    if (!response.ok || !payload.success)
      throw new ApiError(
        response.status === 400 ? "invalid" : "failed",
        response.status === 400
          ? "输入数据未通过检查，请核对 CSV 与元数据。"
          : "本次评估未能完成，请检查后端服务后重试。",
      );
    if (
      payload.success !== true ||
      payload.schema_version !== "1.0" ||
      !payload.data ||
      !Array.isArray(payload.warnings) ||
      payload.warnings.some(w => typeof w !== "string") ||
      typeof payload.request_id !== "string"
    )
      throw new ApiError("incomplete", "后端返回不完整，未替换当前结果。");
    return payload;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      controller.signal.aborted ? "timeout" : "offline",
      controller.signal.aborted
        ? "评估请求超时，请稍后重试。"
        : "Backend unavailable · 无法连接后端，可继续使用本地演示。",
    );
  } finally {
    clearTimeout(timer);
  }
}
export async function healthCheck() {
  const r = await request<HealthResponse>("health", undefined, 8000);
  if (r.data.status !== "ok" || typeof r.data.models_ready !== "boolean")
    throw new ApiError("incomplete", "健康检查返回异常");
  return r;
}
export const validateBMS = (body: BMSRequest) =>
  request<BMSValidationResponse>("bms/validate", body);
export const runAssessment = (body: AssessmentRequest) =>
  request<AssessmentResponse>("assessment", body);
export const getSOH = (body: ModelCase) => request<SOHResult>("soh", body);
export const getRUL = (body: ModelCase) => request<RULResult>("rul", body);
export const getExplainability = (body: ModelCase) =>
  request<ExplainabilityResult>("explain", body);
