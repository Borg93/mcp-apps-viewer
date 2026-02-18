/**
 * Utility functions for the Document Viewer
 */

import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import type { ViewerData, PageData } from "./types";

/**
 * Parse initial tool result (view-document) into ViewerData.
 */
export function parseToolResult(result: CallToolResult): ViewerData | null {
  const sc = (result as any).structuredContent;
  if (sc && typeof sc === "object" && "pageUrls" in sc && "firstPage" in sc) {
    return sc as ViewerData;
  }
  return null;
}

/**
 * Parse load-page tool result into a single PageData.
 */
export function parsePageResult(result: CallToolResult): PageData | null {
  const sc = (result as any).structuredContent;
  if (sc && typeof sc === "object" && "page" in sc) {
    return sc.page as PageData;
  }
  return null;
}
