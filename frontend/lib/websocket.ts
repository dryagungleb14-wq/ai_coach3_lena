const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace("http://", "ws://").replace("https://", "wss://");

if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  console.log("WebSocket URL:", WS_URL);
}

export interface ProgressUpdate {
  call_id: number;
  progress: number;
  status: string;
  message?: string;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private callId: number;
  private onProgress: (update: ProgressUpdate) => void;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(callId: number, onProgress: (update: ProgressUpdate) => void) {
    this.callId = callId;
    this.onProgress = onProgress;
  }

  connect(): void {
    try {
      const wsUrl = `${WS_URL}/ws/analyze/${this.callId}`;
      console.log(`Попытка подключения WebSocket: ${wsUrl}`);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log(`WebSocket подключен для звонка ${this.callId} по адресу ${wsUrl}`);
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data: ProgressUpdate = JSON.parse(event.data);
          this.onProgress(data);
        } catch (error) {
          console.error("Ошибка парсинга WebSocket сообщения:", {
            error,
            rawData: event.data,
            callId: this.callId
          });
        }
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket ошибка:", {
          error,
          url: wsUrl,
          callId: this.callId,
          readyState: this.ws?.readyState
        });
      };

      this.ws.onclose = (event) => {
        console.log(`WebSocket отключен для звонка ${this.callId}`, {
          code: event.code,
          reason: event.reason,
          wasClean: event.wasClean,
          url: wsUrl
        });
        this.ws = null;
        if (!event.wasClean) {
          this.attemptReconnect();
        }
      };
    } catch (error) {
      console.error("Ошибка создания WebSocket соединения:", {
        error,
        url: `${WS_URL}/ws/analyze/${this.callId}`,
        callId: this.callId,
        wsUrl: WS_URL
      });
      this.attemptReconnect();
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * this.reconnectAttempts;
      console.log(`Попытка переподключения ${this.reconnectAttempts}/${this.maxReconnectAttempts} через ${delay}мс для звонка ${this.callId}`);
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error("Достигнуто максимальное количество попыток переподключения", {
        callId: this.callId,
        url: `${WS_URL}/ws/analyze/${this.callId}`
      });
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

