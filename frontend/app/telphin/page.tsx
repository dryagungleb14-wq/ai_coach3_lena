"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  getTelphinStatus,
  getTelphinHistory,
  startTelphinSync,
  TelphinStatus,
  TelphinSyncEntry,
} from "@/lib/api";

export default function TelphinPage() {
  const router = useRouter();
  const [status, setStatus] = useState<TelphinStatus | null>(null);
  const [history, setHistory] = useState<TelphinSyncEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [minDuration, setMinDuration] = useState<number | "">("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [s, h] = await Promise.all([getTelphinStatus(), getTelphinHistory()]);
      setStatus(s);
      setHistory(h.syncs);
      if (minDuration === "" && s.default_min_duration) {
        setMinDuration(s.default_min_duration);
      }
    } catch (e: any) {
      setError(e.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setError("");
    try {
      await startTelphinSync({
        startDate: startDate || undefined,
        endDate: endDate || undefined,
        minDuration: minDuration !== "" ? minDuration : undefined,
      });
      setTimeout(loadData, 2000);
      setTimeout(loadData, 8000);
      setTimeout(loadData, 20000);
    } catch (e: any) {
      setError(e.message || "Ошибка синхронизации");
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    const hasRunning = history.some((s) => s.status === "running");
    if (!hasRunning) return;

    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [history]);

  if (loading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <p className="text-gray-600">Загрузка...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      <div className="mb-4">
        <button onClick={() => router.push("/")} className="text-blue-600 hover:underline">
          ← Назад
        </button>
      </div>

      <h1 className="text-2xl font-semibold mb-6">Telphin — импорт звонков</h1>

      {!status?.configured && (
        <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-yellow-800 font-semibold mb-1">Telphin API не настроен</p>
          <p className="text-yellow-700 text-sm">
            Добавьте TELPHIN_APP_ID и TELPHIN_APP_SECRET в переменные окружения бэкенда.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      <div className="mb-8 p-5 border border-gray-200 rounded">
        <h2 className="text-lg font-semibold mb-4">Запустить синхронизацию</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Дата начала</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Дата окончания</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Мин. длительность (сек)</label>
            <input
              type="number"
              value={minDuration}
              onChange={(e) => setMinDuration(e.target.value ? parseInt(e.target.value) : "")}
              placeholder="120"
              className="w-full px-3 py-2 border border-gray-300 rounded"
            />
          </div>
        </div>

        <p className="text-xs text-gray-500 mb-4">
          Без дат — за последние сутки. Без длительности — по умолчанию {status?.default_min_duration || 120} сек.
          Загруженные звонки автоматически проходят транскрибацию и оценку.
        </p>

        <button
          onClick={handleSync}
          disabled={syncing || !status?.configured}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-40"
        >
          {syncing ? "Запуск..." : "Синхронизировать"}
        </button>
      </div>

      {status?.last_sync && (
        <div className="mb-8 p-5 bg-gray-50 border border-gray-200 rounded">
          <h2 className="text-lg font-semibold mb-2">Последняя синхронизация</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Статус</p>
              <p className={`font-semibold ${
                status.last_sync.status === "completed" ? "text-green-600" :
                status.last_sync.status === "failed" ? "text-red-600" :
                "text-yellow-600"
              }`}>
                {status.last_sync.status === "completed" ? "Завершена" :
                 status.last_sync.status === "failed" ? "Ошибка" :
                 "Выполняется..."}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Найдено</p>
              <p className="font-semibold">{status.last_sync.calls_found}</p>
            </div>
            <div>
              <p className="text-gray-500">Импортировано</p>
              <p className="font-semibold">{status.last_sync.calls_imported}</p>
            </div>
            <div>
              <p className="text-gray-500">Пропущено</p>
              <p className="font-semibold">{status.last_sync.calls_skipped}</p>
            </div>
          </div>
          {status.last_sync.error_message && (
            <p className="mt-2 text-sm text-red-600">{status.last_sync.error_message}</p>
          )}
          {status.last_sync.started_at && (
            <p className="mt-2 text-xs text-gray-400">
              {new Date(status.last_sync.started_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">История синхронизаций</h2>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse border border-gray-300 text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-3 py-2 text-left">Дата</th>
                  <th className="border border-gray-300 px-3 py-2 text-center">Статус</th>
                  <th className="border border-gray-300 px-3 py-2 text-center">Найдено</th>
                  <th className="border border-gray-300 px-3 py-2 text-center">Импорт</th>
                  <th className="border border-gray-300 px-3 py-2 text-center">Пропущено</th>
                  <th className="border border-gray-300 px-3 py-2 text-left">Ошибка</th>
                </tr>
              </thead>
              <tbody>
                {history.map((s) => (
                  <tr key={s.id}>
                    <td className="border border-gray-300 px-3 py-2">
                      {s.started_at ? new Date(s.started_at).toLocaleString() : "—"}
                    </td>
                    <td className={`border border-gray-300 px-3 py-2 text-center font-medium ${
                      s.status === "completed" ? "text-green-600" :
                      s.status === "failed" ? "text-red-600" :
                      "text-yellow-600"
                    }`}>
                      {s.status === "completed" ? "OK" : s.status === "failed" ? "Ошибка" : "..."}
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-center">{s.calls_found}</td>
                    <td className="border border-gray-300 px-3 py-2 text-center">{s.calls_imported}</td>
                    <td className="border border-gray-300 px-3 py-2 text-center">{s.calls_skipped}</td>
                    <td className="border border-gray-300 px-3 py-2 text-red-600 text-xs">
                      {s.error_message || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
