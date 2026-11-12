// Mirrors backend/app/schemas/health.py
export interface HealthResponse {
  status: "ok";
  app: string;
  version: string;
  environment: string;
  agent_provider: string;
}
