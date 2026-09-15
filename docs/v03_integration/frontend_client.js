// Drop into the teammate's existing frontend. No UI is created here.
// Use a backend proxy or start the local API with --allowed-origin <your origin>.
export async function fetchBatteryReport(request, baseUrl = 'http://127.0.0.1:8013') {
  const response = await fetch(`${baseUrl}/v0.3/report`, {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(request)
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || `HTTP ${response.status}`);
  // Render these separately: laboratory evidence is NOT the illustrative pack assessment.
  return {
    laboratory: body.model_evidence,
    simulation: body.scenario_decision,
    displayNotice: body.display_notice,
    canShowRecommendation: body.scenario_decision.recommended_route !== null,
    automaticModelToPackTransfer: body.automatic_model_to_pack_transfer
  };
}
