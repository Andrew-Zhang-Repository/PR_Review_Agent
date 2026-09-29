import os
import sys
#from ollama_local_reviewer.github_client import activate_agents
import argparse
import chromadb
from chromadb.utils import embedding_functions
import yaml
from github_client import load_gitignore,is_text_file,get_git_root, get_current_commit, get_changed_files





BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "providers.yml")
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)


ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url=config["EMBEDDED_URL"],
    model_name=config["EMBED_MODEL"]
)

client = chromadb.PersistentClient(path="./.chroma")
collection = client.get_or_create_collection(name="codebase", embedding_function=ollama_ef)

def inspect_db():
    total = collection.count()
    

    if total == 0:
        return "No files were found"

    files = collection.get(limit=total)
    for i in range(len(files['ids'])):
        file_id = files['ids'][i]
        metadata = files['metadatas'][i]
        document = files['documents'][i]
        
        doc_preview = document[:250].replace('\n', ' ') + "..." if len(document) > 250 else document


        """
        print(f"\nFile ID (Path): {file_id}")
        print(f"Metadata:       {metadata}")
        print(f"Code Preview:   {doc_preview}")
        print("-" * 40)
        """


def index_codebase(repo_path=None):
    ignore_dirs = load_gitignore() 
    always_ignore = {'.git', '.chroma', '__pycache__'}

    if repo_path == None:
        repo_path = get_git_root()
    
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and d not in always_ignore]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            if not is_text_file(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if not content.strip():
                    continue

                collection.upsert(
                    documents=[content],
                    metadatas=[{"filepath": filepath}],
                    ids=[filepath]
                )
            except UnicodeDecodeError:
                print(f"Skipping {filepath}: Cannot decode as UTF-8")
                continue

    print("Codebase successfully indexed.")


def sync_database(collection, repo_path=None):
    if repo_path is None:
        repo_path = get_git_root()
        
    tracker_file = os.path.join("./.chroma", "last_indexed_commit.txt")
    current_commit = get_current_commit()
    
    if not os.path.exists(tracker_file):
        print(f"Initial setup: Running full codebase index from {repo_path}...")
        index_codebase(repo_path)
        
        os.makedirs("./.chroma", exist_ok=True)
        with open(tracker_file, 'w') as f:
            f.write(current_commit)
        return

    with open(tracker_file, 'r') as f:
        last_commit = f.read().strip()
        
    if last_commit == current_commit:
        return 
    
    changes = get_changed_files(last_commit, current_commit)
    
    for status, filepath in changes:
        abs_path = os.path.join(repo_path, filepath)
        
        if status.startswith('D'):
            collection.delete(ids=[abs_path])
            continue
            
        # Check if file was Modified/Added, still exists on disk, and is text
        if status.startswith(('M', 'A')) and os.path.exists(abs_path) and is_text_file(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content.strip():
                    collection.upsert(
                        documents=[content],
                        metadatas=[{"filepath": abs_path}],
                        ids=[abs_path]
                    )
            except UnicodeDecodeError:
                continue
                
    with open(tracker_file, 'w') as f:
        f.write(current_commit)