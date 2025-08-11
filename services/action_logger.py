# services/action_logger.py

import os
import json
import datetime
from pathlib import Path
import threading

class ActionLogger:
    def __init__(self, log_dir='logs'):
        """
        Initialize the action logger
        
        Args:
            log_dir (str): Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()  # Thread-safe logging
        
        # Create today's log file path
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.current_log_file = self.log_dir / f'actions_{today}.log'
        
        # Ensure log file exists
        self.current_log_file.touch()
    
    def log_action(self, action, status='SUCCESS', metadata=None):
        """
        Log an action with timestamp
        
        Args:
            action (str): Description of the action
            status (str): Status of the action (SUCCESS or ERROR)
            metadata (dict): Optional additional metadata
        """
        with self._lock:
            try:
                timestamp = datetime.datetime.now().isoformat()
                
                log_entry = {
                    'timestamp': timestamp,
                    'action': action,
                    'status': status,
                    'metadata': metadata or {}
                }
                
                # Write to current log file
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
                # Also write human-readable format
                readable_entry = f"[{timestamp}] {status}: {action}\n"
                readable_log_file = self.log_dir / f'actions_{datetime.datetime.now().strftime("%Y-%m-%d")}_readable.log'
                
                with open(readable_log_file, 'a', encoding='utf-8') as f:
                    f.write(readable_entry)
                    
                return True
                
            except Exception as e:
                print(f"Failed to log action: {str(e)}")
                return False
    
    def get_logs(self, date=None, limit=None):
        """
        Retrieve logs for a specific date or all logs
        
        Args:
            date (str): Date in YYYY-MM-DD format (optional)
            limit (int): Maximum number of entries to return (optional)
        
        Returns:
            list: List of log entries
        """
        try:
            if date:
                log_file = self.log_dir / f'actions_{date}.log'
            else:
                log_file = self.current_log_file
            
            if not log_file.exists():
                return []
            
            entries = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line.strip())
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            # Sort by timestamp (newest first)
            entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            if limit:
                entries = entries[:limit]
            
            return entries
            
        except Exception as e:
            print(f"Failed to retrieve logs: {str(e)}")
            return []
    
    def get_all_log_files(self):
        """
        Get list of all available log files
        
        Returns:
            list: List of log file names
        """
        try:
            log_files = []
            for file in self.log_dir.glob('actions_*.log'):
                if not file.name.endswith('_readable.log'):
                    log_files.append(file.name)
            
            return sorted(log_files, reverse=True)
            
        except Exception as e:
            print(f"Failed to get log files: {str(e)}")
            return []
    
    def get_log_file_content(self, filename):
        """
        Get content of a specific log file for download
        
        Args:
            filename (str): Name of the log file
        
        Returns:
            str: Content of the log file in readable format
        """
        try:
            log_file = self.log_dir / filename
            if not log_file.exists():
                return None
            
            # Read JSON logs and convert to readable format
            readable_content = []
            readable_content.append(f"Action Log - {filename}")
            readable_content.append("=" * 50)
            readable_content.append("")
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line.strip())
                            timestamp = entry.get('timestamp', 'Unknown')
                            action = entry.get('action', 'Unknown action')
                            status = entry.get('status', 'UNKNOWN')
                            
                            readable_content.append(f"[{timestamp}] {status}: {action}")
                            
                            # Add metadata if present
                            metadata = entry.get('metadata', {})
                            if metadata:
                                for key, value in metadata.items():
                                    readable_content.append(f"  {key}: {value}")
                                readable_content.append("")
                            
                        except json.JSONDecodeError:
                            continue
            
            return '\n'.join(readable_content)
            
        except Exception as e:
            print(f"Failed to get log file content: {str(e)}")
            return None
    
    def cleanup_old_logs(self, days_to_keep=30):
        """
        Remove log files older than specified days
        
        Args:
            days_to_keep (int): Number of days to keep logs
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            for log_file in self.log_dir.glob('actions_*.log'):
                try:
                    # Extract date from filename
                    date_str = log_file.stem.replace('actions_', '').replace('_readable', '')
                    if len(date_str) == 10:  # YYYY-MM-DD format
                        file_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                        if file_date < cutoff_date:
                            log_file.unlink()
                            print(f"Removed old log file: {log_file.name}")
                except (ValueError, OSError) as e:
                    print(f"Failed to process log file {log_file.name}: {str(e)}")
                    
        except Exception as e:
            print(f"Failed to cleanup old logs: {str(e)}")
    
    def get_log_statistics(self):
        """
        Get statistics about logged actions
        
        Returns:
            dict: Statistics about actions
        """
        try:
            stats = {
                'total_actions': 0,
                'success_count': 0,
                'error_count': 0,
                'recent_actions': [],
                'action_types': {}
            }
            
            # Get today's logs
            logs = self.get_logs(limit=100)  # Last 100 actions
            
            stats['total_actions'] = len(logs)
            
            for entry in logs:
                status = entry.get('status', 'UNKNOWN')
                action = entry.get('action', 'Unknown')
                
                if status == 'SUCCESS':
                    stats['success_count'] += 1
                elif status == 'ERROR':
                    stats['error_count'] += 1
                
                # Count action types
                action_type = action.split(' ')[0] if action else 'Unknown'
                stats['action_types'][action_type] = stats['action_types'].get(action_type, 0) + 1
            
            # Get recent actions (last 5)
            stats['recent_actions'] = logs[:5]
            
            return stats
            
        except Exception as e:
            print(f"Failed to get log statistics: {str(e)}")
            return {
                'total_actions': 0,
                'success_count': 0,
                'error_count': 0,
                'recent_actions': [],
                'action_types': {}
            }

# Global logger instance
action_logger = ActionLogger()