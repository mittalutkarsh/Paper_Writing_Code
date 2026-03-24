"""File Watcher — Monitors READMEMISSING.md for changes."""

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from ..config import HITLConfig
from ..utils.logger import get_logger
from .missing_md import parse_missing_md, validate_missing_md
from .models import HumanInput

logger = get_logger(__name__)


class MissingMdHandler(FileSystemEventHandler):
    """Handler for READMEMISSING.md file changes."""
    
    def __init__(
        self,
        filepath: str,
        required_ids: list[str],
        callback: callable
    ):
        """Initialize handler.
        
        Args:
            filepath: Path to READMEMISSING.md
            required_ids: List of required item IDs
            callback: Function to call when all required items are complete
        """
        self.filepath = filepath
        self.required_ids = required_ids
        self.callback = callback
        self.last_content = None
    
    def on_modified(self, event):
        """Handle file modification."""
        if not event.is_directory and event.src_path == self.filepath:
            # Read current content
            try:
                current_content = Path(self.filepath).read_text()
            except Exception:
                return
            
            # Check if content actually changed
            if current_content == self.last_content:
                return
            self.last_content = current_content
            
            logger.info(f"READMEMISSING.md modified, checking completion...")
            
            # Validate
            is_valid, missing = validate_missing_md(self.filepath, self.required_ids)
            
            if is_valid:
                logger.info("All required items complete! Triggering resume...")
                result = parse_missing_md(self.filepath)
                if isinstance(result, HumanInput):
                    self.callback(result)
            else:
                logger.info(f"Still incomplete: {', '.join(missing)}")


def wait_for_human_input(
    filepath: str,
    required_ids: list[str],
    mode: str,
    watch_interval_sec: int = 10
) -> HumanInput | None:
    """Wait for human input via file watching or polling.
    
    Args:
        filepath: Path to READMEMISSING.md
        required_ids: List of required item IDs
        mode: "file_watch" or "poll"
        watch_interval_sec: Polling interval in seconds
        
    Returns:
        HumanInput when complete, None if interrupted
    """
    filepath = Path(filepath).resolve()
    
    if mode == "file_watch":
        logger.info(f"Watching {filepath} for changes...")
        
        result_container = [None]
        
        def callback(human_input: HumanInput):
            result_container[0] = human_input
        
        handler = MissingMdHandler(str(filepath), required_ids, callback)
        observer = Observer()
        observer.schedule(handler, str(filepath.parent), recursive=False)
        observer.start()
        
        try:
            while result_container[0] is None:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            observer.stop()
            return None
        finally:
            observer.stop()
            observer.join()
        
        return result_container[0]
    
    elif mode == "poll":
        logger.info(f"Polling {filepath} every {watch_interval_sec} seconds...")
        
        try:
            while True:
                is_valid, missing = validate_missing_md(str(filepath), required_ids)
                
                if is_valid:
                    logger.info("All required items complete!")
                    result = parse_missing_md(str(filepath))
                    if isinstance(result, HumanInput):
                        return result
                else:
                    logger.debug(f"Still incomplete: {', '.join(missing)}")
                
                time.sleep(watch_interval_sec)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return None
    
    else:
        raise ValueError(f"Invalid mode: {mode}. Use 'file_watch' or 'poll'")
