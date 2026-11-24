import os
import sys
from ollama_local_reviewer.evaluator import Evaluator
import json
import chromadb
from chromadb.utils import embedding_functions
import yaml
from ollama_local_reviewer.github_client import load_gitignore,is_text_file,get_git_root, get_current_commit, get_changed_files, get_full_diff, get_codebase_context
import concurrent.futures




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

max_agents = config["MAX_CONCURRENT_AGENTS"]

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


def activate_agents(model_name,params,concurrent_count = max_agents):
    print("Starting End-to-End Evaluator Test...\n")
    git_root = get_git_root()
    sync_database(collection, repo_path=git_root)

    diff_text = get_full_diff(git_root)
    codebase_context = get_codebase_context(collection, diff_text, git_root)

    combined_payload = f"""
        ### ARCHITECTURE CONTEXT ###
        {codebase_context}

        ### CURRENT PULL REQUEST CHANGES ###
        {diff_text}
    """

    evaluator_default = Evaluator(model_name, params)
    all_agents = evaluator_default.template_manager.get_available_sections()

    target_agents = [a for a in all_agents if a not in ("base_review", "synthesize")]
    
    collected_reports = {}
    has_fatal_block = False

    def run_single_agent(agent_name):
        try:
            raw_response = evaluator_default.run_review(
                agent_name=agent_name, 
                diff_content=combined_payload
            )
            
            if hasattr(raw_response, 'message'):
                json_string = raw_response.message.content
            else:
                json_string = raw_response
          
            parsed = json.loads(json_string)
            return agent_name, parsed, None
        except json.JSONDecodeError:
            return agent_name, None, "Failed to return valid JSON."
        except Exception as e:
            return agent_name, None, str(e)

    active_workers = min(concurrent_count, len(target_agents))
    print(f"Evaluating {len(target_agents)} agents using {active_workers} concurrent threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=active_workers) as executor:

        future_to_agent = {executor.submit(run_single_agent, agent): agent for agent in target_agents}
        for future in concurrent.futures.as_completed(future_to_agent):
            agent_name, parsed_json, error = future.result()
            
            if error:
                print(f"{agent_name.capitalize()} Agent failed: {error}")
            else:
                collected_reports[agent_name] = parsed_json
                if parsed_json.get("fatal_blocks") is True:
                    has_fatal_block = True
                print(f"{agent_name.capitalize()} finished. Score: {parsed_json.get('score')}/100")

    print("\nStitching agent reports together...\n")
    
    aggregated_json_string = json.dumps(collected_reports, indent=2)


    try:
        final_review = evaluator_default.run_review(
            agent_name="synthesize", 
            diff_content=aggregated_json_string
        )

        if hasattr(final_review, 'message'):
            json_string = final_review.message.content
            synthesizer = json.loads(json_string)
            final_markdown_review = synthesizer.get("markdown_comment", "Error: AI did not provide a 'markdown_comment' key.")
       
        write_path = os.path.join(os.getcwd(), "markdown_output.md")
        with open(write_path, "w", encoding="utf-8") as file:
            file.write(final_markdown_review)

        print("==========================================")
        print("FINAL SYNTHESIZED PR COMMENT")
        print("==========================================")
        print(final_markdown_review)
        print("==========================================")
        
        if has_fatal_block:
            print("\nCOMMIT BLOCKED: A fatal security or architecture flaw was detected.")
            sys.exit(1)
        else:
            print("\nCOMMIT APPROVED.")
            sys.exit(0)
            
    except Exception as e:
        print(f"Synthesizer failed: {e}")

