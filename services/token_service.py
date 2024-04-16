from fastapi import HTTPException
from models import TokenRequest, ChatTokenRequest, TokenResponse, ChatTokenResponse, ChatMessage
import tiktoken
import math
import re
import base64
from PIL import Image
from io import BytesIO
import requests


async def handle_token_request(token_request: TokenRequest):
    try:
        encoding = tiktoken.encoding_for_model(token_request.model)
    except KeyError:    
        encoding = tiktoken.get_encoding("cl100k_base")
    
    try:
        text = token_request.text
        tokens = encoding.encode(text)

        max_tokens = token_request.number                
                
        # Reduce tokens to meet the max token requirement
        if len(tokens) > max_tokens:
            tokens = tokens[:max_tokens]  # Truncate the tokens to the max_tokens length
            text = encoding.decode(tokens)   # Join tokens back to text
        
        return TokenResponse(text=text, token_count=len(tokens))
        
    except ValueError as ve:
        # Raise HTTPException for client errors (400-level)
        raise HTTPException(
            status_code=400,
            detail={'error': f'An error occurred processing your request: {str(ve)}'}
        )
        
    except Exception as e:
        # Raise HTTPException for server errors (500-level)
        raise HTTPException(
            status_code=500,
            detail={'error': f'An error occurred processing your request: {str(e)}'}
        )

# Calculate total num_tokens
def calculate_tokens(messages, model="gpt-4"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    # We only use gpt-4 so for now, these are the only tokens we need to consider (https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb)
    tokens_per_message = 3
    tokens_per_name = 1
    
    num_tokens = 3 # every reply is primed with <|start|>assistant<|message|> (https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb)
    for message in messages:
        message_dict = message.model_dump()
        num_tokens += tokens_per_message
        for key, value in message_dict.items():                
            if key != 'id' and value is not None:
                if key == "role":
                    # for function roles messages (where 'key' = 'role' and 'value' = 'function), we need to subtract 2 tokens (again, who knows why)
                    if value == "function": 
                        num_tokens -= 2
                    num_tokens += len(encoding.encode(value))
                elif key == "name":
                    num_tokens += tokens_per_name
                    num_tokens += len(encoding.encode(value))
                elif key == "function_call":
                    # Handle function call                                                
                    num_tokens += 4 # this is correct number to add for function_calls
                    for func_key, func_value in value.items():                                
                        num_tokens += len(encoding.encode(func_value))
                        num_tokens += len(encoding.encode(func_key))   
                elif key == "content":
                    if isinstance(value, str):
                        num_tokens += len(encoding.encode(value))    
                    # images
                    elif isinstance(value, list):                                
                        for item in value:                                    
                            if item["type"] == "text":
                                num_tokens += len(encoding.encode(item["text"]))
                            elif item["type"] == "image_url":                                       
                                num_tokens += calculate_image_token_cost(item["image_url"]["url"], item["image_url"]["detail"])
    return num_tokens

async def handle_chat_token_request(chat_token_request: ChatTokenRequest):    
    messages = chat_token_request.messages
    max_tokens = chat_token_request.number
    model = chat_token_request.model
   
    try:        
        total_tokens = calculate_tokens(messages, model)
        # Variable to track if a message has been removed
        message_removed = False

        # Remove the first 'assistant' message if total_tokens exceeds max_tokens
        while total_tokens > max_tokens:
            for i, message in enumerate(messages):
                if message.role == 'assistant':  # Corrected access to 'role'
                    del messages[i]
                    message_removed = True
                    total_tokens = calculate_tokens(messages, model)
        
        # Function to remove tokens from the last user message content
        def trim_user_message_content(messages):
            nonlocal total_tokens
            
            for i in range(len(messages) - 1, -1, -1):  # Iterate backwards through messages
                if messages[i].role == 'user':  # Corrected access to 'role'
                    if isinstance(messages[i].content, str):
                        user_message_content = messages[i].content.split()
                    
                    while total_tokens > max_tokens and user_message_content:
                        # Remove the first word
                        user_message_content.pop(0)
                        # Update the message content
                        messages[i]['content'] = ' '.join(user_message_content)
                        # Recalculate total tokens
                        total_tokens = calculate_tokens(messages, model)
                        
                        if total_tokens <= max_tokens:
                            break  # Stop if within the token limit
                    
                    break  # Stop after modifying the last 'user' message

        # Add a system message at the start if a message was removed
        if message_removed:
            system_message = {
                'role': 'system',
                'content': 'Some earlier messages you have sent have been removed to fit into the limited context window. You can assume you replied to these messages. You can read the surrounding messages for context as to how you responded. You do not need to mention this to the user.'
            }
            messages.insert(0, system_message)
            # Recalculate the tokens considering the added system message
            total_tokens = calculate_tokens(messages, model)
        
        # If still over max_tokens, start trimming user message content
        if total_tokens > max_tokens:
            trim_user_message_content(messages)                        
        
        messages_dict = [message.model_dump() if isinstance(message, ChatMessage) else message for message in chat_token_request.messages]
        return ChatTokenResponse(token_count = total_tokens, messages = messages_dict)

    except Exception as e:    
        print(e)        
        raise HTTPException(
            status_code=500,
            detail={'error': f'An error occurred processing your request: {str(e)}'}
        )

def get_image_dims(image):
    # Check if the image is in base64 format
    if re.match(r"data:image\/\w+;base64", image):
        image = re.sub(r"data:image\/\w+;base64,", "", image)
        image = Image.open(BytesIO(base64.b64decode(image)))
    # Check if the image is a URL
    elif re.match(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', image):
        response = requests.get(image)
        if response.status_code == 200: # Check if the request was successful
            image = Image.open(BytesIO(response.content))
        else:
            raise ValueError(f"Failed to fetch image from URL. Status code: {response.status_code}")
    else:
        raise ValueError("Image must be a base64 string or a valid URL.")
    print(f"img size: {image.size}")
    
    return image.size

def calculate_image_token_cost(image, detail="auto"):
    # Constants
    LOW_DETAIL_TOKENS = 85
    HIGH_DETAIL_TOKENS_PER_TILE = 170
    ADDITIONAL_TOKENS = 85

    if detail == "auto":
        # assume high detail for now
        detail = "high"

    if detail == "low":
        # Low detail images have a fixed cost
        return LOW_DETAIL_TOKENS
    elif detail == "high":
        # Calculate token cost for high detail images
        width, height = get_image_dims(image)
        # Check if resizing is needed to fit within a 2048 x 2048 square
        if max(width, height) > 2048:
            # Resize the image to fit within a 2048 x 2048 square
            ratio = 2048 / max(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Further scale down to 768px on the shortest side
        if min(width, height) > 768:
            ratio = 768 / min(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Calculate the number of 512px squares
        num_squares = math.ceil(width / 512) * math.ceil(height / 512)
        # Calculate the total token cost
        total_cost = num_squares * HIGH_DETAIL_TOKENS_PER_TILE + ADDITIONAL_TOKENS
        return total_cost
    else:
        # Invalid detail_option
        raise ValueError("Invalid value for detail parameter. Use 'low' or 'high'.")