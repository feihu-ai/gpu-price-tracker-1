import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path

try:
    import requests
except ModuleNotFoundError:
    requests = None


DATA_FILE = Path(__file__).resolve().parent / "gpu_price_history.json"
SOURCE = "模拟行情"
HISTORY_DAYS = 30

MODELS = (
    {"name": "RTX 4060", "base": 2299, "decline": 0.045, "volatility": 0.012},
    {"name": "RTX 4070", "base": 3999, "decline": 0.038, "volatility": 0.010},
    {"name": "RTX 4080", "base": 7699, "decline": 0.032, "volatility": 0.008},
    {"name": "RTX 4090", "base": 13999, "decline": 0.026, "volatility": 0.007},
    {"name": "RTX 5060", "base": 2699, "decline": 0.022, "volatility": 0.009},
    {"name": "RTX 5070", "base": 4499, "decline": 0.018, "volatility": 0.008},
    {"name": "RTX 5080", "base": 9499, "decline": 0.014, "volatility": 0.0065},
    {"name": "RTX 5090", "base": 16999, "decline": 0.012, "volatility": 0.0055},
)
MODELS_BY_NAME = {model["name"]: model for model in MODELS}
MODEL_ORDER = {model["name"]: index for index, model in enumerate(MODELS)}


def get_gpu_price(product: str, price_date: date, anchor_date: date) -> int:
    """Return a deterministic simulated market price for one model and day."""
    model = MODELS_BY_NAME[product]
    days_ago = max(0, (anchor_date - price_date).days)
    trend_position = min(days_ago, HISTORY_DAYS - 1) / max(1, HISTORY_DAYS - 1)
    rng = random.Random(f"{product}|{price_date.isoformat()}")
    noise = rng.uniform(-model["volatility"], model["volatility"])
    raw_price = model["base"] * (1 + model["decline"] * trend_position + noise)
    return max(100, int(round(raw_price / 10) * 10 - 1))


def build_records_for_date(price_date: date, anchor_date: date) -> list[dict]:
    return [
        {
            "date": price_date.isoformat(),
            "product": model["name"],
            "price": get_gpu_price(model["name"], price_date, anchor_date),
            "currency": "CNY",
            "source": SOURCE,
        }
        for model in MODELS
    ]


def generate_history(days: int, anchor_date: date) -> list[dict]:
    start_date = anchor_date - timedelta(days=days - 1)
    records = []
    for offset in range(days):
        records.extend(build_records_for_date(start_date + timedelta(days=offset), anchor_date))
    return records


def load_history() -> list[dict]:
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        history = json.load(file)

    if not isinstance(history, list):
        raise ValueError(f"{DATA_FILE.name} 必须是 JSON 数组")
    return history


def save_history(history: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=2)
        file.write("\n")


def merge_records(history: list[dict], new_records: list[dict]) -> list[dict]:
    records_by_key = {
        (record.get("date"), record.get("product")): record
        for record in history
        if isinstance(record, dict)
    }
    for record in new_records:
        records_by_key[(record["date"], record["product"])] = record

    return sorted(
        records_by_key.values(),
        key=lambda record: (
            record.get("date", ""),
            MODEL_ORDER.get(record.get("product"), len(MODEL_ORDER)),
            record.get("product", ""),
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 RTX 显卡模拟价格历史")
    parser.add_argument(
        "--backfill",
        type=int,
        metavar="DAYS",
        help="覆盖生成指定天数的历史数据，例如 --backfill 30",
    )
    args = parser.parse_args()

    if requests is None:
        print("提示：未安装 requests，当前使用模拟价格")

    anchor_date = date.today()
    if args.backfill is not None:
        if args.backfill < 1:
            parser.error("--backfill 必须是正整数")
        history = generate_history(args.backfill, anchor_date)
        save_history(history)
        latest_records = [record for record in history if record["date"] == anchor_date.isoformat()]
        print(f"历史价格生成成功：{args.backfill} 天 × {len(MODELS)} 款显卡")
        print(json.dumps(latest_records, ensure_ascii=False, indent=2))
        return

    history = load_history()
    if not history:
        history = generate_history(HISTORY_DAYS, anchor_date)
        save_history(history)
        print(f"未找到历史数据，已自动生成 {HISTORY_DAYS} 天 × {len(MODELS)} 款显卡")
        print(json.dumps([record for record in history if record["date"] == anchor_date.isoformat()], ensure_ascii=False, indent=2))
        return

    today_records = build_records_for_date(anchor_date, anchor_date)
    history = merge_records(history, today_records)
    save_history(history)
    print("今日价格获取成功")
    print(json.dumps(today_records, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
