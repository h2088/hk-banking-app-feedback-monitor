# 命令与调用

Python 3.10+。离线分析、导出、报告和静态检查使用标准库；联网采集另需 `assets/requirements-collection.txt` 中的两个锁定版本。浏览器检查另需已安装 Edge／Chrome／Chromium。不需要 API key、不调用 LLM API；执行 Skill 的 Codex 负责语义阅读和解释。

以下为 PowerShell。`$reviewSkill` 是本 Skill 所在目录；如果仍在项目内，也可设为 `D:\7-Short project\skills\app-review-feedback`。替换批次位置和日期后逐阶段执行，不把示例路径当成新一轮默认。

## 新采集

```powershell
$reviewSkill = 'C:\Users\1\.codex\skills\app-review-feedback'
$reviewBatch = 'D:\7-Short project\runs\feedback_2026-11-19'
$reviewPython = 'D:\7-Short project\.venv\Scripts\python.exe'
& $reviewPython -m pip install -r "$reviewSkill\assets\requirements-collection.txt"
& $reviewPython "$reviewSkill\scripts\run_feedback.py" init --root $reviewBatch --as-of 2026-11-19
& $reviewPython "$reviewSkill\scripts\run_feedback.py" collect --root $reviewBatch
```

已有依赖不要重复安装；缺失时按当前环境权限安装到合适虚拟环境。需要批准的联网／目录／浏览器权限按当前环境处理，不绕过。

不传 `--as-of` 使用当前香港日期，未传 `--since` 则往前六个日历月；两者可显式指定。自定义两款应用用 `init --apps <apps.json>`，格式参考 `assets/apps.json`：`key,name,bank,role,google_id,google_language,apple_id,apple_slug,apple_language`，Apple ID 必须是字符串。

`config.json` 可在采集／prepare 前调整页数、等待间隔、是否继续窗口以前的 Google 页和语言修订。Google 上限 1–500 页，Apple 1–10 页，等待 0.5–30 秒。脚本不支持非 HK、非英文或平台拆分报告；这些需求需明确适配。

## 导入已有快照

用同样的 `init` 创建另一目录，然后只选 `import`，不再 `collect`：

```powershell
& $reviewPython "$reviewSkill\scripts\run_feedback.py" import --root $reviewBatch --input 'D:\7-Short project\data\merged_2026-10-19\master_all_reviews.json' --evidence-root 'D:\7-Short project' --coverage-note '导入已存来源；本轮未重新联网。来源覆盖范围见原采集记录。'
```

`--evidence-root` 是输入相对 raw 路径的基准目录，所有引用必须留在该目录内。优先导入所有已取回语言的记录，这样可重新筛选日期和追踪排除理由；只导入英文窗口文件也可以，但必须说明可观察数据范围更窄。导入复用已有语言标签，如需更正，按方法文档添加精确修订。

## 共用处理与阅读

```powershell
& $reviewPython "$reviewSkill\scripts\run_feedback.py" prepare --root $reviewBatch
& $reviewPython "$reviewSkill\scripts\run_feedback.py" qa --root $reviewBatch
& $reviewPython "$reviewSkill\scripts\run_feedback.py" analyze --root $reviewBatch
Get-Content -Raw -Encoding UTF8 "$reviewBatch\data\analysis\validation_sample.json"
```

现在实际阅读全部样本，再编辑根目录 `manual_review.json`。保留 `sample_sha256`、所有唯一键和指纹；逐项填写：

```json
{
  "rating_assessment": "disagreement_noted",
  "theme_assessment": "plausible",
  "notes": "正文抱怨截图限制但给 4 星；星级映射正面，不能当成文本正面。功能建议主题符合内容。"
}
```

`rating_assessment` 取 `plausible` 或 `disagreement_noted`；`theme_assessment` 取 `plausible`、`insufficient_text` 或 `limitation_noted`。填写有内容的实际观察。读完后设顶层 `status=reviewed`、`reviewer`、`reviewed_at`；若由 agent 检查，应写明 agent，不能称为独立人工准确率验证。不要写自动循环把所有 pending 设为 plausible。

## 报告与交付

```powershell
& $reviewPython "$reviewSkill\scripts\run_feedback.py" review-status --root $reviewBatch
& $reviewPython "$reviewSkill\scripts\run_feedback.py" build --root $reviewBatch
& $reviewPython "$reviewSkill\scripts\run_feedback.py" verify --root $reviewBatch
& $reviewPython "$reviewSkill\scripts\run_feedback.py" browser-test --root $reviewBatch
# 读取 browser_test_results.json，实际查看 screenshots 中三张图后继续。
& $reviewPython "$reviewSkill\scripts\run_feedback.py" finalize --root $reviewBatch
```

其他浏览器路径通过 `browser-test --browser <executable>` 指定。测试失败先查结果与错误，修复后使用新批次重建；不要直接改 HTML 数字去让测试通过。仅测试工具失败且交付 HTML 未变，可修复工具后重跑对应测试。

最终入口 `report_customer_feedback.html`，总表在 `data/merged/master_english_six_months.csv` 与 `reviews_master.xlsx`，逐条标签在 `data/analysis/comment_labels.*`。A–F、plan、handover 在批次根目录；manifest 保存完整性信息。

## 用户直接调用示例

> 使用 $app-review-feedback，重新采集 SC Mobile Hong Kong 和 HSBC HK 的香港英文评论，分析截至 2026-11-19 的近六个月，HSBC 作 benchmark，合并商店报告，输出到 D:\7-Short project\runs\feedback_2026-11-19。

> 使用 $app-review-feedback，基于这次保存的 master_all_reviews.json 离线重做分析，不重新联网，改为观察 2026-09-01 到 2026-09-30，输出到新的批次目录。

> 使用 $app-review-feedback，检查这个已有批次到哪一步，只继续尚未完成的阶段。

Skill 是由 Codex 按说明执行的流程和脚本包；不是 Windows 调度任务。新装后若当前会话未发现名称，可新建会话，或直接要求读取本目录 `SKILL.md` 执行。
