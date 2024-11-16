# Cloudflare Speed Test 结果同步至华为云 DNS

本项目实现将 Cloudflare Speed Test 的测速结果同步到华为云指定的 DNS 记录，支持多域名和分线路配置。应用程序通过解析 CSV 文件中的测速数据，动态更新华为云的 DNS 记录。

---

## 功能特点

1. **支持多域名与分线路**：
   - 可自动更新多个域名的 DNS 记录。
   - 支持不同的线路（如默认、电信、移动等）。

2. **基于 CSV 文件的测速输入**：
   - 从 Cloudflare Speed Test 结果的 CSV 文件中提取性能最优的 IP。

3. **华为云 DNS 集成**：
   - 自动获取并更新华为云上的 DNS 记录。
   - 检测并删除重复的 DNS 记录。

4. **可定制化配置**：
   - 使用 YAML 配置文件轻松设置域名、记录类型和线路信息。

5. **详细日志记录**：
   - 采用 `loguru` 进行日志管理，支持日志轮替与保存。

---

## 环境依赖

- **Python 版本**：Python 3.8 及以上
- **依赖库**：
  - `huaweicloudsdkcore`
  - `huaweicloudsdkdns`
  - `pandas`
  - `pyyaml`
  - `loguru`

可以使用以下命令安装所需依赖：

```bash
pip install huaweicloudsdkcore huaweicloudsdkdns pandas pyyaml loguru
```

---

## 使用步骤

### 1. 配置文件 `config.yaml`

在根目录创建 `config.yaml` 文件，示例格式如下：

```yaml
huawei_cloud:
  access_key_id: "your-access-key-id"
  access_key_secret: "your-access-key-secret"
  region: "your-region"  # 华为云的区域，例如 cn-north-1
  domains:
    - domain_name: "example.com"
      target_name: "sub.example.com"
      line: "default"
      type: "A"
      csv_file: "speedtest_results.csv"
    - domain_name: "anotherdomain.com"
      target_name: "sub.anotherdomain.com"
      line: "telecom"
      type: "A"
      csv_file: "speedtest_results_telecom.csv"

csv:
  n_rows: 5  # 提取 CSV 文件中的前 n 行数据作为目标 IP
```

### 2. CSV 文件

在配置文件中指定的路径提供 Cloudflare Speed Test 的结果文件。例如，`speedtest_results.csv` 的格式：

```csv
ip,speed
1.1.1.1,100
8.8.8.8,95
9.9.9.9,90
```

程序将按照速度排序，提取前 n 行的 IP。

### 3. 运行程序

使用以下命令运行程序：

```bash
python main.py
```

程序会自动读取配置文件、处理域名信息，并同步结果到华为云 DNS。

---

## 日志

程序会在运行目录生成日志文件 `dns_management.log`，包括详细的运行信息、错误记录以及操作结果。

---

## 项目结构

```plaintext
├── main.py             # 主程序代码
├── config.yaml         # 配置文件
├── speedtest_results.csv  # CSV 文件（示例）
├── dns_management.log  # 日志文件
```

---

## 注意事项

1. 确保华为云账户有足够的权限管理 DNS。
2. `config.yaml` 中的访问密钥和域名配置信息务必保密。
3. 如需更新特定线路的记录，请正确填写 `line` 值（例如 `default`、`telecom`）。

---
