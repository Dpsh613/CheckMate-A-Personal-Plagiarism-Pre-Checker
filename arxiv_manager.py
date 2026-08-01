import os
import arxiv
import requests

DATASET_FOLDER = "dataset_pdfs"
os.makedirs(DATASET_FOLDER, exist_ok=True)

def search_arxiv_metadata(topic: str, max_results: int = 10):
    """Step 1: Just get the data, DO NOT download the PDF."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    
    results = []
    for result in client.results(search):
        results.append({
            "title": result.title,
            "authors": [a.name for a in result.authors],
            "published": result.published.strftime("%Y-%m-%d"),
            "summary": result.summary[:200] + "...",
            "pdf_url": result.pdf_url
        })
    return results

def download_specific_arxiv_paper(pdf_url: str, title: str, db_manager_add_func):
    """Step 2: Download, Index, and DELETE the PDF to save space."""
    if not pdf_url.startswith(("http://arxiv.org/", "https://arxiv.org/")):
        return False, "Invalid URL. Only arxiv.org URLs are allowed."
        
    safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    filename = f"arxiv_{safe_title.replace(' ', '_')}.pdf"
    file_path = os.path.join(DATASET_FOLDER, filename)

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(pdf_url, headers=headers)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Index it into the database
            success, msg = db_manager_add_func(file_path, filename)
            
            # CRITICAL: Delete PDF after indexing to save hardware storage!
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return success, msg
        return False, f"HTTP Error {response.status_code}"
    except Exception as e:
        return False, str(e)