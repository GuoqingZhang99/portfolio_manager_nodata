# 邮件通知配置指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 文件并重命名为 `.env`：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入您的真实配置。

## Gmail 配置（推荐）

### 步骤 1: 开启两步验证

1. 访问 https://myaccount.google.com/security
2. 找到"两步验证"并开启

### 步骤 2: 生成应用专用密码

1. 在"两步验证"页面，向下滚动找到"应用专用密码"
2. 点击"生成"
3. 选择"邮件"和"Windows 电脑"（或对应设备）
4. 复制生成的 16 位密码（格式：xxxx xxxx xxxx xxxx）

### 步骤 3: 配置 .env 文件

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=xxxx xxxx xxxx xxxx
DEFAULT_RECIPIENT_EMAIL=your_email@gmail.com
DEFAULT_NOTIFICATION_METHOD=桌面
```

## Outlook/Hotmail 配置

### .env 文件配置

```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SENDER_EMAIL=your_email@outlook.com
SENDER_PASSWORD=your_password
DEFAULT_RECIPIENT_EMAIL=your_email@outlook.com
DEFAULT_NOTIFICATION_METHOD=桌面
```

## 使用说明

### 默认通知方式：桌面通知

- 系统默认使用**桌面通知**，无需配置邮箱即可使用
- 添加预警时，通知方式默认为"桌面"
- 支持 Windows、macOS、Linux

### 使用邮件通知

1. 在添加预警时，选择"邮件"通知方式
2. 邮箱地址可以留空，将使用 `.env` 中配置的默认接收邮箱
3. 也可以填写特定邮箱，发送到不同的地址

### 默认接收邮箱

在 `.env` 中配置 `DEFAULT_RECIPIENT_EMAIL`，这样：
- 添加预警时不填写邮箱地址
- 系统会自动使用默认接收邮箱

## 安全提示

- ⚠️ **不要将 `.env` 文件提交到 Git**
- ✅ `.env` 文件已经被添加到 `.gitignore`
- ✅ 只分享 `.env.example` 文件作为模板
- ✅ 使用应用专用密码，而非账户主密码

## 故障排除

### Gmail 发送失败

1. 确认已开启两步验证
2. 确认使用的是应用专用密码，而非账户密码
3. 检查 `.env` 文件中的邮箱地址是否正确

### Outlook 发送失败

1. 检查账户是否开启了"安全性较低的应用访问"
2. 尝试使用应用密码代替账户密码

### 桌面通知不显示

- **Windows**: 需要安装 `win10toast` 库（已包含在 requirements.txt）
- **macOS**: 系统原生支持
- **Linux**: 需要 `notify-send` 命令

## 环境变量说明

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `SMTP_SERVER` | SMTP 服务器地址 | smtp.gmail.com |
| `SMTP_PORT` | SMTP 端口 | 587 |
| `SENDER_EMAIL` | 发件人邮箱 | your_email@gmail.com |
| `SENDER_PASSWORD` | 发件人密码/应用专用密码 | xxxx xxxx xxxx xxxx |
| `DEFAULT_RECIPIENT_EMAIL` | 默认接收邮箱 | your_email@gmail.com |
| `DEFAULT_NOTIFICATION_METHOD` | 默认通知方式 | 桌面 或 邮件 |
