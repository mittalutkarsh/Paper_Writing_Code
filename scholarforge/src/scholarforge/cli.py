"""CLI Entry Point — Typer-based."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import load_config, create_default_config
from .pipeline import Pipeline
from .utils.logger import setup_logging
from .repo_reader import RepoContext

app = typer.Typer(name="scholarforge", help="Autonomous academic research paper pipeline")
console = Console()


def _get_output_dir(config_path: str) -> Path:
    """Get output directory from config."""
    try:
        config = load_config(config_path)
        return Path(config.project.output_dir)
    except Exception:
        return Path("./output")


@app.command()
def run(
    topic: str = typer.Option(..., help="Research topic"),
    config: str = typer.Option("config.yaml", help="Config file path"),
    auto_approve: bool = typer.Option(False, help="Skip all human approval gates"),
    readme: str = typer.Option(None, help="Path to README file to include as context"),
    code_repo: str = typer.Option(None, help="Path to code repository to analyze"),
    code_extensions: str = typer.Option(".py,.js,.ts,.java,.cpp,.c,.go,.rs", help="File extensions to include from code repo"),
):
    """Run the full pipeline from scratch."""
    console.print(f"[bold blue]ScholarForge[/bold blue] - Research Paper Pipeline")
    console.print(f"Topic: {topic}")
    if readme:
        console.print(f"README: {readme}")
    if code_repo:
        console.print(f"Code Repository: {code_repo}")
    console.print()
    
    # Load configuration
    try:
        cfg = load_config(config)
        if auto_approve:
            cfg.human_in_the_loop.auto_approve = True
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    
    # Setup logging
    setup_logging(
        level=cfg.logging.level,
        log_file=cfg.logging.file,
        console=False  # Rich handles console output
    )
    
    # Load repo context if provided
    repo_context = None
    if readme or code_repo:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Reading repository files...", total=None)
            
            try:
                repo_context = RepoContext.from_paths(
                    readme_path=readme,
                    code_repo_path=code_repo,
                    code_extensions=code_extensions.split(",") if code_extensions else None
                )
                console.print(f"[green]Loaded repo context:[/green]")
                console.print(f"  README: {len(repo_context.readme_content)} chars")
                console.print(f"  Code files: {len(repo_context.code_files)} files")
                console.print(f"  Total code: {sum(len(f['content']) for f in repo_context.code_files)} chars")
                console.print()
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load repo context: {e}[/yellow]")
                console.print()
    
    # Run pipeline
    pipeline = Pipeline(cfg)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running pipeline...", total=None)
        
        try:
            result = pipeline.run(topic, repo_context=repo_context)
        except Exception as e:
            console.print(f"[red]Pipeline failed: {e}[/red]")
            raise typer.Exit(1)
    
    # Display results
    if result.get("status") == "paused":
        console.print(f"[yellow]Pipeline paused at gate: {result['gate']}[/yellow]")
        console.print(f"Run ID: {result['run_id']}")
        
        if result.get('missing_md_path'):
            console.print(f"\nPlease edit: {result['missing_md_path']}")
        
        console.print(f"\nTo resume, run:")
        console.print(f"[green]scholarforge resume --run-id {result['run_id']} --config {config}[/green]")
    else:
        console.print(f"[green]Pipeline complete![/green]")
        console.print(f"Run ID: {result['run_id']}")
        console.print(f"Output directory: {result['output_dir']}")


@app.command()
def resume(
    run_id: str = typer.Option(..., help="Run ID to resume"),
    config: str = typer.Option("config.yaml", help="Config file path"),
    readme: str = typer.Option(None, help="Path to README file (if not provided during run)"),
    code_repo: str = typer.Option(None, help="Path to code repository (if not provided during run)"),
    code_extensions: str = typer.Option(".py,.js,.ts,.java,.cpp,.c,.go,.rs", help="File extensions to include from code repo"),
):
    """Resume a paused pipeline from where it stopped."""
    console.print(f"[bold blue]ScholarForge[/bold blue] - Resuming Pipeline")
    console.print(f"Run ID: {run_id}")
    if readme:
        console.print(f"README: {readme}")
    if code_repo:
        console.print(f"Code Repository: {code_repo}")
    console.print()
    
    # Load configuration
    try:
        cfg = load_config(config)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    
    # Setup logging
    setup_logging(
        level=cfg.logging.level,
        log_file=cfg.logging.file,
        console=False
    )
    
    # Load repo context if provided
    repo_context = None
    if readme or code_repo:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Reading repository files...", total=None)
            
            try:
                repo_context = RepoContext.from_paths(
                    readme_path=readme,
                    code_repo_path=code_repo,
                    code_extensions=code_extensions.split(",") if code_extensions else None
                )
                console.print(f"[green]Loaded repo context:[/green]")
                console.print(f"  README: {len(repo_context.readme_content)} chars")
                console.print(f"  Code files: {len(repo_context.code_files)} files")
                console.print()
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load repo context: {e}[/yellow]")
                console.print()
    
    # Resume pipeline
    pipeline = Pipeline(cfg)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Resuming pipeline...", total=None)
        
        try:
            result = pipeline.resume(run_id, repo_context=repo_context)
        except Exception as e:
            import traceback
            console.print(f"[red]Pipeline failed: {e}[/red]")
            console.print(traceback.format_exc())
            raise typer.Exit(1)
    
    # Display results
    if result.get("status") == "paused":
        console.print(f"[yellow]Pipeline paused at gate: {result['gate']}[/yellow]")
        console.print(f"\nTo resume, run:")
        console.print(f"[green]scholarforge resume --run-id {result['run_id']} --config {config}[/green]")
    else:
        console.print(f"[green]Pipeline complete![/green]")
        console.print(f"Output directory: {result['output_dir']}")


@app.command()
def status(
    run_id: str = typer.Option(..., help="Run ID to check"),
    config: str = typer.Option("config.yaml", help="Config file path"),
):
    """Show current pipeline status."""
    output_dir = _get_output_dir(config)
    state_path = output_dir / "pipeline_state.json"
    
    if not state_path.exists():
        console.print(f"[red]No pipeline state found for run_id: {run_id}[/red]")
        raise typer.Exit(1)
    
    with open(state_path) as f:
        state = json.load(f)
    
    if state.get("run_id") != run_id:
        console.print(f"[red]Run ID mismatch[/red]")
        raise typer.Exit(1)
    
    # Display status table
    table = Table(title=f"Pipeline Status: {run_id}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Run ID", state["run_id"])
    table.add_row("Created", state["created_at"])
    table.add_row("Current Stage", str(state["current_stage"]))
    table.add_row("Topic", state.get("topic", "N/A")[:50] + "...")
    
    console.print(table)
    
    # Display stage statuses
    if state.get("stage_statuses"):
        console.print("\n[bold]Stage Statuses:[/bold]")
        for stage, status in state["stage_statuses"].items():
            console.print(f"  {stage}: {status}")


@app.command()
def verify(
    bib: str = typer.Option(..., help="Path to .bib file to verify"),
    config: str = typer.Option("config.yaml", help="Config file path"),
):
    """Standalone: run 4-layer verification on an existing .bib file."""
    console.print(f"[bold blue]ScholarForge[/bold blue] - Citation Verification")
    console.print(f"Bib file: {bib}")
    console.print()
    
    # Load configuration
    try:
        cfg = load_config(config)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    
    # TODO: Parse .bib file and run verification
    console.print("[yellow]Not yet implemented[/yellow]")


@app.command()
def review(
    draft: str = typer.Option(..., help="Path to paper draft .md file"),
    config: str = typer.Option("config.yaml", help="Config file path"),
):
    """Standalone: run multi-agent peer review on an existing draft."""
    console.print(f"[bold blue]ScholarForge[/bold blue] - Peer Review")
    console.print(f"Draft: {draft}")
    console.print()
    
    # Load configuration
    try:
        cfg = load_config(config)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    
    # TODO: Load draft and run peer review
    console.print("[yellow]Not yet implemented[/yellow]")


@app.command()
def init(
    output: str = typer.Option("config.yaml", help="Output config file path"),
):
    """Create a new config.yaml from the example template."""
    if Path(output).exists():
        overwrite = typer.confirm(f"{output} already exists. Overwrite?")
        if not overwrite:
            console.print("Cancelled.")
            raise typer.Exit(0)
    
    create_default_config(output)
    console.print(f"[green]Created config file: {output}[/green]")
    console.print("\nPlease edit the file to configure:")
    console.print("  - Your LLM provider and API key")
    console.print("  - Research topic")
    console.print("  - Output directory")


if __name__ == "__main__":
    app()
