import os
import sys
# import discord
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QLabel, QPushButton, QMessageBox)
from PyQt6.QtCore import QTimer
import keyboard
import win32gui
import win32process
import psutil
import asyncio
from datetime import datetime
import re
import threading
from pathlib import Path
from openai import AsyncOpenAI, OpenAI
from dotenv import load_dotenv
from logger import FileLogger
from PIL import ImageGrab
import io
import base64
import requests
from pydantic import BaseModel
from qasync import QEventLoop, asyncSlot
import cv2 
import pytesseract
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
from doomscroll import DoomscrollingPopup
import aiohttp
from typing import Optional
from pywinauto import Application # pip install pywinauto




class CurrentWebsiteAnalysis(BaseModel):
    website_name: str
    website_content: str
    doom_scrolling: bool


# Load environment variables and API key
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY") 
# openai_api_key = None

class GlobalTextMonitor(QMainWindow):
    """Main application window for monitoring and analyzing text input"""
    
    def __init__(self, openai_api_key):
        super().__init__()
        self.openai_api_key = openai_api_key
        self.fps = 10
        self.min_time_spent = 5*60
        self.max_frames = self.min_time_spent*self.fps
        self._lock = asyncio.Lock()
        self.processing = False
        if (openai_api_key):
            self.client = AsyncOpenAI(api_key=self.openai_api_key)
        
        # Initialize components
        self.logger = FileLogger()
        self.app = Application(backend='uia')
        self.base64Frames = []
        self.analysis = []
        # Set up monitoring
        self.setup_monitoring()
   
        # Start screenshot monitoring
        self.setup_screenshot_timer()
        self.logger.log_debug("Application initialized")

    def setup_screenshot_timer(self):
        """Sets up a timer to take screenshots periodically."""

        # Timer to take screenshots every second
        self.screenshot_timer = QTimer(self)
        self.screenshot_timer.setInterval(1000//self.fps)  # 10 fps
        self.screenshot_timer.timeout.connect(self.take_screenshot)
        self.screenshot_timer.start()
        self.analysis_timer = QTimer(self)
        self.analysis_timer.setInterval(self.min_time_spent * 1000)  # try to analyze the screenshots every second
        self.analysis_timer.timeout.connect(self.take_and_analyze_screenshot)
        self.analysis_timer.start()
    

    def take_screenshot(self):
        """Captures a screenshot and stores it in base64 format in the buffer."""
        screenshot = ImageGrab.grab()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Convert to base64 string immediately
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # print(self.get_message_content(base64_string))
        # Store the base64 string in the buffer
        self.base64Frames.append(base64_string)
        
        # Limit the buffer size to avoid excessive memory usage
        if len(self.base64Frames) > self.max_frames:  # Adjust as needed
            self.base64Frames.pop(0)
            

    @asyncSlot()
    async def take_and_analyze_screenshot(self):
        """Takes a screenshot of the current screen and sends it to OpenAI for analysis."""

        # check if the current process should even be considered for analysis (has been on the site for quite a while)
        
        print(self.context)
        try:
            if self.processing:
                return None
            if self._lock.locked():
                self.logger.log_debug("Screenshot analysis already in progress, skipping...")
                return None
            async with self._lock:
                if not self.processing:
                    self.processing = True
                    skip = len(self.base64Frames) // 10 # only sends 5 frames
                    if (skip == 0):
                        skip = 1

                    PROMPT_MESSAGES = [
                        {
                            "role": "user",
                            "content": [
                                f"""Attached are is a video of a user's screen from of 5+ minutes please identify:
                                1. the website name and what the user is specifically consuming on the website
                                2. if the user is doomscrolling -- unproductively scrolling through social media or news websites, if the user is merely researching/doing a time intensive task then they are not doomscrolling. Please note sometimes a user can go afk and have all the screenshots displayed be the same simply because they are not at their computer. This is not doomscrolling. However, if the images are constantly changing but are all from similar social media websites that seem to be of little to no productive value warn of doomscrolling. This is the website name: {self.context['parent_website']}""",
                                *map(lambda x: {"image": x, "resize": 768,}, self.base64Frames[min(0, len(self.base64Frames) - self.max_frames):len(self.base64Frames):skip]),
                            ],
                        },
                        
                    ]
                    params = {
                        "model": "gpt-4o",
                        "messages": PROMPT_MESSAGES,
                        "max_tokens": 500,
                        "response_format": CurrentWebsiteAnalysis,
                    }
                    print("skibidi?")
                    # Send to OpenAI API
                    result = await self.client.beta.chat.completions.parse(**params)
                    # print(result.choices[0].message.content)

                    result = CurrentWebsiteAnalysis.model_validate_json(result.choices[0].message.content)
                    print(result, result.doom_scrolling)

                    if (result.doom_scrolling):
                        self.show_doomscrolling_popup(result.website_name)
                        self.base64Frames.clear()
                    self.processing = False
                    self.context['timestamp'] = datetime.now()

        except Exception as e:
            self.logger.log_debug(f"Error capturing or analyzing screenshot: {str(e)}")

    
    def show_doomscrolling_popup(self, site):
        """
        Method to show the doomscrolling popup
        
        :param site: The website the user is currently on
        :param duration: Duration spent on the site in minutes
        """
        # Create popup if it doesn't exist
        if not hasattr(self, '_doomscrolling_popup'):
            self._doomscrolling_popup = DoomscrollingPopup(site, parent=self)
        
        # Update popup content
        self._doomscrolling_popup.setWindowTitle(f"Doomscrolling Alert - {site}")
        
        # Ensure popup is created only once and reused
        if not self._doomscrolling_popup.isVisible():
            self._doomscrolling_popup.show()

    def closeEvent(self, event):
        """Handles application shutdown"""
        try:
            keyboard.unhook_all()
            self.display_timer.stop()
            
            self.logger.log_debug("Application shutting down cleanly...")
            
        except Exception as e:
            self.logger.log_debug(f"Error during cleanup: {str(e)}")
        
        event.accept()

    def create_empty_context(self):
        """Creates and returns a new context dictionary with default values"""
        return {
            'window_handle': None,
            'process_name': "Unknown",
            'window_title': "Unknown",
            'url': "",
            'file_path': "",
            'cursor_pos': (0, 0),
            'timestamp': datetime.now(),
        }

    def setup_monitoring(self):
        """Initializes all monitoring systems"""
        self.context = self.create_empty_context()       
        self.context_timer = QTimer(self)
        self.context_timer.setInterval(100)
        self.context_timer.timeout.connect(self.update_context)
        self.context_timer.start()

    def update_context(self):
        """Updates the current context with new window and process information"""
        # try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = "Unknown Process"
        
        try:
            window_title = win32gui.GetWindowText(hwnd)
            self.app.connect(title_re=".*Chrome.*", found_index=0)
            element_name="Address and search bar"
            dlg = self.app.top_window()
            url = dlg.child_window(title=element_name, control_type="Edit", found_index=0).get_value()
            parent_url = url.split('/')[2] if url else ""
        except:
            url = self.context['url'] if 'url' in self.context else ""
            parent_url = self.context['parent_website'] if 'parent_website' in self.context else ""
        if (hwnd != self.context['window_handle'] or 
            window_title != self.context['window_title'] and url != self.context['url']):
            


            new_context = self.create_empty_context()
            
            if ('parent_website' not in self.context or self.context['parent_website'] != parent_url): # only if the user goes to a new website does it reset the timer
                new_context['timestamp'] = datetime.now()

            new_context.update({
                'window_handle': hwnd,
                'process_name': process_name,
                'window_title': window_title,
                'cursor_pos': win32gui.GetCursorPos(),
                'url': url,
                'parent_website': parent_url,
            })


            # if process_name.lower() in ['chrome.exe', 'firefox.exe', 'msedge.exe']:
            #     url = self.extract_url_from_title(window_title)
            #     if url:
            #         new_context['url'] = url

            file_path = self.extract_file_path_from_title(window_title)
            if file_path:
                new_context['file_path'] = file_path

            self.context = new_context

        # except Exception as e:
        #     self.logger.log_debug(f"Error updating context: {str(e)}")

    def extract_url_from_title(self, title):
        """Extracts a URL from a browser window title"""
        patterns = [
            r"(?:https?://)?(?:www\.)?([^\s/]+\.[^\s/]+)(?:/[^\s]*)?",
            r"([^\s/]+\.[^\s/]+(?:/[^\s]*)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        return ""

    def extract_file_path_from_title(self, title):
        """Extracts a file path from a window title"""
        patterns = [
            r"[A-Za-z]:\\[^*|\"<>?\n]*\.[^\\\/\n]+",  # Windows path
            r"/[^/\n]*\.[^/\n]+",  # Unix-like path
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(0)
        return ""


def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    # Set up qasync event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Initialize the application
    monitor = GlobalTextMonitor(openai_api_key=openai_api_key)
    monitor.show()
    
    # Start the asyncio event loop
    with loop:
        loop.run_forever()

if __name__ == '__main__':
    main()
