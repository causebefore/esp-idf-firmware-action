# ESP-IDF Firmware Release Action

一个面向 ESP-IDF OTA 的可复用 GitHub Action。它接收项目已经生成的 `.bin` 与 OTA
清单，执行以下工作：

1. 校验固件大小、完整文件 SHA-256、固件目标和 OTA 版本；
2. 按 `<firmware_target>-v<ota_version>` 生成 Release tag；
3. 把固件重命名为 `<artifact_id>.bin`；
4. 向清单写入公开的 `download_url`；
5. 将固件与最终清单一起发布到 GitHub Releases。

构建命令保留在调用项目中，因为每个 ESP-IDF 项目的组件、版本注入和产物路径不同；
本 Action 复用的是构建完成后的校验与发布契约。

## 使用示例

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v4

  - name: Build and create OTA manifest
    run: ./your-project-build-command

  - name: Publish firmware
    uses: causebefore/esp-idf-firmware-action@v1
    with:
      token: ${{ secrets.FIRMWARE_RELEASE_TOKEN }}
      repository: causebefore/desksuite-firmware
      firmware: path/to/application.bin
      manifest: path/to/firmware_target.json
      target: main
```

如果 Release 仓库就是当前仓库，可传入 `${{ github.token }}`，并给当前 job 配置
`contents: write`。跨仓库发布时，`GITHUB_TOKEN` 不能写入另一个仓库，需要传入只对目标
Release 仓库授予 `Contents: Read and write` 的细粒度令牌。

同一 tag 已存在时，Action 会下载现有固件和清单并比较 SHA-256：内容完全一致则视为幂等
成功，任一资产不同则拒绝覆盖。

## 输入

| 输入 | 必填 | 说明 |
| --- | --- | --- |
| `token` | 是 | 对 Release 仓库具有 `Contents: write` 权限的令牌 |
| `repository` | 是 | `owner/repo` 格式的目标仓库 |
| `firmware` | 是 | 已编译的应用固件 `.bin` |
| `manifest` | 是 | OTA 协议 v2 清单 |
| `target` | 否 | Release tag 指向的分支或提交，默认 `main` |

## 输出

| 输出 | 说明 |
| --- | --- |
| `tag` | 实际 Release tag |
| `download-url` | 固件公开下载地址 |
| `firmware-asset` | 校验并重命名后的固件路径 |
| `manifest-asset` | 已写入 `download_url` 的最终清单路径 |
