import os
import sys
from ollama_local_reviewer.github_client import activate_agents
import argparse



def main():
    parser = argparse.ArgumentParser(description="Driver script to run evaluator")
    parser.add_argument("-m", "--model", type=str, help="Model choice")
    parser.add_argument("-p", "--parameters", type=dict, help="Model Parameters")

    args = parser.parse_args()
    model = args.model
    params = args.parameters
    activate_agents(model,params)



if __name__ == "__main__":
    main()