import chromadb

# CONFIG
DB_PATH = "./my_plagiarism_db"
COLLECTION_NAME = "condensed_matter"
FILE_TO_REMOVE = "wrong_book_v1.pdf"  # <--- Put the exact filename here

def remove_file():
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    # Delete entries where metadata 'source' matches the filename
    collection.delete(
        where={"source": FILE_TO_REMOVE}
    )
    
    print(f"Removed all entries for {FILE_TO_REMOVE} from database.")

if __name__ == "__main__":
    remove_file()
