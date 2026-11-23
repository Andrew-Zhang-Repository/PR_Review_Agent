import os
import sys
import subprocess
from typing import List, Dict
import re


from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
import subprocess

current_dir = Path(__file__).parent
root_dir = current_dir.parent 
file_path = root_dir / ".gitignore"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_full_diff(git_root):
    try:
        diff_text = subprocess.check_output(
            ['git', 'diff', 'HEAD'], text=True, cwd=git_root
        )
    except subprocess.CalledProcessError:
        diff_text = ""

    untracked = subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard'], 
        text=True, cwd=git_root
    ).strip().split('\n')

    for file in untracked:
        if not file: continue
        abs_path = os.path.join(git_root, file)
        
        if is_text_file(abs_path):
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            diff_text += f"\n--- /dev/null\n+++ b/{file}\n"
            diff_text += "\n".join([f"+{line}" for line in content.split('\n')])
            diff_text += "\n"

    return diff_text


def is_text_file(filepath, blocksize=512):
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(blocksize)
            if b'\0' in chunk:
                return False
            return True
    except Exception:
        return False

def load_gitignore(gitignore_path=file_path):

    if not os.path.exists(gitignore_path):
        return PathSpec.from_lines(GitWildMatchPattern, [])
    
    with open(gitignore_path, "r", encoding="utf-8") as file:
        lines = file.read().splitlines()
        
    return lines

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
    
def get_current_commit():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()

def get_changed_files(old_commit, new_commit):
    output = subprocess.check_output(
        ['git', 'diff', '--name-status', old_commit, new_commit], 
        text=True
    )
    changes = []
    for line in output.strip().split('\n'):
        if line:
            status, path = line.split('\t')
            changes.append((status, path))
    return changes

def get_real_git_diff() -> str:
   
    try:
    
        result = subprocess.run(
            ['git', 'diff', 'HEAD'], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            check=True ,
            encoding="utf-8"
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Git command failed. Are you in a git repository? Error: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("it is not installed or not found in the system path.")
        sys.exit(1)









def split_diff(diff_text,git_root):

    file_diffs = {}
    chunks = re.split(r'(?=^diff --git |^--- /dev/null)', diff_text, flags=re.MULTILINE)

    for i in chunks:

        if i.strip() == False:
            continue

        match = re.search(r'^\+\+\+ b/(.+)$', i, flags=re.MULTILINE)
        if match:
            rel_path = match.group(1).strip()
            abs_path = os.path.normpath(os.path.join(git_root, rel_path))
            file_diffs[abs_path] = i


    return file_diffs

def get_codebase_context(collection, diff_text, git_root, per_file_k=2, max_total_files=3, max_distance=0.6):
    if not diff_text.strip():
        return ""

    file_diffs = split_diff(diff_text, git_root)
    if not file_diffs:
        return "No relevant context found."

    modified_paths = list(file_diffs.keys())
    query_chunks = list(file_diffs.values())

    results = collection.query(
        query_texts=query_chunks,
        n_results=per_file_k,
        where={"filepath": {"$nin": modified_paths}},
        include=["documents", "metadatas", "distances"]
    )

    best_matches = {} 
    
    for docs, metas, dists in zip(results["documents"], results["metadatas"], results["distances"]):
        for doc, meta, dist in zip(docs, metas, dists):
            if dist > max_distance:
                continue
            filepath = meta.get("filepath", "Unknown")
            if filepath not in best_matches or dist < best_matches[filepath][0]:
                best_matches[filepath] = (dist, doc)

    if not best_matches:
        return "No relevant context found."


    top_matches = sorted(best_matches.items(), key=lambda x: x[1][0])[:max_total_files]

    context_blocks = [
        f"--- START FILE: {filepath} ---\n{doc}\n--- END FILE ---"
        for filepath, (_, doc) in top_matches
    ]

    return "\n\n".join(context_blocks)

