"use client";

import { useState, useRef } from "react";
import { uploadFiles, Call } from "@/lib/api";

interface AudioUploadProps {
  onUploadComplete: (calls: Call[]) => void;
  onAnalysisStarted?: (callIds: number[]) => void;
}

export default function AudioUpload({ onUploadComplete, onAnalysisStarted }: AudioUploadProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [manager, setManager] = useState("");
  const [callDate, setCallDate] = useState("");
  const [callIdentifier, setCallIdentifier] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setUploading(true);
    try {
      const calls = await uploadFiles(files, manager || undefined, callDate || undefined, callIdentifier || undefined);
      onUploadComplete(calls);
      
      if (onAnalysisStarted && calls.length > 0) {
        const callIds = calls.map(call => call.id);
        onAnalysisStarted(callIds);
      }
      
      setFiles([]);
      setManager("");
      setCallDate("");
      setCallIdentifier("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error: any) {
      console.error("Upload error:", error);
      const errorMessage = error?.message || "Ошибка загрузки файлов";
      alert(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-white border border-gray-200 rounded">
      <h2 className="text-xl font-semibold mb-4">Загрузка аудио файлов</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Менеджер</label>
        <input
          type="text"
          value={manager}
          onChange={(e) => setManager(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded"
          placeholder="Имя менеджера"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Дата звонка</label>
        <input
          type="date"
          value={callDate}
          onChange={(e) => setCallDate(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Идентификатор звонка</label>
        <input
          type="text"
          value={callIdentifier}
          onChange={(e) => setCallIdentifier(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded"
          placeholder="ID звонка"
        />
      </div>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-gray-300 rounded p-8 text-center mb-4"
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="audio/*"
          onChange={handleFileSelect}
          className="hidden"
          id="file-input"
        />
        <label htmlFor="file-input" className="cursor-pointer">
          <p className="text-gray-600 mb-2">Перетащите файлы сюда или нажмите для выбора</p>
          <p className="text-sm text-gray-500">Поддерживаются аудио файлы</p>
        </label>
        {files.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-medium">Выбрано файлов: {files.length}</p>
            <ul className="mt-2 text-sm text-gray-600">
              {files.map((file, idx) => (
                <li key={idx}>{file.name}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        onClick={handleUpload}
        disabled={files.length === 0 || uploading}
        className="w-full px-4 py-2 bg-black text-white rounded disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {uploading ? "Загрузка..." : "Загрузить"}
      </button>
    </div>
  );
}


