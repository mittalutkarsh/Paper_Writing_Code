"""Comparison Chart Generator."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Try to use SciencePlots, fallback to default if not available
try:
    plt.style.use(['science', 'ieee'])
except Exception:
    logger.debug("SciencePlots not available, using default matplotlib style")


# Colorblind-safe palette (Paul Tol)
TOL_PALETTE = [
    '#4477AA', '#EE6677', '#228833', '#CCBB44', 
    '#66CCEE', '#AA3377', '#BBBBBB'
]


def generate_comparison_bar_chart(
    data: dict[str, list[float]],
    labels: list[str],
    ylabel: str,
    title: str,
    output_path: str,
    errors: dict[str, list[float]] | None = None,
    width: float = 3.5,  # IEEE single-column width in inches
    height: float = 2.625
) -> str:
    """Generate a comparison bar chart.
    
    Args:
        data: Dict of method_name -> list of values
        labels: X-axis labels
        ylabel: Y-axis label
        title: Chart title
        output_path: Output file path (PDF)
        errors: Optional dict of method_name -> error values
        width: Figure width in inches
        height: Figure height in inches
        
    Returns:
        Output file path
    """
    fig, ax = plt.subplots(figsize=(width, height))
    
    x = np.arange(len(labels))
    bar_width = 0.8 / len(data)
    
    for i, (method, values) in enumerate(data.items()):
        offset = (i - len(data) / 2 + 0.5) * bar_width
        color = TOL_PALETTE[i % len(TOL_PALETTE)]
        
        if errors and method in errors:
            ax.bar(x + offset, values, bar_width, label=method, 
                   color=color, yerr=errors[method], capsize=3)
        else:
            ax.bar(x + offset, values, bar_width, label=method, color=color)
    
    ax.set_xlabel('Dataset')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha='right')
    ax.legend(loc='best', frameon=True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.close()
    
    logger.info(f"Generated bar chart: {output_path}")
    return output_path


def generate_line_plot(
    data: dict[str, tuple[list[float], list[float]]],
    xlabel: str,
    ylabel: str,
    title: str,
    output_path: str,
    width: float = 3.5,
    height: float = 2.625
) -> str:
    """Generate a line plot.
    
    Args:
        data: Dict of method_name -> (x_values, y_values)
        xlabel: X-axis label
        ylabel: Y-axis label
        title: Chart title
        output_path: Output file path (PDF)
        width: Figure width in inches
        height: Figure height in inches
        
    Returns:
        Output file path
    """
    fig, ax = plt.subplots(figsize=(width, height))
    
    for i, (method, (x, y)) in enumerate(data.items()):
        color = TOL_PALETTE[i % len(TOL_PALETTE)]
        ax.plot(x, y, label=method, color=color, linewidth=1.5, marker='o', markersize=4)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc='best', frameon=True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.close()
    
    logger.info(f"Generated line plot: {output_path}")
    return output_path


def generate_charts(
    experiment_data: dict,
    output_dir: str,
    style: str = "ieee"
) -> list[dict]:
    """Generate all comparison charts from experiment data.
    
    Args:
        experiment_data: Dict with experiment results
        output_dir: Directory for output files
        style: Plot style (ieee, nature, etc.)
        
    Returns:
        List of chart metadata dicts
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    charts = []
    
    # Try to apply style
    try:
        plt.style.use(['science', style])
    except Exception:
        pass
    
    # Generate accuracy comparison chart if data available
    if 'accuracy' in experiment_data:
        acc_data = experiment_data['accuracy']
        chart_path = output_path / "comparison_accuracy.pdf"
        
        generate_comparison_bar_chart(
            data=acc_data.get('values', {}),
            labels=acc_data.get('datasets', ['Dataset 1', 'Dataset 2']),
            ylabel='Accuracy (%)',
            title='Accuracy Comparison',
            output_path=str(chart_path),
            errors=acc_data.get('errors')
        )
        
        charts.append({
            'filepath': str(chart_path),
            'latex_ref': 'fig:comparison_accuracy',
            'caption': 'Comparison of accuracy across datasets.',
            'label': 'fig:comparison_accuracy'
        })
    
    # Generate training curve if data available
    if 'training_curves' in experiment_data:
        curve_data = experiment_data['training_curves']
        chart_path = output_path / "training_curves.pdf"
        
        plot_data = {}
        for method, values in curve_data.get('curves', {}).items():
            steps = list(range(len(values)))
            plot_data[method] = (steps, values)
        
        generate_line_plot(
            data=plot_data,
            xlabel='Training Steps',
            ylabel='Loss',
            title='Training Curves',
            output_path=str(chart_path)
        )
        
        charts.append({
            'filepath': str(chart_path),
            'latex_ref': 'fig:training_curves',
            'caption': 'Training loss curves for different methods.',
            'label': 'fig:training_curves'
        })
    
    logger.info(f"Generated {len(charts)} charts in {output_dir}")
    return charts
