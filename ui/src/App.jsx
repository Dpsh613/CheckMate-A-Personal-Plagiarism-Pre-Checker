// If the screen goes blank or shows nothing after loading, it usually means **React crashed** silently while trying to render the data, or the styles are hiding everything.

// Please follow these 3 steps to fix the blank screen and get the UI working.

// ### Step 1: Open the Console (The Truth Teller)
// We need to know if it's a code crash or a CSS issue.
// 1.  Right-click your browser page and select **Inspect**.
// 2.  Click the **Console** tab.
// 3.  **If you see red text (Errors):** It is a code crash (e.g., `Cannot read properties of null`).
// 4.  **If it is empty:** It is a CSS/Layout issue (the content exists but is invisible).

// ### Step 2: Clean Slate (The "Guaranteed to Work" Version)
// To rule out your local Tailwind installation being broken, I have written a version of the code that **force-loads Tailwind via CDN** automatically. It also includes "Safety Checks" so the page won't crash if the data is slightly off.

// Replace your **entire** `PlagiarismDashboard.jsx` (or `App.js`) content with this code.

// **Copy ALL of this:**


import React, { useState, useEffect } from 'react';


// Simple Icons (SVG) so we don't depend on external libraries crashing the app
const IconUpload = () => <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>;
const IconAlert = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>;
const IconClose = () => <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>;

const API_URL = "http://localhost:8000/analyze";

export default function PlagiarismDashboard() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSegment, setSelectedSegment] = useState(null);

  // --- FORCE TAILWIND VIA CDN (HACK TO FIX STYLING) ---
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://cdn.tailwindcss.com";
    document.head.appendChild(script);
  }, []);

  const getStatusStyles = (status) => {
    if (!status) return "";
    const s = status.toUpperCase();
    // Simplified logic to ensure matches get colors
    if (s.includes("EXACT")) return "bg-red-200 text-red-900 cursor-pointer border-b-2 border-red-400";
    if (s.includes("PARA") || s.includes("AI")) return "bg-orange-100 text-orange-900 cursor-pointer border-b-2 border-orange-300";
    if (s.includes("TOPIC")) return "bg-green-100 text-green-900 cursor-pointer border-b-2 border-green-300";
    return "";
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setAnalysis(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("Sending request to:", API_URL);
      const response = await fetch(API_URL, { method: "POST", body: formData });
      
      if (!response.ok) {
        throw new Error(`Server Error: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log("Received Data:", data); // Check Console F12 if this prints
      
      if (!data || !data.segments) {
        throw new Error("Invalid data format received from backend");
      }

      setAnalysis(data);
    } catch (err) {
      console.error("Fetch error:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      
      {/* 1. TOP BAR */}
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center shadow-sm">
        <h1 className="text-xl font-bold">PlagScan Check</h1>
        {analysis && (
          <button 
            onClick={() => { setAnalysis(null); setFile(null); setSelectedSegment(null); }}
            className="text-sm text-blue-600 underline"
          >
            Start Over
          </button>
        )}
      </header>

      {/* 2. ERROR DISPLAY */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 m-4 rounded relative">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {/* 3. MAIN CONTENT */}
      <main className="p-8 flex justify-center">
        
        {/* VIEW A: UPLOAD SCREEN */}
        {!analysis && !loading && (
          <div className="w-full max-w-md bg-white p-10 rounded-xl shadow-lg border border-gray-200 text-center">
             <div className="flex justify-center mb-4 text-indigo-500"><IconUpload /></div>
             <h2 className="text-xl font-bold mb-4">Upload PDF</h2>
             <input 
               type="file" 
               accept=".pdf" 
               className="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-indigo-50 file:text-indigo-700
                hover:file:bg-indigo-100 mb-6"
               onChange={(e) => setFile(e.target.files[0])}
             />
             <button 
                onClick={handleAnalyze} 
                disabled={!file}
                className="w-full bg-black text-white py-3 rounded-lg font-bold disabled:bg-gray-300"
             >
                ANALYZE DOCUMENT
             </button>
          </div>
        )}

        {/* VIEW B: LOADING SCREEN */}
        {loading && (
          <div className="text-center mt-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-500">Scanning document chunks...</p>
          </div>
        )}

        {/* VIEW C: RESULTS (The "Insane" Layout) */}
        {analysis && !loading && (
           <div className="flex flex-col lg:flex-row gap-8 w-full max-w-7xl">
              
              {/* C1. PAPER READER */}
              <div className="flex-1 bg-white p-10 shadow-xl min-h-[800px] border border-gray-200">
                <h2 className="text-center font-serif text-3xl mb-8 font-bold border-b pb-4">Analyzed Text</h2>
                <div className="font-serif text-lg leading-loose text-justify text-gray-700">
                   {analysis.segments.length === 0 && <p>No text found in document.</p>}
                   
                   {analysis.segments.map((segment) => (
                     <span 
                       key={segment.id}
                       className={`
                         transition-all duration-200 px-0.5 rounded
                         ${getStatusStyles(segment.status)}
                       `}
                       title={segment.status !== "ORIGINAL" ? segment.status : ""}
                       onClick={() => {
                          if (segment.status !== "ORIGINAL") setSelectedSegment(segment);
                       }}
                     >
                        {segment.text}{" "}
                     </span>
                   ))}
                </div>
              </div>

              {/* C2. INSPECTOR SIDEBAR (Sticky) */}
              <div className="lg:w-80 w-full h-fit bg-gray-100 p-6 rounded-xl border sticky top-4">
                 <h3 className="font-bold text-gray-500 uppercase text-xs mb-4">Inspector</h3>
                 
                 {selectedSegment ? (
                    <div className="bg-white p-4 rounded shadow animate-pulse-once">
                       <div className="flex justify-between items-start mb-2">
                          <span className="font-bold text-sm text-indigo-600">MATCH DETAILS</span>
                          <button onClick={() => setSelectedSegment(null)}><IconClose /></button>
                       </div>
                       <div className="mb-4">
                          <p className="text-sm italic bg-gray-50 p-2 rounded">"{selectedSegment.text}"</p>
                       </div>
                       
                       {selectedSegment.match_details ? (
                         <>
                            <div className="mb-2">
                               <p className="text-xs text-gray-500">Source:</p>
                               <p className="font-medium text-sm break-all">{selectedSegment.match_details.source_doc}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-2 mt-4">
                               <div className="bg-red-50 p-2 text-center border border-red-100 rounded">
                                  <div className="text-red-600 font-bold">{selectedSegment.match_details.semantic_score}%</div>
                                  <div className="text-[10px] text-red-400 uppercase">Semantic</div>
                               </div>
                               <div className="bg-blue-50 p-2 text-center border border-blue-100 rounded">
                                  <div className="text-blue-600 font-bold">{selectedSegment.match_details.structural_score}%</div>
                                  <div className="text-[10px] text-blue-400 uppercase">Exact</div>
                               </div>
                            </div>
                         </>
                       ) : (
                         <p className="text-sm text-orange-600 font-medium">{selectedSegment.status}</p>
                       )}
                    </div>
                 ) : (
                    // GLOBAL STATS
                    <div className="space-y-4">
                       <div className="bg-white p-4 rounded shadow flex justify-between items-center">
                          <span className="font-bold text-gray-600">Plagiarism Risk</span>
                          <span className="text-2xl font-bold text-red-500">{analysis.summary.plagiarism_percent}%</span>
                       </div>
                       <div className="bg-white p-4 rounded shadow flex justify-between items-center">
                          <span className="font-bold text-gray-600">AI Detection</span>
                          <span className="text-2xl font-bold text-purple-500">{analysis.summary.ai_percent}%</span>
                       </div>
                       <div className="mt-4">
                          <p className="text-xs font-bold text-gray-400 uppercase mb-2">Top Sources</p>
                          {analysis.sources.map((s, i) => (
                             <div key={i} className="text-xs mb-1 p-2 bg-white rounded border flex justify-between">
                                <span className="truncate w-40">{s.filename}</span>
                                <span className="font-bold text-red-500">{s.contribution_percent}%</span>
                             </div>
                          ))}
                          {analysis.sources.length === 0 && <p className="text-xs text-gray-400">No external sources detected.</p>}
                       </div>
                       <div className="bg-blue-50 p-4 rounded border border-blue-200 text-sm text-blue-800">
                          <div className="flex gap-2 items-center mb-1"><IconAlert /> Tip:</div>
                          Click on any highlighted text in the document to see exactly where it was found.
                       </div>
                    </div>
                 )}
              </div>
           </div>
        )}

      </main>
    </div>
  );
}


// ### Step 3: What if it's STILL not highlighting?
// If the document shows up (it's not blank anymore), but everything is **white** (no Red/Orange highlights):

// It means your API is saying everything is **100% Original**. You need to loosen the strictness of the detector.

// 1.  Open `api.py`.
// 2.  Change `SEQUENCE_THRESHOLD` from `0.70` to **`0.10`** (just for testing).
// 3.  Restart python (`Ctrl+C` then `python api.py`).
// 4.  Re-upload the file.

// If it turns Red now, we know the frontend is working perfectly, and we just need to tune the backend numbers.