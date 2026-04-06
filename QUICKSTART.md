# 🚀 快速部署指南

## 1. 注册 Vercel
- 访问 https://vercel.com
- 点击 Sign Up → Continue with GitHub

## 2. 创建 GitHub 仓库
- 新建仓库，名称随意（如 `quiz-bot`）
- 上传本目录所有代码

## 3. 导入 Vercel
- 登录 Vercel Dashboard
- Add New → Project
- 选择刚创建的 GitHub 仓库
- Framework Preset 选 **Other**
- 点击 Deploy

## 4. 配置环境变量
在 Vercel 项目 Settings → Environment Variables 中添加：
```
FEISHU_APP_SECRET = 1fhQUBuVVCNfLjSnaWaYydxYVcLiQyoD
```
然后点击 Redeploy

## 5. 配置飞书
1. 复制 Vercel 域名（如 `https://quiz-bot-xxx.vercel.app`）
2. 打开飞书开放平台 → 你的应用
3. 事件与回调 → 将事件发送至开发者服务器
4. 填写：`https://你的域名/webhook`
5. 添加事件：`im.message.receive_v1` 和 `card.action.trigger`
6. 权限管理 → 添加：`im:message:send`, `contact:user.department:readonly`, `bitable:record`
7. 发布应用

## 6. 测试
在飞书中发送：`我要答题`

---
**预计耗时：5-10分钟**
