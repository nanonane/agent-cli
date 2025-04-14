# AI Agent CLI

This project is a simple command-line LLM agent.

## Installation

To install the required dependencies, run:

```
pip install -r requirements.txt
```

## Usage

To start the AI agent, run the following command in your terminal:

```
python ag.py
```

To run it with `ag` command, add the following line in your `~/.zshrc` (or `~/.bashrc`):

```bash
alias ag='/path/to/agent-cli/start.sh'
```

then run

```bash
source ~/.zshrc
ag
```

You can then enter queries to interact with the AI services. The agent will process your input and return the appropriate responses.
