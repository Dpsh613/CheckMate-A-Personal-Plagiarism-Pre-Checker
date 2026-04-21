import re
import unicodedata
import pdfplumber

def normalize_text(text):
    if not text: return ""
    text = unicodedata.normalize('NFKD', text)
    
    # Remove citations [1], (Smith, 2020)
    text = re.sub(r'\[\d+(?:-\d+)?\]', '', text) 
    text = re.sub(r'\([A-Za-z]+(?: et al\.)?, \d{4}\)', '', text)
    
    # Strip standalone heavy math garble (heuristic: lines with lots of equals, slashes, greek)
    text = re.sub(r'(?m)^.*[\=\+\\\/∑∞∫π].*$', '', text)

    # Standard cleanup
    text = re.sub(r'-\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_from_pdf(pdf_path):
    pages_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    # Crop out headers/footers (top 10%, bottom 10%)
                    bbox = page.bbox
                    x0, y0, x1, y1 = bbox
                    page_height = y1 - y0
                    crop_rect = (x0, y0 + (page_height * 0.10), x1, y0 + (page_height * 0.90))
                    cropped_page = page.crop(bbox=crop_rect)
                    text = cropped_page.extract_text(x_tolerance=2, y_tolerance=2)
                except:
                    text = page.extract_text()

                if text:
                    cleaned_text = normalize_text(text)
                    if len(cleaned_text) > 50: 
                        pages_data.append({"page": i + 1, "text": cleaned_text})
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return pages_data

def get_sliding_windows(pages_data, window_size=40, overlap=15):
    """
    Industry standard: break text into overlapping chunks of words.
    Much safer than relying on periods (which math formulas ruin).
    """
    chunks_with_meta = []
    for entry in pages_data:
        words = entry['text'].split()
        if not words: continue
        
        for i in range(0, len(words), window_size - overlap):
            chunk = " ".join(words[i:i + window_size])
            if len(chunk) > 30: # Ignore tiny fragments
                chunks_with_meta.append({
                    "text": chunk,
                    "page": entry['page']
                })
    return chunks_with_meta