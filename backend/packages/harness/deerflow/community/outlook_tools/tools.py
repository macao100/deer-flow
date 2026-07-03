"""
Outlook email automation tools — send/search emails via pywin32 (Windows COM).

Requires Microsoft Outlook installed and configured on the local machine.
Windows only — relies on pywin32 COM dispatch.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from langchain.tools import tool

logger = logging.getLogger(__name__)


def _get_outlook():
    """Get the Outlook application object via COM."""
    try:
        import win32com.client
        return win32com.client.Dispatch("Outlook.Application")
    except Exception as exc:
        raise RuntimeError(f"Could not connect to Outlook. Is Outlook installed? Error: {exc}")


def _check_outlook_available() -> str | None:
    """Return an error message if Outlook COM is not available."""
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return "pywin32 is not installed. Run: pip install pywin32"
    return None


def _get_default_save_path() -> str:
    """Get user's Desktop as a safe default save location."""
    return os.path.join(os.environ.get("USERPROFILE", "C:\"), "Desktop")


@tool("send_outlook_email", parse_docstring=True)
def send_outlook_email_tool(
    to: str,
    subject: str = "",
    body: str = "",
    cc: str = "",
    bcc: str = "",
    attachment_paths: str = "",
) -> str:
    """Send an email through Microsoft Outlook.

    Creates the email in Outlook's draft folder and displays it for review.
    The user must click Send manually (safety measure).

    Args:
        to: Recipient email address(es), semicolon-separated for multiple.
        subject: Email subject line.
        body: Email body text (plain text).
        cc: CC recipient(s), semicolon-separated.
        bcc: BCC recipient(s), semicolon-separated.
        attachment_paths: Semicolon-separated list of file paths to attach.
    """
    err = _check_outlook_available()
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)

    if not to or not to.strip():
        return json.dumps({"error": "Recipient (to) is required"}, ensure_ascii=False)

    try:
        outlook = _get_outlook()
        mail = outlook.CreateItem(0)  # olMailItem = 0

        mail.To = to.strip()
        if cc.strip():
            mail.CC = cc.strip()
        if bcc.strip():
            mail.BCC = bcc.strip()
        mail.Subject = subject.strip() if subject.strip() else "(No subject)"
        mail.Body = body.strip() if body.strip() else ""

        # Attachments
        if attachment_paths.strip():
            for path in attachment_paths.split(";"):
                path = path.strip()
                if path and os.path.isfile(path):
                    mail.Attachments.Add(os.path.abspath(path))

        # Display for review (user clicks Send manually)
        mail.Display(True)

        return json.dumps(
            {
                "status": "displayed_for_review",
                "to": mail.To,
                "cc": mail.CC if cc else "",
                "subject": mail.Subject,
                "attachments": [a.FileName for a in mail.Attachments] if attachment_paths.strip() else [],
                "message": "Email opened in Outlook. Review and click Send to deliver.",
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("Failed to send email: %s", exc)
        return json.dumps({"error": f"Failed to send email: {exc}"}, ensure_ascii=False)


@tool("search_outlook_inbox", parse_docstring=True)
def search_outlook_inbox_tool(
    folder_name: str = "Inbox",
    max_results: int = 10,
    unread_only: bool = False,
    days_back: int = 7,
    search_term: str = "",
) -> str:
    """Search emails in an Outlook folder.

    Returns email metadata (sender, subject, received time, body preview).

    Args:
        folder_name: Outlook folder name (e.g. "Inbox", "Sent Items", or custom).
        max_results: Maximum number of emails to return (default 10, max 50).
        unread_only: If True, only return unread emails.
        days_back: Number of days back to search (default 7).
        search_term: Optional text to filter by subject or body.
    """
    err = _check_outlook_available()
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)

    max_results = min(max(max_results, 1), 50)

    try:
        outlook = _get_outlook()
        namespace = outlook.GetNamespace("MAPI")

        # Try to find the folder
        folder = None
        try:
            folder = namespace.Folders.Item(1).Folders(folder_name)
        except Exception:
            # Try default folders
            ol_default_folders = {
                "Inbox": 6,
                "Calendar": 9,
                "Contacts": 10,
                "Deleted Items": 3,
                "Drafts": 16,
                "Junk Email": 23,
                "Outbox": 4,
                "Sent Items": 5,
                "Tasks": 13,
            }
            ol_folder_type = ol_default_folders.get(folder_name)
            if ol_folder_type is not None:
                folder = namespace.GetDefaultFolder(ol_folder_type)

        if folder is None:
            # List available folders
            try:
                default_store = namespace.Folders.Item(1)
                available = [f.Name for f in default_store.Folders]
            except Exception:
                available = []
            return json.dumps(
                {
                    "error": f"Folder '{folder_name}' not found.",
                    "available_folders": available,
                },
                ensure_ascii=False,
            )

        # Filter by date
        cutoff = datetime.now() - timedelta(days=days_back)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        # Use Items.Restrict for filtering
        items = folder.Items
        items.Sort("[ReceivedTime]", True)

        # Build filter
        filters = [f"[ReceivedTime] >= '{cutoff_str}'"]
        if unread_only:
            filters.append("[UnRead] = True")
        if search_term:
            filters.append(
                f"@SQL="urn:schemas:httpmail:subject" ci_startswith '{search_term}'"
            )

        if len(filters) == 1:
            filtered = items.Restrict(filters[0])
        else:
            filtered = items.Restrict(" AND ".join(f"({f})" for f in filters))

        emails = []
        count = 0
        for item in filtered:
            if count >= max_results:
                break
            try:
                received = item.ReceivedTime
                received_str = received.strftime("%Y-%m-%d %H:%M") if received else ""
            except Exception:
                received_str = ""

            emails.append({
                "subject": getattr(item, "Subject", "(No subject)"),
                "sender": getattr(item, "SenderName", getattr(item, "SenderEmailAddress", "")),
                "received": received_str,
                "unread": bool(getattr(item, "UnRead", False)),
                "body_preview": (getattr(item, "Body", "") or "")[:200],
                "categories": getattr(item, "Categories", ""),
                "importance": {0: "Low", 1: "Normal", 2: "High"}.get(getattr(item, "Importance", 1), "Normal"),
            })
            count += 1

        return json.dumps(
            {
                "folder": folder_name,
                "total_found": count,
                "filter": {
                    "unread_only": unread_only,
                    "days_back": days_back,
                    "search_term": search_term or None,
                },
                "emails": emails,
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("Failed to search Outlook: %s", exc)
        return json.dumps({"error": f"Failed to search Outlook: {exc}"}, ensure_ascii=False)


@tool("list_outlook_folders", parse_docstring=True)
def list_outlook_folders_tool() -> str:
    """List all available email folders in the default Outlook store.

    Useful to discover folder names for search_outlook_inbox.
    """
    err = _check_outlook_available()
    if err:
        return json.dumps({"error": err}, ensure_ascii=False)

    try:
        outlook = _get_outlook()
        namespace = outlook.GetNamespace("MAPI")
        default_store = namespace.Folders.Item(1)

        folders = []
        for folder in default_store.Folders:
            try:
                item_count = folder.Items.Count
            except Exception:
                item_count = 0
            folders.append({
                "name": folder.Name,
                "item_count": item_count,
                "folder_path": folder.FolderPath,
            })

        return json.dumps(
            {
                "store_name": default_store.Name,
                "folders": folders,
                "total_folders": len(folders),
            },
            indent=2,
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("Failed to list Outlook folders: %s", exc)
        return json.dumps({"error": f"Failed to list Outlook folders: {exc}"}, ensure_ascii=False)
