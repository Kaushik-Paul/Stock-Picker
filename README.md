# AI Stock Picker

[![Live Demo – Hugging Face Space](https://img.shields.io/badge/Live%20Demo-Hugging%20Face%20Space-yellow?logo=huggingface&logoColor=white)](https://huggingface.co/spaces/kaushikpaul/Stock-Picker)

An AI-powered stock research assistant that:
- Finds companies trending in the news for a chosen sector
- Researches each company in depth
- Picks the best candidate for investment with a clear, markdown report
- Emails the full HTML report to you

The app uses a Gradio UI backed by a CrewAI pipeline with multiple agents and tools. It relies on OpenRouter-hosted LLMs (DeepSeek Chat v3.1 by default) and Brave Search for web data.

## Live Demo
- Access the hosted app on Hugging Face: https://huggingface.co/spaces/kaushikpaul/Stock-Picker

## Features
- __Sector-based discovery__
  - Finds 2–3 companies trending in the selected sector using Brave Search
  - Avoids picking the same company twice
- __Automated research pipeline__
  - Multi-agent CrewAI workflow: finder → researcher → picker → email sender
  - Produces a concise, readable markdown report
- __Email delivery__
  - Converts the report to HTML and emails it via Mailjet
  - UI shows the same markdown content returned by the pipeline
- __Simple, modern UI__
  - Gradio-based interface with email validation and helpful accordions
- __Rate-limit friendly search__
  - Brave search calls are throttled to reduce API rate-limit issues

## Architecture Overview
- __Crew & Agents__: `src/stock_picker/crew.py`
  - Agents configured in `src/stock_picker/config/agents.yaml`
  - Tasks configured in `src/stock_picker/config/tasks.yaml`
- __Tools__
  - Brave search wrapper with throttling: `src/stock_picker/tools/throttled_brave_tool.py`
  - Mailjet email sender: `src/stock_picker/tools/push_tool.py`
- __UI__: `src/stock_picker/gradio_ui/stock_picker_ui.py`
- __Entry point__: `src/stock_picker/main.py`
- __Outputs__: `src/stock_picker/output/`
  - `trending_companies.json`, `research_report.json`, `decision.md`, `final_output.md`

## Prerequisites
- Python 3.10–3.12 (project targets >=3.10 per `pyproject.toml`)
- A modern browser (Chrome, Edge, Safari, Firefox)
- API keys and credentials (see Configuration)

## Quick Start

### 1) Clone the repo
```bash
git clone https://github.com/Kaushik-Paul/Stock-Picker.git
cd Stock-Picker
```

### 2) (Optional) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

### Option A — Install with uv (recommended)
1) Install uv
- Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# ensure ~/.local/bin is on your PATH
export PATH="$HOME/.local/bin:$PATH"
```
- Windows (PowerShell):
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2) Sync dependencies
```bash
uv sync
```

### Option B — Install with pip
```bash
pip install -r requirements.txt
```

### 3) Create a .env file
Create a `.env` in the project root with the following variables (adjust as needed):

```ini
# OpenRouter (LLM provider used in agents.yaml)
OPENROUTER_API_KEY=your_openrouter_key

# Brave Search (used by BraveSearchTool)
# Name per crewai_tools BraveSearchTool docs; commonly BRAVE_API_KEY
BRAVE_API_KEY=your_brave_search_api_key

# Mailjet (email delivery)
MAILJET_API_KEY=your_mailjet_key
MAILJET_API_SECRET=your_mailjet_secret
MAILJET_FROM_EMAIL=from_address@yourdomain.com
```

Notes
- The Brave Search tool reads its API key from the environment as defined by crewai_tools. If your environment uses a different variable name, follow the crewai_tools BraveSearchTool documentation.
- Ensure the `MAILJET_FROM_EMAIL` domain is verified in your Mailjet account.

### 4) Run the app
Using uv:
```bash
uv run python -m src.stock_picker.main
```
Using python directly:
```bash
python -m src.stock_picker.main
```
Gradio will print a local URL (e.g., http://127.0.0.1:7860). Open it in your browser.

## Configuration

### LLMs and Agents
- File: `src/stock_picker/config/agents.yaml`
- Default agents use DeepSeek Chat v3.1 via OpenRouter: `openrouter/deepseek/deepseek-chat-v3.1:free`. The manager uses `openrouter/meta-llama/llama-3.1-405b-instruct:free`.
- To change models or providers, update the `llm` field for each agent. Ensure the appropriate API key and base configuration are set for your provider.

### Tasks & Outputs
- File: `src/stock_picker/config/tasks.yaml`
- Pipeline:
  1. `find_trending_companies` → outputs `output/trending_companies.json`
  2. `research_trending_companies` → outputs `output/research_report.json`
  3. `pick_best_company` → outputs `output/decision.md`
  4. `send_email_task` → emails HTML, returns the original markdown to the UI and writes `output/final_output.md`

### UI Behavior
- File: `src/stock_picker/gradio_ui/stock_picker_ui.py`
- You must enter a valid email to enable the Analyze button.
- The app displays progress and renders markdown results. The email is sent in HTML format.

## Usage
1. Choose a sector from the dropdown.
2. Enter your email address.
3. Click “Analyze Sector”.
4. Wait a few minutes while the pipeline runs. The result appears in the app and a full HTML email is sent to you.

## Outputs
Generated files are saved under `src/stock_picker/output/`:
- `trending_companies.json` — Initial list of companies from the news
- `research_report.json` — Detailed research for each company
- `decision.md` — The picker’s markdown report
- `final_output.md` — The final markdown returned to the UI (email is sent as HTML)

## Deployment
- The project is already hosted on Hugging Face Spaces: https://huggingface.co/spaces/kaushikpaul/Stock-Picker
- To deploy your own Space:
  - Set Space SDK to “Gradio” and point to `src/stock_picker/main.py` as the entry file.
  - Add required secrets in the Space settings (`OPENROUTER_API_KEY`, `BRAVE_API_KEY`, `MAILJET_API_KEY`, `MAILJET_API_SECRET`, `MAILJET_FROM_EMAIL`).
  - Ensure the Python version matches (3.10–3.12) and install via `requirements.txt` or `pyproject.toml`.

## Troubleshooting
- __Missing or invalid API keys__
  - Verify `.env` values and that your provider accounts are active.
- __Brave Search rate limits__
  - The tool adds a small delay between calls, but you may still hit limits. Consider higher limits or caching.
- __Mailjet send failures__
  - Check API credentials, sender domain verification, and recipient address validity.
- __LLM errors / 429s__
  - Confirm `OPENROUTER_API_KEY` is valid and you’re using model IDs available to your account.
- __Virtualenv issues on Windows__
  - Use `.venv\Scripts\activate` and ensure `python` points to the venv interpreter.

## Security & Privacy
- Do not commit `.env` files or secrets.
- Emails are sent via Mailjet. Review Mailjet’s data policies for production usage.


## License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.