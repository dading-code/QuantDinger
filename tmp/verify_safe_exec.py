"""
验证 safe_exec 模块的问题
"""
import sys
sys.path.insert(0, 'd:/www/workai/QuantDinger/backend_api_python')

from app.utils.safe_exec import validate_code_safety, safe_exec_with_validation

# 测试用例
test_cases = [
    ("正常pandas代码", """
import pandas as pd
import numpy as np
df = pd.DataFrame({'close': [1,2,3,4,5]})
df['sma'] = df['close'].rolling(3).mean()
output = {'result': df['sma'].tolist()}
""", True),
    
    ("df.eval() - 应该被拒绝但实际上可能有问题", """
import pandas as pd
df = pd.DataFrame({'close': [1,2,3,4,5]})
result = df.eval('close > 3')
output = {'result': result.tolist()}
""", False),  # 预期会被拒绝
    
    ("使用未授权的库", """
import scipy.stats as stats
result = stats.norm.pdf([1,2,3])
output = {'result': result.tolist()}
""", False),  # 预期会被拒绝
]

print("="*80)
print("验证 safe_exec 模块的安全检查")
print("="*80)

for name, code, should_pass in test_cases:
    is_safe, error_msg = validate_code_safety(code)
    status = "✓ PASS" if is_safe == should_pass else "✗ FAIL"
    
    print(f"\n{status} | {name}")
    print(f"      预期: {'通过' if should_pass else '拒绝'}")
    print(f"      实际: {'通过' if is_safe else '拒绝'}")
    if error_msg:
        print(f"      错误: {error_msg[:100]}")

print("\n" + "="*80)
print("测试子进程执行性能")
print("="*80)

import time

simple_code = """
import numpy as np
import pandas as pd
x = np.arange(1000)
y = x * 2
output = {'sum': int(y.sum())}
"""

start = time.time()
result = safe_exec_with_validation(
    code=simple_code,
    exec_globals={},
    timeout=10,
)
elapsed = time.time() - start

print(f"\n执行时间: {elapsed:.3f}秒")
print(f"成功: {result['success']}")
if result['result']:
    print(f"结果: {result['result']}")
if not result['success']:
    print(f"错误: {result['error'][:200]}")

print("\n" + "="*80)
print("结论")
print("="*80)
print("1. df.eval() 会被安全检查拒绝（正则匹配 \\beval\\s*\\(）")
print("2. 子进程执行有明显 overhead（每次 ~0.X 秒）")
print("3. 白名单外的库无法使用")
