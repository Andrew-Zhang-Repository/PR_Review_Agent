import os
import sys
#from ollama_local_reviewer.github_client import activate_agents
import argparse
import chromadb
from chromadb.utils import embedding_functions
import yaml
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
import subprocess

current_dir = Path(__file__).parent
root_dir = current_dir.parent 
file_path = root_dir / ".gitignore"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "providers.yml")
with open(CONFIG_PATH, "r") as file:
    config = yaml.safe_load(file)


ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url=config["EMBEDDED_URL"],
    model_name=config["EMBED_MODEL"]
)


def load_gitignore(gitignore_path=file_path):

    if not os.path.exists(gitignore_path):
        return PathSpec.from_lines(GitWildMatchPattern, [])
    
    with open(gitignore_path, "r", encoding="utf-8") as file:
        lines = file.read().splitlines()
        
    return lines


client = chromadb.PersistentClient(path="./.chroma")
collection = client.get_or_create_collection(name="codebase", embedding_function=ollama_ef)

import os
import chromadb

def is_text_file(filepath, blocksize=512):
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(blocksize)
            if b'\0' in chunk:
                return False
            return True
    except Exception:
        return False



def get_git_root():
    try:
        root = subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'], 
            text=True, 
            stderr=subprocess.DEVNULL
        ).strip()
        return root
    except subprocess.CalledProcessError:
        return "."
    
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

"""def main():
    parser = argparse.ArgumentParser(description="Driver script to run evaluator")
    parser.add_argument("-m", "--model", type=str, help="Model choice")
    parser.add_argument("-p", "--parameters", type=dict, help="Model Parameters")

    args = parser.parse_args()
    model = args.model
    params = args.parameters
    activate_agents(model,params)



if __name__ == "__main__":
    main()
"""
index_codebase()
