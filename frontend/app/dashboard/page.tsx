"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getStats, Stats } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [manager, setManager] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await getStats(
        manager || undefined,
        startDate || undefined,
        endDate || undefined
      );
      setStats(data);
    } catch (error) {
      console.error("Error loading stats:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = () => {
    loadStats();
  };

  const formatDuration = (seconds: number) => {
    if (!seconds) return "—";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const parameterNames: Record<string, string> = {
    "1": "Приветствие",
    "2": "Первичная квалификация",
    "3.1": "Вопросы вторичной квалификации",
    "3.2": "Вопрос о цели обучения",
    "3.3": "Резюмирование потребности",
    "4.1": "Презентация обучения",
    "4.2": "Презентация формата",
    "4.3": "Презентация стоимости",
    "4.4": "Информация для пробного",
    "5": "Уточнить сомнение",
    "6": "Завершение сделки",
    "7.1": "Грамотность и формулировки",
    "7.2": "Инициатива за ведение диалога"
  };

  return (
    <div className="w-full max-w-7xl mx-auto p-6">
      <div className="mb-4">
        <button
          onClick={() => router.push("/")}
          className="text-blue-600 hover:underline"
        >
          ← Назад
        </button>
      </div>

      <h1 className="text-2xl font-semibold mb-6">Дашборд статистики</h1>

      <div className="mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <input
            type="text"
            value={manager}
            onChange={(e) => setManager(e.target.value)}
            placeholder="Менеджер"
            className="px-3 py-2 border border-gray-300 rounded"
          />
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            placeholder="Дата начала"
            className="px-3 py-2 border border-gray-300 rounded"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            placeholder="Дата окончания"
            className="px-3 py-2 border border-gray-300 rounded"
          />
        </div>
        <button
          onClick={handleFilter}
          className="px-4 py-2 bg-black text-white rounded"
        >
          Применить фильтр
        </button>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : stats ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 p-4 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Всего звонков</div>
              <div className="text-2xl font-bold">{stats.total_calls}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Средний балл</div>
              <div className="text-2xl font-bold">{stats.avg_score.toFixed(2)}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Средний процент</div>
              <div className="text-2xl font-bold">{stats.avg_percent.toFixed(1)}%</div>
            </div>
            <div className="bg-gray-50 p-4 rounded border border-gray-200">
              <div className="text-sm text-gray-600">Средняя длительность</div>
              <div className="text-2xl font-bold">{formatDuration(stats.avg_duration)}</div>
            </div>
          </div>

          {stats.managers_stats.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Статистика по менеджерам</h2>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse border border-gray-300">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="border border-gray-300 px-4 py-2 text-left">Менеджер</th>
                      <th className="border border-gray-300 px-4 py-2 text-center">Звонков</th>
                      <th className="border border-gray-300 px-4 py-2 text-center">Средний балл</th>
                      <th className="border border-gray-300 px-4 py-2 text-center">Средний %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.managers_stats.map((manager) => (
                      <tr key={manager.manager}>
                        <td className="border border-gray-300 px-4 py-2">{manager.manager}</td>
                        <td className="border border-gray-300 px-4 py-2 text-center">{manager.total_calls}</td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          {manager.avg_score > 0 ? manager.avg_score.toFixed(2) : "—"}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          {manager.avg_percent > 0 ? `${manager.avg_percent.toFixed(1)}%` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div>
            <h2 className="text-xl font-semibold mb-4">Статистика по параметрам</h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border border-gray-300">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border border-gray-300 px-4 py-2 text-left">Параметр</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Оценено</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">MAX (1)</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">МИД (0.5)</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">МИН (0)</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">N/A</th>
                    <th className="border border-gray-300 px-4 py-2 text-center">Средний балл</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.parameter_stats).map(([key, param]) => (
                    <tr key={key}>
                      <td className="border border-gray-300 px-4 py-2">
                        {parameterNames[key] || key}
                      </td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{param.total}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{param.max}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{param.mid}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{param.min}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">{param.na}</td>
                      <td className="border border-gray-300 px-4 py-2 text-center">
                        {param.avg_score > 0 ? param.avg_score.toFixed(2) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {stats.time_series.length > 0 && (
            <div>
              <h2 className="text-xl font-semibold mb-4">Динамика показателей</h2>
              <div className="bg-gray-50 p-4 rounded border border-gray-200">
                <div className="text-sm text-gray-600 mb-2">
                  Показано {stats.time_series.length} оценок за период
                </div>
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {stats.time_series.map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm">
                      <span>{item.date}</span>
                      <span>
                        Балл: {item.score.toFixed(2)} ({item.percent.toFixed(1)}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">Нет данных</div>
      )}
    </div>
  );
}

