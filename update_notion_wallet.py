import os
import requests
import yfinance as yf

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_current_price(ticker):
    """yfinance를 이용해 최신 현재가를 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d")
        if not df.empty:
            return round(df['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"❌ 티커 {ticker} 주가 수집 실패: {e}")
    return None

def update_notion_wallet():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ 노션 DB 조회 실패: {response.text}")
        return

    pages = response.json().get("results", [])
    print(f"📊 총 {len(pages)}개의 노션 페이지를 찾았습니다. 업데이트를 시작합니다.")

    for page in pages:
        page_id = page["id"]
        properties = page["properties"]

        # 1. 안전하게 종목명 가져오기
        stock_name = "Unknown"
        title_prop = properties.get("종목명", {}).get("title", [])
        if title_prop:
            stock_name = title_prop[0].get("text", {}).get("content", "Unknown")

        # 2. 안전하게 티커 가져오기 (텍스트 속성)
        ticker_prop = properties.get("티커", {}).get("rich_text", [])
        if not ticker_prop:
            print(f"⏩ [{stock_name}]: 티커 칸이 비어 있어 건너넙니다.")
            continue
            
        ticker = ticker_prop[0].get("text", {}).get("content", "").strip()
        if not ticker:
            print(f"⏩ [{stock_name}]: 티커 텍스트가 비어 있어 건너넙니다.")
            continue
        
        # 3. 최신 주가 수집
        current_price = get_current_price(ticker)
        if current_price is None:
            print(f"⏩ [{stock_name}] ({ticker}): 주가를 가져오지 못했습니다.")
            continue

        # 4. 노션 DB 업데이트
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        update_data = {
            "properties": {
                "현재가": {
                    "number": current_price
                }
            }
        }
        
        up_res = requests.patch(update_url, headers=headers, json=update_data)
        if up_res.status_code == 200:
            print(f"✅ {stock_name} ({ticker}) ➡️ 현재가 {current_price:,} 업데이트 완료!")
        else:
            print(f"❌ {stock_name} 업데이트 실패: {up_res.text}")

if __name__ == "__main__":
    update_notion_wallet()
