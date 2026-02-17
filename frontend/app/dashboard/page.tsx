"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStats, Stats } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    loadStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await getStats(
        undefined,
        startDate || undefined,
        endDate || undefined
      );
      setStats(data);
    } catch (error) {
      console.error("Error loading stats:", error);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

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

      <h1 className="text-2xl font-semibold mb-6">Дашборд</h1>

      <div className="mb-6 flex items-end gap-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">От</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded"
          />
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">До</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded"
          />
        </div>
        <button
          onClick={loadStats}
          className="px-4 py-2 bg-black text-white rounded"
        >
          Применить
        </button>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : stats ? (
        <div className="space-y-8">
          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-5 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Оценено звонков</div>
              <div className="text-3xl font-bold mt-1">{stats.total_calls}</div>
            </div>
            <div className="bg-gray-50 p-5 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Средний % по чек-листу</div>
              <div className="text-3xl font-bold mt-1">
                {stats.avg_percent > 0 ? `${stats.avg_percent}%` : "—"}
              </div>
            </div>
            <div className={`p-5 rounded border ${stats.requires_review_count > 0 ? "bg-red-50 border-red-200" : "bg-gray-50 border-gray-200"}`}>
              <div className="text-sm text-gray-600">Требуют проверки</div>
              <div className={`text-3xl font-bold mt-1 ${stats.requires_review_count > 0 ? "text-red-700" : ""}`}>
                {stats.requires_review_count}
              </div>
            </div>
          </div>

          {/* Managers table */}
          {stats.managers_stats.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Менеджеры</h2>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-gray-300">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="border border-gray-300 px-4 py-2 text-left">Менеджер</th>
                      <th className="border border-gray-300 px-4 py-2 text-center">Звонков</th>
                      <th className="border border-gray-300 px-4 py-2 text-center">Средний %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.managers_stats.map((m) => (
                      <tr
                        key={m.manager}
                        className="hover:bg-gray-50 cursor-pointer"
                        onClick={() => router.push(`/history?manager=${encodeURIComponent(m.manager)}`)}
                      >
                        <td className="border border-gray-300 px-4 py-2">{m.manager}</td>
                        <td className="border border-gray-300 px-4 py-2 text-center">{m.total_calls}</td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          {m.avg_percent > 0 ? `${m.avg_percent}%` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Requires review */}
          {stats.requires_review_calls.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-3">Требуют проверки</h2>
              <div className="space-y-2">
                {stats.requires_review_calls.map((call) => (
                  <div
                    key={call.id}
                    className="p-4 border border-gray-200 rounded cursor-pointer hover:bg-gray-50"
                    onClick={() => router.push(`/calls/${call.id}`)}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{call.filename}</p>
                        <p className="text-sm text-gray-600">
                          {call.manager && `${call.manager} · `}
                          {call.call_date && new Date(call.call_date).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="text-right">
                        {call.score_percent != null ? (
                          <p className="font-semibold">{call.score_percent}%</p>
                        ) : call.special_note ? (
                          <p className="text-sm text-gray-500 italic">{call.special_note}</p>
                        ) : (
                          <p className="text-sm text-gray-400">—</p>
                        )}
                      </div>
                    </div>
                    {call.score_percent != null && call.special_note && (
                      <p className="text-xs text-gray-500 mt-1 italic">* {call.special_note}</p>
                    )}
                  </div>
                ))}
              </div>
              {stats.requires_review_count > 5 && (
                <button
                  onClick={() => router.push("/history?requires_review=true")}
                  className="mt-3 text-blue-600 hover:underline text-sm"
                >
                  Смотреть все {stats.requires_review_count} →
                </button>
              )}
            </div>
          )}

          {stats.total_calls === 0 && (
            <div className="text-center py-8 text-gray-500">
              Нет оценённых звонков за выбранный период
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">Ошибка загрузки данных</div>
      )}
    </div>
  );
}
