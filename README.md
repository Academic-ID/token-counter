# Simple token counter

A simple server with two API endpoints. Performs two functions:

1. to count tokens in strings or chat completion objects; and,
2. limit the length of strings/chat completion objects to fit under a given
   token count (e.g. for keeping strings under the embeddings max length,
   ensuring chat completion message history is under max token length, or
   counting usage tokens for streaming chat completions).

The logic is contained within the `token_service.py` file if you are just after
the functionality.

## Endpoints:

`/tokens` takes text and a number. The number is the max tokens you want the
string to be. For exmple, if you are using the OpenAI/Azure OpenAI service for
embeddings, you can make a call with the string

```JSON
 { "text": "the string to be counted", "number": 8192 }
```

---

`/chat_tokens` takes an array of chat message history objects as per the
OpenAI/Azure OpenAI service chat message. It will count image tokens as part of
the request, as well as function_call messages and all other message and content
types currently supported by the OpenAI specification.

The request will take the below and return a list of the chatMessages that fit
within the `numberOfMaxTokens` that you specified. It will also return the final
`token_count` of the messages.

```JSON
{ "messages": listOfOpenAIChatMessages, "number": numberOfMaxTokens }
```

---

## How to Use / API Key

To get this code up and running, simply clone this repository and run:

```python
pip install -r requirements.txt
```

Then run the server with (update the port as necessary):

```python
uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Key (optional)

The code is set up to handle basic API key auth. All you need to do is set the
`API-KEY` environmental variable with a key and pass this value when calling the
API by setting the `X-Api-Key` header to the `API-KEY` value.

## Notes:

1. This is currently only set up to count `cl100k_base` encoding which is used
   in the following models:

```
gpt-4, gpt-3.5-turbo, text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
```

2. This has undergone preliminary testing and seems to be correct. **However,**
   it is not entirely certain how tokens are counted by OpenAI/Azure's OpenAI
   service. The best starting point is the code in the
   [OpenAI Cookbook](https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb).
   Testing with the addition of images and function_call message types etc., has
   involved repeated calls with varying lengths and comparing this to the
   returned token usage numbers returned by calling the OpenAI/Azure OpenAI
   service endpoints. While unlikely, how tokens are counted and as a result how
   you are charged may change. As such, it is recommended to test thoroughly
   before using in your own applications and regularly updating the code as
   needed.
