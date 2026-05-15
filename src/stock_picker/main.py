#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stock_picker.crew import StockPicker
from stock_picker.gradio_ui.stock_picker_ui import StockPickerUi

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# load environment variables
load_dotenv()

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
    
    # Format the output with markdown
    output = f"# Stock Picker Results\n\n"
    output += f"**Sector Analyzed:** {sector}\n\n"
    output += f"**Analysis Report:**\n\n{result.raw}"
    
    return output

if __name__ == "__main__":
    stock_picker = StockPickerUi.create_gradio_interface(run_stock_picker)
    stock_picker.launch(**StockPickerUi.launch_kwargs())
