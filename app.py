from pathlib import Path

from tracker.gui import App


def main() -> None:
    data_file = Path(__file__).parent / "data" / "products.json"
    app = App(data_file=data_file)
    app.mainloop()


if __name__ == "__main__":
    main()
