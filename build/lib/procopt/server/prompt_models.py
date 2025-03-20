from pydantic import BaseModel
from typing import Optional, List


########################################################
# Process Map Transcription
########################################################

class StepModel(BaseModel):
    step_number: int
    name: str
    operator: Optional[str] = None
    system: Optional[str] = None
    material: Optional[str] = None
    timing: Optional[str] = None
    frequency: Optional[str] = None
    pain_points: List[str]
    transitions: List[str]

class TranscriptionOutputModel(BaseModel):
    thinking: str
    is_valid: bool # TRUE if the image is valid (i.e. contains steps and is not empty)
    steps: List[StepModel]

class MergeTranscriptionOutputModel(BaseModel):
    thinking: str
    steps: List[StepModel]

########################################################
# Bottlenecks
########################################################

class BottleneckModel(BaseModel):
    step_number: int
    description: str
    impact: str

class BottleneckOutputModel(BaseModel):
    thinking: str
    bottlenecks: List[BottleneckModel]

########################################################
# Improvements
########################################################

class ImprovementModel(BaseModel):
    bottleneck_id: int
    description: str
    impacted_steps: List[int]
    impact: str
    timeline: str

class ImprovementOutputModel(BaseModel):
    thinking: str
    improvements: List[ImprovementModel]