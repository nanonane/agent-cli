import argparse
import requests
import json
import sys
import os
from pathlib import Path
import subprocess


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


def get_user_input() -> str:
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


def main():
    parser = argparse.ArgumentParser(description="(LLM) AGent for everything (not really).")
    parser.add_argument("-c", "--cot", action="store_true", help="Use Chain of Thought (CoT) reasoning.")
    parser.add_argument("-q", "--query", help="Query stdin contents with argv.")
    parser.add_argument("-a", "--agent", action="store_true", help="Chat with agent (more powerful, but slower).")
    parser.add_argument("-r", "--revise", action="store_true", help="Revise the content; produces diff form.")

    args = parser.parse_args()
    # print(repr(args))

    model = reasoner_model if args.cot else chat_model
    system_prompt = "You are a helpful assistant and a computer science expert."
    messages = [{"role": "system", "content": system_prompt}]

    # chat with agent
    while True:
        print("\n💬")
        request = get_user_input()
        if request is None:
            break
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
