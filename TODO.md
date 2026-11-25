# TODO · 未完成项（不假装完成）

## 1. Google Fact Check API —— 待用户自备 Key
- 状态：**未接入**。`factchecktools.googleapis.com` 的 claims:search / claims:imageSearch 需用户自备 Google Cloud API Key，本技能不代办、不索要密钥。
- 无 Key 时的 v1 做法：L0 已判库改用 **Fact Check Explorer 网页人工查 + 搜索代查**，并在门禁报告/证据卡备注中标注「已判库为人工查，非 API」。
- 下一步：用户备好 Key 后，另走连接器审计流程做薄封装，再把人工查替换为 API 查。

## 2. MiniCheck 中文实测 —— 未跑通（卡点记录，2026-11-25）
- 计划：MiniCheck-Flan-T5-Large（0.8B）对 20 条中文样本（证据原文, 旁白句）测判准率，再定是否作本地主裁。
- 本次最小实验实测（本机 VM）：
  - `minicheck` 包本身可下载（pip download 成功，0.4.0 wheel 56 KB）；
  - 但本机无 `transformers`/`torch`（`import transformers` → ModuleNotFoundError），且模型权重约 3 GB 级，超出本机 /tmp 配额与当前环境，**未实际加载模型、未跑任何样本，不报跑通**。
- 下一步（不阻塞 v1）：在 Windows 主力机（RTX 3070 Ti）或 Colab 建独立 venv 装 transformers+torch，下权重后跑 20 条中文样本，判准率达标才启用为 L1.5 本地裁决；在此之前 L2 裁决走异源 LLM（GLM/Gemini）对证据卡原文判支持度。

## 3. 阶段二待并入
- 出片后视听 QA 条目（textbbox 高光 / Tofu 防缺字 / 抽帧复核）阶段二并入 SKILL.md 占位节。
- domain-quality 域名先验表仅作内部参考，未随技能分发。
