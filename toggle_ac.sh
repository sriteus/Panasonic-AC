#!/bin/bash
# Toggle AC script for Siri Shortcut

CMD=$1
if [ -z "$CMD" ]; then
    CMD="on"
fi

cd /Users/sarthak/Desktop/mirale
./venv/bin/python ac_control.py "$CMD"
