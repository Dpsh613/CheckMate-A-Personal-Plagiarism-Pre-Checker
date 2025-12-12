import fitz  # PyMuPDF
import re
import unicodedata

# --- TEXT CLEANING ---
def clean_and_fix_text(text):
    """
    Applies the 'Enhanced' logic:
    1. Fixes Ligatures (unicode normalization).
    2. Joins hyphenated words broken by newlines.
    3. Removes standard newlines and cleans whitespace.
    """
    if not text:
        return ""

    # 1. Fix "Ligatures" (e.g., turns "ﬁ" into "fi")
    text = unicodedata.normalize('NFKD', text)

    # 2. Join hyphenated words (e.g., "incre-\ndible" -> "incredible")
    text = re.sub(r'-\n\s*', '', text)

    # 3. Remove newlines within paragraphs (replace with space)
    text = text.replace('\n', ' ')

    # 4. Collapse multiple spaces into one
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# --- MAIN EXTRACTION FUNCTION  ---
def extract_text_with_metadata(pdf_path):
    """
    Opens a PDF and extracts text page by page.
    NEW FEATURE: Ignores the top 5% and bottom 5% of the page 
    to remove Headers, Footers, and Page Numbers.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF {pdf_path}: {e}")
        return []

    pages_data = []

    for page_num, page in enumerate(doc):
        # 1. Get Page Dimensions
        page_height = page.rect.height
        
        # 2. Define Exclusion Zones (The "Turnitin" Logic)
        # We ignore the top 5% (headers) and bottom 8% (footers/page numbers)
        # Note: Bottom is often larger due to copyright disclaimers.
        header_cutoff = page_height * 0.05 
        footer_cutoff = page_height * 0.92 

        # sort=True ensures we read columns properly
        blocks = page.get_text("blocks", sort=True)
        page_text_pieces = []

        for b in blocks:
            # Block structure in PyMuPDF: 
            # (x0, y0, x1, y1, text, block_no, block_type)
            # y0 = Top of the block, y1 = Bottom of the block
            y0 = b[1]
            y1 = b[3]
            block_text = b[4]

            # --- HEADER/FOOTER FILTERING ---
            # If the block is entirely inside the top 5%, Skip it.
            if y1 < header_cutoff:
                continue
            
            # If the block starts inside the bottom 8%, Skip it.
            if y0 > footer_cutoff:
                continue
            # -------------------------------

            # Apply the cleaning logic to this specific block
            cleaned_block = clean_and_fix_text(block_text)

            # Filter out tiny artifacts
            if len(cleaned_block) > 3:
                page_text_pieces.append(cleaned_block)

        # Join all blocks on this page into one big string
        full_page_text = ' '.join(page_text_pieces)
        
        # Only add the page if it actually has text
        if len(full_page_text) > 50: 
            pages_data.append({
                "page": page_num + 1, 
                "text": full_page_text
            })
            
    return pages_data

# --- CHUNKING FUNCTION  ---
def chunk_text_with_page_mapping(pages_data, chunk_size=100, overlap=25):
    """
    Splits text into sliding windows but keeps track of the page number.
    """
    chunks_with_meta = []
    
    for page_entry in pages_data:
        text = page_entry['text']
        page_num = page_entry['page']
        
        # Split by whitespace to get words
        words = text.split()
        
        # Create sliding windows
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Only keep chunks that are substantial enough
            if len(chunk_words) > 25:
                chunks_with_meta.append({
                    "text": chunk_text,
                    "page": page_num
                })
            
    return chunks_with_meta
