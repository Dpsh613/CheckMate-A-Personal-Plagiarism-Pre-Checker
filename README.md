# ♟️ CheckMate: A Personal Plagiarism Pre-Checker

**CheckMate** is a small, locally-hosted utility app built as a student project. It acts as a "pre-checker" for students and writers to run their drafts against a personal, curated database of sources before making a final submission to official tools like Turnitin.

### 💡 Why I Built This
When writing a paper, students often download dozens of PDFs (from ArXiv or textbooks). It's easy to accidentally patch-write or forget to paraphrase properly. 

However, you can't submit an unfinished draft to Turnitin just to check it. CheckMate solves this: it lets you build a **mini, private database** of your specific reference materials, and scans your draft against *only those files*. Best of all, because it runs locally on your computer, your unpublished draft stays completely private.

---

## ✨ What It Does

* 🔒 **100% Private & Local:** Your draft never leaves your computer. All processing happens on your own hardware.
* 📚 **Personal Knowledge Base:** You control the database. Upload local PDFs or search and import papers directly from the ArXiv API.
* 🧠 **Smart Matching:** Uses an AI vector model (`sentence-transformers`) to find similar paragraphs, then uses mathematical N-Gram overlap to highlight the exact copied words.
* ✂️ **Cleans Academic Text:** Automatically ignores citations (like `[1]`) and math formulas so you don't get penalized for standard academic formatting.

---

## 🛠️ How It Was Built (Tech Stack)

As a student project, I wanted to learn how to combine modern web development with local AI models:

* **Frontend:** React.js (Vite) + Tailwind CSS
* **Backend:** FastAPI (Python)
* **AI & Search:** `ChromaDB` (Vector Database) + `sentence-transformers` (MiniLM)
* **File Processing:** `pdfplumber` (with custom logic to crop out PDF headers/footers)

---

## 🚀 How to Run It Locally

Since this app runs AI models directly on your machine, it requires about 1GB of RAM and Python installed on your computer.

### 1. Start the Backend
Clone the repository and Install the Python libraries:
```bash
git clone https://github.com/yourusername/checkmate.git
cd checkmate
pip install -r requirements.txt

Run the FastAPI server:
```bash
python api.py

### 2. Start the Frontend
Open a new terminal window, go to the i folder, and start the React app:
```bash
cd ui
npm install
npm run dev

### 3. Open localhost in your Chrome Browser
Open http://localhost:5173 in your browser.
