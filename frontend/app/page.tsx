"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import AudioUpload from "@/components/AudioUpload";
import { getCalls, Call, exportCalls, checkBackendHealth } from "@/lib/api";
import { WebSocketClient } from "@/lib/websocket";

interface AnalysisProgress {
  callId: number;
  progress: number;
  status: string;
  message?: string;
}

export default function Home() {
  const router = useRouter();
  const [recentCalls, setRecentCalls] = useState<Call[]>([]);
  const [backendStatus, setBackendStatus] = useState<{ status: boolean; message: string; url: string } | null>(null);
  const [isCheckingBackend, setIsCheckingBackend] = useState(true);
  const [analyzingCalls, setAnalyzingCalls] = useState<Map<number, AnalysisProgress>>(new Map());
  const wsClientsRef = useRef<Map<number, WebSocketClient>>(new Map());

  useEffect(() => {
    checkBackend();
    loadRecentCalls();
    
    return () => {
      wsClientsRef.current.forEach(client => client.disconnect());
      wsClientsRef.current.clear();
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      loadRecentCalls();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    setIsCheckingBackend(true);
    const health = await checkBackendHealth();
    setBackendStatus(health);
    setIsCheckingBackend(false);
  };

  const loadRecentCalls = async () => {
    try {
      const data = await getCalls();
      setRecentCalls(data.slice(0, 5));
    } catch (error: any) {
      console.error("Error loading calls:", error);
    }
  };

  const handleUploadComplete = () => {
    loadRecentCalls();
  };

  const handleAnalysisStarted = (callIds: number[]) => {
    callIds.forEach(callId => {
      const client = new WebSocketClient(callId, (update) => {
        setAnalyzingCalls(prev => {
          const newMap = new Map(prev);
          newMap.set(callId, {
            callId,
            progress: update.progress,
            status: update.status,
            message: update.message
          });
          return newMap;
        });
        
        if (update.status === "completed" || update.status === "failed") {
          if (update.status === "failed" && update.message) {
            alert(update.message);
          }
          client.disconnect();
          wsClientsRef.current.delete(callId);
          setAnalyzingCalls(prev => {
            const newMap = new Map(prev);
            newMap.delete(callId);
            return newMap;
          });
          loadRecentCalls();
        }
      });
      
      client.connect();
      wsClientsRef.current.set(callId, client);
      
      setAnalyzingCalls(prev => {
        const newMap = new Map(prev);
        newMap.set(callId, {
          callId,
          progress: 0,
          status: "processing",
          message: "Начало анализа..."
        });
        return newMap;
      });
    });
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="w-full max-w-6xl mx-auto p-6">
        <h1 className="text-3xl font-semibold mb-6">AI Coach - Анализ звонков</h1>

        {isCheckingBackend ? (
          <div className="mb-4 p-4 bg-gray-100 rounded">
            <p className="text-gray-600">Проверка подключения к бэкенду...</p>
          </div>
        ) : backendStatus && !backendStatus.status ? (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-red-800 font-semibold mb-2">⚠️ Проблема с подключением к бэкенду</p>
            <p className="text-red-700 text-sm mb-2">{backendStatus.message}</p>
            <button
              onClick={checkBackend}
              className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
            >
              Проверить снова
            </button>
          </div>
        ) : backendStatus && backendStatus.status ? (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded">
            <p className="text-green-800 text-sm">✅ Бэкенд доступен: {backendStatus.url}</p>
          </div>
        ) : null}

        <div className="mb-8">
          <AudioUpload onUploadComplete={handleUploadComplete} onAnalysisStarted={handleAnalysisStarted} />
        </div>

        {analyzingCalls.size > 0 && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Анализ в процессе</h2>
            <div className="space-y-3">
              {Array.from(analyzingCalls.values()).map((progress) => {
                const call = recentCalls.find(c => c.id === progress.callId);
                return (
                  <div key={progress.callId} className="p-4 border border-gray-200 rounded">
                    <div className="flex justify-between items-center mb-2">
                      <p className="font-medium">{call?.filename || `Звонок #${progress.callId}`}</p>
                      <span className="text-sm text-gray-600">{progress.progress}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                      <div
                        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress.progress}%` }}
                      ></div>
                    </div>
                    {progress.message && (
                      <p className={`text-sm ${progress.status === "failed" ? "text-red-600 font-semibold" : "text-gray-600"}`}>
                        {progress.message}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="mb-4 flex gap-4">
          <button
            onClick={() => router.push("/history")}
            className="px-4 py-2 bg-gray-600 text-white rounded"
          >
            История звонков
          </button>
          <button
            onClick={async () => {
              try {
                const blob = await exportCalls();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `calls_export_${new Date().toISOString().split("T")[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
              } catch (error: any) {
                console.error("Error exporting:", error);
                alert(`Ошибка экспорта: ${error?.message || "Неизвестная ошибка"}`);
              }
            }}
            className="px-4 py-2 bg-gray-600 text-white rounded"
          >
            📥 Экспорт в CSV
          </button>
        </div>

        {recentCalls.length > 0 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Последние звонки</h2>
            <div className="space-y-2">
              {recentCalls.map((call) => (
                <div
                  key={call.id}
                  className="p-4 border border-gray-200 rounded cursor-pointer hover:bg-gray-50"
                  onClick={() => router.push(`/calls/${call.id}`)}
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium">{call.filename}</p>
                      <p className="text-sm text-gray-600">
                        {call.manager && `Менеджер: ${call.manager} • `}
                        {call.call_date && new Date(call.call_date).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="text-right">
                      {call.evaluation?.итоговая_оценка !== undefined && (
                        <p className="font-semibold">
                          {call.evaluation.итоговая_оценка} баллов
                        </p>
                      )}
                      {call.evaluation?.нарушения && (
                        <p className="text-sm text-red-600">Нарушения</p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
