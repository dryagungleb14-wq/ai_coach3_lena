"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getCall, analyzeCall, retestCall, CallDetail, exportCall } from "@/lib/api";
import { WebSocketClient } from "@/lib/websocket";
import EvaluationTable from "@/components/EvaluationTable";

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const callId = parseInt(params.id as string);
  
  const [call, setCall] = useState<CallDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);

  useEffect(() => {
    loadCall();
    
    return () => {
      if (wsClient) {
        wsClient.disconnect();
      }
    };
  }, [callId]);

  useEffect(() => {
    if (analyzing && !wsClient) {
      const client = new WebSocketClient(callId, (update) => {
        setProgress(update.progress);
        if (update.message) {
          setStatusMessage(update.message);
        }
        
        if (update.status === "completed") {
          setAnalyzing(false);
          client.disconnect();
          setWsClient(null);
          loadCall();
        } else if (update.status === "failed") {
          setAnalyzing(false);
          client.disconnect();
          setWsClient(null);
          const errorMessage = update.message || "Ошибка при анализе. Попробуйте еще раз.";
          alert(errorMessage);
          loadCall();
        }
      });
      
      client.connect();
      setWsClient(client);
    }
    
    return () => {
      if (wsClient && !analyzing) {
        wsClient.disconnect();
        setWsClient(null);
      }
    };
  }, [analyzing, callId]);

  const loadCall = async () => {
    try {
      const data = await getCall(callId);
      setCall(data);
    } catch (error: any) {
      console.error("Error loading call:", error);
      const errorMessage = error?.message || "Ошибка загрузки звонка";
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setProgress(0);
    try {
      await analyzeCall(callId);
    } catch (error: any) {
      console.error("Error analyzing:", error);
      const errorMessage = error?.message || "Ошибка анализа";
      alert(`Ошибка анализа: ${errorMessage}`);
      setAnalyzing(false);
    }
  };

  const handleRetest = async () => {
    setAnalyzing(true);
    try {
      await retestCall(callId);
      await loadCall();
    } catch (error: any) {
      console.error("Error retesting:", error);
      const errorMessage = error?.message || "Ошибка повторной проверки";
      alert(`Ошибка повторной проверки: ${errorMessage}`);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return <div className="p-6">Загрузка...</div>;
  }

  if (!call) {
    return <div className="p-6">Звонок не найден</div>;
  }

  const latestEvaluation = call.evaluations?.[0];

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      <div className="mb-4">
        <button
          onClick={() => router.push("/")}
          className="text-blue-600 hover:underline"
        >
          ← Назад
        </button>
      </div>

      <h1 className="text-2xl font-semibold mb-4">{call.filename}</h1>
      
      <div className="mb-4 space-y-2">
        {call.manager && <p><strong>Менеджер:</strong> {call.manager}</p>}
        {call.call_date && <p><strong>Дата звонка:</strong> {new Date(call.call_date).toLocaleDateString()}</p>}
        {call.call_identifier && <p><strong>ID звонка:</strong> {call.call_identifier}</p>}
      </div>

      <div className="mb-6">
        {!call.transcription ? (
          <div>
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="px-4 py-2 bg-black text-white rounded disabled:bg-gray-400 mb-4"
            >
              {analyzing ? "Анализ..." : "Запустить анализ"}
            </button>
            
            {analyzing && (
              <div className="mt-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-sm text-gray-600">{statusMessage || "Прогресс анализа"}</span>
                  <span className="text-sm text-gray-600">{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                {wsClient && !wsClient.isConnected() && (
                  <p className="text-xs text-yellow-600 mt-1">Переподключение...</p>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={handleRetest}
              disabled={analyzing}
              className="px-4 py-2 bg-gray-600 text-white rounded disabled:bg-gray-400"
            >
              {analyzing ? "Проверка..." : "Повторная проверка"}
            </button>
            {latestEvaluation && (
              <button
                onClick={async () => {
                  try {
                    const blob = await exportCall(callId);
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `call_${callId}_export_${new Date().toISOString().split("T")[0]}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                  } catch (error: any) {
                    console.error("Error exporting:", error);
                    alert(`Ошибка экспорта: ${error?.message || "Неизвестная ошибка"}`);
                  }
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                📥 Экспорт в CSV
              </button>
            )}
          </div>
        )}
      </div>

      {call.transcription && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-2">Расшифровка</h2>
          <div className="bg-gray-50 p-4 rounded border border-gray-200">
            <p className="whitespace-pre-wrap">{call.transcription}</p>
          </div>
        </div>
      )}

      {latestEvaluation && (
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-2">Оценка</h2>
          <EvaluationTable evaluation={latestEvaluation} />
        </div>
      )}

      {call.evaluations && call.evaluations.length > 1 && (
        <div className="mt-6">
          <h2 className="text-xl font-semibold mb-2">История оценок</h2>
          {call.evaluations.slice(1).map((evaluation) => (
            <div key={evaluation.id} className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                {new Date(evaluation.created_at).toLocaleString()} {evaluation.is_retest && "(Повторная проверка)"}
              </p>
              <EvaluationTable evaluation={evaluation} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

