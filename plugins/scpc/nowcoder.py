import requests
from html import unescape
from json import loads
from typing import Optional, List
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag

def nowcoder_recent_contests_url() -> str:
    """获取 牛客 最近比赛列表的 URL (HTML文本数据, 非JSON)"""
    return f'https://ac.nowcoder.com/acm/contest/vip-index'

headers = {
    'Origin': 'https://ac.nowcoder.com',
    'Referer': 'https://ac.nowcoder.com/acm/contest/vip-index',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json, text/plain, */*',
}
@dataclass
class NowcoderContest:
    id: int
    name: str
    start_time: str
    duration: int
    contest_url: str

def get_nowcoder_recent_contests() -> Optional[List[NowcoderContest]]:
    try:
        response = requests.get(nowcoder_recent_contests_url(), headers=headers)
    except Exception as e:
        return None
    soup = BeautifulSoup(response.text, 'html.parser')
    find_item = soup.find('div', class_='platform-mod js-current')
    if not isinstance(find_item, Tag):
        return None
    items = []
    contest_table = find_item.find_all('div', class_='platform-item js-item')
    for contest in contest_table:
        data = loads(unescape(str(contest["data-json"])))
        id = unescape(str(contest["data-id"]))
        contest_url = f"https://ac.nowcoder.com/acm/contest/{id}"
        items.append(
            NowcoderContest(
                id=int(id),
                name=data['contestName'],
                start_time=str(data["contestStartTime"] / 1000),
                contest_url=contest_url,
                duration=data["contestDuration"] / 1000
            )
        )
            
    return items
