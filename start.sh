#!/bin/bash
export AG_PATH=$(dirname "$(realpath "$0")")
source "$AG_PATH/venv/bin/activate"
python "$AG_PATH/ag.py" "$@"
