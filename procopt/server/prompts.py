from typing import List


def prompt__transcribe_process_map() -> str:
    return """You are given a subsection of a larger image of a process map.

# Instructions

Please identify all of the steps depicted in the image and describe them in detail in text.
Note that the image might be a subsection of a larger process map, and thus not all steps will be present in this image. 
DO NOT make assumptions about any steps that are not present in this image, and faithfully transcribe the steps exactly as presented in the image.

If the image is not clear, if the image is blank, or if it does not contain any steps, please respond with "is_valid" set to false. 

Otherwise, set "is_valid" to true and for each step:
    1. Identify the step number (as labeled in the image) and name. Note that the step number is not always sequential, and might start with any number. This is because you are shown a subsection of a larger process map, and steps might be missing from this image.
    2. Look for labels that indicate:
        - Op/Operator: Who performs the step
        - Sys/System: What system or equipment is used
        - Mat/Material: What materials are involved
        - T/Time/Timing: How long the step takes
        - F/Freq/Frequency: How often the step occurs
    3. Note any pain points or issues associated with the step (often specified in red)
    4. Identify transitions/connections to other steps.

You must copy the text on the image EXACTLY as it appears VERBATIM. Do not add any additional information.

Format your response as follows:

{{
    "thinking": "Your analysis of the process map",
    "is_valid" : bool <Whether the image is clear and it contains steps>,
    "steps": [
        {{
            "step_number": int <Number of the step specified in the image>,
            "name": str <Name of the step>,
            "operator": str <Name of the operator>,
            "system": str <Name of the system>,
            "material": str <Name of the material>,
            "timing": str <Timing of the step>,
            "frequency": str <Frequency of the step>,
            "pain_points": List[str] <Pain points of the step>,
            "transitions": List[str] <Names of other steps to which this step transitions>,
        }}
    ]
}}

Please list all of the steps in the order that they appear in the image.
"""

def prompt__merge_transcribed_process_map_blocks(blocks: List[str]) -> str:
    return f"""Previously, you were given subsections of a larger process map (i.e. "chunks").
For each chunk, you transcribed the visual contents of the chunk into a list of textual steps contained within that chunk. Note that each chunk is a subsection of the larger process map, and thus not all steps will be present in each chunk. Chunks may be missing steps, have overlapping steps with other chunks, or contain steps not present in other chunks.

Now, you will be given the transcription from each chunk. Your task is to merge the chunks together to form a complete, coherent, and accurate process map.

# Process Map Chunks

{blocks}

# Instructions

Merge the chunks together to form a complete, coherent, and accurate process map. 

Rules:
- If two steps are the same, merge them together into a single step and combine their information as completely as possible.
- If two steps are different, keep them as separate steps.
- Make sure to include all steps from all chunks in the final process map.
- Order the steps in the proper order based on their numbers.

Format your response as a list of steps, formatted as follows:
{{
    "thinking" : str <First, think step-by-step about how to merge the chunks together, and explain your reasoning.>,
    "steps" : List[StepModel] <The merged steps, formatted as in the prompt__transcribe_process_map function.>,
}}

"""

def prompt__identify_bottlenecks(transcription: str) -> str:
    return f"""You are given a process map.

# Process Map

{transcription}

# Instructions

Using your expert knowledge of process improvement and optimization for enterprise workflows, please identify up to 5 main bottlenecks in this process. For each bottleneck:
1. Identify which step number(s) it affects
2. Explain why it's a bottleneck
3. Quantify the impact if possible (time delays, resource constraints, etc.)

Format your response as a list of bottlenecks, formatted as follows:
{{
    "thinking" : str <First, think step-by-step about what bottlenecks exist in the process map, and explain your reasoning.>,
    "bottlenecks" : [
        {{
            "step_number" : int <Number of the step that is a bottleneck>,
            "description" : str <Description of the bottleneck>,
            "impact" : str <Impact of the bottleneck>,
        }}
    ]
}}

Please list the main bottlenecks in this process map below.
"""

def prompt__generate_improvements(transcription: str, bottlenecks: str) -> str:
    return f"""You are given a process map and bottlenecks previously identified in the process map.

# Process Map

{transcription}

# Bottlenecks

{bottlenecks}

# Instructions
For each bottleneck, suggest 3 specific improvements that could address the issue. For each improvement:
1. Describe the proposed change
2. Explain how it addresses the bottleneck
3. Note which step(s) would be affected
4. Estimate the potential impact
5. Estimate the timeline for implementing the improvement (short / medium / long term)

Format your response as a list of improvements, formatted as follows:
{{
    "thinking" : str <First, think step-by-step about what improvements could be made to the process map, and explain your reasoning.>,
    "improvements" : [
        {{
            "bottleneck_id" : int <ID of the bottleneck>,
            "description" : str <Description of the improvement and how it addresses the bottleneck>,
            "impacted_steps" : List[int] <List of step numbers that would be impacted by the improvement>,
            "impact" : str <Potential impact of the improvement>,
            "timeline" : str <Timeline for implementing the improvement>,
        }}
    ]
}}

Please list the improvements in this process map below."""

def prompt__sort_improvements(transcription: str, bottlenecks: str, improvements: str) -> str:
    return f"""You are given a process map, bottlenecks previously identified in the process map, and improvements previously generated for the bottlenecks.

# Process Map

{transcription}

# Bottlenecks

{bottlenecks}

# Proposed Improvements

{improvements}

# Instructions

Categorize each improvement into one of these categories:
1. Quick wins (fast implementation, low effort)
2. Medium-term improvements (moderate time/effort)
3. Long-term solutions (significant time/effort, high impact)

For each improvement, include:
1. Implementation timeline
2. Resource requirements
3. Expected impact
4. Dependencies on other improvements

Structure your response using the TranscriptionOutputModel format."""
