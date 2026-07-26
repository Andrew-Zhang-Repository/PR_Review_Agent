# Ollama Reviewer

A local multi-agent code review tool that uses Ollama-hosted LLMs to analyze git diffs and produce structured PR reviews.

## How It Works

The tool runs several specialised review agents against your staged/unstaged code changes (git diff HEAD):

1. **Code Smells & Metrics** — analyses code quality, complexity, and anti-patterns
2. **Readability Review** — evaluates naming, documentation, and overall clarity
3. **Security Review** — checks for common vulnerabilities and insecure patterns
4. **Synthesizer** — stitches the individual agent reports into a single markdown PR comment

Each agent returns a JSON score out of 100. If any agent detects a fatal block (security flaw or architecture issue), the commit is blocked with exit code 1.

## Requirements

- [Ollama](https://ollama.com/) running locally with at least one model pulled
- Python 3.10+

## Setup

```bash
# Install the package
pip install -e . # for any local installs from git

# Pull a supported model or check available models at end of page (default: gemma3:12b)
ollama pull gemma3:12b
```

## Usage

Run from the root of any git repository you want to review:

```bash
ollama-review -m AVAILABLE_MODEL -p MODEL_PARAMS
```

Specify a different model:

```bash
ollama-review -m "qwen3:4b"
```

Model parameters (temperature, top_p) are configured in `providers.yml`.

## Output

- Prints each agent's score as it runs
- Writes a final synthesised markdown review to `markdown_output.md`
- Exits with code 0 on approval, code 1 if a fatal issue is found

## Available models in providers.yml, feel free to add your on
- "qwen3:1.7b":  { "temperature": 0.0, "top_p": 0.9 },
- "gemma3:1b":   { "temperature": 0.0, "top_p": 0.9 },
- "qwen3:4b":    { "temperature": 0.1, "top_p": 0.4 },
- "gemma3:4b":   { "temperature": 0.1, "top_p": 0.9 },
- "gemma3:12b":  { "temperature": 0.1, "top_p": 0.9 },
- "mistral:7b":  { "temperature": 0.1, "top_p": 0.9 }
