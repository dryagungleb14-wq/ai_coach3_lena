const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  console.log("API URL:", API_URL);
}

export interface Call {
  id: number;
  filename: string;
  manager?: string;
  call_date?: string;
  call_identifier?: string;
  duration?: number;
  created_at: string;
  requires_review?: boolean;
  evaluation?: {
    итоговая_оценка?: number;
    max_score?: number;
    score_percent?: number;
    нарушения?: boolean;
  };
}

export interface CallDetail extends Call {
  transcription?: string;
  duration?: number;
  evaluations?: Evaluation[];
  requires_review?: boolean;
}

export interface Evaluation {
  id: number;
  scores: Record<string, any>;
  итоговая_оценка: number;
  max_score?: number;
  score_percent?: number;
  нарушения: boolean;
  комментарии: string;
  is_retest: boolean;
  created_at: string;
}

export async function checkBackendHealth(): Promise<{ status: boolean; message: string; url: string }> {
  try {
    const response = await fetch(`${API_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    });
    
    if (response.ok) {
      return { status: true, message: "Бэкенд доступен", url: API_URL };
    } else {
      return { 
        status: false, 
        message: `Бэкенд вернул ошибку: ${response.status}`, 
        url: API_URL 
      };
    }
  } catch (error: any) {
    const errorMessage = error.name === "AbortError" 
      ? "Таймаут подключения к бэкенду"
      : error.message?.includes("Failed to fetch")
      ? "Не удалось подключиться к бэкенду"
      : error.message || "Неизвестная ошибка";
    
    console.error("Backend health check failed:", {
      error: errorMessage,
      url: API_URL,
      errorDetails: error
    });
    
    return { 
      status: false, 
      message: `${errorMessage}. URL: ${API_URL}`, 
      url: API_URL 
    };
  }
}

export async function uploadFiles(
  files: File[],
  manager?: string,
  callDate?: string,
  callIdentifier?: string
): Promise<Call[]> {
  const formData = new FormData();
  
  files.forEach((file) => {
    formData.append("files", file);
  });
  
  if (manager) formData.append("manager", manager);
  if (callDate) formData.append("call_date", callDate);
  if (callIdentifier) formData.append("call_identifier", callIdentifier);
  
  try {
    const response = await fetch(`${API_URL}/api/upload`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = "Ошибка загрузки файлов";
      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }
      throw new Error(errorMessage);
    }
    
    const data = await response.json();
    return data.calls;
  } catch (error: any) {
    console.error("Upload error:", {
      error: error.message,
      url: `${API_URL}/api/upload`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function analyzeCall(callId: number): Promise<any> {
  try {
    const response = await fetch(`${API_URL}/api/analyze/${callId}`, {
      method: "POST",
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
    }
    
    return response.json();
  } catch (error: any) {
    console.error("Analyze error:", {
      error: error.message,
      url: `${API_URL}/api/analyze/${callId}`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function getAnalyzeStatus(callId: number): Promise<{status: string, progress: number}> {
  try {
    const response = await fetch(`${API_URL}/api/analyze/${callId}/status`);
    
    if (!response.ok) {
      throw new Error(`Failed to get status: ${response.status}`);
    }
    
    return response.json();
  } catch (error: any) {
    console.error("Get status error:", {
      error: error.message,
      url: `${API_URL}/api/analyze/${callId}/status`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function retestCall(callId: number): Promise<any> {
  try {
    const response = await fetch(`${API_URL}/api/analyze/${callId}/retest`, {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error("Retest failed");
    }
    
    return response.json();
  } catch (error: any) {
    console.error("Retest error:", {
      error: error.message,
      url: `${API_URL}/api/analyze/${callId}/retest`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export interface CallsResponse {
  calls: Call[];
  total: number;
}

export async function getCalls(options?: {
  manager?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}): Promise<CallsResponse> {
  try {
    const params = new URLSearchParams();
    if (options?.manager) params.append("manager", options.manager);
    if (options?.startDate) params.append("start_date", options.startDate);
    if (options?.endDate) params.append("end_date", options.endDate);
    if (options?.limit !== undefined) params.append("limit", String(options.limit));
    if (options?.offset !== undefined) params.append("offset", String(options.offset));

    const response = await fetch(`${API_URL}/api/calls?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch calls: ${response.status}`);
    }

    const data = await response.json();
    return { calls: data.calls, total: data.total ?? data.calls.length };
  } catch (error: any) {
    console.error("Error fetching calls:", {
      error: error.message,
      url: `${API_URL}/api/calls`,
      errorDetails: error
    });

    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function getCall(callId: number): Promise<CallDetail> {
  try {
    const response = await fetch(`${API_URL}/api/calls/${callId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch call: ${response.status}`);
    }
    
    return response.json();
  } catch (error: any) {
    console.error("Error fetching call:", {
      error: error.message,
      url: `${API_URL}/api/calls/${callId}`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function exportCall(callId: number): Promise<Blob> {
  try {
    const response = await fetch(`${API_URL}/api/export/${callId}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Export failed: ${response.status} - ${errorText}`);
    }
    
    return response.blob();
  } catch (error: any) {
    console.error("Error exporting call:", {
      error: error.message,
      url: `${API_URL}/api/export/${callId}`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export async function exportCalls(
  manager?: string,
  startDate?: string,
  endDate?: string
): Promise<Blob> {
  try {
    const params = new URLSearchParams();
    if (manager) params.append("manager", manager);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    
    const response = await fetch(`${API_URL}/api/export?${params.toString()}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Export failed: ${response.status} - ${errorText}`);
    }
    
    return response.blob();
  } catch (error: any) {
    console.error("Error exporting calls:", {
      error: error.message,
      url: `${API_URL}/api/export`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export interface Stats {
  total_calls: number;
  avg_score: number;
  avg_percent: number;
  avg_duration: number;
  managers_stats: Array<{
    manager: string;
    total_calls: number;
    avg_score: number;
    avg_percent: number;
  }>;
  parameter_stats: Record<string, {
    total: number;
    max: number;
    mid: number;
    min: number;
    na: number;
    avg_score: number;
  }>;
  time_series: Array<{
    date: string;
    score: number;
    percent: number;
  }>;
}

export async function getStats(
  manager?: string,
  startDate?: string,
  endDate?: string
): Promise<Stats> {
  try {
    const params = new URLSearchParams();
    if (manager) params.append("manager", manager);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    
    const response = await fetch(`${API_URL}/api/stats?${params.toString()}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch stats: ${response.status}`);
    }
    
    return response.json();
  } catch (error: any) {
    console.error("Error fetching stats:", {
      error: error.message,
      url: `${API_URL}/api/stats`,
      errorDetails: error
    });
    
    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export interface ChecklistCriterion {
  key: string;
  description: string;
  max: { score: number; criterion: string };
  mid: { score: number; criterion: string };
  min: { score: number; criterion: string };
}

export interface ChecklistStage {
  name: string;
  criteria: ChecklistCriterion[];
}

export interface ChecklistData {
  stages: ChecklistStage[];
  rules: string[];
  special_circumstances: Record<string, string>;
}

export async function getChecklist(): Promise<ChecklistData> {
  try {
    const response = await fetch(`${API_URL}/api/checklist`);

    if (!response.ok) {
      throw new Error(`Failed to fetch checklist: ${response.status}`);
    }

    return response.json();
  } catch (error: any) {
    console.error("Error fetching checklist:", {
      error: error.message,
      url: `${API_URL}/api/checklist`,
      errorDetails: error
    });

    if (error.message?.includes("Failed to fetch") || error.name === "TypeError") {
      throw new Error(`Не удалось подключиться к серверу по адресу ${API_URL}. Убедитесь, что бэкенд запущен и доступен.`);
    }
    throw error;
  }
}

export interface TelphinSyncEntry {
  id: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  calls_found: number;
  calls_imported: number;
  calls_skipped: number;
  error_message: string | null;
  filter_min_duration?: number;
}

export interface TelphinStatus {
  configured: boolean;
  default_min_duration: number;
  last_sync: TelphinSyncEntry | null;
}

export async function getTelphinStatus(): Promise<TelphinStatus> {
  const response = await fetch(`${API_URL}/api/telphin/status`);
  if (!response.ok) throw new Error(`Failed: ${response.status}`);
  return response.json();
}

export async function getTelphinHistory(): Promise<{ syncs: TelphinSyncEntry[] }> {
  const response = await fetch(`${API_URL}/api/telphin/history`);
  if (!response.ok) throw new Error(`Failed: ${response.status}`);
  return response.json();
}

export async function startTelphinSync(options?: {
  startDate?: string;
  endDate?: string;
  minDuration?: number;
}): Promise<{ status: string; message: string }> {
  const formData = new FormData();
  if (options?.startDate) formData.append("start_date", options.startDate);
  if (options?.endDate) formData.append("end_date", options.endDate);
  if (options?.minDuration !== undefined) formData.append("min_duration", String(options.minDuration));

  const response = await fetch(`${API_URL}/api/telphin/sync`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Failed: ${response.status}`);
  }
  return response.json();
}

export async function cancelTelphinSync(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_URL}/api/telphin/sync/cancel`, {
    method: "POST",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Failed: ${response.status}`);
  }
  return response.json();
}

export interface TelphinExtensionItem {
  id: number;
  extension_id: string;
  extension_name: string;
  extension_type: string;
  manager_name: string;
  is_monitored: boolean;
}

export async function getTelphinExtensions(): Promise<{ extensions: TelphinExtensionItem[] }> {
  const response = await fetch(`${API_URL}/api/telphin/extensions`);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Failed: ${response.status}`);
  }
  return response.json();
}

export async function updateTelphinExtension(
  id: number,
  data: { manager_name?: string; is_monitored?: boolean }
): Promise<TelphinExtensionItem> {
  const params = new URLSearchParams();
  if (data.manager_name !== undefined) params.set("manager_name", data.manager_name);
  if (data.is_monitored !== undefined) params.set("is_monitored", String(data.is_monitored));
  const qs = params.toString();
  const url = `${API_URL}/api/telphin/extensions/${id}${qs ? `?${qs}` : ""}`;
  const response = await fetch(url, { method: "PUT" });
  if (!response.ok) {
    const res = await response.json().catch(() => ({}));
    throw new Error(res.detail || `Failed: ${response.status}`);
  }
  return response.json();
}
