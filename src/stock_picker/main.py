#!/usr/bin/env python
import html
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stock_picker.crew import StockPicker
from stock_picker.gradio_ui.stock_picker_ui import StockPickerUi
from stock_picker.tools.push_tool import MailJetNotificationTool

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# load environment variables
load_dotenv()

REPORT_PATH = Path("output/decision.md")


def _report_markdown(result):
    if REPORT_PATH.exists():
        return REPORT_PATH.read_text(encoding="utf-8").strip()
    return str(getattr(result, "raw", result)).strip()


def _markdown_to_html(markdown):
    html_lines = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            close_list()
            continue

        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_inline_markdown_to_html(line[2:])}</li>")
            continue

        close_list()
        if line.startswith("### "):
            html_lines.append(f"<h3>{_inline_markdown_to_html(line[4:])}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{_inline_markdown_to_html(line[3:])}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{_inline_markdown_to_html(line[2:])}</h1>")
        elif line == "---":
            html_lines.append("<hr>")
        else:
            html_lines.append(f"<p>{_inline_markdown_to_html(line)}</p>")

    close_list()
    return "\n".join(html_lines)


def _inline_markdown_to_html(text):
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _send_report_email(markdown, sector, email_address):
    subject = f"AI Stock Picker Report: {sector}"
    message = _markdown_to_html(markdown)
    return MailJetNotificationTool()._run(subject, message, email_address)


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
    result = StockPicker().crew().kickoff(inputs=inputs)
    report = _report_markdown(result)
    email_status = ""
    try:
        _send_report_email(report, sector, email_address)
    except Exception as exc:
        email_status = f"\n\n**Email status:** Failed to send email: {exc}"
    
    # Format the output with markdown
    output = f"# Stock Picker Results\n\n"
    output += f"**Sector Analyzed:** {sector}\n\n"
    output += f"**Analysis Report:**\n\n{report}"
    output += email_status
    
    return output

if __name__ == "__main__":
    stock_picker = StockPickerUi.create_gradio_interface(run_stock_picker)
    stock_picker.launch(**StockPickerUi.launch_kwargs())
