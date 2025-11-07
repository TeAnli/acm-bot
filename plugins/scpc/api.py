
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Content-Type': 'application/json',
}

def user_info_url(username: str) -> str:
    return f'http://scpc.fun/api/get-user-home-info?username={username}'

def codeforces_contests_url(include_gym: bool = False) -> str:
    return f'https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}'

def scpc_contests_url(page: int = 1, page_size: int = 20) -> str:
    """SCPC 比赛列表接口（可能随平台变动，保持容错）。"""
    # 常见约定：分页参数 page/pageSize，如不支持则后端忽略
    return f'http://scpc.fun/api/contest/list?page={page}&pageSize={page_size}'

def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    return f'http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}'


