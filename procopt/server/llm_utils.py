import traceback
from PIL import Image
import io
import re
import json
import litellm
import numpy as np
from openai import OpenAI
import base64
from typing import Union, List, Optional
from dotenv import load_dotenv
import os
from typing import Union, Dict
from pydantic import BaseModel
from procopt.server.utils import encode_image, remove_markdown
from procopt.server.prompt_models import TranscriptionOutputModel
load_dotenv()

IS_TEST: bool = False
SYSTEM_PROMPT: str = "You are a process optimization consultant. Your client has provided you with a process map and your job is to analyze it."
MODEL: str = "gpt-4o-mini"

def sys_prompt(additional_context: str = '') -> Dict[str, str]:
    return { 
        "role": "system",
        "content": SYSTEM_PROMPT + additional_context,
    }

def get_user_text_prompt(text: str) -> Dict[str, str]:
    return {
        "role": "user",
        "content": [
            get_text_prompt(text),
        ],
    }

def get_user_image_prompt(image_bytes_or_path: Union[str, bytes] = None, 
                      image_format: str = None) -> Dict[str, str]:
    return {
        "role": "user",
        "content": [
            get_image_prompt(image_bytes_or_path, image_format),
        ],
    }

def get_text_prompt(text: str) -> Dict[str, str]:
    return {
        "type": "text",
        "text": text,
    }

def get_image_prompt(image_bytes_or_path: Union[str, bytes] = None, 
                      image_format: str = None) -> Dict[str, str]:
    if isinstance(image_bytes_or_path, str):
        image_bytes = encode_image(image_bytes_or_path)
    else:
        image_bytes = base64.b64encode(image_bytes_or_path).decode('utf-8')
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/{image_format};base64,{image_bytes}",
        },
    }

def call_llm(messages: List[Dict[str, str]], model: str = MODEL, response_format: Optional[BaseModel] = None, **kwargs) -> Union[BaseModel, str]:
    try:
        response = litellm.completion(
            model=model,
            response_format=response_format,
            messages=messages,
            **kwargs
        )
        
        if response_format:
            return response_format(**json.loads(response.choices[0].message.content))
        return response.choices[0].message.content
    except Exception as e:
        traceback.print_exc()
        print(f"Error in call_llm: {str(e)}")
        raise e


def generate_chat_history(image_bytes: Union[str, bytes] = None, 
                          image_format: str = None, 
                          transcription: str = None, 
                          bottlenecks: str = None, 
                          improvements: str = None) -> str:
    content = []
    if isinstance(image_bytes, str):
        image_bytes = encode_image(image_bytes)
    else:
        image_bytes = base64.b64encode(image_bytes).decode('utf-8')
    content += [
        {
            "type": "text",
            "text": "Here is an image containing a process map."
        },
        {
            "type": "image_url",
            "image_url": {
                "url" : f"data:image/{image_format};base64,{image_bytes}",
            }
        }
    ]
    if transcription is not None:
        content += [
            {
                "type": "text",
                "text": f"Here is a written description of all of the steps in that process map: {transcription}"
            }
        ]
    if bottlenecks is not None:
        content += [
            {
                "type": "text",
                "text": f"Here is a list of the main bottlenecks in this process: {bottlenecks}"
            }
        ]
    if improvements is not None:
        content += [
            {
                "type": "text",
                "text": f"Here is a list of the main improvement opportunities identified for the bottlenecks of this process: {improvements}"
            }
        ]
    return content

def transcribe_process_map_from_image(**kwargs) -> str:
    """Use VLM to generate a textual version from an image of a process map"""
    if IS_TEST: return "QUICK TEST RESPONSE"
    messages = [
        sys_prompt(),
        { 
            "role": "user",
            "content": generate_chat_history(**kwargs) + [
                {
                    "type": "text",
                    "text": "Please enumerate all of the steps in the process map. If there are any decision points, include the conditions for each branch. Please provide as much detail as is included in the image. Start your answer by stating the title of the process. DO NOT include anything in your answer besides information on the process (i.e. no extraneous commentary or pleasantries). Format your answer in Markdown."
                },
            ]
        }
    ]
    response = call_llm(messages=messages, model=MODEL, response_format=TranscriptionOutputModel)
    return response

def identify_bottlenecks(**kwargs) -> str:
    """Use VLM to identify bottlenecks in a process map"""
    if IS_TEST: return "QUICK TEST RESPONSE"
    messages = [
        sys_prompt(),
        { 
            "role": "user",
            "content": generate_chat_history(**kwargs) + [
                {
                    "type": "text",
                    "text": "What are the main bottlenecks in this process? Please list 3-5 main bottlenecks and provide a brief explanation for each. Identify which step in the process that each bottleneck corresponds to. DO NOT include anything in your answer besides information on the bottlenecks of the process (i.e. no extraneous commentary or pleasantries). Format your answer in Markdown."
                }
            ]
        }
    ]
    response = call_llm(messages=messages, model=MODEL, response_format=TranscriptionOutputModel)
    return response

def generate_improvements(**kwargs) -> str:
    """Use VLM to suggest improvements to a process map"""
    if IS_TEST: return "QUICK TEST RESPONSE"
    messages = [
        { 
            "role" : "system",
            "content" : SYSTEM_PROMPT,
        },
        { 
            "role" : "user",
            "content" : generate_chat_history(**kwargs) + [
                {
                    "type": "text",
                    "text": "Given the process and the main bottlenecks identified, please suggest 3 ways to improve each bottleneck. Be creative but also realistic. Make suggestions that a skilled process optimization consultant would make. Identify which step in the process each improvement would affect. DO NOT include anything in your answer besides information on improvements for the bottlenecks (i.e. no extraneous commentary or pleasantries). Format your answer in Markdown."
                }
            ]
        }
    ]
    response = call_llm(messages=messages, model=MODEL, response_format=TranscriptionOutputModel)
    return response

def sort_improvements(**kwargs) -> str:
    """Use VLM to sort improvements to a process map"""
    if IS_TEST: return "QUICK TEST RESPONSE"
    messages = [
        { 
            "role" : "system",
            "content" : SYSTEM_PROMPT,
        },
        { 
            "role" : "user",
            "content" : generate_chat_history(**kwargs) + [
                {
                    "type": "text",
                    "text": "Given the improvements suggested, rank and sort them into the following three buckets:\n\n1. Quick wins -- improvements that can be implemented quickly and with minimal effort\n2. Medium-term wins -- improvements that require some effort and time to implement\n3. Long-term wins-- improvements that require significant effort and time to implement, but may have high payoff.\n\nBe sure to include every suggested improvement in your rankings. Identify which bottleneck and which step in the process each improvement corresponds to. DO NOT include anything in your answer besides information on improvements for the bottlenecks (i.e. no extraneous commentary or pleasantries). Format your answer in Markdown."
                }
            ]
        }
    ]
    response = call_llm(messages=messages, model=MODEL, response_format=TranscriptionOutputModel)
    return response


def process_blocks_with_sliding_window(blocks: List[Image.Image]) -> List[str]:
    """Process blocks using 2x2 grid sliding window approach"""
    results = []
    num_blocks = len(blocks)
    num_cols = int(np.ceil(np.sqrt(num_blocks)))  
    
    print(f"Processing {num_blocks} blocks in {num_cols}x{num_cols} grid")
    
    def combine_grid_blocks(grid_blocks):
        if not grid_blocks or len(grid_blocks) < 4:
            return None
            
        
        block_width = grid_blocks[0].width
        block_height = grid_blocks[0].height
        combined_image = Image.new('RGB', (block_width * 2, block_height * 2))
        
        
        positions = [
            (0, 0),      # top left
            (block_width, 0),  # top right
            (0, block_height),  # bottom left
            (block_width, block_height)  # bottom right
        ]
        
        for block, pos in zip(grid_blocks[:4], positions):
            combined_image.paste(block, pos)
            
        return combined_image
    
    
    for row in range(0, num_cols - 1, 2):
        for col in range(0, num_cols - 1, 2):
            
            indices = [
                row * num_cols + col,          
                row * num_cols + col + 1,       
                (row + 1) * num_cols + col,     
                (row + 1) * num_cols + col + 1  
            ]

            grid_blocks = [blocks[i] for i in indices if i < num_blocks]
            
            if len(grid_blocks) < 4:
                continue  # Skip incomplete grids
                
            print(f"Processing grid at row {row}, col {col}")
            combined_image = combine_grid_blocks(grid_blocks)
            
            if combined_image:
                buffer = io.BytesIO()
                combined_image.save(buffer, format="PNG")
                block_bytes = buffer.getvalue()
                
                try:
                    result = transcribe_process_map_from_image(
                        image_bytes=block_bytes,
                        image_format="png"
                    )
                    print(f"Successfully processed grid at ({row}, {col})")
                    results.append(remove_markdown(result))
                except Exception as e:
                    print(f"Error processing grid at ({row}, {col}): {str(e)}")

    remaining_blocks = []
    last_full_grid = ((num_cols - 1) // 2) * 2
    
    for row in range(last_full_grid, num_cols):
        for col in range(num_cols):
            idx = row * num_cols + col
            if idx < num_blocks:
                remaining_blocks.append(blocks[idx])
    
    if remaining_blocks:
        print(f"Processing {len(remaining_blocks)} remaining blocks")
        # Combine remaining blocks horizontally
        total_width = sum(block.width for block in remaining_blocks)
        max_height = max(block.height for block in remaining_blocks)
        combined_image = Image.new('RGB', (total_width, max_height))
        
        x_offset = 0
        for block in remaining_blocks:
            combined_image.paste(block, (x_offset, 0))
            x_offset += block.width
            
        buffer = io.BytesIO()
        combined_image.save(buffer, format="PNG")
        block_bytes = buffer.getvalue()
        
        try:
            result = transcribe_process_map_from_image(
                image_bytes=block_bytes,
                image_format="png"
            )
            print("Successfully processed remaining blocks")
            results.append(remove_markdown(result))
        except Exception as e:
            print(f"Error processing remaining blocks: {str(e)}")
    
    return results

