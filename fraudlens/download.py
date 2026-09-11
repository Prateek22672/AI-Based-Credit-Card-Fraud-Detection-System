"""Download both datasets into data/raw/.

    python -m fraudlens.download

* Sparkov simulated card transactions (Jan 2019 - Jun 2020, 1,296,675 rows),
  the Kaggle "kartik2112/fraud-detection" training file, via a public
  Hugging Face mirror (no Kaggle login needed).
* ULB / Worldline European card transactions (284,807 rows, 492 frauds),
  via the public TensorFlow mirror of the Kaggle "mlg-ulb/creditcardfraud" file.
"""
from __future__ import annotations

import urllib.request

from . import config

SOURCES = {
    config.SPARKOV_PARQUET: "https://huggingface.co/datasets/alenc123/credit-card-fraud/resolve/main/credit_card_transactions.parquet",
    config.ULB_CSV: "https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv",
}


def main() -> None:
    for path, url in SOURCES.items():
        if path.exists():
            print(f"exists: {path.relative_to(config.ROOT)}")
            continue
        print(f"downloading {url}")
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(path)
        print(f"  -> {path.relative_to(config.ROOT)} ({path.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
