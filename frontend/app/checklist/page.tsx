"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getChecklist, ChecklistData } from "@/lib/api";

export default function ChecklistPage() {
  const router = useRouter();
  const [data, setData] = useState<ChecklistData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadChecklist();
  }, []);

  const loadChecklist = async () => {
    try {
      const result = await getChecklist();
      setData(result);
    } catch (e: any) {
      setError(e.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <p className="text-gray-600">Загрузка...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <p className="text-red-600">{error || "Не удалось загрузить данные"}</p>
      </div>
    );
  }

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

      <h1 className="text-2xl font-semibold mb-6">Критерии оценки звонков</h1>

      <div className="mb-8 p-5 bg-blue-50 border border-blue-200 rounded">
        <h2 className="text-lg font-semibold mb-3">Общие правила оценки</h2>
        <ol className="list-decimal list-inside space-y-1.5 text-sm">
          {data.rules.map((rule, idx) => (
            <li key={idx}>{rule}</li>
          ))}
        </ol>
      </div>

      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Чек-лист по этапам</h2>

        {data.stages.map((stage) => (
          <div key={stage.name} className="mb-6">
            <h3 className="text-base font-semibold bg-gray-100 px-4 py-2 rounded-t border border-gray-300 border-b-0">
              {stage.name}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse border border-gray-300">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="border border-gray-300 px-3 py-2 text-left text-sm w-40">Критерий</th>
                    <th className="border border-gray-300 px-3 py-2 text-left text-sm">Описание</th>
                    <th className="border border-gray-300 px-3 py-2 text-left text-sm bg-green-50">1 балл (MAX)</th>
                    <th className="border border-gray-300 px-3 py-2 text-left text-sm bg-yellow-50">0.5 балла (МИД)</th>
                    <th className="border border-gray-300 px-3 py-2 text-left text-sm bg-red-50">0 баллов (МИН)</th>
                  </tr>
                </thead>
                <tbody>
                  {stage.criteria.map((c) => (
                    <tr key={c.key}>
                      <td className="border border-gray-300 px-3 py-2 text-sm font-medium align-top">
                        {c.key}
                      </td>
                      <td className="border border-gray-300 px-3 py-2 text-sm align-top whitespace-pre-line">
                        {c.description}
                      </td>
                      <td className="border border-gray-300 px-3 py-2 text-sm align-top bg-green-50 whitespace-pre-line">
                        {c.max?.criterion || "—"}
                      </td>
                      <td className="border border-gray-300 px-3 py-2 text-sm align-top bg-yellow-50 whitespace-pre-line">
                        {c.mid?.criterion && c.mid.criterion !== "нет" ? c.mid.criterion : "—"}
                      </td>
                      <td className="border border-gray-300 px-3 py-2 text-sm align-top bg-red-50 whitespace-pre-line">
                        {c.min?.criterion || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      <div className="mb-8 p-5 bg-amber-50 border border-amber-200 rounded">
        <h2 className="text-lg font-semibold mb-3">Особые обстоятельства</h2>
        <p className="text-sm text-gray-600 mb-3">
          Система автоматически определяет наличие особых обстоятельств, которые могли повлиять на ход разговора.
          При обнаружении — звонок помечается флагом «Нужна проверка».
        </p>
        <ul className="space-y-1.5 text-sm">
          {Object.entries(data.special_circumstances).map(([key, desc]) => (
            <li key={key} className="flex gap-2">
              <span className="text-amber-600 font-mono text-xs bg-amber-100 px-1.5 py-0.5 rounded shrink-0">
                {key}
              </span>
              <span>{desc}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
