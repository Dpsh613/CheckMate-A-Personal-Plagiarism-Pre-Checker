import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Upload,
  FileText,
  X,
  ChevronRight,
  BarChart2,
  Layers,
  Search,
  CheckCircle,
  RefreshCw,
  Brain,
  Database,
  Trash2,
  Plus,
  AlertTriangle,
  ArrowDown,
} from "lucide-react";

const API_BASE = "http://localhost:8000";

// --- STYLES HELPER ---
const getHighlightStyle = (status, isSelected) => {
  if (!status || status === "ORIGINAL")
    return "hover:bg-gray-100 rounded px-1 transition-colors";

  let baseStyle =
    "cursor-pointer transition-all duration-200 px-1 rounded mx-0.5 box-decoration-clone border-b-2";

  if (status.includes("EXACT")) {
    baseStyle += isSelected
      ? " bg-red-200 border-red-500 text-red-900 font-medium ring-2 ring-red-400 ring-offset-1"
      : " bg-red-100 border-red-300 text-red-900 hover:bg-red-200";
  } else if (status.includes("PATCHWORK") || status.includes("PARAPHRASED")) {
    baseStyle += isSelected
      ? " bg-yellow-200 border-yellow-500 text-yellow-900 font-medium ring-2 ring-yellow-400 ring-offset-1"
      : " bg-yellow-100 border-yellow-300 text-yellow-900 hover:bg-yellow-200";
  } else if (status.includes("POTENTIAL")) {
    baseStyle += isSelected
      ? " bg-orange-200 border-orange-500 text-orange-900 font-medium ring-2 ring-orange-400 ring-offset-1"
      : " bg-orange-100 border-orange-300 text-orange-900 hover:bg-orange-200";
  }
  return baseStyle;
};

export default function PlagiarismDashboard() {
  const [viewMode, setViewMode] = useState("analyzer");
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const fileInputRef = useRef(null);
  const [dbFiles, setDbFiles] = useState([]);
  const [dbLoading, setDbLoading] = useState(false);
  const dbInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setAnalysis(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await axios.post(`${API_BASE}/analyze`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAnalysis(response.data);
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to analyze document. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setAnalysis(null);
    setSelectedSegment(null);
  };

  const fetchDbFiles = async () => {
    setDbLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/database/files`);
      setDbFiles(res.data.files);
    } catch (err) {
      console.error(err);
    } finally {
      setDbLoading(false);
    }
  };

  const handleDbUpload = async (e) => {
    if (!e.target.files || !e.target.files[0]) return;
    const uploadFile = e.target.files[0];
    setDbLoading(true);
    const formData = new FormData();
    formData.append("file", uploadFile);
    try {
      await axios.post(`${API_BASE}/database/upload`, formData);
      fetchDbFiles();
    } catch (err) {
      alert("Upload failed");
    } finally {
      setDbLoading(false);
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete ${filename} from database?`)) return;
    setDbLoading(true);
    try {
      await axios.delete(`${API_BASE}/database/files/${filename}`);
      fetchDbFiles();
    } catch (err) {
      alert("Delete failed");
    } finally {
      setDbLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === "database") fetchDbFiles();
  }, [viewMode]);

  return (
    <div className="h-screen bg-zinc-100 flex flex-col font-sans overflow-hidden">
      <header className="bg-slate-900 text-white h-16 flex justify-between items-center px-6 shadow-md shrink-0 z-30">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-1.5 rounded">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold tracking-wide">
              Check<span className="font-light text-blue-400">Mate</span>
            </h1>
          </div>
          <div className="bg-slate-800 p-1 rounded-lg flex gap-1 ml-8">
            <button
              onClick={() => setViewMode("analyzer")}
              className={`px-4 py-1.5 text-xs font-bold uppercase tracking-wide rounded transition-all ${
                viewMode === "analyzer"
                  ? "bg-blue-600 text-white shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Analyzer
            </button>
            <button
              onClick={() => setViewMode("database")}
              className={`px-4 py-1.5 text-xs font-bold uppercase tracking-wide rounded transition-all ${
                viewMode === "database"
                  ? "bg-blue-600 text-white shadow"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              Database
            </button>
          </div>
        </div>

        {viewMode === "analyzer" && (
          <div className="flex items-center gap-4">
            {analysis && (
              <div className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded border border-slate-700">
                <span className="text-xs text-slate-400 font-bold uppercase">
                  Originality:
                </span>
                <span
                  className={`text-sm font-bold ${
                    analysis.summary.plagiarism_percent < 20
                      ? "text-green-400"
                      : "text-red-400"
                  }`}
                >
                  {100 - Math.ceil(analysis.summary.plagiarism_percent)}%
                </span>
              </div>
            )}
            {analysis && (
              <button
                onClick={reset}
                className="flex items-center gap-2 text-xs bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-white transition font-medium"
              >
                <RefreshCw className="w-3 h-3" /> New Scan
              </button>
            )}
          </div>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden relative">
        {viewMode === "database" && (
          <div className="flex-1 bg-zinc-100 p-8 overflow-y-auto">
            <div className="max-w-4xl mx-auto">
              <div className="flex justify-between items-end mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">
                    Database Manager
                  </h2>
                  <p className="text-slate-500 text-sm">
                    Manage the reference documents.
                  </p>
                </div>
                <input
                  type="file"
                  accept=".pdf"
                  ref={dbInputRef}
                  onChange={handleDbUpload}
                  className="hidden"
                />
                <button
                  onClick={() => dbInputRef.current.click()}
                  disabled={dbLoading}
                  className="bg-slate-900 text-white px-5 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 hover:bg-slate-800 transition shadow-lg shadow-slate-300"
                >
                  {dbLoading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4" />
                  )}{" "}
                  Add Reference PDF
                </button>
              </div>
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
                        File Name
                      </th>
                      <th className="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-right">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {dbFiles.map((f, i) => (
                      <tr key={i} className="hover:bg-slate-50 transition">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="bg-blue-50 p-2 rounded text-blue-600">
                              <Database className="w-4 h-4" />
                            </div>
                            <span className="font-medium text-slate-700 text-sm">
                              {f}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => handleDelete(f)}
                            className="text-red-400 hover:text-red-600 hover:bg-red-50 p-2 rounded-lg transition"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                    {dbFiles.length === 0 && (
                      <tr>
                        <td
                          colSpan="2"
                          className="px-6 py-12 text-center text-slate-400 text-sm"
                        >
                          No files in database yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {viewMode === "analyzer" && (
          <>
            <div className="flex-1 overflow-y-auto bg-zinc-200/80 scrollbar-thin scrollbar-thumb-zinc-400">
              {!analysis ? (
                <div className="h-full flex flex-col items-center justify-center p-8">
                  <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl p-10 border border-white/50">
                    <div className="text-center">
                      <div className="bg-blue-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 ring-8 ring-blue-50/50">
                        <Upload className="w-10 h-10 text-blue-600" />
                      </div>
                      <h2 className="text-2xl font-bold text-slate-800 mb-2">
                        Check Plagiarism
                      </h2>
                      <p className="text-slate-500 text-sm mb-8 px-8">
                        Upload a student paper to check against your{" "}
                        {dbFiles.length} database files.
                      </p>
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        ref={fileInputRef}
                        className="hidden"
                      />
                      {!file ? (
                        <button
                          onClick={() => fileInputRef.current.click()}
                          className="w-full py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl transition shadow-xl shadow-slate-200"
                        >
                          Select Student Paper
                        </button>
                      ) : (
                        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-300">
                          <div className="flex items-center gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
                            <div className="bg-white p-2 rounded shadow-sm border border-slate-100">
                              <FileText className="w-6 h-6 text-red-500" />
                            </div>
                            <div className="flex-1 min-w-0 text-left">
                              <span className="block text-sm font-bold text-slate-700 truncate">
                                {file.name}
                              </span>
                              <span className="block text-xs text-slate-400">
                                {(file.size / 1024 / 1024).toFixed(2)} MB
                              </span>
                            </div>
                            <button
                              onClick={() => setFile(null)}
                              className="text-slate-400 hover:text-red-500 p-2"
                            >
                              <X className="w-5 h-5" />
                            </button>
                          </div>
                          <button
                            onClick={handleAnalyze}
                            disabled={loading}
                            className="w-full py-3.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-blue-200 disabled:opacity-70 disabled:cursor-not-allowed"
                          >
                            {loading ? "Scanning Document..." : "Run Analysis"}{" "}
                            {!loading && <ChevronRight className="w-4 h-4" />}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex justify-center py-12 px-4 min-h-full">
                  <div className="w-[850px] bg-white shadow-2xl min-h-[1100px] p-[80px] relative transition-all duration-500 ease-in-out">
                    <div className="mb-12 border-b-2 border-slate-800 pb-4 flex justify-between items-end">
                      <h2 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">
                        Analysis Report
                      </h2>
                      <div className="text-right">
                        <p className="font-serif text-xs text-slate-500 uppercase tracking-widest">
                          Analysis ID
                        </p>
                        <p className="font-mono text-sm text-slate-700">
                          #{Math.floor(Math.random() * 10000000)}
                        </p>
                      </div>
                    </div>
                    <div className="font-serif text-[1.1rem] leading-[2.2rem] text-slate-800 text-justify">
                      {analysis.segments.map((segment, index) => {
                        const isNewPage =
                          index > 0 &&
                          analysis.segments[index - 1].page !== segment.page;
                        return (
                          <React.Fragment key={index}>
                            {isNewPage && (
                              <div className="w-full h-px bg-slate-200 my-8 relative flex items-center justify-center group">
                                <span className="bg-slate-100 text-slate-400 text-[10px] uppercase font-bold px-3 py-1 rounded-full border border-slate-200">
                                  Page {segment.page}
                                </span>
                              </div>
                            )}
                            <span
                              className={getHighlightStyle(
                                segment.status,
                                selectedSegment?.text === segment.text
                              )}
                              onClick={() => {
                                if (
                                  segment.status &&
                                  segment.status !== "ORIGINAL"
                                ) {
                                  setSelectedSegment(segment);
                                } else {
                                  setSelectedSegment(null);
                                }
                              }}
                            >
                              {segment.text}
                            </span>
                            <span> </span>
                          </React.Fragment>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {analysis && (
              <aside className="w-[450px] bg-white border-l border-zinc-300 shadow-2xl z-20 flex flex-col">
                <div className="flex border-b border-zinc-200">
                  <button
                    className={`flex-1 py-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${
                      !selectedSegment
                        ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50/50"
                        : "text-zinc-400 hover:text-zinc-600 hover:bg-zinc-50"
                    }`}
                    onClick={() => setSelectedSegment(null)}
                  >
                    <Layers className="w-4 h-4" /> Summary
                  </button>
                  <button
                    className={`flex-1 py-4 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${
                      selectedSegment
                        ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50/50"
                        : "text-zinc-400 hover:text-zinc-600 hover:bg-zinc-50"
                    }`}
                    disabled={!selectedSegment}
                  >
                    <Search className="w-4 h-4" /> Match Detail
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto bg-slate-50/50">
                  {selectedSegment ? (
                    <div className="p-6 space-y-6 animate-in slide-in-from-right-8 duration-300">
                      <div className="flex justify-between items-center">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                          Investigation
                        </h3>
                        <button
                          onClick={() => setSelectedSegment(null)}
                          className="p-1 hover:bg-slate-200 rounded-full transition"
                        >
                          <X className="w-5 h-5 text-slate-400" />
                        </button>
                      </div>

                      {/* --- STUDENT TEXT --- */}
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase mb-2 block">
                          Student Text
                        </span>
                        <div
                          className={`p-4 rounded-xl border-l-4 shadow-sm bg-white ${
                            selectedSegment.status.includes("EXACT")
                              ? "border-red-500"
                              : selectedSegment.status.includes("PATCHWORK")
                              ? "border-yellow-500"
                              : "border-orange-500"
                          }`}
                        >
                          <p className="font-serif italic text-slate-700 text-sm leading-relaxed">
                            "{selectedSegment.text}"
                          </p>
                        </div>
                      </div>

                      {/* --- COMPARISON ARROW --- */}
                      <div className="flex justify-center text-slate-300">
                        <ArrowDown className="w-5 h-5" />
                      </div>

                      {/* --- MATCHED DATABASE TEXT (NEW FEATURE) --- */}
                      {selectedSegment.matched_db_text && (
                        <div>
                          <span className="text-[10px] font-bold text-slate-400 uppercase mb-2 block">
                            Matched Database Source
                          </span>
                          <div className="p-4 rounded-xl border-l-4 border-blue-400 shadow-sm bg-blue-50/50">
                            <p className="font-serif italic text-slate-600 text-sm leading-relaxed">
                              "{selectedSegment.matched_db_text}"
                            </p>
                          </div>
                        </div>
                      )}

                      <div className="space-y-4 pt-4 border-t border-slate-200">
                        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                          <div className="flex items-start gap-3 mb-4">
                            <div className="bg-slate-100 p-2 rounded-lg text-slate-600">
                              <FileText className="w-5 h-5" />
                            </div>
                            <div>
                              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                                Source File
                              </p>
                              <p className="text-sm font-bold text-slate-800 break-all leading-tight mt-1">
                                {selectedSegment.source || "Unknown"}
                              </p>
                            </div>
                          </div>

                          <div className="flex flex-col gap-2">
                            <div className="flex justify-between items-center text-xs text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                              <span className="uppercase text-[9px] font-bold text-slate-400">
                                Match Status
                              </span>
                              <span
                                className={`font-bold px-2 py-0.5 rounded ${
                                  selectedSegment.status.includes("EXACT")
                                    ? "bg-red-100 text-red-600"
                                    : selectedSegment.status.includes(
                                        "PATCHWORK"
                                      )
                                    ? "bg-yellow-100 text-yellow-600"
                                    : "bg-orange-100 text-orange-600"
                                }`}
                              >
                                {selectedSegment.status
                                  .replace("🔴 ", "")
                                  .replace("🟠 ", "")
                                  .replace("🟡 ", "")}
                              </span>
                            </div>

                            <div className="flex justify-between items-center text-xs text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                              <span className="uppercase text-[9px] font-bold text-slate-400">
                                Overlap Score
                              </span>
                              <div className="flex items-center gap-2">
                                <div className="h-1.5 w-16 bg-slate-200 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-blue-500 rounded-full"
                                    style={{
                                      width: `${selectedSegment.score}%`,
                                    }}
                                  ></div>
                                </div>
                                <span className="font-bold text-slate-700">
                                  {selectedSegment.score}%
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // --- SUMMARY PANEL ---
                    <div className="p-0">
                      <div className="bg-white p-8 border-b border-zinc-200 flex flex-col items-center justify-center relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-red-500 via-orange-400 to-green-500"></div>
                        <div className="relative w-40 h-40 flex items-center justify-center">
                          <div className="text-center">
                            <span className="block text-5xl font-black text-slate-800">
                              {analysis.summary.plagiarism_percent}%
                            </span>
                            <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mt-1">
                              Plagiarism
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-px bg-zinc-200 border-b border-zinc-200">
                        <div className="bg-white p-6 hover:bg-purple-50/50 transition cursor-help group">
                          <div className="flex items-center gap-2 mb-2">
                            <Brain className="w-4 h-4 text-purple-500" />
                            <span className="text-[10px] font-bold uppercase text-slate-400 group-hover:text-purple-500 transition">
                              AI Likelihood
                            </span>
                          </div>
                          <div className="text-3xl font-bold text-slate-800 group-hover:text-purple-700 transition">
                            {analysis.summary.ai_percent}%
                          </div>
                        </div>
                        <div className="bg-white p-6 hover:bg-red-50/50 transition cursor-help group">
                          <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="w-4 h-4 text-red-500" />
                            <span className="text-[10px] font-bold uppercase text-slate-400 group-hover:text-red-500 transition">
                              Sentences Matched
                            </span>
                          </div>
                          <div className="text-3xl font-bold text-slate-800 group-hover:text-red-700 transition">
                            {analysis.summary.matched_sentences}{" "}
                            <span className="text-sm font-normal text-slate-400">
                              / {analysis.summary.total_sentences}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="p-6">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                          <BarChart2 className="w-4 h-4" /> Top Sources
                        </h4>
                        <div className="space-y-3">
                          {analysis.sources.map((source, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-3 p-4 bg-white border border-zinc-200 rounded-xl hover:border-red-300 hover:shadow-md transition cursor-pointer group"
                            >
                              <div className="w-8 h-8 rounded-lg bg-red-50 text-red-600 font-bold text-xs flex items-center justify-center border border-red-100 group-hover:bg-red-500 group-hover:text-white transition">
                                {i + 1}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-bold text-slate-700 truncate group-hover:text-red-700 transition">
                                  {source.filename}
                                </p>
                                <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
                                  Database Match
                                </p>
                              </div>
                              <div className="text-right">
                                <div className="text-sm font-black text-slate-800">
                                  {source.count}
                                </div>
                                <div className="text-[9px] text-slate-400 font-bold uppercase">
                                  Sentences
                                </div>
                              </div>
                            </div>
                          ))}
                          {analysis.sources.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
                              <CheckCircle className="w-10 h-10 mb-3 opacity-20" />
                              <p className="text-sm font-medium">
                                No external sources found.
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </aside>
            )}
          </>
        )}
      </div>
    </div>
  );
}
