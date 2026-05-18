from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")


# model_name="gemma-4-e4b-it"
model_name = "local-model"
completion = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": "say gaff 10 times"}],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "say_gaff",
                "description": "prints word gaff specified number of times",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number_of_times": {
                            "type": "int",
                            "description": "number of times to print gaff",
                        }
                    },
                    "required": ["number_of_times"],
                },
            },
        },
    ],
    tool_choice="auto",
)

output_message = completion.choices[0].message
tool_calls = output_message.tool_calls
one_tool_call = tool_calls[0]
called_function = one_tool_call.function
function_name = called_function.name
function_arguments = called_function.arguments
print(f"Number of tool calls : {len(tool_calls)}\ntool call : {one_tool_call}")
print(
    f"Called function name : {function_name}\nFunction arguments : \n{function_arguments}"
)
