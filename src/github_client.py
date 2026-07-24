import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
from src.evaluator import Evaluator


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

def main():
    print("Starting End-to-End Evaluator Test...\n")
    
    mock_git_diff = get_real_git_diff()

    try:
        evaluator_default = Evaluator()
        result_1 = evaluator_default.run_review(agent_name="code_smells_and_metrics", diff_content=mock_git_diff)
        print(f"Result:\n{result_1}\n")
    except Exception as e:
        print(f"Default Evaluator failed: {e}")


print(main())