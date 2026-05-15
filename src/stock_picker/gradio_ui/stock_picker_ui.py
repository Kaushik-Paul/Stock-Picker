import os
import socket
import sys

try:
    import gradio as gr
except ModuleNotFoundError as exc:
    if exc.name != "gradio":
        raise
    virtual_env = os.getenv("VIRTUAL_ENV", "not set")
    raise ModuleNotFoundError(
        "Gradio is not installed in the active Python environment.\n"
        f"Python executable: {sys.executable}\n"
        f"VIRTUAL_ENV: {virtual_env}\n"
        "From this repo, run one of:\n"
        "  source .venv/bin/activate && python src/stock_picker/main.py\n"
        "  uv run python src/stock_picker/main.py"
    ) from exc


class StockPickerUi:
    CSS = """
    .center-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }
    .narrow {
        width: 40% !important;
        margin: 0 auto;
    }
    .wide {
        width: 90% !important;
        margin: 20px auto;
    }
    .result-content {
        text-align: left;
        display: inline-block;
        margin: 20px auto;
        max-width: 100%;
        text-align: left;
    }
    .disclaimer {
        margin-top: 20px;
        padding: 15px;
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        color: #856404;
        font-size: 0.9em;
    }
    """

    CUSTOM_JS = "() => { document.title = 'AI Stock Picker'; }"

    @staticmethod
    def launch_kwargs():
        kwargs = {"css": StockPickerUi.CSS, "js": StockPickerUi.CUSTOM_JS}
        server_port = StockPickerUi._server_port()
        if server_port is not None:
            kwargs["server_port"] = server_port
        return kwargs

    @staticmethod
    def _server_port():
        configured_port = os.getenv("GRADIO_SERVER_PORT")
        if configured_port:
            return int(configured_port)

        if os.getenv("SPACE_ID") or os.getenv("HF_SPACE_ID"):
            return None

        for port in range(7860, 8060):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    if sock.connect_ex(("127.0.0.1", port)) != 0:
                        return port
            except OSError:
                return None
        return None

    @staticmethod
    def create_gradio_interface(run_stock_picker):
        """
        Create and launch the Gradio interface.
        """
        with gr.Blocks(
                title="AI Stock Picker"
        ) as demo:
            with gr.Column(elem_classes=["center-content"]):
                gr.Markdown("# AI Stock Picker\n\nEnter a sector to analyze and get stock recommendations.")

                with gr.Column(elem_classes=["narrow"]):
                    sector = gr.Dropdown(
                        ["Technology", "Healthcare", "Finance", "Energy", "Consumer Goods"],
                        label="Select Sector",
                        value="Technology"
                    )

                    email = gr.Textbox(
                        label="Email Address",
                        placeholder="Enter your email to receive the full report",
                        type="email",
                        info="Please enter a valid email address"
                    )

                    analyze_btn = gr.Button(
                        "Analyze Sector",
                        variant="primary",
                        elem_classes=["narrow"],
                        interactive=False
                    )

                    def validate_email(email):
                        import re
                        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                        return bool(re.match(pattern, email)) if email else False

                    email.change(
                        fn=lambda x: gr.Button(interactive=validate_email(x)),
                        inputs=[email],
                        outputs=[analyze_btn]
                    )

                    with gr.Accordion("ℹ️ Important Note", open=False):
                        gr.Markdown("""
                        **Please Note:** This analysis may take a few minutes to complete. 

                        You can safely close this tab if needed - we'll send the full report to your email when it's ready.
                        """)

                    with gr.Accordion("⚠️ Disclaimer", open=False):
                        gr.Markdown("""
                        **Disclaimer:** This application is for educational and informational purposes only. 

                        The information provided by this tool should not be considered as financial advice. 
                        Always conduct your own research and consider consulting with a qualified financial 
                        advisor before making any investment decisions. The developers of this application 
                        are not responsible for any financial losses or decisions made based on this tool's outputs.
                        """)

                # Results section with wider width
                with gr.Column(elem_classes=["wide"]):
                    gr.Markdown("## Analysis Results\n\nYour analysis will appear here.")
                    output = gr.Markdown("", elem_classes=["result-content"])

            analyze_btn.click(
                fn=run_stock_picker,
                inputs=[sector, email],
                outputs=output,
                api_name="analyze",
                show_progress=True
            )

        return demo
