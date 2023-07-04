from typing import List

from pydantic import BaseModel, Field

from ..enums.file_type import FileType
from ..enums.language import Language
from ..models.question import Question


class Instrument(BaseModel):
    file_id: str = Field(None, description="Unique identifier for the file (UUID-4)")
    instrument_id: str = Field(
        None, description="Unique identifier for the instrument (UUID-4)"
    )
    instrument_name: str = Field(
        "Untitled instrument", description="Human-readable name of the instrument"
    )
    file_name: str = Field("Untitled file", description="The name of the input file")
    file_type: FileType = Field(None, description="The file type (pdf, xlsx, txt)")
    file_section: str = Field(
        None, description="The sub-section of the file, e.g. Excel tab"
    )
    study: str = Field(None, description="The study")
    sweep: str = Field(None, description="The sweep")
    metadata: dict = Field(
        None,
        description="Optional metadata about the instrument (URL, citation, DOI, copyright holder)",
    )
    language: Language = Field(
        Language.English,
        description="The ISO 639-2 (alpha-2) encoding of the instrument language",
    )
    questions: List[Question] = Field(description="the items inside the instrument")

    class Config:
        schema_extra = {
            "example": {
                "file_id": "fd60a9a64b1b4078a68f4bc06f20253c",
                "instrument_id": "7829ba96f48e4848abd97884911b6795",
                "instrument_name": "GAD-7 English",
                "file_name": "GAD-7.pdf",
                "file_type": "pdf",
                "file_section": "GAD-7 English",
                "language": "en",
                "study": "MCS",
                "sweep": "Sweep 1",
                "questions": [
                    {
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
                ],
            }
        }
