import traceback
from typing import List, Tuple
import io
from tqdm import tqdm
from procopt.server.db import db
from procopt.server.llm_utils import MODEL, get_user_text_prompt
from procopt.server.models import ProcessRun
from procopt.server.prompt_models import BottleneckModel, BottleneckOutputModel, ImprovementModel, ImprovementOutputModel, MergeTranscriptionOutputModel, StepModel
from procopt.server.utils import (
    split_image_into_blocks,
    TranscriptionOutputModel
)
from procopt.server.llm_utils import (
    call_llm,
    sys_prompt,
    get_text_prompt,
    get_image_prompt,
)
from procopt.server.prompts import (
    prompt__identify_bottlenecks,
    prompt__generate_improvements,
    prompt__merge_transcribed_process_map_blocks,
    prompt__transcribe_process_map
)

BLOCK_SIZE = 1000  

def format_improvement_as_markdown(improvement: ImprovementModel) -> str:
    """Given an ImprovementModel, format it as a markdown string"""
    improvement_desc: List[str] = [f"#### Improvement for Bottleneck #{improvement.bottleneck_id}"]
    improvement_desc.append(f"- Description: {improvement.description}")
    improvement_desc.append(f"- Impacted Steps: {improvement.impacted_steps}")
    improvement_desc.append(f"- Impact: {improvement.impact}")
    improvement_desc.append(f"- Timeline: {improvement.timeline}")
    return "\n".join(improvement_desc)

def format_bottleneck_as_markdown(bottleneck: BottleneckModel) -> str:
    """Given a BottleneckModel, format it as a markdown string"""
    bottleneck_desc: List[str] = [f"#### Bottleneck for Step #{bottleneck.step_number}"]
    bottleneck_desc.append(f"- Description: {bottleneck.description}")
    bottleneck_desc.append(f"- Impact: {bottleneck.impact}")
    return "\n".join(bottleneck_desc)

def format_step_as_markdown(step: StepModel) -> str:
    """Given a StepModel, format it as a markdown string"""
    step_desc = [f"#### Step {step.step_number}: {step.name}"]
    step_desc.append(f"Number: {step.step_number}")

    # Only include fields that have values
    if step.operator:
        step_desc.append(f"- Operator: {step.operator}")
    if step.system:
        step_desc.append(f"- System: {step.system}")
    if step.material:
        step_desc.append(f"- Material: {step.material}")
    if step.timing:
        step_desc.append(f"- Timing: {step.timing}")
    if step.frequency:
        step_desc.append(f"- Frequency: {step.frequency}")
    
    if step.pain_points:
        step_desc.append("- Pain Points:")
        for point in step.pain_points:
            step_desc.append(f"  - {point}")
    
    if step.transitions:
        step_desc.append("- Transitions:")
        for transition in step.transitions:
            step_desc.append(f"  - {transition}")

    return "\n".join(step_desc)

def merge_block_results(block_results: List[TranscriptionOutputModel]) -> List[StepModel]:
    """Synthesize results from blocks into a coherent process description"""
    all_steps = []
    for result in block_results:
        if result.is_valid:
            all_steps.extend(result.steps)

    all_steps.sort(key=lambda x: x.step_number)
    seen_steps = {}
    for step in all_steps:
        if step.step_number not in seen_steps:
            seen_steps[step.step_number] = step
        else:
            existing = seen_steps[step.step_number]
            if step.operator and not existing.operator:
                existing.operator = step.operator
            if step.system and not existing.system:
                existing.system = step.system
            if step.material and not existing.material:
                existing.material = step.material
            if step.timing and not existing.timing:
                existing.timing = step.timing
            if step.frequency and not existing.frequency:
                existing.frequency = step.frequency
            existing.pain_points.extend([p for p in step.pain_points if p not in existing.pain_points])
            existing.transitions.extend([t for t in step.transitions if t not in existing.transitions])
    
    markdown_lines: List[str] = [
        format_step_as_markdown(seen_steps[step_num])
        for step_num in sorted(seen_steps.keys())
    ]
    
    print(f"Merging {len(markdown_lines)} chunks together...")
    merged_transcription = call_llm(
        messages=[
            sys_prompt(),
            get_user_text_prompt(prompt__merge_transcribed_process_map_blocks('\n'.join(markdown_lines))),
        ],
        model=MODEL,
        response_format=MergeTranscriptionOutputModel
    )
    print(f"Merged transcription: # steps={len(merged_transcription.steps)}")

    return merged_transcription.steps

def run_pipeline(app, run_id: int, pipeline_step: str) -> Tuple[str, str]:
    """Process a task based on its type"""
    with app.app_context():
        run = db.session.get(ProcessRun, run_id)
        
        if not run:
            print(f"Run not found for run_id=`{run_id}`")
            return

        try:
            print(f"Starting run_pipeline() for run_id=`{run_id}`, pipeline_step=`{pipeline_step}`")

            with open(run.image_path, "rb") as f:
                image_bytes = f.read()
            
            if pipeline_step == "transcribe":
                run.status = "transcribing"
                db.session.commit()
                print("Starting transcription process")
                
                blocks = split_image_into_blocks(image_bytes, block_size=BLOCK_SIZE)
                print(f"Split image into {len(blocks)} blocks")
                
                block_results: List[TranscriptionOutputModel] = []

                for block_image in tqdm(blocks, desc="Transcribing blocks", total=len(blocks)):
                    buffer = io.BytesIO()
                    block_image.save(buffer, format="PNG")
                    block_bytes = buffer.getvalue()
                    
                    try:
                        response = call_llm(
                            messages=[
                                sys_prompt(),
                                {
                                    "role": "user",
                                    "content": [
                                        get_text_prompt(prompt__transcribe_process_map()),
                                        get_image_prompt(block_bytes, "png"),
                                    ]
                                }
                            ],
                            model=MODEL,
                            max_tokens=4000,
                            response_format=TranscriptionOutputModel
                        )
                        print(f"Response received from {MODEL}: {response}...")
                        if response.is_valid:
                            block_results.append(response)
                            print(f"Successfully transcribed block {len(block_results)}/{len(blocks)}")
                        else:
                            print(f"Invalid transcription for block {len(block_results)}/{len(blocks)}")
                    except Exception as e:
                        print(f"Direct API call error: {str(e)}")

                merged_steps: List[StepModel] = merge_block_results(block_results)
                run.transcription = '\n'.join(format_step_as_markdown(step) for step in merged_steps)
                run.status = "transcribed"
                
            elif pipeline_step == "bottlenecks":
                run.status = "bottlenecks"
                db.session.commit()
                
                bottleneck_output: BottleneckOutputModel = call_llm(
                    messages=[
                        sys_prompt(),
                        get_user_text_prompt(prompt__identify_bottlenecks(run.transcription)),
                    ],
                    model=MODEL,
                    response_format=BottleneckOutputModel
                )
                run.bottlenecks = '\n'.join([ format_bottleneck_as_markdown(bottleneck) for bottleneck in bottleneck_output.bottlenecks ])
                run.status = "bottlenecks_complete"
                
            elif pipeline_step == "improvements":
                run.status = "improvements"
                db.session.commit()
                
                print(f"Generating improvements for run_id=`{run_id}`")
                raw_improvements = call_llm(
                    messages=[
                        sys_prompt(),
                        get_user_text_prompt(prompt__generate_improvements( run.transcription, run.bottlenecks ))
                    ],
                    model=MODEL,
                    response_format=ImprovementOutputModel
                )
                print(f"Generated {len(raw_improvements.improvements)} improvements for run_id=`{run_id}`")

                run.improvements = '\n'.join([ format_improvement_as_markdown(improvement) for improvement in raw_improvements.improvements ])
                run.status = "complete"
            
            db.session.commit()
            
        except Exception as e:
            print(f"Error in run_pipeline: {str(e)}")
            traceback.print_exc()
            run.status = f"{pipeline_step}_failed"
            db.session.commit()
