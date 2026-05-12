# QuantDinger 部署快速指南

## 🚀 一键部署（推荐）

### Windows PowerShell
```powershell
cd d:\www\workai\QuantDinger
.\deploy_oneclick.ps1
```

### Linux/Mac/Git Bash
```bash
cd /path/to/QuantDinger
chmod +x deploy_oneclick.sh
./deploy_oneclick.sh
```

**脚本会自动完成**:
1. ✅ 检查SSH连接
2. ✅ 上传后端代码
3. ✅ 复制到容器
4. ✅ 重启backend
5. ✅ 重启frontend（刷新DNS）
6. ✅ 验证服务状态

---

## 🔧 手动部署（不推荐）

如果一键脚本失败，可以手动执行：

### 步骤1: 上传代码
```bash
# Windows PowerShell
scp -r d:\www\workai\QuantDinger\backend_api_python root@39.105.150.99:/opt/quantdinger/QuantDinger/

# Linux/Mac
scp -r backend_api_python/ root@39.105.150.99:/opt/quantdinger/QuantDinger/
```

### 步骤2: 复制到容器
```bash
ssh root@39.105.150.99 "cd /opt/quantdinger/QuantDinger && podman cp backend_api_python backend:/app/backend_api_python"
```

### 步骤3: 重启backend
```bash
ssh root@39.105.150.99 "podman restart backend"
```

### 步骤4: 等待10秒
```bash
sleep 10
```

### 步骤5: 重启frontend（重要！）
```bash
ssh root@39.105.150.99 "podman restart quantdinger-frontend"
```

### 步骤6: 验证
```bash
curl http://39.105.150.99:8888/api/health
```

---

## ⚠️ 常见问题

### Q1: 为什么总是502错误？
**A**: Backend重启后IP变化，Nginx仍使用旧IP。  
**解决**: 必须重启frontend容器刷新DNS缓存。

### Q2: 为什么新文件没有生效？
**A**: `podman cp` 可能没有复制新文件。  
**解决**: 检查服务器上是否有该文件：
```bash
ssh root@39.105.150.99 "ls -la /opt/quantdinger/QuantDinger/backend_api_python/app/routes/local_client.py"
```

### Q3: Git pull失败怎么办？
**A**: GitHub网络问题或仓库权限问题。  
**解决**: 直接使用scp上传代码（一键脚本已处理）。

### Q4: 如何查看部署日志？
```bash
# Backend日志
ssh root@39.105.150.99 "podman logs -f backend"

# Frontend日志
ssh root@39.105.150.99 "podman logs -f quantdinger-frontend"

# 最近50行错误日志
ssh root@39.105.150.99 "podman logs --tail 50 backend | grep ERROR"
```

### Q5: 如何回滚到上一个版本？
```bash
# 在服务器上执行
ssh root@39.105.150.99 << 'EOF'
cd /opt/quantdinger/QuantDinger
git log --oneline -5  # 查看最近5个提交
git reset --hard <commit-id>  # 回滚到指定提交
podman cp backend_api_python backend:/app/backend_api_python
podman restart backend
sleep 10
podman restart quantdinger-frontend
EOF
```

---

## 📊 部署时间参考

| 步骤 | 耗时 |
|------|------|
| 上传代码 | 10-30秒（取决于文件大小） |
| 复制到容器 | 2-5秒 |
| 重启backend | 10-15秒 |
| 重启frontend | 3-5秒 |
| **总计** | **~30-60秒** |

---

## 🎯 最佳实践

1. **永远使用一键脚本** - 避免人为错误
2. **部署前提交Git** - 确保代码可追溯
3. **部署后立即验证** - 检查健康状态和关键路由
4. **监控日志** - 发现潜在问题
5. **定期备份数据库** - 防止数据丢失

---

## 🔍 故障排查清单

部署失败时，按顺序检查：

```bash
# 1. SSH连接
ssh root@39.105.150.99 "echo OK"

# 2. 容器状态
ssh root@39.105.150.99 "podman ps | grep -E 'backend|frontend'"

# 3. Backend日志
ssh root@39.105.150.99 "podman logs --tail 50 backend | grep -E 'ERROR|INFO' | tail -20"

# 4. 健康检查
curl http://39.105.150.99:8888/api/health

# 5. DNS解析
ssh root@39.105.150.99 "podman exec frontend nslookup backend"

# 6. 端口监听
ssh root@39.105.150.99 "podman exec backend netstat -tlnp | grep 5000"
```

---

## 💡 提示

- ✅ **绿色** = 成功
- ⚠️ **黄色** = 警告（可能需要关注）
- ❌ **红色** = 失败（需要修复）

---

**记住**: 好的部署应该是**无聊的** - 每次都应该一样成功！🎯
