from openai import OpenAI
import json

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)

response = client.responses.create(
    model="gemma-4-e4b-it",
    input="What is the weather like in Boston MA in celsius today?",
    tools=[
        {
            "type": "function",
            "name": "get_current_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location", "unit"]
            }
        }
    ],
    tool_choice="auto"
)

# response.output is a list with one element
# ResponseFunctionToolCall(arguments='{"location":"Boston MA","unit":"celsius"}', 
# call_id='call_2451150040620008', name='get_current_weather', 
# type='function_call', id='fc_68jfh31au2gkrngpv8v7vo', namespace=None, status='completed')
print(response)