from src.stock_picker.gradio_ui.stock_picker_ui import StockPickerUi
from src.stock_picker.main import run_stock_picker


demo = StockPickerUi.create_gradio_interface(run_stock_picker)


if __name__ == "__main__":
    demo.launch(**StockPickerUi.launch_kwargs())
