"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getCalls, exportCalls, Call } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [manager, setManager] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  useEffect(() => {
    loadCalls();
  }, []);

  const loadCalls = async () => {
    try {
      const data = await getCalls(
        manager || undefined,
        startDate || undefined,
        endDate || undefined
      );
      setCalls(data);
    } catch (error) {
      console.error("Error loading calls:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilter = () => {
    setLoading(true);
    loadCalls();
  };

  const handleExport = async () => {
    try {
      const blob = await exportCalls(
        manager || undefined,
        startDate || undefined,
        endDate || undefined
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `calls_export_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Error exporting:", error);
      alert("Ошибка экспорта");
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

      <h1 className="text-2xl font-semibold mb-6">История звонков</h1>

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
        <div className="flex gap-2">
          <button
            onClick={handleFilter}
            className="px-4 py-2 bg-black text-white rounded"
          >
            Применить фильтр
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            📥 Экспорт в CSV
          </button>
        </div>
      </div>

      {loading ? (
        <div>Загрузка...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 px-4 py-2 text-left">ID</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Файл</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Менеджер</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Дата звонка</th>
                <th className="border border-gray-300 px-4 py-2 text-left">Длительность</th>
                <th className="border border-gray-300 px-4 py-2 text-left">ID звонка</th>
                <th className="border border-gray-300 px-4 py-2 text-center">Оценка</th>
                <th className="border border-gray-300 px-4 py-2 text-center">Действия</th>
              </tr>
            </thead>
            <tbody>
              {calls.map((call) => (
                <tr key={call.id}>
                  <td className="border border-gray-300 px-4 py-2">{call.id}</td>
                  <td className="border border-gray-300 px-4 py-2">{call.filename}</td>
                  <td className="border border-gray-300 px-4 py-2">{call.manager || "-"}</td>
                  <td className="border border-gray-300 px-4 py-2">
                    {call.call_date ? new Date(call.call_date).toLocaleDateString() : "-"}
                  </td>
                  <td className="border border-gray-300 px-4 py-2">
                    {call.duration
                      ? `${Math.floor(call.duration / 60)}:${Math.floor(call.duration % 60).toString().padStart(2, "0")}`
                      : "-"}
                  </td>
                  <td className="border border-gray-300 px-4 py-2">{call.call_identifier || "-"}</td>
                  <td className="border border-gray-300 px-4 py-2 text-center">
                    {call.evaluation?.итоговая_оценка !== undefined
                      ? `${call.evaluation.итоговая_оценка}${call.evaluation.score_percent ? ` (${call.evaluation.score_percent.toFixed(1)}%)` : ""}`
                      : "-"}
                  </td>
                  <td className="border border-gray-300 px-4 py-2 text-center">
                    <button
                      onClick={() => router.push(`/calls/${call.id}`)}
                      className="text-blue-600 hover:underline"
                    >
                      Открыть
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {calls.length === 0 && (
            <div className="text-center py-8 text-gray-500">Нет звонков</div>
          )}
        </div>
      )}
    </div>
  );
}


