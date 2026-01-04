import re
import unicodedata
import pdfplumber
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except:
    import os
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def normalize_text(text):
    if not text: return ""
    text = unicodedata.normalize('NFKD', text)
    
    # 1. Remove Brackets/Citations [1], (Ref 2)
    text = re.sub(r'\[\d+(?:-\d+)?\]', '', text) 
    text = re.sub(r'\(\w+ et al\., \d{4}\)', '', text)
    
    # 2. Fix Chemical Formulas (Li 3 -> Li3)
    text = re.sub(r'([a-zA-Z])\s+(\d)', r'\1\2', text)

    # 3. Standard cleanup
    text = re.sub(r'-\n\s*', '', text)
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_from_pdf(pdf_path):
    pages_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                
                # --- ROBUST CROP LOGIC ---
                # Get the ACTUAL page boundaries (x0, top, x1, bottom)
                # Some PDFs don't start at (0,0)
                try:
                    bbox = page.bbox
                    x0, y0, x1, y1 = bbox
                    page_height = y1 - y0
                    
                    # Calculate margins based on ACTUAL dimensions
                    # Crop top 10% and keep up to 90% (remove bottom 10%)
                    top_crop = y0 + (page_height * 0.10)
                    bottom_crop = y0 + (page_height * 0.90)
                    
                    # Create the safe bounding box
                    # Ensure we don't go out of bounds
                    crop_rect = (x0, top_crop, x1, bottom_crop)
                    
                    # Crop the page
                    cropped_page = page.crop(bbox=crop_rect)
                    text = cropped_page.extract_text(x_tolerance=2, y_tolerance=2)
                    
                except ValueError:
                    # Fallback: If cropping fails (due to weird geometry), read the whole page
                    # It's better to have noisy text than NO text
                    # print(f"Warning: Could not crop page {i+1} of {pdf_path}. Reading full page.")
                    text = page.extract_text(x_tolerance=2, y_tolerance=2)
                except Exception as e:
                    print(f"Skipping page {i+1} due to error: {e}")
                    continue

                if text:
                    cleaned_text = normalize_text(text)
                    if len(cleaned_text) > 100: 
                        pages_data.append({
                            "page": i + 1,
                            "text": cleaned_text
                        })
                        
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    
    return pages_data

def get_sentences_from_text(pages_data):
    sentences_with_meta = []
    for entry in pages_data:
        doc = nlp(entry['text'])
        for sent in doc.sents:
            clean_sent = sent.text.strip()
            # Strict filter: Sentences must be > 30 chars
            if len(clean_sent) > 30: 
                sentences_with_meta.append({
                    "text": clean_sent,
                    "page": entry['page']
                })
    return sentences_with_meta