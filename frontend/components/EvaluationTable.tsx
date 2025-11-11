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
        { key: "1", label: "1 Приветствие, знакомство" }
      ]
    },
    {
      name: "Квалификация",
      items: [
        { key: "2", label: "2 Первичная квалификация" }
      ]
    },
    {
      name: "Выявление потребностей",
      items: [
        { key: "3.1", label: "3.1 Вопросы вторичной квалификации" },
        { key: "3.2", label: "3.2 Вопрос о цели обучения" },
        { key: "3.3", label: "3.3 Резюмирование потребности" }
      ]
    },
    {
      name: "Презентация",
      items: [
        { key: "4.1", label: "4.1 Презентация обучения из потребности" },
        { key: "4.2", label: "4.2 Презентация формата обучения" },
        { key: "4.3", label: "4.3 Презентация стоимости" },
        { key: "4.4", label: "4.4 Озвучивание информации для пробного" }
      ]
    },
    {
      name: "Работа с возражениями",
      items: [
        { key: "5", label: "5 Уточнить сомнение клиента" }
      ]
    },
    {
      name: "Завершение сделки",
      items: [
        { key: "6", label: "6 Завершение сделки" }
      ]
    },
    {
      name: "Голосовые характеристики",
      items: [
        { key: "7.1", label: "7.1 Грамотность и формулировки" },
        { key: "7.2", label: "7.2 Инициатива за ведение диалога" }
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
            <td className="border border-gray-300 px-4 py-2"></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
