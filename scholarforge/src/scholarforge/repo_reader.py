"""Repository Reader - Extract context from README and code files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils.logger import get_logger

logger = get_logger(__name__)

# Default file extensions to include
DEFAULT_CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.go', '.rs', '.swift', '.kt', '.scala', '.rb', '.php', '.cs', '.r', '.m'
}

# Directories to exclude
EXCLUDE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env',
    'dist', 'build', '.pytest_cache', '.mypy_cache', '.tox', 'target',
    '.idea', '.vscode', 'vendor', 'third_party', 'third-party'
}

# Files to exclude
EXCLUDE_FILES = {
    'package-lock.json', 'yarn.lock', 'Pipfile.lock', 'poetry.lock',
    '.DS_Store', 'Thumbs.db', '*.min.js', '*.min.css'
}


@dataclass
class RepoContext:
    """Context extracted from a repository."""
    readme_content: str = ""
    readme_path: Optional[str] = None
    code_files: list[dict] = field(default_factory=list)
    repo_path: Optional[str] = None
    
    @classmethod
    def from_paths(
        cls,
        readme_path: Optional[str] = None,
        code_repo_path: Optional[str] = None,
        code_extensions: Optional[list[str]] = None
    ) -> "RepoContext":
        """Create RepoContext from file paths.
        
        Args:
            readme_path: Path to README file
            code_repo_path: Path to code repository root
            code_extensions: List of file extensions to include (e.g., ['.py', '.js'])
            
        Returns:
            RepoContext with extracted content
        """
        context = cls()
        
        # Read README
        if readme_path:
            readme_file = Path(readme_path)
            if readme_file.exists():
                context.readme_content = readme_file.read_text(encoding='utf-8', errors='ignore')
                context.readme_path = str(readme_file.resolve())
                logger.info(f"Loaded README: {readme_file}")
            else:
                logger.warning(f"README not found: {readme_path}")
        
        # Read code files
        if code_repo_path:
            repo_path = Path(code_repo_path)
            if repo_path.exists() and repo_path.is_dir():
                context.repo_path = str(repo_path.resolve())
                extensions = set(code_extensions) if code_extensions else DEFAULT_CODE_EXTENSIONS
                context.code_files = cls._read_code_files(repo_path, extensions)
                logger.info(f"Loaded {len(context.code_files)} code files from {repo_path}")
            else:
                logger.warning(f"Code repository not found: {code_repo_path}")
        
        return context
    
    @staticmethod
    def _read_code_files(repo_path: Path, extensions: set[str]) -> list[dict]:
        """Read all code files from repository.
        
        Args:
            repo_path: Repository root path
            extensions: Set of file extensions to include
            
        Returns:
            List of dicts with file info and content
        """
        code_files = []
        
        for file_path in repo_path.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip excluded directories
            if any(part in EXCLUDE_DIRS for part in file_path.parts):
                continue
            
            # Skip excluded files
            if file_path.name in EXCLUDE_FILES:
                continue
            if any(file_path.match(pattern) for pattern in EXCLUDE_FILES if '*' in pattern):
                continue
            
            # Check extension
            if file_path.suffix.lower() not in extensions:
                continue
            
            # Read file
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Skip very large files (>100KB)
                if len(content) > 100_000:
                    logger.debug(f"Skipping large file: {file_path}")
                    continue
                
                # Skip files that are mostly binary/non-code
                if RepoContext._is_mostly_binary(content):
                    logger.debug(f"Skipping binary-like file: {file_path}")
                    continue
                
                rel_path = file_path.relative_to(repo_path)
                
                code_files.append({
                    'path': str(rel_path),
                    'full_path': str(file_path.resolve()),
                    'extension': file_path.suffix,
                    'content': content,
                    'lines': len(content.splitlines())
                })
                
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
                continue
        
        # Sort by path for consistency
        code_files.sort(key=lambda x: x['path'])
        
        return code_files
    
    @staticmethod
    def _is_mostly_binary(content: str, threshold: float = 0.1) -> bool:
        """Check if content appears to be binary/non-text.
        
        Args:
            content: File content
            threshold: Ratio of null bytes to consider binary
            
        Returns:
            True if content appears binary
        """
        if not content:
            return True
        
        # Check for null bytes
        null_count = content.count('\x00')
        if null_count / len(content) > threshold:
            return True
        
        # Check for very high ratio of non-printable characters
        non_printable = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
        if non_printable / len(content) > threshold:
            return True
        
        return False
    
    def get_summary(self, max_code_files: int = 20, max_lines_per_file: int = 50) -> str:
        """Get a summary of the repository context.
        
        Args:
            max_code_files: Maximum number of code files to include
            max_lines_per_file: Maximum lines per code file
            
        Returns:
            Formatted summary string
        """
        lines = []
        
        # Add README
        if self.readme_content:
            lines.append("=" * 60)
            lines.append("README CONTENT")
            lines.append("=" * 60)
            lines.append(self.readme_content[:5000])  # Limit README length
            lines.append("")
        
        # Add code files
        if self.code_files:
            lines.append("=" * 60)
            lines.append("CODE FILES")
            lines.append("=" * 60)
            lines.append("")
            
            for i, file_info in enumerate(self.code_files[:max_code_files]):
                lines.append(f"--- {file_info['path']} ---")
                
                # Get first N lines, skip shebang if present
                file_lines = file_info['content'].splitlines()
                start_idx = 1 if file_lines and file_lines[0].startswith('#!') else 0
                
                for line in file_lines[start_idx:start_idx + max_lines_per_file]:
                    lines.append(line)
                
                if len(file_lines) > max_lines_per_file:
                    lines.append(f"... ({len(file_lines) - max_lines_per_file} more lines)")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'readme_path': self.readme_path,
            'readme_content': self.readme_content[:10000] if self.readme_content else "",  # Limit
            'repo_path': self.repo_path,
            'code_files': [
                {
                    'path': f['path'],
                    'extension': f['extension'],
                    'lines': f['lines'],
                    'content': f['content'][:5000]  # Limit content per file
                }
                for f in self.code_files[:50]  # Limit number of files
            ]
        }
