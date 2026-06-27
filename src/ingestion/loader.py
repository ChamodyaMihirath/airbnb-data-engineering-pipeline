from pathlib import Path
import pandas as pd


class DataLoader:

    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)

    def load_listings(self):
        path = self.data_dir / "listings.csv.gz"

        return pd.read_csv(
            path,
            compression="gzip",
            keep_default_na=False,
            dtype={"price": str}
        )

    def load_calendar(self):
        path = self.data_dir / "calendar.csv.gz"

        return pd.read_csv(
            path,
            compression="gzip",
            keep_default_na=False,
            dtype={
                "price": str,
                "adjusted_price": str
            }
        )

    def load_reviews(self):
        path = self.data_dir / "reviews.csv.gz"

        return pd.read_csv(
            path,
            compression="gzip",
            keep_default_na=False
        )

    def load_neighbourhoods(self):
        path = self.data_dir / "neighbourhoods.csv"

        return pd.read_csv(
            path,
            keep_default_na=False
        )

    def load_all(self):
        return {
            "listings": self.load_listings(),
            "calendar": self.load_calendar(),
            "reviews": self.load_reviews(),
            "neighbourhoods": self.load_neighbourhoods(),
        }