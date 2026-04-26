"""
PSX Local News Scraper
Uses Google News RSS to fetch the latest headlines for the Pakistan Economy and PSX.
This feeds directly into the Sentiment Agent.
"""
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def fetch_psx_news(lookback_days: int = 3) -> list:
    """
    Fetch recent news headlines related to Pakistan Stock Exchange and economy.
    Returns a list of dicts with keys: title, link, pubDate.
    """
    query = f"Pakistan Stock Exchange OR PSX OR State Bank of Pakistan"
    # URL encode the query
    query = query.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={query}+when:{lookback_days}d&hl=en-PK&gl=PK&ceid=PK:en"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        news_items = []
        
        for item in root.findall('./channel/item')[:15]: # Top 15 headlines
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            # Clean up the origin site from the title (e.g. " - Business Recorder")
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
                
            news_items.append({
                "title": title,
                "link": link,
                "published": pub_date
            })
            
        return news_items
    except Exception as e:
        print(f"[News Scraper] Error fetching PSX news: {e}")
        return []

if __name__ == "__main__":
    # Test execution
    news = fetch_psx_news()
    for n in news:
        print(f"- {n['title']} ({n['published']})")
