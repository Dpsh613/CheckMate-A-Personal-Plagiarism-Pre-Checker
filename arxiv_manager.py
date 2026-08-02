import hashlib
import os
import tempfile
from urllib.parse import urlsplit

import arxiv
import requests


DATASET_FOLDER = "dataset_pdfs"
MAX_ARXIV_DOWNLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_ARXIV_HOSTS = {"arxiv.org", "export.arxiv.org"}
os.makedirs(DATASET_FOLDER, exist_ok=True)


def search_arxiv_metadata(topic: str, max_results: int = 10):
    client = arxiv.Client()
    search = arxiv.Search(query=topic, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    return [
        {
            "title": result.title,
            "authors": [author.name for author in result.authors],
            "published": result.published.strftime("%Y-%m-%d"),
            "summary": result.summary[:200] + "...",
            "pdf_url": result.pdf_url,
        }
        for result in client.results(search)
    ]


def _is_valid_arxiv_pdf_url(pdf_url: str) -> bool:
    parsed = urlsplit(pdf_url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in ALLOWED_ARXIV_HOSTS
        and parsed.port is None
        and parsed.path.startswith("/pdf/")
    )


def download_specific_arxiv_paper(pdf_url: str, title: str, db_manager_add_func):
    """Download a bounded PDF from arXiv, index it, and always remove the temporary file."""
    if not _is_valid_arxiv_pdf_url(pdf_url):
        return False, "Invalid arXiv PDF URL."

    # Do not use a supplied title as a filesystem name. A stable URL-derived name
    # avoids traversal, filename-length issues, and concurrent-request collisions.
    filename = f"arxiv_{hashlib.sha256(pdf_url.encode('utf-8')).hexdigest()[:24]}.pdf"
    file_path = None
    try:
        with requests.get(
            pdf_url,
            headers={"User-Agent": "CheckMate/1.0"},
            stream=True,
            timeout=(5, 30),
            allow_redirects=False,
        ) as response:
            if response.status_code != 200:
                return False, "arXiv did not return the requested PDF."
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type:
                return False, "arXiv returned an unexpected file type."

            with tempfile.NamedTemporaryFile(mode="xb", suffix=".pdf", prefix="arxiv_", dir=DATASET_FOLDER, delete=False) as output:
                file_path = output.name
                total_size = 0
                first_chunk = b""
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    if not first_chunk:
                        first_chunk = chunk
                    total_size += len(chunk)
                    if total_size > MAX_ARXIV_DOWNLOAD_BYTES:
                        return False, "arXiv PDF exceeds the 10MB limit."
                    output.write(chunk)

        if not first_chunk.startswith(b"%PDF-"):
            return False, "arXiv returned an invalid PDF."
        return db_manager_add_func(file_path, filename)
    except requests.RequestException:
        return False, "Unable to download the arXiv PDF right now."
    except OSError:
        return False, "Unable to store the arXiv PDF temporarily."
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
