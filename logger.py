from datetime import datetime
from pathlib import Path


class FileLogger:
    """Handles logging messages and analysis results to files"""
    
    def __init__(self, log_dir="./logs"):
        # Create log directory if it doesn't exist
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Define log file paths
        self.message_log_path = self.log_dir / "messages.log"
        self.analysis_log_path = self.log_dir / "speech_analysis.log"
        self.debug_log_path = self.log_dir / "debug.log"
        
        # Clear existing logs before starting
        self._clear_existing_logs()
        
        # Initialize new log files with headers
        self._initialize_log_files()
    
    def _clear_existing_logs(self):
        """Removes existing log files to start fresh"""
        log_files = [self.message_log_path, self.analysis_log_path, self.debug_log_path]
        for log_file in log_files:
            try:
                if log_file.exists():
                    log_file.unlink()  # This deletes the file
            except Exception as e:
                print(f"Error clearing log file {log_file}: {e}")
    
    def _initialize_log_files(self):
        """Creates fresh log files with headers and startup timestamp"""
        startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Initialize message log
        self._write_log(self.message_log_path, 
            f"=== Message Log ===\nSession started: {startup_time}\n")
        
        # Initialize speech analysis log
        self._write_log(self.analysis_log_path, 
            f"=== Speech Analysis Log ===\nSession started: {startup_time}\n")
        
        # Initialize debug log
        self._write_log(self.debug_log_path, 
            f"=== Debug Log ===\nSession started: {startup_time}\n")
    def _write_log(self, log_path, content):
        """Writes content to specified log file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, 'a', encoding='utf-8') as f:
            print(log_path, content)
            f.write(f"[{timestamp}] {content}\n")
    
    def log_message(self, content, context):
        """Logs detected messages with context"""
        log_entry = (
            f"\nMessage Detected\n"
            f"Window: {context['window_title']}\n"
            f"Process: {context['process_name']}\n"
            f"Content: {content}\n"
            f"{'-' * 50}"
        )
        self._write_log(self.message_log_path, log_entry)
    
    def log_analysis(self, text, analysis):
        """Logs speech analysis results"""
        analysis_entry = (
            f"\nSpeech Analysis Results\n"
            f"Message Content: '{text}'\n"
            f"Speech Type: {analysis.get('speech_type', 'Unknown')}\n"
            f"Severity: {analysis.get('severity', 0):.2f}\n"
            f"Groups Referenced: {', '.join(analysis.get('target_groups', []))}\n"
            f"Positive Elements: {', '.join(analysis.get('positive_elements', []))}\n"
            f"Concerning Elements: {', '.join(analysis.get('negative_elements', []))}\n"
            f"Confidence: {analysis.get('confidence', 0):.2f}\n"
            f"{'-' * 50}"
        )
        self._write_log(self.analysis_log_path, analysis_entry)
        
        # Log alert separately if attention is required
        if analysis.get('requires_attention', False):
            alert_text = "⚠️ Review Recommended - "
            if analysis['speech_type'] == 'hate_speech':
                alert_text += "Potentially harmful content detected"
            elif analysis['speech_type'] == 'positive_speech':
                alert_text += "Notable positive impact detected"
            self._write_log(self.analysis_log_path, f"ALERT: {alert_text}")
    
    def log_debug(self, message):
        """Logs debug messages"""
        self._write_log(self.debug_log_path, message) 