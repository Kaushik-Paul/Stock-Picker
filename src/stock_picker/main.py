#!/usr/bin/env python
import html
import sys
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stock_picker.crew import StockPicker
from stock_picker.gradio_ui.stock_picker_ui import StockPickerUi
from stock_picker.tools.push_tool import EMAIL_STATUS_PATH, MailJetNotificationTool

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# load environment variables
load_dotenv()

REPORT_PATH = Path("output/decision.md")


def _report_markdown(result):
    if REPORT_PATH.exists():
        return REPORT_PATH.read_text(encoding="utf-8").strip()
    return str(getattr(result, "raw", result)).strip()


def _markdown_to_html(markdown_text):
    try:
        from markdown_it import MarkdownIt

        body = MarkdownIt("commonmark").render(markdown_text)
        return f"<html><body>{body}</body></html>"
    except Exception:
        escaped = html.escape(markdown_text)
        return f"<html><body><pre>{escaped}</pre></body></html>"


def _email_subject(report):
    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or "Stock Picker Investment Report"
    return "Stock Picker Investment Report"


def _remove_email_status_marker():
    try:
        EMAIL_STATUS_PATH.unlink()
    except FileNotFoundError:
        pass


def _send_email_if_agent_did_not(email_address, report):
    if EMAIL_STATUS_PATH.exists():
        return

    status = MailJetNotificationTool()._run(
        subject=_email_subject(report),
        message=_markdown_to_html(report),
        to_user=email_address,
    )
    print(f"Email fallback sent via MailJet: {status}")


def run_stock_picker(sector, email_address):
    """
    Run the stock picker with the given sector and email address.
    """
    inputs = {
        'sector': sector,
        'current_date': str(datetime.now()),
        'user_email_address': email_address
    }

    # Create and run the crew
    _remove_email_status_marker()
    result = StockPicker().crew().kickoff(inputs=inputs)
    report = _report_markdown(result)
    _send_email_if_agent_did_not(email_address, report)
    
    # Format the output with markdown
    output = f"# Stock Picker Results\n\n"
    output += f"**Sector Analyzed:** {sector}\n\n"
    output += f"**Analysis Report:**\n\n{report}"
    
    return output

if __name__ == "__main__":
    stock_picker = StockPickerUi.create_gradio_interface(run_stock_picker)
    stock_picker.launch(**StockPickerUi.launch_kwargs())
