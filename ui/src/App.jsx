import React, { useState, useRef } from "react";
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
} from "lucide-react";

const API_URL = "http://localhost:8000/analyze";

// --- STYLES HELPER ---
const getHighlightStyle = (status, isSelected) => {
  if (!status || status === "ORIGINAL")
    return "hover:bg-gray-100 rounded px-1 transition-colors";

  let baseStyle =
    "cursor-pointer transition-all duration-200 px-1 rounded mx-0.5 box-decoration-clone";

  // Specific styles for Plagiarism types
  if (status.includes("EXACT COPY")) {
    baseStyle += isSelected
      ? " bg-red-300 ring-2 ring-red-500 ring-offset-1 text-red-900 font-medium"
      : " bg-red-200/70 text-red-900 hover:bg-red-300";
  } else if (status.includes("HEAVY PARAPHRASED")) {
    baseStyle += isSelected
      ? " bg-orange-300 ring-2 ring-orange-500 ring-offset-1 text-orange-900 font-medium"
      : " bg-orange-200/70 text-orange-900 hover:bg-orange-300";
  } else if (status.includes("TOPIC MATCH")) {
    baseStyle += isSelected
      ? " bg-blue-300 ring-2 ring-blue-500 ring-offset-1 text-blue-900 font-medium"
      : " bg-blue-100/70 text-blue-900 hover:bg-blue-200";
  }

  return baseStyle;
};

export default function PlagiarismDashboard() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setAnalysis(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(API_URL, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAnalysis(response.data);
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to analyze document.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setAnalysis(null);
    setSelectedSegment(null);
  };

  return (
    <div className="h-screen bg-zinc-100 flex flex-col font-sans overflow-hidden">
      {/* HEADER */}
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
          {analysis && (
            <>
              <div className="h-6 w-px bg-slate-700 mx-2"></div>
              <div className="flex flex-col justify-center">
                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">
                  Document Analysis
                </span>
                <span className="text-sm font-medium truncate max-w-[200px] text-slate-200">
                  {file?.name}
                </span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
          {analysis && (
            <div className="flex items-center gap-2 px-3 py-1 bg-slate-800 rounded border border-slate-700">
              <span className="text-xs text-slate-400 font-bold uppercase">
                Originality Score:
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
              className="flex items-center gap-2 text-xs bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded text-white transition shadow-lg shadow-blue-900/50 font-medium"
            >
              <RefreshCw className="w-3 h-3" /> New Scan
            </button>
          )}
        </div>
      </header>

      {/* MAIN BODY */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* DOCUMENT VIEWPORT */}
        <div className="flex-1 overflow-y-auto bg-zinc-200/80 scrollbar-thin scrollbar-thumb-zinc-400">
          {!analysis ? (
            // --- UPLOAD STATE ---
            <div className="h-full flex flex-col items-center justify-center p-8">
              <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl p-10 border border-white/50">
                <div className="text-center">
                  <div className="bg-blue-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 ring-8 ring-blue-50/50">
                    <Upload className="w-10 h-10 text-blue-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-800 mb-2">
                    Upload Research Paper
                  </h2>
                  <p className="text-slate-500 text-sm mb-8 px-8">
                    Supported format: PDF only. We will scan for similarity, AI
                    generation, and topic relevance.
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
                      Select PDF Document
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
                        {loading ? "Scanning Document..." : "Run Analysis"}
                        {!loading && <ChevronRight className="w-4 h-4" />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            // --- DOCUMENT READER STATE ---
            <div className="flex justify-center py-12 px-4 min-h-full">
              <div className="w-[850px] bg-white shadow-2xl min-h-[1100px] p-[80px] relative transition-all duration-500 ease-in-out">
                {/* Paper Header */}
                <div className="mb-12 border-b-2 border-slate-800 pb-4 flex justify-between items-end">
                  <h2 className="text-3xl font-serif font-bold text-slate-900 tracking-tight">
                    Analysis Report
                  </h2>
                  <div className="text-right">
                    <p className="font-serif text-xs text-slate-500 uppercase tracking-widest">
                      Submission ID
                    </p>
                    <p className="font-mono text-sm text-slate-700">
                      Ref-{Math.floor(Math.random() * 10000000)}
                    </p>
                  </div>
                </div>

                {/* Text Body */}
                <div className="font-serif text-[1.1rem] leading-[2.2rem] text-slate-800 text-justify">
                  {analysis.segments.map((segment, index) => {
                    const isNewPage =
                      index > 0 &&
                      analysis.segments[index - 1].page !== segment.page;
                    return (
                      <React.Fragment key={segment.id}>
                        {/* Page Break Indicator */}
                        {isNewPage && (
                          <div className="w-full h-px bg-slate-200 my-8 relative flex items-center justify-center group">
                            <span className="bg-slate-100 text-slate-400 text-[10px] uppercase font-bold px-3 py-1 rounded-full border border-slate-200">
                              Page {segment.page}
                            </span>
                          </div>
                        )}
                        {/* The Sentence */}
                        <span
                          className={getHighlightStyle(
                            segment.status,
                            selectedSegment?.id === segment.id
                          )}
                          onClick={() => {
                            // Check if the segment has a status other than ORIGINAL to select it
                            if (
                              segment.status &&
                              segment.status !== "ORIGINAL"
                            ) {
                              setSelectedSegment(segment);
                            } else {
                              // Otherwise deselect
                              setSelectedSegment(null);
                            }
                          }}
                        >
                          {segment.text}
                        </span>

                        {/* LOGIC: If it's the end of a paragraph, add break. Otherwise, add space. */}
                        {segment.is_end_of_paragraph ? (
                          <div className="h-4 block w-full content-['']" />
                        ) : (
                          <span> </span>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* SIDEBAR DASHBOARD */}
        {analysis && (
          <aside className="w-[420px] bg-white border-l border-zinc-300 shadow-2xl z-20 flex flex-col">
            {/* TABS */}
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
                // --- DETAILED MATCH VIEW ---
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

                  {/* Snippet Card */}
                  <div
                    className={`p-5 rounded-xl border-l-4 shadow-sm bg-white ${
                      selectedSegment.status.includes("EXACT")
                        ? "border-red-500"
                        : "border-orange-500"
                    }`}
                  >
                    <p className="font-serif italic text-slate-600 text-sm leading-relaxed">
                      "...{selectedSegment.text}..."
                    </p>
                  </div>

                  {selectedSegment.match_details && (
                    <div className="space-y-4">
                      {/* Source Info */}
                      <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                        <div className="flex items-start gap-3 mb-4">
                          <div className="bg-slate-100 p-2 rounded-lg text-slate-600">
                            <FileText className="w-5 h-5" />
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                              Source Match
                            </p>
                            <p className="text-sm font-bold text-slate-800 break-all leading-tight mt-1">
                              {selectedSegment.match_details.source_doc}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 text-xs text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                          <div className="flex flex-col">
                            <span className="uppercase text-[9px] font-bold text-slate-400">
                              Found on Page
                            </span>
                            <span className="font-bold text-slate-700 text-sm">
                              {selectedSegment.match_details.source_page}
                            </span>
                          </div>
                          <div className="h-6 w-px bg-slate-200"></div>
                          <div className="flex flex-col">
                            <span className="uppercase text-[9px] font-bold text-slate-400">
                              Match Type
                            </span>
                            <span className="font-bold text-slate-700 text-sm">
                              {selectedSegment.status.includes("EXACT")
                                ? "Verbatim"
                                : "Paraphrase"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Scores */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center">
                          <div className="text-2xl font-black text-red-500">
                            {selectedSegment.match_details.semantic_score}%
                          </div>
                          <div className="text-[10px] font-bold uppercase text-slate-400">
                            Semantic Match
                          </div>
                        </div>
                        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center">
                          <div className="text-2xl font-black text-blue-500">
                            {selectedSegment.match_details.structural_score}%
                          </div>
                          <div className="text-[10px] font-bold uppercase text-slate-400">
                            Structure Match
                          </div>
                        </div>
                      </div>

                      {/* AI Warning */}
                      {selectedSegment.ai_probability > 50 && (
                        <div className="bg-purple-50 border border-purple-100 p-4 rounded-xl flex items-center gap-3">
                          <Brain className="w-8 h-8 text-purple-600" />
                          <div>
                            <p className="text-xs font-bold text-purple-700 uppercase">
                              AI Writing Detected
                            </p>
                            <p className="text-xs text-purple-600">
                              There is a{" "}
                              <span className="font-bold">
                                {selectedSegment.ai_probability}%
                              </span>{" "}
                              chance this specific segment is AI generated.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                // --- SUMMARY VIEW ---
                <div className="p-0">
                  {/* OVERALL SCORE CIRCLE */}
                  <div className="bg-white p-8 border-b border-zinc-200 flex flex-col items-center justify-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-red-500 via-orange-400 to-green-500"></div>

                    <div className="relative w-40 h-40 flex items-center justify-center">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle
                          cx="80"
                          cy="80"
                          r="70"
                          stroke="#f1f5f9"
                          strokeWidth="10"
                          fill="transparent"
                        />
                        <circle
                          cx="80"
                          cy="80"
                          r="70"
                          stroke="#ef4444"
                          strokeWidth="10"
                          fill="transparent"
                          strokeDasharray={440}
                          strokeDashoffset={
                            440 -
                            (440 * analysis.summary.plagiarism_percent) / 100
                          }
                          className="transition-all duration-1000 ease-out drop-shadow-lg"
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute text-center">
                        <span className="block text-5xl font-black text-slate-800">
                          {analysis.summary.plagiarism_percent}%
                        </span>
                        <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mt-1">
                          Similarity
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* STATS GRID */}
                  <div className="grid grid-cols-2 gap-px bg-zinc-200 border-b border-zinc-200">
                    <div className="bg-white p-6 hover:bg-purple-50/50 transition cursor-help group">
                      <div className="flex items-center gap-2 mb-2">
                        <Brain className="w-4 h-4 text-purple-500" />
                        <span className="text-[10px] font-bold uppercase text-slate-400 group-hover:text-purple-500 transition">
                          AI Probability
                        </span>
                      </div>
                      <div className="text-3xl font-bold text-slate-800 group-hover:text-purple-700 transition">
                        {analysis.summary.ai_percent}%
                      </div>
                    </div>
                    <div className="bg-white p-6 hover:bg-green-50/50 transition cursor-help group">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span className="text-[10px] font-bold uppercase text-slate-400 group-hover:text-green-500 transition">
                          On Topic
                        </span>
                      </div>
                      <div className="text-3xl font-bold text-slate-800 group-hover:text-green-700 transition">
                        {analysis.summary.topic_relevance_percent}%
                      </div>
                    </div>
                  </div>

                  {/* SOURCES LIST */}
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
                              {source.contribution_percent}%
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
      </div>
    </div>
  );
}
