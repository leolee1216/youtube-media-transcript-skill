#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


REPLACEMENTS = [
    ("这是初学者的Codex指南。", "这是面向初学者的 Codex 终极指南。"),
    ("我的名字是大卫·安德烈 我花了一千多小时 和AI的编码。", "我叫 David Andre，已经花了上千小时用 AI 编程。"),
    ("我还用Codex来建立Vectal, 我的AI启动, 去年获得的7位数。", "我还用 Codex 打造了我的 AI 初创公司 Vectal，并在去年以七位数价格被收购。"),
    ("我是第一个在YouTube上 开始教 Codex的人之一", "我是 YouTube 上最早开始讲解 Codex 的人之一。"),
    ("我帮助成千上万的人学会了如何使用 Codex", "我已经帮助成千上万的人学会如何使用 Codex。"),
    ("如果他们能做到,你也能做到", "如果他们能做到，你也一定可以。"),
    ("现在,为了开始使用 Codex, 你不需要任何编码经验。", "现在开始使用 Codex，你不需要任何编程经验。"),
    ("我将一步一步地告诉你每件事", "我会一步一步带你过完整个流程。"),
    ("到这门课结束时 你就能造出任何东西", "学完这门课后，你将能够构建任何东西。"),
    ("您将有能力将任何想法转换成真正的软件应用程序", "你将有能力把任何想法变成真正的软件应用。"),
    ("在不到一个小时的时间里 互联网上完全被安装了", "并且在不到一个小时内把它完整部署到互联网上。"),
    ("法典也会让你更富有生产力", "Codex 还会让你效率大幅提升。"),
    ("不仅仅是在生活和生意的多数领域进行编码。", "而且不只是写代码，在生活和商业的很多场景里都一样。"),
    ("我知道,因为我说话 经验。", "这一点我很有发言权，因为这就是我的亲身经验。"),
    ("这就是我们将要覆盖的。", "接下来我们会覆盖这些内容。"),
    ("首先,基本原理。", "首先是基础部分。"),
    ("安装编码, 设置环境,", "安装 Codex、配置环境，"),
    ("我的个人Codex设置, 并理解它是如何在 IDE 内部工作。", "我的个人 Codex 配置，以及它在 IDE 中的工作方式。"),
    ("然后我们一起从头开始 建造一个真正的应用程序 并让它正常运行", "然后我们会一起从零开始做一个真实应用，并把它部署上线。"),
    ("因此,它可以在互联网上提供 你的朋友,家人,或潜在客户。", "这样你的朋友、家人或潜在客户都可以在互联网上访问它。"),
    ("我们只要说普通的英语, Codex,就可以完成所有这一切。", "而这一切，我们只需要用自然语言对 Codex 下指令就能完成。"),
    ("在那之后,我们将去 先进的东西。", "之后我们会进入更进阶的部分。"),
    ("分剂、技能、自动化、草木、MCP服务器、", "包括子代理、技能、自动化、Git worktrees、MCP 服务器，"),
    ("和更多的高压剂。", "以及更多高级能力。"),
    ("是的,这真的是终极编码指南", "没错，这真的就是一份终极 Codex 指南。"),
    ("所以,让我们开始吧。", "所以，我们开始吧。"),
    ("现在,实际上有四种不同的使用 Codex的方法。", "实际上，使用 Codex 一共有四种不同方式。"),
    ("这是OpenAI的正式文件。", "这是 OpenAI 的官方文档。"),
    ("我要把它连接到视频下面", "我会把它放在视频下方的说明里。"),
    ("幸运的是,有一个简单的单线安装命令,对吧?", "幸运的是，它有一个很简单的一行安装命令。"),
    ("所以如果我们复制这个 然后打开你的终端", "所以如果我们复制这条命令，然后打开终端，"),
    ("通过在麦克风OS上的焦点搜索键入终端可以做到这一点", "在 macOS 上你可以通过 Spotlight 搜索“Terminal”来打开它。"),
    ("或按 Windows 键, 按 Windows + R 键入 CMD 键入 。", "在 Windows 上，可以按 `Windows + R` 然后输入 `cmd`。"),
    ("但打开终端,复制此命令, 并粘贴这个在,繁荣。", "打开终端，复制这条命令，粘贴进去就行了。"),
    ("这将在您的机器上安装编码 CLI 。", "这会在你的机器上安装 Codex CLI。"),
    ("在那之后,我们需要做的就是简单地输入编码", "装好之后，我们只需要直接输入 `codex`。"),
    ("发射CodexCLI", "这样就会启动 Codex CLI。"),
]


def polish_text(text: str) -> str:
    fixed = text
    for old, new in REPLACEMENTS:
        fixed = fixed.replace(old, new)

    fixed = fixed.replace("CodexCLI", "Codex CLI")
    fixed = fixed.replace("YouTube上", "YouTube 上")
    fixed = fixed.replace("OpenAI的", "OpenAI 的")
    fixed = fixed.replace("Codex的人", "Codex 的人")

    fixed = re.sub(r"\s+,", "，", fixed)
    fixed = re.sub(r"\s+\.", "。", fixed)
    fixed = fixed.replace(",", "，")
    fixed = fixed.replace("?", "？")
    fixed = fixed.replace("!", "！")
    fixed = fixed.replace("，。", "。")
    fixed = fixed.replace("。。", "。")

    fixed = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", fixed)
    fixed = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[A-Za-z])", " ", fixed)
    fixed = re.sub(r"(?<=[A-Za-z])\s+(?=[\u4e00-\u9fff])", " ", fixed)
    fixed = re.sub(r"\s{2,}", " ", fixed).strip()

    if fixed and fixed[-1] not in "。！？…":
        fixed += "。"
    return fixed


def polish_srt(input_path: Path, output_path: Path) -> None:
    text = input_path.read_text(encoding="utf-8", errors="replace")
    blocks = [block for block in text.split("\n\n") if block.strip()]
    out_blocks = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            out_blocks.append(block)
            continue
        head = lines[:2]
        body = "\n".join(lines[2:]).strip()
        body = polish_text(body)
        out_blocks.append("\n".join(head + [body]))
    output_path.write_text("\n\n".join(out_blocks) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: polish_zh_srt.py <input.srt> <output.srt>", file=sys.stderr)
        return 2
    polish_srt(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
