#!/usr/bin/env python3
"""
VITA QA Agent CLI - Enhanced Test Case Generation Tool (v2 consolidated)

特性:
- 支持多个PRD文件输入
- 支持URI (本地路径或HTTP URL)
- 可配置的LLM提示词
- 增强的错误处理
- 支持实体化为DB/ES对象
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
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
from src.entities import MaterializedBundle, materialize_generation_outputs
from src.utils.logger import setup_logger
from src.utils.file_utils import (
    write_json_file,
    write_jsonl_file,
    write_markdown_file,
    generate_output_filename,
)
from src.utils.file_loader import load_multiple_prds, load_content_from_uri, merge_prd_contents
from src.utils.config_loader import get_config_loader
from src.utils.exceptions import QAAgentError, FileOperationError, ConfigurationError

app = typer.Typer(help="VITA QA Agent - 自动化测试用例生成工具 (v2 consolidated)")
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
    prd: List[str] = typer.Option(..., "--prd", "-p", help="PRD文档路径或URL (支持多个，可重复使用 --prd)"),
    output_dir: str = typer.Option("outputs", "--output", "-o", help="输出目录"),
    project_name: Optional[str] = typer.Option(None, "--project", help="项目名称"),
    metric: Optional[str] = typer.Option(None, "--metric", "-m", help="Metric文档路径或URL (可选)"),
    principles: Optional[str] = typer.Option(None, "--principles", help="用例拆解原则文档路径或URL (可选)"),
    prompts_config: Optional[str] = typer.Option(None, "--prompts-config", help="自定义提示词配置文件路径"),
    model_provider: str = typer.Option("auto", "--provider", help="模型提供商 (auto/doubao/g2m)"),
    save_rule: bool = typer.Option(True, "--save-rule", help="是否保存生成的walkthrough rule"),
    merge_prds: bool = typer.Option(True, "--merge-prds", help="是否合并多个PRD为单一文档"),
    materialize: bool = typer.Option(True, "--materialize/--no-materialize", help="是否将输出实体化为DB/ES对象并落盘"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """
    从PRD文档生成测试用例 (支持多文件和URI输入)

    示例:
        # 单个本地文件
        python cli/main.py generate --prd metric/识人识物_用例设计原则与示例.md

        # 多个本地文件
        python cli/main.py generate --prd prd1.md --prd prd2.md --project multi_module

        # 从URL加载
        python cli/main.py generate --prd https://example.com/prd.md --project remote

        # 混合本地和远程
        python cli/main.py generate --prd local.md --prd https://example.com/remote.md
    """
    # Load environment
    load_env()

    # Setup logger
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logger(level=log_level)

    console.print("\n[bold cyan]VITA QA Agent - 增强版测试用例生成[/bold cyan]\n")

    try:
        # Load custom prompts config if provided
        if prompts_config:
            try:
                config_loader = get_config_loader(Path(prompts_config).parent)
                console.print(f"[green]✓[/green] 使用自定义提示词配置: {prompts_config}")
            except Exception as e:
                console.print(f"[yellow]![/yellow] 无法加载自定义配置，使用默认配置: {e}")

        # Step 1: Load PRD files (support multiple and URI)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task(f"加载 {len(prd)} 个PRD文档...", total=None)

            try:
                prds = load_multiple_prds(prd)
            except FileOperationError as e:
                console.print(f"\n[bold red]✗ 加载PRD失败: {e}[/bold red]")
                raise typer.Exit(code=1)

            # Get project name from first PRD if not provided
            if not project_name:
                project_name = prds[0]["name"]

            # Load metric if provided
            metric_content = None
            if metric:
                progress.update(task, description="加载Metric文档...")
                try:
                    metric_content = load_content_from_uri(metric)
                except FileOperationError as e:
                    console.print(f"[yellow]![/yellow] 无法加载Metric文档: {e}")

            # Load principles if provided
            principles_content = None
            if principles:
                progress.update(task, description="加载拆解原则...")
                try:
                    principles_content = load_content_from_uri(principles)
                except FileOperationError as e:
                    console.print(f"[yellow]![/yellow] 无法加载拆解原则: {e}")

        # Display loaded PRDs
        console.print(f"\n[green]✓[/green] 成功加载 {len(prds)} 个PRD文档:")
        for i, prd_info in enumerate(prds, 1):
            console.print(f"  {i}. {prd_info['name']} ({prd_info['uri']})")

        if metric:
            console.print(f"[green]✓[/green] Metric文档已加载")
        if principles:
            console.print(f"[green]✓[/green] 拆解原则已加载")

        # Merge PRDs if needed
        if len(prds) > 1 and merge_prds:
            console.print(f"\n[bold]合并 {len(prds)} 个PRD文档...[/bold]")
            prd_content = merge_prd_contents(prds)
        else:
            prd_content = prds[0]["content"]

        # Step 2: Initialize model client
        console.print(f"\n[bold]初始化模型客户端 ({model_provider})...[/bold]")
        try:
            model_client = get_default_client()
            console.print(f"[green]✓[/green] 模型客户端初始化完成")
        except Exception as e:
            console.print(f"\n[bold red]✗ 模型客户端初始化失败: {e}[/bold red]")
            raise typer.Exit(code=1)

        # Step 3: Parse requirements
        console.print(f"\n[bold]解析需求文档...[/bold]")
        parser = RequirementParser(model_client)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("分析PRD内容...", total=None)
            try:
                parsed_req = parser.parse(
                    prd_content=prd_content,
                    metric_content=metric_content,
                    project_name=project_name,
                )
            except QAAgentError as e:
                console.print(f"\n[bold red]✗ 需求解析失败: {e}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                raise typer.Exit(code=1)

        console.print(f"[green]✓[/green] 需求解析完成")
        console.print(f"  - 模块数量: {len(parsed_req.modules)}")
        for module in parsed_req.modules:
            console.print(f"    • {module.name} ({len(module.features)} 个功能)")

        # Step 4: Generate walkthrough rule
        console.print(f"\n[bold]生成Walkthrough Rule...[/bold]")
        rule_gen = RuleGenerator(model_client)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("生成用例生成规则...", total=None)
            try:
                walkthrough_rule = rule_gen.generate_rule(
                    parsed_requirement=parsed_req,
                    decomposition_principles=principles_content,
                    metric_definitions=metric_content,
                )
            except QAAgentError as e:
                console.print(f"\n[bold red]✗ 规则生成失败: {e}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                raise typer.Exit(code=1)

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
            try:
                result = case_gen.generate_testcases(
                    parsed_requirement=parsed_req,
                    walkthrough_rule=walkthrough_rule,
                )
            except QAAgentError as e:
                console.print(f"\n[bold red]✗ 用例生成失败: {e}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                raise typer.Exit(code=1)

        testcases = result["testcases"]
        scenes = result["scenes"]
        scene_mappings = result["scene_mappings"]

        bundle: Optional[MaterializedBundle] = None
        if materialize:
            bundle = materialize_generation_outputs(
                result,
                output_dir=str(Path(output_dir) / "testcases"),
            )

        if bundle:
            console.print(f"  - 已实体化: {len(bundle.test_cases)} 条DB用例, {len(bundle.index_docs)} 条ES文档")

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

        # Save DB entities and ES docs
        if bundle:
            db_cases_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="db_testcases",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(
                str(db_cases_jsonl),
                [case.model_dump() for case in bundle.test_cases],
            )
            console.print(f"[green]✓[/green] DB用例JSONL: {db_cases_jsonl}")

            db_scenes_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="db_scenes",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(
                str(db_scenes_jsonl),
                [scene.model_dump() for scene in bundle.scenes],
            )
            console.print(f"[green]✓[/green] DB场景JSONL: {db_scenes_jsonl}")

            db_scene_mappings_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="db_scene_mappings",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(
                str(db_scene_mappings_jsonl),
                [mapping.model_dump() for mapping in bundle.scene_mappings],
            )
            console.print(f"[green]✓[/green] DB场景映射JSONL: {db_scene_mappings_jsonl}")

            db_relations_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="db_relations",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(
                str(db_relations_jsonl),
                [relation.model_dump() for relation in bundle.relations],
            )
            console.print(f"[green]✓[/green] DB关系JSONL: {db_relations_jsonl}")

            es_docs_jsonl = output_path / "testcases" / generate_output_filename(
                prefix="es_docs",
                suffix="jsonl",
                project_name=project_name,
            )
            write_jsonl_file(
                str(es_docs_jsonl),
                [doc.model_dump() for doc in bundle.index_docs],
            )
            console.print(f"[green]✓[/green] ES文档JSONL: {es_docs_jsonl}")

        # Save Markdown summary
        md_content = generate_markdown_summary(
            project_name=project_name,
            parsed_req=parsed_req,
            testcases=clean_testcases,
            scenes=scenes,
            prds=prds,
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

    except typer.Exit:
        raise
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
    prds: list = None,
) -> str:
    """Generate Markdown summary report."""
    lines = [
        f"# 测试用例生成报告 - {project_name}",
        "",
        f"生成时间: {testcases[0]['create_time'] if testcases else 'N/A'}",
        "",
    ]

    # PRD sources
    if prds and len(prds) > 1:
        lines.extend([
            "## PRD来源",
            "",
        ])
        for i, prd_info in enumerate(prds, 1):
            lines.append(f"{i}. **{prd_info['name']}**: {prd_info['uri']}")
        lines.append("")

    lines.extend([
        "## 统计信息",
        "",
        f"- **项目名称**: {project_name}",
        f"- **PRD数量**: {len(prds) if prds else 1}",
        f"- **模块数量**: {len(parsed_req.modules)}",
        f"- **测试用例总数**: {len(testcases)}",
        f"- **场景数量**: {len(scenes)}",
        "",
        "## 模块列表",
        "",
    ])

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
    console.print("[bold cyan]VITA QA Agent v2[/bold cyan]")
    console.print("版本: 0.2.0")
    console.print("描述: 增强版自动化测试用例生成工具")
    console.print("\n新特性:")
    console.print("  • 支持多个PRD文件")
    console.print("  • 支持URI输入 (本地路径或HTTP URL)")
    console.print("  • 可配置的LLM提示词")
    console.print("  • 增强的错误处理")


if __name__ == "__main__":
    app()
