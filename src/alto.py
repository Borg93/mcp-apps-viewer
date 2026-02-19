import logging
import re

import httpx

from src.models import AltoData, TextLine

logger = logging.getLogger(__name__)


def fetch_alto_xml_from_url(url: str) -> str:
    """Fetch ALTO XML from a URL."""
    logger.debug("Fetching ALTO XML: %s", url)
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    logger.debug("ALTO fetched: status=%d, length=%d", response.status_code, len(response.text))
    return response.text


def parse_alto_xml(xml_string: str) -> AltoData:
    """Parse ALTO XML and extract text lines with polygons."""
    text_lines: list[TextLine] = []
    transcription_lines: list[str] = []

    # Extract page dimensions
    page_match = re.search(r'<Page[^>]*WIDTH="(\d+)"[^>]*HEIGHT="(\d+)"', xml_string)
    if page_match:
        page_width = int(page_match.group(1))
        page_height = int(page_match.group(2))
    else:
        page_width = 6192
        page_height = 5432
        logger.warning("No <Page> dimensions found, using defaults: %dx%d", page_width, page_height)

    # Extract all TextLine elements
    text_line_pattern = re.compile(
        r'<TextLine[^>]*ID="([^"]*)"[^>]*HPOS="(\d+)"[^>]*VPOS="(\d+)"[^>]*HEIGHT="(\d+)"[^>]*WIDTH="(\d+)"[^>]*>([\s\S]*?)</TextLine>',
        re.MULTILINE,
    )

    skipped_no_polygon = 0
    skipped_no_transcription = 0

    for match in text_line_pattern.finditer(xml_string):
        line_id = match.group(1)
        hpos = int(match.group(2))
        vpos = int(match.group(3))
        height = int(match.group(4))
        width = int(match.group(5))
        line_content = match.group(6)

        polygon_match = re.search(r'<Polygon[^>]*POINTS="([^"]*)"', line_content)
        polygon = polygon_match.group(1) if polygon_match else ""

        words = re.findall(r'<String[^>]*CONTENT="([^"]*)"', line_content)
        transcription = " ".join(words)

        if not polygon:
            skipped_no_polygon += 1
        if not transcription:
            skipped_no_transcription += 1

        if polygon and transcription:
            text_lines.append(
                TextLine(
                    id=line_id,
                    polygon=polygon,
                    transcription=transcription,
                    hpos=hpos,
                    vpos=vpos,
                    width=width,
                    height=height,
                )
            )
            transcription_lines.append(transcription)

    logger.info("ALTO parsed: %d text lines, page %dx%d", len(text_lines), page_width, page_height)
    if skipped_no_polygon:
        logger.warning("Skipped %d lines with no polygon", skipped_no_polygon)
    if skipped_no_transcription:
        logger.warning("Skipped %d lines with no transcription", skipped_no_transcription)

    return AltoData(
        text_lines=text_lines,
        page_width=page_width,
        page_height=page_height,
        full_text="\n".join(transcription_lines),
    )
