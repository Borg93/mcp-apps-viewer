from pydantic import BaseModel, Field


class TextLine(BaseModel):
    id: str
    polygon: str
    transcription: str
    hpos: int
    vpos: int
    width: int
    height: int


class AltoData(BaseModel):
    text_lines: list[TextLine]
    page_width: int
    page_height: int
    full_text: str


class ViewDocumentResult(BaseModel):
    """Successful document view with image and ALTO text lines."""

    image_id: str = Field(alias="imageId")
    image_url: str = Field(alias="imageUrl")
    alto_url: str = Field(alias="altoUrl")
    page_width: int = Field(alias="pageWidth")
    page_height: int = Field(alias="pageHeight")
    text_lines: list[TextLine] = Field(alias="textLines")
    total_lines: int = Field(alias="totalLines")
    full_text: str = Field(alias="fullText")

    model_config = {"populate_by_name": True}


class ViewDocumentError(BaseModel):
    """Error response when document fetching fails."""

    error: bool = True
    image_id: str = Field(alias="imageId")
    message: str

    model_config = {"populate_by_name": True}


class UploadDocumentResult(BaseModel):
    """Response for opening the upload view."""

    mode: str
    message: str
