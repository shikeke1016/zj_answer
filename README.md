# 答题系统 - Vercel Serverless 部署

## 📁 文件结构

```
quiz-system-vercel/
├── api/
│   └── index.py          # 主处理程序 (Serverless Function)
├── vercel.json           # Vercel 配置文件
└── README.md             # 本文件
```

## 🚀 部署步骤

### 第一步：注册 Vercel 账号

1. 访问 [vercel.com](https://vercel.com)
2. 点击 **Sign Up**，选择 **Continue with GitHub**（推荐）
3. 完成注册和登录

### 第二步：创建代码仓库

1. 在 GitHub 上创建新仓库（如 `quiz-system`）
2. 将本目录代码推送到仓库：

```bash
# 本地初始化并推送
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/quiz-system.git
git push -u origin main
```

或者直接上传代码到 GitHub。

### 第三步：部署到 Vercel

#### 方式一：通过 Vercel Dashboard（推荐）

1. 登录 [vercel.com/dashboard](https://vercel.com/dashboard)
2. 点击 **Add New...** → **Project**
3. 选择你的 GitHub 仓库 `quiz-system`
4. 点击 **Import**
5. 在配置页面：
   - Framework Preset: 选择 **Other**
   - 点击 **Deploy**

6. 部署完成后，复制生成的域名（如 `https://quiz-system-xxx.vercel.app`）

#### 方式二：通过 Vercel CLI

```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 部署
cd quiz-system-vercel
vercel --prod
```

### 第四步：配置环境变量

1. 在 Vercel Dashboard 中，进入你的项目
2. 点击 **Settings** → **Environment Variables**
3. 添加以下环境变量：

| 变量名 | 值 |
|--------|-----|
| `FEISHU_APP_SECRET` | `1fhQUBuVVCNfLjSnaWaYydxYVcLiQyoD` |

其他变量已在 `vercel.json` 中预配置，无需重复添加。

### 第五步：配置飞书事件订阅

1. 登录 [飞书开放平台](https://open.feishu.cn/app)
2. 找到应用 `cli_a9475f00d17c5cd5`
3. 进入「事件与回调」
4. 选择 **将事件发送至开发者服务器**
5. 填写请求地址：`https://你的vercel域名/webhook`
   - 例如：`https://quiz-system-xxx.vercel.app/webhook`
6. 添加事件：
   - ✅ `im.message.receive_v1`
   - ✅ `card.action.trigger`
7. 保存配置

### 第六步：配置权限并发布

1. 进入「权限管理」，添加：
   - ✅ `im:message:send`
   - ✅ `contact:user.department:readonly`
   - ✅ `bitable:record`

2. 进入「版本管理与发布」，创建版本并发布

## ✅ 测试

在飞书中：
1. 找到机器人
2. 发送：`我要答题`
3. 应该收到开场白和题目卡片

## 📝 注意事项

### 关于会话状态
Vercel 是 Serverless 架构，每次请求可能在不同实例上执行。当前使用内存存储会话状态，有以下限制：
- 答题过程中如果间隔时间较长，会话可能丢失
- 建议在生产环境中使用 Redis 或数据库存储会话

### 免费额度
Vercel 免费版包含：
- 100GB 带宽/月
- Serverless Function 100GB-hours/月
- 对于答题系统来说完全够用

## 🔧 故障排查

| 问题 | 解决方案 |
|------|----------|
| 部署失败 | 检查代码是否有语法错误 |
| 机器人无响应 | 检查 Vercel 日志 (Dashboard → Logs) |
| 无法发送卡片 | 检查飞书权限配置 |
| 答题记录未保存 | 检查多维表格权限和 App Secret |

## 🎉 完成！

现在你的答题系统已经部署在 Vercel 上，可以免费稳定运行。
