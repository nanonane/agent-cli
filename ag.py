import argparse
import requests
import json
import sys
import os
from pathlib import Path
import subprocess
from typing import Optional
import threading
import time


# Load configuration from config.json
ag_path = os.getenv("AG_PATH", "~/agent-cli")
with open(Path(ag_path, "config.json"), "r") as file:
    config = json.load(file)

url = config["url"]  # LLM API URL
api_key = config["api_key"]  # API key
chat_model = config["chat_model"]  # name of the chat model
reasoner_model = config["reasoner_model"]  # name of the reasoning model

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}


def get_response(model: str, messages: list) -> str:
    data = {
        "model": model,
        "messages": messages,
    }

    response = requests.post(url=url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        result = response.json()
        if model == reasoner_model:
            reasoning_content = result["choices"][0]["message"]["reasoning"]
            print("\n----- Reasoning -----\n")
            print(reasoning_content)
            print("\n----- End of Reasoning -----\n")
            sys.stdout.flush()
        content = result["choices"][0]["message"]["content"]
        print(content)
        return content
    else:
        raise Exception(f"Request fail: {response.status_code} {response.text}")


def get_stream_response(model: str, messages: list):
    data = {
        "model": model,
        "messages": messages,
        "stream": True
    }

    with requests.post(url, headers=headers, data=json.dumps(data), stream=True) as response:
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code} {response.text}")

        reply = ""

        reasoning = (model == reasoner_model)
        if reasoning:
            print("\n----- Reasoning -----\n")
            sys.stdout.flush()

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8").lstrip("data: ")
                if line.strip() == "[DONE]":
                    break
                try:
                    delta = json.loads(line)["choices"][0]["delta"]
                    if reasoning and delta.get("reasoning"):
                        reasoning_content = delta.get("reasoning")
                        sys.stdout.write(reasoning_content)
                        sys.stdout.flush()
                        continue

                    content = delta.get("content", "")
                    if reasoning and content:  # start of answer content
                        reasoning = False
                        print('\n----- End of Reasoning -----\n')
                        sys.stdout.flush()
                    sys.stdout.write(content)
                    sys.stdout.flush()
                    reply += content
                except Exception:  # in case content is None
                    continue
        return reply


def get_user_input() -> Optional[str]:
    """
    Get user input from stdin until one empty line are entered.
    """
    buffer, empty_count = [], 0
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            buffer.append(line)
        except EOFError:
            return None

    request = "\n".join(buffer).strip()
    if not request:
        print("No input provided.")
        return None
    return request


def execute_shell_command(command: str) -> Optional[str]:
    """
    Execute a shell command in zsh and return the output.
    """
    try:
        # Remove the leading '!' from the command
        cmd = command[1:].strip()
        if not cmd:
            print("Error: Empty command")
            return None
        
        # Execute the command in zsh
        result = subprocess.run(
            cmd,
            shell=True,
            executable="/bin/zsh",
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        output = f"Command: {cmd}\n"
        output += f"Exit code: {result.returncode}\n"
        
        if result.stdout:
            output += f"Output:\n{result.stdout}"
        
        if result.stderr:
            output += f"Error:\n{result.stderr}"
            
        return output
        
    except subprocess.TimeoutExpired:
        print(f"Error: Command '{cmd}' timed out after 30 seconds")
        return None
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        return None


def main():
    parser = argparse.ArgumentParser(description="(LLM) AGent for everything (not really).")
    parser.add_argument("-c", "--cot", action="store_true", help="Use Chain of Thought (CoT) reasoning.")
    parser.add_argument("-q", "--query", help="Query stdin contents with argv.")
    parser.add_argument("-a", "--agent", action="store_true", help="Chat with agent (more powerful, but slower).")
    parser.add_argument("-r", "--revise", action="store_true", help="Revise the content; produces diff form.")
    parser.add_argument("-g", "--grep", action="store_true", help="Grep for specific content from stdin.")

    args = parser.parse_args()
    # print(repr(args))

    model = reasoner_model if args.cot else chat_model
    system_prompt = "You are a helpful assistant and a computer science expert. Please always respond in Chinese."
    messages = [{"role": "system", "content": system_prompt}]

    # chat with agent
    while True:
        print("\n💬")
        request = get_user_input()
        if request is None:
            break

        # Check if the request starts with '!' (shell command)
        if request.startswith('!'):
            print(f"🔧 Executing shell command: {request}")
            command_output = execute_shell_command(request)
            if command_output is None:
                continue
            print(command_output)
            
            # Add the command and its output to the conversation context
            messages.append({"role": "user", "content": f"I executed the shell command: {request}\n\nOutput:\n{command_output}"})
            
            # Ask the user if they want to continue the conversation
            print("\n(You can now ask questions about the command output, or enter another command)")
            continue

        messages.append({"role": "user", "content": request})

        print(f"🤖 {model}")
        try:
            reply = get_stream_response(model, messages)
            print()
            messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"\nError: {e}")
            break


if __name__ == "__main__":
    main()
