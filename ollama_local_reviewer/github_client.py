import os
import sys
import json
import requests
import subprocess
from ollama_local_reviewer.evaluator import Evaluator
from typing import List, Dict

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

def activate_agents(model_name,params):
    print("Starting End-to-End Evaluator Test...\n")
    
    git_diff = get_real_git_diff()

    evaluator_default = Evaluator(model_name,params)
    agents = evaluator_default.template_manager.get_available_sections()
    collected_reports = {}
    has_fatal_block = False
    
    for i in agents:

        if i == "base_review" or i == "synthesize":
            continue 

        try:
            raw_response = evaluator_default.run_review(agent_name=i, diff_content=git_diff)
            if hasattr(raw_response, 'message'):
                json_string = raw_response.message.content
            else:
                json_string = raw_response
          
            parsed_json = json.loads(json_string)
            collected_reports[i] = parsed_json
    
            if parsed_json.get("fatal_blocks") is True:
                has_fatal_block = True
            print(f"{i.capitalize()} finished. Score: {parsed_json.get('score')}/100")
        except json.JSONDecodeError:
            print(f"{i.capitalize()} Agent failed to return valid JSON. Skipping.")
        except Exception as e:
            print(f"{i.capitalize()} Agent failed: {e}")

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
       
        # write to path of markdown
        write_path = os.path.join(os.getcwd(),"markdown_output.md")
        with open(write_path, "w", encoding="utf-8") as file:
            file.write(final_markdown_review)

        print("==========================================")
        print("FINAL SYNTHESIZED PR COMMENT")
        print("==========================================")
        print(final_markdown_review)
        print("==========================================")
        
        if has_fatal_block:
            print("\nCOMMIT BLOCKED: A fatal security or architecture flaw was detected or error reading responses from agents.")
            sys.exit(1)
        else:
            print("\nCOMMIT APPROVED.")
            sys.exit(0)
            
    except Exception as e:
        print(f"Synthesizer failed: {e}")



    
