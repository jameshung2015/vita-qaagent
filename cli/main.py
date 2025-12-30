#!/usr/bin/env python3
"""
VITA QA Agent CLI - Test Case Generation Tool

主命令行入口，支持从PRD自动生成测试用例
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.model_factory import get_default_client
from src.agents.requirement_parser import RequirementParser
from src.agents.rule_generator import RuleGenerator
from src.agents.testcase_generator import TestCaseGenerator
from src.utils.logger import setup_logger
from src.utils.file_utils import (
    read_markdown_file,
    write_json_file,
    write_jsonl_file,
    write_markdown_file,
    generate_output_filename,
)

app = typer.Typer(help="VITA QA Agent - 自动化测试用例生成工具")
console = Console()


def load_env():
    """Load environment variables from config/.env"""
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        console.print(f"[green]✓[/green] 已加载环境配置: {env_path}")
    else:
        console.print(f"[yellow]![/yellow] 未找到配置文件: {env_path}")


@app.command()
def generate(
    prd: str = typer.Option(..., "--prd", "-p", help="PRD文档路径 (Markdown格式)"),
    output_dir: str = typer.Option("outputs", "--output", "-o", help="输出目录"),
    project_name: Optional[str] = typer.Option(None, "--project", help="项目名称"),
    metric: Optional[str] = typer.Option(None, "--metric", "-m", help="Metric文档路径 (可选)"),
    principles: Optional[str] = typer.Option(None, "--principles", help="用例拆解原则文档路径 (可选)"),
    model_provider: str = typer.Option("auto", "--provider", help="模型提供商 (auto/doubao/g2m)"),
    save_rule: bool = typer.Option(True, "--save-rule", help="是否保存生成的walkthrough rule"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """
    从PRD文档生成测试用例

    示例:
        python cli/main.py generate --prd metric/识人识物_用例设计原则与示例.md --project recognition
    """
    # Load environment
    load_env()

    # Setup logger
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logger(level=log_level)

    console.print("\n[bold cyan]VITA QA Agent - 测试用例生成[/bold cyan]\n")

    try:
        # Step 1: Read input files
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("读取PRD文档...", total=None)

            prd_content = read_markdown_file(prd)

            # Get project name from file if not provided
            if not project_name:
                project_name = Path(prd).stem

            metric_content = None
            if metric:
                progress.update(task, description="读取Metric文档...")
                metric_content = read_markdown_file(metric)

            principles_content = None
            if principles:
                progress.update(task, description="读取拆解原则...")
                principles_content = read_markdown_file(principles)

        console.print(f"[green]✓[/green] PRD文档读取完成: {prd}")
        if metric:
            console.print(f"[green]✓[/green] Metric文档读取完成: {metric}")

        # Step 2: Initialize model client
        console.print(f"\n[bold]初始化模型客户端 ({model_provider})...[/bold]")
        model_client = get_default_client()
        console.print(f"[green]✓[/green] 模型客户端初始化完成")

        # Step 3: Parse requirements
        console.print(f"\n[bold]解析需求文档...[/bold]")
        parser = RequirementParser(model_client)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("分析PRD内容...", total=None)
            parsed_req = parser.parse(
                prd_content=prd_content,
                metric_content=metric_content,
                project_name=project_name,
            )

        console.print(f"[green]✓[/green] 需求解析完成")
        console.print(f"  - 模块数量: {len(parsed_req.modules)}")
        for module in parsed_req.modules:
            console.print(f"    • {module.name} ({len(module.features)} 个功能)")

        # Step 4: Generate walkthrough rule
        console.print(f"\n[bold]生成Walkthrough Rule...[/bold]")
        rule_gen = RuleGenerator(model_client)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("生成用例生成规则...", total=None)
            walkthrough_rule = rule_gen.generate_rule(
                parsed_requirement=parsed_req,
                decomposition_principles=principles_content,
                metric_definitions=metric_content,
            )

        console.print(f"[green]✓[/green] Walkthrough Rule生成完成")
        console.print(f"  - 规则ID: {walkthrough_rule.get('rule_id')}")
        console.print(f"  - 场景维度: {len(walkthrough_rule.get('scenario_dimensions', []))} 个")

        # Save rule if requested
        if save_rule:
            rule_file = Path(output_dir) / "rules" / generate_output_filename(
                prefix="rule",
                suffix="json",
                project_name=project_name,
            )
            write_json_file(str(rule_file), walkthrough_rule)
            console.print(f"[green]✓[/green] Rule已保存: {rule_file}")

        # Step 5: Generate test cases
        console.print(f"\n[bold]生成测试用例...[/bold]")
        case_gen = TestCaseGenerator(model_client)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("生成测试用例...", total=None)
            result = case_gen.generate_testcases(
                parsed_requirement=parsed_req,
                walkthrough_rule=walkthrough_rule,
            )

        testcases = result["testcases"]
        scenes = result["scenes"]
        scene_mappings = result["scene_mappings"]

        console.print(f"[green]✓[/green] 测试用例生成完成")
        console.print(f"  - 用例数量: {len(testcases)}")
        console.print(f"  - 场景数量: {len(scenes)}")

        # Step 6: Save output files
        console.print(f"\n[bold]保存输出文件...[/bold]")

        output_path = Path(output_dir)

        # Save test cases JSONL
        testcases_jsonl = output_path / "testcases" / generate_output_filename(
            prefix="testcases",
            suffix="jsonl",
            project_name=project_name,
        )
        # Remove metadata before saving
        clean_testcases = []
        for tc in testcases:
            tc_copy = tc.copy()
            tc_copy.pop("_metadata", None)
            clean_testcases.append(tc_copy)

        write_jsonl_file(str(testcases_jsonl), clean_testcases)
        console.print(f"[green]✓[/green] 测试用例JSONL: {testcases_jsonl}")

        # Save scenes JSONL
        if scenes:
            scenes_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="scenes",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(str(scenes_jsonl), scenes)
            console.print(f"[green]✓[/green] 场景JSONL: {scenes_jsonl}")

        # Save scene mappings JSONL
        if scene_mappings:
            mappings_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="scene_mappings",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(str(mappings_jsonl), scene_mappings)
            console.print(f"[green]✓[/green] 场景映射JSONL: {mappings_jsonl}")

        # Save Markdown summary
        md_content = generate_markdown_summary(
            project_name=project_name,
            parsed_req=parsed_req,
            testcases=clean_testcases,
            scenes=scenes,
        )
        md_file = output_path / "reports" / generate_output_filename(
            prefix="summary",
            suffix="md",
            project_name=project_name,
        )
        write_markdown_file(str(md_file), md_content)
        console.print(f"[green]✓[/green] Markdown报告: {md_file}")

        # Success message
        console.print(f"\n[bold green]✓ 测试用例生成成功！[/bold green]")
        console.print(f"\n输出目录: [cyan]{output_path.absolute()}[/cyan]")

    except Exception as e:
        console.print(f"\n[bold red]✗ 错误: {e}[/bold red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(code=1)


def generate_markdown_summary(
    project_name: str,
    parsed_req,
    testcases: list,
    scenes: list,
) -> str:
    """Generate Markdown summary report."""
    lines = [
        f"# 测试用例生成报告 - {project_name}",
        "",
        f"生成时间: {testcases[0]['create_time'] if testcases else 'N/A'}",
        "",
        "## 统计信息",
        "",
        f"- **项目名称**: {project_name}",
        f"- **模块数量**: {len(parsed_req.modules)}",
        f"- **测试用例总数**: {len(testcases)}",
        f"- **场景数量**: {len(scenes)}",
        "",
        "## 模块列表",
        "",
    ]

    for module in parsed_req.modules:
        lines.append(f"### {module.name}")
        lines.append("")
        lines.append(f"**功能数量**: {len(module.features)}")
        lines.append("")
        for feature in module.features:
            lines.append(f"- {feature.name}")
        lines.append("")

    lines.extend([
        "## 测试用例列表",
        "",
        "| 用例ID | 用例名称 | 模块 | 优先级 | 等级 | 状态 |",
        "|--------|----------|------|--------|------|------|",
    ])

    for tc in testcases:
        lines.append(
            f"| {tc['case_id']} | {tc['title']} | {tc['module']} | "
            f"{tc['priority']} | {tc['level']} | {tc['status']} |"
        )

    if scenes:
        lines.extend([
            "",
            "## 场景列表",
            "",
            "| 场景ID | 场景名称 | 描述 |",
            "|--------|----------|------|",
        ])

        for scene in scenes:
            lines.append(
                f"| {scene['scene_id']} | {scene['scene_name']} | {scene.get('scene_desc', '')} |"
            )

    return "\n".join(lines)


@app.command()
def version():
    """显示版本信息"""
    console.print("[bold cyan]VITA QA Agent[/bold cyan]")
    console.print("版本: 0.1.0")
    console.print("描述: 自动化测试用例生成工具")


if __name__ == "__main__":
    app()
