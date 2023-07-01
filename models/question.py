from typing import List

from pydantic import BaseModel, Field


class Question(BaseModel):
    question_no: str = Field(None, description="Number of the question")
    question_intro: str = Field(
        None, description="Introductory text applying to the question"
    )
    question_text: str = Field(description="Text of the question")
    options: List[str] = Field([], description="The possible answer options")
    source_page: int = Field(
        0,
        description="The page of the PDF on which the question was located, zero-indexed",
    )
    instrument_id: str = Field(
        None, description="Unique identifier for the instrument (UUID-4)"
    )
    instrument_name: str = Field(
        None, description="Human readable name for the instrument"
    )
    topics_auto: list = Field(
        None, description="Automated list of topics identified by model"
    )
    nearest_match_from_mhc_auto: dict = Field(
        None, description="Automatically identified nearest MHC match"
    )

    class Config:
        schema_extra = {
            "example": {
                "question_no": "1",
                "question_intro": "Over the last two weeks, how often have you been bothered by the following problems?",
                "question_text": "Feeling nervous, anxious, or on edge",
                "options": [
                    "Not at all",
                    "Several days",
                    "More than half the days",
                    "Nearly every day",
                ],
                "source_page": 0,
            }
        }
