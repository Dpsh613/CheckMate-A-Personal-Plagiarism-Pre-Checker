import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  UploadCloud,
  FileText,
  Search,
  Database,
  Trash2,
  AlertCircle,
  CheckCircle,
  Loader2,
  BookOpen,
  File,
  Info,
} from "lucide-react";

const API_BASE = "http://localhost:8000";

// Refined, softer color palette for easier reading
const SOURCE_COLORS = [
  {
    text: "text-rose-600",
    bg: "bg-rose-50",
    highlight:
      "bg-rose-100 text-rose-900 border-b-2 border-rose-300 rounded-sm",
    dot: "bg-rose-500",
  },
  {
    text: "text-blue-600",
    bg: "bg-blue-50",
    highlight:
      "bg-blue-100 text-blue-900 border-b-2 border-blue-300 rounded-sm",
    dot: "bg-blue-500",
  },
  {
    text: "text-emerald-600",
    bg: "bg-emerald-50",
    highlight:
      "bg-emerald-100 text-emerald-900 border-b-2 border-emerald-300 rounded-sm",
    dot: "bg-emerald-500",
  },
  {
    text: "text-purple-600",
    bg: "bg-purple-50",
    highlight:
      "bg-purple-100 text-purple-900 border-b-2 border-purple-300 rounded-sm",
    dot: "bg-purple-500",
  },
  {
    text: "text-amber-600",
    bg: "bg-amber-50",
    highlight:
      "bg-amber-100 text-amber-900 border-b-2 border-amber-300 rounded-sm",
    dot: "bg-amber-500",
  },
];

export default function PlagiarismDashboard() {
  const [viewMode, setViewMode] = useState("analyzer");
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const fileInputRef = useRef(null);

  const [dbFiles, setDbFiles] = useState([]);
  const [arxivTopic, setArxivTopic] = useState("");
  const [arxivResults, setArxivResults] = useState([]);
  const [arxivLoading, setArxivLoading] = useState(false);

  const fetchDbFiles = async () => {
    try {
      const res = await axios.get(`${API_BASE}/database/files`);
      setDbFiles(res.data.files);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (viewMode === "database") fetchDbFiles();
  }, [viewMode]);

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await axios.post(`${API_BASE}/analyze`, formData);
      setAnalysis(response.data);
    } finally {
      setLoading(false);
    }
  };

  const handleArxivSearch = async () => {
    if (!arxivTopic.trim()) return;
    setArxivLoading(true);
    try {
      const res = await axios.get(
        `${API_BASE}/arxiv/search?topic=${encodeURIComponent(arxivTopic)}`,
      );
      setArxivResults(res.data.results);
    } finally {
      setArxivLoading(false);
    }
  };

  const indexArxivPaper = async (paper) => {
    try {
      await axios.post(`${API_BASE}/arxiv/download`, {
        pdf_url: paper.pdf_url,
        title: paper.title,
      });
      alert("Paper Indexed & Deleted from Disk!");
      fetchDbFiles();
    } catch (err) {
      alert("Failed to index paper.");
    }
  };

  const deleteDbFile = async (filename) => {
    await axios.delete(`${API_BASE}/database/files/${filename}`);
    fetchDbFiles();
  };

  const getSourceColor = (sourceName) => {
    if (!analysis || !sourceName) return null;
    const index = analysis.sources.findIndex((s) => s.filename === sourceName);
    return SOURCE_COLORS[index % SOURCE_COLORS.length];
  };

  const getScoreColor = (score) => {
    if (score < 15) return "text-emerald-500 border-emerald-500 bg-emerald-50";
    if (score < 40) return "text-amber-500 border-amber-500 bg-amber-50";
    return "text-rose-500 border-rose-500 bg-rose-50";
  };

  const renderHighlightedText = (segment) => {
    if (segment.status === "ORIGINAL" || !segment.matched_words) {
      return <span>{segment.text} </span>;
    }

    const color = getSourceColor(segment.source);
    const words = segment.text.split(" ");

    return (
      <span
        className={`cursor-pointer transition-colors duration-200 ${
          selectedSegment === segment
            ? "bg-gray-100 ring-2 ring-gray-200 rounded"
            : ""
        }`}
        onClick={() => setSelectedSegment(segment)}
      >
        {words.map((w, i) => {
          const cleanWord = w.replace(/[.,!?()]/g, "").toLowerCase();
          const isMatch = segment.matched_words.includes(cleanWord);
          if (isMatch) {
            return (
              <mark
                key={i}
                className={`px-[1px] mx-[1px] bg-transparent ${color.highlight}`}
              >
                {w}
              </mark>
            );
          }
          return <span key={i}> {w} </span>;
        })}
      </span>
    );
  };

  return (
    <div className="h-screen flex flex-col font-sans bg-gray-50 text-gray-800">
      {/* Navbar */}
      <header className="bg-white border-b border-gray-200 h-16 flex items-center px-8 gap-8 shrink-0">
        <div className="flex items-center gap-2 text-indigo-600">
          <BookOpen className="w-6 h-6" />
          <h1 className="font-bold text-xl tracking-tight text-gray-900">
            CheckMate
          </h1>
        </div>

        <nav className="flex gap-1 ml-4">
          <button
            onClick={() => setViewMode("analyzer")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              viewMode === "analyzer"
                ? "bg-indigo-50 text-indigo-600"
                : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" /> Analyzer
            </div>
          </button>
          <button
            onClick={() => setViewMode("database")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              viewMode === "database"
                ? "bg-indigo-50 text-indigo-600"
                : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
            }`}
          >
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4" /> Database
            </div>
          </button>
        </nav>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {viewMode === "database" ? (
          <div className="flex-1 p-8 overflow-y-auto">
            <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Database Panel */}
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex flex-col h-[80vh]">
                <div className="mb-6">
                  <h2 className="font-semibold text-lg text-gray-900 flex items-center gap-2">
                    <Database className="w-5 h-5 text-indigo-500" /> Indexed
                    Sources
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">
                    Files stored securely as vectors for similarity matching.
                  </p>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2 pr-2">
                  {dbFiles.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <File className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      <p>No sources indexed yet.</p>
                    </div>
                  ) : (
                    dbFiles.map((f, i) => (
                      <div
                        key={i}
                        className="flex justify-between items-center p-3 rounded-lg border border-gray-100 hover:border-gray-200 hover:shadow-sm transition-all group bg-gray-50/50"
                      >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <FileText className="w-4 h-4 text-gray-400 shrink-0" />
                          <span className="text-sm font-medium text-gray-700 truncate">
                            {f}
                          </span>
                        </div>
                        <button
                          onClick={() => deleteDbFile(f)}
                          className="opacity-0 group-hover:opacity-100 p-2 hover:bg-rose-100 rounded-md transition-all text-rose-500"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Arxiv Panel */}
              <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex flex-col h-[80vh]">
                <div className="mb-6">
                  <h2 className="font-semibold text-lg text-gray-900 flex items-center gap-2">
                    <Search className="w-5 h-5 text-indigo-500" /> Import from
                    ArXiv
                  </h2>
                  <p className="text-sm text-gray-500 mt-1">
                    Search and index academic papers directly.
                  </p>
                </div>

                <div className="flex gap-2 mb-6">
                  <div className="relative flex-1">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                    <input
                      className="w-full border border-gray-300 py-2 pl-9 pr-4 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                      placeholder="Enter a research topic..."
                      value={arxivTopic}
                      onChange={(e) => setArxivTopic(e.target.value)}
                      onKeyDown={(e) =>
                        e.key === "Enter" && handleArxivSearch()
                      }
                    />
                  </div>
                  <button
                    onClick={handleArxivSearch}
                    disabled={arxivLoading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-70"
                  >
                    {arxivLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "Search"
                    )}
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                  {arxivResults.map((res, i) => (
                    <div
                      key={i}
                      className="border border-gray-200 p-4 rounded-lg hover:border-indigo-300 hover:shadow-sm transition-all bg-white"
                    >
                      <h3 className="text-sm font-semibold text-gray-800 line-clamp-2 leading-snug">
                        {res.title}
                      </h3>
                      <button
                        onClick={() => indexArxivPaper(res)}
                        className="mt-3 text-xs font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
                      >
                        <UploadCloud className="w-3.5 h-3.5" /> Index Paper
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* Analyzer Left - Document Viewer */}
            <div className="flex-1 overflow-y-auto bg-gray-100/50 flex flex-col items-center p-8 relative">
              {!analysis ? (
                <div className="m-auto w-full max-w-md">
                  <div className="bg-white p-10 rounded-2xl shadow-sm border border-gray-200 text-center">
                    <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6">
                      <UploadCloud className="w-8 h-8 text-indigo-500" />
                    </div>
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                      Upload Document
                    </h3>
                    <p className="text-gray-500 text-sm mb-8">
                      Select a text or PDF file to scan for similarity against
                      your indexed database.
                    </p>

                    <input
                      type="file"
                      id="file-upload"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files[0])}
                    />
                    <label
                      htmlFor="file-upload"
                      className="cursor-pointer flex flex-col items-center justify-center w-full border-2 border-dashed border-gray-300 rounded-lg p-6 hover:bg-gray-50 hover:border-indigo-400 transition-all mb-4"
                    >
                      <span className="text-sm font-medium text-gray-600">
                        {file ? file.name : "Click to browse files"}
                      </span>
                    </label>

                    <button
                      onClick={handleAnalyze}
                      disabled={!file || loading}
                      className="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-lg font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />{" "}
                          Scanning...
                        </>
                      ) : (
                        "Scan Document"
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="bg-white shadow-md ring-1 ring-gray-200 w-full max-w-4xl p-12 lg:p-20 font-serif leading-loose text-lg text-gray-800 text-justify rounded-sm min-h-full">
                  {analysis.segments.map((seg, i) => (
                    <React.Fragment key={i}>
                      {renderHighlightedText(seg)}
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>

            {/* Analyzer Right - Results Sidebar */}
            {analysis && (
              <div className="w-[380px] bg-white border-l border-gray-200 shadow-xl flex flex-col shrink-0 z-10">
                {/* Score Header */}
                <div className="p-8 border-b border-gray-100 flex flex-col items-center justify-center">
                  <div
                    className={`w-32 h-32 rounded-full border-8 flex flex-col items-center justify-center ${getScoreColor(analysis.summary.plagiarism_percent)} shadow-inner`}
                  >
                    <span className="text-4xl font-black tracking-tighter">
                      {analysis.summary.plagiarism_percent}%
                    </span>
                  </div>
                  <span className="block text-xs font-bold uppercase tracking-widest mt-4 text-gray-400">
                    Similarity Score
                  </span>
                </div>

                {/* Match Overview */}
                <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
                  <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" /> Match Overview
                  </h3>

                  <div className="space-y-2">
                    {analysis.sources.map((src, i) => {
                      const color = SOURCE_COLORS[i % SOURCE_COLORS.length];
                      return (
                        <div
                          key={i}
                          className="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                        >
                          <div
                            className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold text-white ${color.dot}`}
                          >
                            {i + 1}
                          </div>
                          <div className="flex-1 truncate text-sm font-medium text-gray-700">
                            {src.filename}
                          </div>
                          <div className="text-xs font-semibold text-gray-500 bg-gray-100 px-2 py-1 rounded">
                            {src.matched_words} words
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Context Viewer */}
                  {selectedSegment && selectedSegment.source ? (
                    <div className="mt-8 border border-indigo-100 bg-indigo-50/50 rounded-xl p-5 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-300">
                      <div className="flex items-center gap-2 mb-3">
                        <Info className="w-4 h-4 text-indigo-600" />
                        <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">
                          Source Context
                        </h4>
                      </div>
                      <p className="text-sm font-serif italic text-indigo-800/80 leading-relaxed">
                        "...{selectedSegment.matched_db_text}..."
                      </p>
                    </div>
                  ) : (
                    <div className="mt-8 text-center text-sm text-gray-400 italic px-4">
                      Click on highlighted text in the document to see the
                      original source context.
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
