import json
import sys
from datetime import date
from pathlib import Path

try:
    import requests
except ModuleNotFoundError as error:
    print("错误：缺少 requests，请先运行 pip install requests。", file=sys.stderr)
    raise SystemExit(1) from error


DATA_FILE = Path(__file__).resolve().parent / "gpu_price_history.json"
API_URL = "https://open.er-api.com/v6/latest/USD"
PRODUCT_NAME = "RTX 5090"
SOURCE = "open.er-api.com"
USD_PRICE = 2000
REQUEST_TIMEOUT_SECONDS = 15


def fetch_cny_rate() -> float:
    try:
        response = requests.get(API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        rate = payload["rates"]["CNY"]
    except (requests.RequestException, KeyError, TypeError, ValueError) as error:
        print(f"错误：获取 USD/CNY 汇率失败：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    if not isinstance(rate, (int, float)) or rate <= 0:
        print("错误：API 返回的 CNY 汇率无效。", file=sys.stderr)
        raise SystemExit(1)

    return float(rate)


def load_history() -> list[dict]:
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            history = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"错误：读取 {DATA_FILE.name} 失败：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    if not isinstance(history, list):
        print(f"错误：{DATA_FILE.name} 必须是 JSON 数组。", file=sys.stderr)
        raise SystemExit(1)

    return history


def append_rtx_5090_price(rate: float) -> dict:
    record = {
        "date": date.today().isoformat(),
        "product": PRODUCT_NAME,
        "price": round(USD_PRICE * rate, 2),
        "currency": "CNY",
        "source": SOURCE,
    }
    history = load_history()
    history.append(record)

    try:
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=2)
            file.write("\n")
    except OSError as error:
        print(f"错误：写入 {DATA_FILE.name} 失败：{error}", file=sys.stderr)
        raise SystemExit(1) from error

    return record


def main() -> None:
    rate = fetch_cny_rate()
    record = append_rtx_5090_price(rate)
    print("RTX 5090 动态价格获取并追加成功")
    print(f"USD/CNY = {rate:.4f}")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
