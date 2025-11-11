"use client";

import React from "react";
import { Evaluation } from "@/lib/api";

interface EvaluationTableProps {
  evaluation: Evaluation;
}

export default function EvaluationTable({ evaluation }: EvaluationTableProps) {
  const scores = evaluation.scores || {};
  
  const categories = [
    {
      name: "Установление контакта",
      items: [
        { key: "1.1", label: "1.1 Приветствие" },
        { key: "1.2", label: "1.2 Наличие техники" }
      ]
    },
    {
      name: "Диагностика",
      items: [
        { key: "2.1", label: "2.1 Выявление цели, боли" },
        { key: "2.2", label: "2.2 Критерии обучения" }
      ]
    },
    {
      name: "Продажа",
      items: [
        { key: "3.1", label: "3.1 Запись на пробное" },
        { key: "3.2", label: "3.2 Повторная связь" }
      ]
    },
    {
      name: "Презентация",
      items: [
        { key: "4.1", label: "4.1 Презентация формата" },
        { key: "4.2", label: "4.2 Презентация до пробного" }
      ]
    },
    {
      name: "Работа с возражениями",
      items: [
        { key: "5.1", label: "5.1 Выявление возражений" },
        { key: "5.2", label: "5.2 Отработка возражений" }
      ]
    },
    {
      name: "Завершение",
      items: [
        { key: "6", label: "6. Контрольные точки" },
        { key: "7", label: "7. Корректность сделки" },
        { key: "8", label: "8. Грамотность" },
        { key: "9", label: "9. Нарушения" }
      ]
    }
  ];

  let comments: Record<string, string> = {};
  try {
    comments = JSON.parse(evaluation.комментарии || "{}");
  } catch {
    comments = {};
  }

  const getScoreDisplay = (key: string) => {
    const scoreData = scores[key];
    if (!scoreData) return "-";
    
    if (key === "9") {
      return scoreData.violation ? "TRUE" : "FALSE";
    }
    
    return scoreData.score !== undefined ? scoreData.score : "-";
  };

  const getComment = (key: string) => {
    const scoreData = scores[key];
    return comments[key] || scoreData?.comment || "";
  };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-100">
            <th className="border border-gray-300 px-4 py-2 text-left">Этап</th>
            <th className="border border-gray-300 px-4 py-2 text-center">Балл</th>
            <th className="border border-gray-300 px-4 py-2 text-left">Комментарий</th>
          </tr>
        </thead>
        <tbody>
          {categories.map((category, catIdx) => (
            <React.Fragment key={catIdx}>
              {category.items.map((item, itemIdx) => {
                const isFirstInCategory = itemIdx === 0;
                return (
                  <tr key={item.key}>
                    {isFirstInCategory && (
                      <td 
                        className="border border-gray-300 px-4 py-2 font-semibold bg-gray-50 align-top" 
                        rowSpan={category.items.length}
                      >
                        {category.name}
                      </td>
                    )}
                    <td className="border border-gray-300 px-4 py-2">{item.label}</td>
                    <td className="border border-gray-300 px-4 py-2 text-center">
                      {getScoreDisplay(item.key)}
                    </td>
                    <td className="border border-gray-300 px-4 py-2">{getComment(item.key)}</td>
                  </tr>
                );
              })}
            </React.Fragment>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-gray-50 font-semibold">
            <td className="border border-gray-300 px-4 py-2" colSpan={2}>Итоговая оценка</td>
            <td className="border border-gray-300 px-4 py-2 text-center">{evaluation.итоговая_оценка}</td>
            <td className="border border-gray-300 px-4 py-2">
              {evaluation.нарушения ? "Обнулено из-за нарушений" : ""}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
