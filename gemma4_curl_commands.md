
# Command to call a tool

CURL Gemma4 running on LMStudio to call a tool

```bash
curl http://localhost:1234/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-e4b-it",
    "input": "What is the weather like in Boston MA in celcius today?",
    "tools": [
        {
            "type": "function",
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": [
                            "celsius",
                            "fahrenheit"
                        ]
                    }
                },
                "required": [
                    "location",
                    "unit"
                ]
            }
        }
    ],
    "tool_choice": "auto"
}'
```

# Simple chat curl

Simple chat curl command to interact with Gemma4 running on LMStudio

```bash
curl http://localhost:1234/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-e4b-it",
    "system_prompt": "You answer only in rhymes.",
    "input": "What is your favorite color?"
}'
```


# CURL command to call mcp connectors

Curl command to make Gemma4 run with mcp connectors

```bash
curl http://localhost:1234/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4-e4b-it",
    "input": "What is the top trending model on hugging face?",
    "integrations": [
        {
            "type": "ephemeral_mcp",
            "server_label": "huggingface",
            "server_url": "https://huggingface.co/mcp",
            "allowed_tools": [
                "model_search"
            ]
        }
    ]
}'
```