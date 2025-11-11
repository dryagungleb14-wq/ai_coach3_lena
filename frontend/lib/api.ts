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
  created_at: string;
  evaluation?: {
    итоговая_оценка?: number;
    нарушения?: boolean;
  };
}

export interface CallDetail extends Call {
  transcription?: string;
  duration?: number;
  evaluations?: Evaluation[];
}

export interface Evaluation {
  id: number;
  scores: Record<string, any>;
  итоговая_оценка: number;
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

export async function getCalls(
  manager?: string,
  startDate?: string,
  endDate?: string
): Promise<Call[]> {
  try {
    const params = new URLSearchParams();
    if (manager) params.append("manager", manager);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);
    
    const response = await fetch(`${API_URL}/api/calls?${params.toString()}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch calls: ${response.status}`);
    }
    
    const data = await response.json();
    return data.calls;
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

