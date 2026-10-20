# 本批实际使用的已安装 Skill 入口与步骤，供复核。
# 这些是执行记录；批次已经存在，请勿直接向同目录重复执行 init/import。
# 原始网页没有在本轮重新抓取。人工复核步骤需由执行者真实阅读后完成。
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'D:\7-Short project'
$feedbackPython = '.\.venv\Scripts\python.exe'
$feedbackEntry = 'C:\Users\1\.codex\skills\app-review-feedback\scripts\run_feedback.py'
$feedbackBatch = 'runs\skill_reproduction_2026-10-19'

& $feedbackPython -B $feedbackEntry init --root $feedbackBatch --since 2026-04-19 --as-of 2026-10-19
& $feedbackPython -B $feedbackEntry import --root $feedbackBatch --input 'data\merged_2026-10-19\master_all_reviews.json' --evidence-root 'D:\7-Short project' --coverage-note '复现验证：导入原项目保存的全部 5278 条快照及原始响应；本轮未重新联网采集或识别语言。Apple 为当时香港公共 RSS 每应用 500 条，Google 为当时地区／语言参数返回样本；均不保证评论全集。'
& $feedbackPython -B $feedbackEntry prepare --root $feedbackBatch
& $feedbackPython -B $feedbackEntry qa --root $feedbackBatch
& $feedbackPython -B $feedbackEntry analyze --root $feedbackBatch

# 在这里真实阅读 validation_sample.csv 的全部 10 条样本，
# 并填写 manual_review.json；本批记录已保存，禁止用脚本伪造复核。
& $feedbackPython -B $feedbackEntry review-status --root $feedbackBatch
& $feedbackPython -B $feedbackEntry build --root $feedbackBatch
& $feedbackPython -B $feedbackEntry verify --root $feedbackBatch
& $feedbackPython -B $feedbackEntry browser-test --root $feedbackBatch

# 浏览器首次因沙箱临时文件访问失败，随后通过产品提权批准运行成功。
# 查看三张截图后，执行独立对照，再完成本批 E/F 与交付清单。
& $feedbackPython -B 'runs\skill_reproduction_2026-10-19\compare_with_original.py'
& $feedbackPython -B $feedbackEntry finalize --root $feedbackBatch
