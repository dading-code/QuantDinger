import re

# 测试正则表达式是否会误判正常代码
test_cases = [
    ('result = df.query("price > 100")', r'\beval\s*\(', False),
    ('x = eval("1+1")', r'\beval\s*\(', True),
    ('df.eval("col > 5")', r'\beval\s*\(', True),  # 这个会被误判！
    ('print("hello")', r'\bprint\s*\(', False),  # print不在危险模式中
]

for code, pattern, expected in test_cases:
    match = bool(re.search(pattern, code))
    status = "✓" if match == expected else "✗"
    print(f"{status} Pattern: {pattern:20} | Code: {code[:40]:40} | Match: {match:5} | Expected: {expected}")
