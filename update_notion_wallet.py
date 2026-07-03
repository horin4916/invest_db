import os
import requests
import yfinance as yf

# GitHub Secrets에서 보안 정보를 환경변수로 받아옵니다.
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_current_price(ticker):
    """yfinance를 이용해 자산 종류 불문 최신 현재가를 가져옵니다."""
    try:
        stock = yf.Ticker(ticker)
        # 실시간에 가장 가까운 최신 종가 혹은 현재가 추출
        df = stock.history(period="1d")
        if not df.empty:
            return round(df['Close'].iloc[-1], 2)
    except Exception as e:
        print(f"❌ 티커 {ticker} 주가 수집 실패: {e}")
    return None

def update_notion_wallet():
    # 1. 노션 데이터베이스에서 등록된 모든 종목 정보 읽어오기
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

        # ⚠️ 노션 DB의 실제 '속성 이름'과 일치해야 합니다! (대소문자/공백 주의)
        # 종목명 가져오기 (로그 출력용)
        title_list = properties.get("종목명", {}).get("title", [])
        stock_name = title_list[0]["text"]["content"] if title_list else "Unknown"

        # 티커 속성 가져오기 (텍스트 속성 기준)
        ticker_list = properties.get("티커", {}).get("rich_text", [])
        if not ticker_list:
            print(f"⏩ {stock_name}: 티커 정보가 없어 건너넙니다.")
            continue
        
        ticker = ticker_list[0]["text"]["content"].strip()
        
        # 2. 최신 주가 수집
        current_price = get_current_price(ticker)
        if current_price is None:
            continue

        # 3. 노션 DB의 '현재가' 속성에 원격 업데이트
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
            print(f"✅ {stock_name} ({ticker}) ➡️ 현재가 {current_price:,}원/달러 업데이트 완료!")
        else:
            print(f"❌ {stock_name} 업데이트 실패: {up_res.text}")

if __name__ == "__main__":
    update_notion_wallet()
