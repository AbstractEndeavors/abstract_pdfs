[
    {
        "prompt": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "assistant",
                    "content": "\n-----------------------------------------------------------------------------\n#instructions#\n\nYour response is expected to be in JSON format, with boolean responses as lowercase unquoted values (true/false), using the following keys:\n\n0) api_response - \"\"\"{'instruction': 'Place response to prompt here.', 'example': 'This is the reply to your request.', 'default': True}\"\"\"\n1) generate_title - \"\"\"{'instruction': 'Generate a short and concise title for this query, using underscores instead of spaces and avoiding special characters. The title should not exceed 200 characters to ensure compatibility with file systems.', 'example': 'Short_Title_for_Query', 'default': True}\"\"\"\n\nBelow is an example of the expected JSON dictionary response format, with default inputs. This response MUST be a dict:\n{\n  \"api_response\": \"This is the reply to your request.\",\n  \"generate_title\": \"Short_Title_for_Query\"\n}\n-----------------------------------------------------------------------------\n#prompt#\n\n\nWrite the **Installation** section for a README.\n\n**Context:**\n- Metadata: {'name': 'abstract_pdfs', 'version': '0.0.0.001', 'author': 'putkoff', 'author_email': 'partners@abstractendeavors.com', 'description': 'abstract_pdfs', 'long_description': '', 'long_description_content_type': 'text/markdown', 'url': 'https://github.com/AbstractEndeavors/abstract_pdfs', 'classifiers': ['Development Status :: 3 - Alpha', 'Intended Audience :: Developers', 'License :: OSI Approved :: MIT License', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.11'], 'install_requires': ['abstract_ocr', 'abstract_utilities'], 'package_dir': {'': 'src'}, 'packages': ['ast_analyzer', 'module_datas', 'imports', 'ast_analyzer.src', 'module_datas.src', 'imports.functions', 'imports.managers', 'imports.constants', 'imports.constants.prompts'], 'python_requires': '>=3.6'}\n\n**Include:**\n- Prerequisites (Python version, required system libraries like poppler-utils or tesseract).\n- Pip installation (`pip install abstract_pdfs`)\n- Installation from source (git clone and pip install).\n\nFormat all commands in Markdown code blocks.\n"
                }
            ],
            "max_tokens": 7637
        },
        "response": {
            "id": "chatcmpl-CT0DpDi0zDQYYAifwPQmZEFgrJaSj",
            "object": "chat.completion",
            "created": 1761028401,
            "model": "gpt-4-0613",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "{\n  \"api_response\": \"## Installation\n\nRequirements:\n- Python 3.6 or higher is required.\n- You also need system libraries 'poppler-utils' and 'tesseract' installed on your system.\n\nYou can install abstract_pdfs using pip:\n\n```bash\npip install abstract_pdfs\n```\n\nTo install from source, clone the repository from GitHub and install using pip:\n\n```bash\ngit clone https://github.com/AbstractEndeavors/abstract_pdfs.git\ncd abstract_pdfs\npip install .\n```\n\nPlease note, this package has dependencies on 'abstract_ocr' and 'abstract_utilities'. Make sure to have them installed before using 'abstract_pdfs'.\",\n  \n  \"generate_title\": \"Abstract_PDFs_Installation_Instructions\"\n}",
                        "refusal": null,
                        "annotations": []
                    },
                    "logprobs": null,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 466,
                "completion_tokens": 158,
                "total_tokens": 624,
                "prompt_tokens_details": {
                    "cached_tokens": 0,
                    "audio_tokens": 0
                },
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "audio_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0
                }
            },
            "service_tier": "default",
            "system_fingerprint": null,
            "file_path": "/home/computron/Documents/pythonTools/modules/src/scripts/readme_generation/response_data/raw_response/1761028401.json",
            "title": 1761028401
        },
        "file_path": "/home/computron/Documents/pythonTools/modules/src/scripts/readme_generation/response_data/2025-10-21/gpt-4-0613/Abstract_PDFs_Installation_Ins.json",
        "title": "Abstract_PDFs_Installation_Instructions",
        "model": "gpt-4-0613"
    }
]