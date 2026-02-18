"""
Document Viewer MCP App — Tools

Two tools:
  - view-document: entry point, fetches first page, returns URL list for pagination
  - load-page: fetches a single page on demand (called by View via callServerTool)
"""

import base64
import logging
from pathlib import Path
from typing import Annotated

import httpx
from fastmcp.server.apps import AppConfig
from fastmcp.tools import ToolResult
from mcp import types

from src import mcp
from src.alto import fetch_alto_xml_from_url, parse_alto_xml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

DIST_DIR = Path(__file__).parent.parent / "dist"
RESOURCE_URI = "ui://document-viewer/mcp-app.html"


def _fetch_image_as_data_url(url: str) -> str:
    """Fetch image and return as base64 data URL."""
    logger.info(f"Fetching image: {url}")
    resp = httpx.get(url, timeout=60.0, follow_redirects=True)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "image/jpeg")
    b64 = base64.b64encode(resp.content).decode("ascii")
    logger.info(f"Image fetched: {len(resp.content)} bytes, {content_type}")
    return f"data:{content_type};base64,{b64}"


def _fetch_and_parse_alto(url: str) -> dict:
    """Fetch ALTO XML and parse into structured text line data."""
    logger.info(f"Fetching ALTO: {url}")
    xml = fetch_alto_xml_from_url(url)
    data = parse_alto_xml(xml)
    logger.info(f"ALTO parsed: {len(data.text_lines)} lines, {data.page_width}x{data.page_height}")
    return {
        "textLines": [
            {
                "id": line.id,
                "polygon": line.polygon,
                "transcription": line.transcription,
                "hpos": line.hpos,
                "vpos": line.vpos,
                "width": line.width,
                "height": line.height,
            }
            for line in data.text_lines
        ],
        "pageWidth": data.page_width,
        "pageHeight": data.page_height,
    }


def _build_page_data(index: int, image_url: str, alto_url: str) -> tuple[dict, list[str]]:
    """Fetch image + ALTO for a single page. Returns (page_dict, errors)."""
    page: dict = {"index": index}
    errors: list[str] = []

    try:
        page["imageDataUrl"] = _fetch_image_as_data_url(image_url)
    except Exception as e:
        logger.error(f"Image fetch failed for page {index}: {e}")
        errors.append(f"Page {index + 1} image: {e}")
        page["imageDataUrl"] = ""

    try:
        page["alto"] = _fetch_and_parse_alto(alto_url)
    except Exception as e:
        logger.error(f"ALTO fetch failed for page {index}: {e}")
        errors.append(f"Page {index + 1} ALTO: {e}")
        page["alto"] = {"textLines": [], "pageWidth": 0, "pageHeight": 0}

    return page, errors


@mcp.tool(
    name="view-document",
    description=(
        "Display document pages with zoomable images and ALTO text overlays. "
        "Provide paired lists: image_urls[i] pairs with alto_urls[i]. "
        "Only the first page is fetched immediately; remaining pages load on demand via pagination."
    ),
    app=AppConfig(resource_uri=RESOURCE_URI),
)
def view_document(
    image_urls: Annotated[list[str], "List of image URLs (one per page)."],
    alto_urls: Annotated[list[str], "List of ALTO XML URLs (one per page, paired with image_urls)."],
) -> ToolResult:
    """View document pages with zoomable images and ALTO overlays."""
    if len(image_urls) != len(alto_urls):
        return ToolResult(
            content=[types.TextContent(
                type="text",
                text=f"Error: mismatched URL counts ({len(image_urls)} images vs {len(alto_urls)} ALTO files)",
            )],
        )

    # Build URL list for all pages
    page_urls = [
        {"image": img_url, "alto": alto_url}
        for img_url, alto_url in zip(image_urls, alto_urls)
    ]

    # Fetch only the first page
    first_page, errors = _build_page_data(0, image_urls[0], alto_urls[0])

    total_lines = len(first_page.get("alto", {}).get("textLines", []))
    summary = f"Loaded page 1 of {len(page_urls)} with {total_lines} text lines."
    if errors:
        summary += f" Errors: {'; '.join(errors)}"

    logger.info(f"view-document: {summary}")
    return ToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structured_content={
            "pageUrls": page_urls,
            "firstPage": first_page,
        },
    )


@mcp.tool(
    name="load-page",
    description="Load a single document page (image + ALTO). Used by the viewer for pagination.",
    app=AppConfig(resource_uri=RESOURCE_URI),
)
def load_page(
    image_url: Annotated[str, "Image URL for the page."],
    alto_url: Annotated[str, "ALTO XML URL for the page."],
    page_index: Annotated[int, "Zero-based page index."],
) -> ToolResult:
    """Fetch a single page on demand."""
    page, errors = _build_page_data(page_index, image_url, alto_url)

    total_lines = len(page.get("alto", {}).get("textLines", []))
    summary = f"Page {page_index + 1}: {total_lines} text lines."
    if errors:
        summary += f" Errors: {'; '.join(errors)}"

    logger.info(f"load-page: {summary}")
    return ToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structured_content={"page": page},
    )


@mcp.resource(uri=RESOURCE_URI)
def get_ui_resource() -> str:
    html_path = DIST_DIR / "mcp-app.html"
    if not html_path.exists():
        raise FileNotFoundError(f"UI resource not found: {html_path}")
    return html_path.read_text(encoding="utf-8")
