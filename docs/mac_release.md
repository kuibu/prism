# macOS 发布流水线（签名 + 公证 + GitHub 自动更新）

本项目的发布级 macOS 流水线由以下文件组成：

- 工作流：`.github/workflows/mac-release.yml`
- 构建配置：`clients/mac/electron-builder.config.cjs`
- 公证脚本：`clients/mac/scripts/notarize.cjs`
- 密钥写入脚本：`scripts/setup_mac_release_secrets.sh`

## 一次性准备

1. 准备 Apple Developer ID Application 证书（`.p12`）与密码  
2. 准备 App Store Connect API Key（`.p8`、Key ID、Issuer ID）  
3. 记录 Apple Team ID

## 写入 GitHub Secrets

```bash
cd /Users/a/repos/prism
scripts/setup_mac_release_secrets.sh \
  --repo kuibu/prism \
  --cert-p12 /path/to/DeveloperID_Application.p12 \
  --cert-password '***' \
  --api-key-p8 /path/to/AuthKey_XXXXXX.p8 \
  --api-key-id XXXXXX \
  --api-issuer xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx \
  --team-id TEAMID1234
```

## 发布前预检

```bash
cd /Users/a/repos/prism
make mac-release-check
```

预检会输出：

- `MISSING_SECRETS`：说明哪些 GitHub Secrets 还没配置
- `LOCAL_CODESIGN_IDENTITY`：本机是否有可用签名身份
- `WORKFLOW_EXISTS`：发布工作流是否已存在

## 触发发布

```bash
cd /Users/a/repos/prism
make mac-release-run VERSION=0.1.1
```

注意：工作流中已强制开启：

- `PRISM_REQUIRE_SIGNING=1`
- `PRISM_REQUIRE_NOTARIZATION=1`

即签名或公证任一步失败都会直接失败，不会再产出“未公证包”。

## 观察发布状态

```bash
gh run watch --repo kuibu/prism --exit-status
```

成功后会产出并上传：

- `Prism Desktop-<version>-arm64.dmg`
- `Prism Desktop-<version>-arm64.zip`
- `latest-mac.yml`（自动更新元数据）
- `*.blockmap`

## 下载验证

1. 打开 Releases 页面下载 `.dmg`
2. 安装后首次运行，进入系统设置放行（若需要）
3. 在 Finder 中查看签名：

```bash
codesign -dv --verbose=4 "/Applications/Prism Desktop.app"
```

4. 验证公证票据：

```bash
spctl -a -t exec -vv "/Applications/Prism Desktop.app"
```

## 自动更新验证

1. 安装旧版本（例如 `0.1.0`）
2. 发布新版本（例如 `0.1.1`）
3. 打开旧版 App，菜单中点击 `Check for Updates...`
4. 应出现新版本下载与重启安装提示
