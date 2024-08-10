import config
import requests
import os
import json
import logging
import time
written_files = set()
tools = []

def gen_tools():
    global tools
    tools = [
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "exec_python",
        #         "description": "Execute raw Python code and get the result. Return the result as a string, or an error message. DO NOT accept user input or interaction. If you do not want to execute, PLEASE USE write_file instead.",
        #         "parameters": {
        #                     "type": "object",
        #             "properties": {
        #                 "code": {
        #                     "type": "string",
        #                     "description": "The raw Python code to be executed. DO NOT USE ```."
        #                 }
        #             }
        #         },
        #         "required": [
        #             "code"
        #         ]
        #     }
        # },
        {
                "name": "exec_python_file",
                "description": "Execute a Python file and get the result. Cannot detect bugs. Be sure to review the code first. If the program requires user input, please use this function first, and then use 'input' function to pass your input.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename of the Python file to be executed."
                        }
                    }
            }
        },
        {
                "name": "input",
                "description": "Input a string to the running Python code. Only available after exec_python_file is called.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The string to be input."
                        }
                    }
                }
        },
        {
                "name": "read_file",
                "description": "Read the content of a file. Return file content and file hash. Existing files:\n"+str(written_files)+"\nTo modify a file, please first read it, then write it(using the same hash)." if written_files else "No existing files are available. Please write a file first.",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename to be read."
                        }
                    }
                },
                "required": [
                    "filename"
                ]
        },
        {
                "name": "write_file",
                "description": f"Write raw content to a file. If the file exists, only overwrite when overwrite = True and hash value (get it from read_file) is correct. Existing files: {written_files} Do not include ``` in the content. You can only write to your own TODO list.",
                "parameters": {
                            "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "The filename to be written."
                        },
                        "content": {
                            "type": "string",
                            "description": r"The content to be written. Use \n instead of \\n for a new line."
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "Optional. Whether to overwrite the file if it exists. Default is False. If True, base_commit_hash is required."
                        },
                        "base_commit_hash": {
                            "type": "string",
                            "description": "Optional. The hash value of the file to be modified(get it from read_file). Required when overwrite = True."
                        }
                    }
                },
                "required": [
                    "filename",
                    "content"
                ]
        }
    ]


def _get_llm_response(messages):
    api_key = config.api_key
    url = config.url
    headers = {'Content-Type': 'application/json',
            'Authorization':f'Bearer {api_key}'}
    gen_tools()
    body = {
        'model': config.model,
        "messages": messages,
        "temperature": 0,
        # "parameters": {
        #     "result_format": "message",
        "functions": tools
        # }
    }
    try:
        response = requests.post(url, headers=headers, json=body)
        # print(response.content)
        return response.json()
    except Exception as e:
        return {'error': e}

def get_llm_response(messages):
    response = _get_llm_response(messages)
    while 'choices' not in response:
        logging.error(response)
        # time.sleep(3)
        response = _get_llm_response(messages)
    return response
    