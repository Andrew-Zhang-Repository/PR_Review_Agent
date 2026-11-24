from ollama_local_reviewer.chroma_ops import activate_agents
import argparse





def main():
    parser = argparse.ArgumentParser(description="Driver script to run evaluator")
    parser.add_argument("-m", "--model", type=str, help="Model choice", default="gemma3:12b")
    parser.add_argument("-p", "--parameters", type=dict, help="Model Parameters")
    parser.add_argument("-a", "--agentcount", type=int, help="Agent count",default=1)

    args = parser.parse_args()
    model = args.model
    params = args.parameters
    agent_count = args.agentcount
    activate_agents(model,params,agent_count)



if __name__ == "__main__":
    main()


