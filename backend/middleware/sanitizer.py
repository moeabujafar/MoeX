import re
_BLOCK_LINES = re.compile(r'(?im)^(?:\s*)(teach:|sys:|system:|internal:|debug:|tl;dr|tldr)\b.*?$')
_SPACES      = re.compile(r'\n{3,}')
def sanitize(text: str) -> str:
    x = _BLOCK_LINES.sub('', text or '')
    x = _SPACES.sub('\n\n', x).strip()
    return x
