from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="not-needed")

completion = client.chat.completions.create(
    model="local-model",
    messages=[
        {"role": "system", "content": "Always answer in rhymes"},
        {"role": "user", "content": "Introduce yourself"},
    ],
    temperature=0.7,
)

output_message_role = completion.choices[0].message.role
output_message_content = completion.choices[0].message.content
print(f"Output role : {output_message_role}\nMessage content:\n{output_message_content}")
