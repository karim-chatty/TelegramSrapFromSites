
# THIS PYTHON SCRAPPING SCRIPT CAN TAKE POSTS FROM WEBSITS AND POSTE IT ON YOUR OWN TELEGRAM ACC 
# THE SCRIPT NEED FROM U API_ID|API HASH, AND THE BOT TOKEN (U NEED TO CRAETE A BOT AND ADD IT AS AN ADMIN INTO THE CHANNEL U CAN GET THE TOKEN ON BOTHFATHER ON TELEGRAM), AND THE URL U WANT TO SCRAPP FROM


import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class Course:
    title: str
    description: str
    link: str
    image_url: Optional[str]

# Configuration
load_dotenv()

CONFIG = {
    'api_id': os.getenv("API_ID"),
    'api_hash': os.getenv("API_HASH"),
    'bot_token': os.getenv("BOT_TOKEN"),
    'channel_username': os.getenv("CHANNEL_USERNAME"),
    'keywords_filter': os.getenv("KEYWORDS").split(','),
    'db_file': os.getenv("DB_FILE"),
    'scrape_url': os.getenv("SCRAPE_URL"),
    'invite_link': os.getenv("INVITE_LINK")
}

class CourseScraperBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.posted_courses = self._load_posted_courses()
        self.client = TelegramClient('course_bot_session', CONFIG['api_id'], CONFIG['api_hash'])

    def _load_posted_courses(self) -> List[str]:
        """Load previously posted courses from JSON file."""
        try:
            with open(CONFIG['db_file'], 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_posted_courses(self):
        """Save posted courses to JSON file."""
        with open(CONFIG['db_file'], 'w') as f:
            json.dump(self.posted_courses, f)

    def scrape_courses(self) -> List[Course]:
        """Scrape courses from StudyBullet."""
        courses = []
        try:
            response = self.session.get(CONFIG['scrape_url'])
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find course elements (Modify based on the actual website structure)
            course_elements = soup.find_all('article', class_='blog-entry')
            
            for element in course_elements:
                title = element.find('h2').text.strip()  # Title
                description = element.find('div', class_='blog-entry-summary').text.strip()  # Description
                link = element.find('a')['href']  # Course link
                image_url = element.find('img')['src'] if element.find('img') else None  # Image URL
                
                # Apply keyword filtering if configured
                if CONFIG['keywords_filter']:
                    if not any(keyword.lower() in title.lower() for keyword in CONFIG['keywords_filter']):
                        continue
                
                courses.append(Course(
                    title=title,
                    description=description,
                    link=link,
                    image_url=image_url
                ))
                
        except Exception as e:
            print(f"Error scraping courses: {e}")
        
        return courses

    async def format_message(self, course: Course) -> str:
        """Format course data into a Telegram message."""
        invite_link = CONFIG.get("invite_link", "https://t.me/HQ_courses")
        return f"""🎓 {course.title}

📝 {course.description}

🔗 [View Course]({course.link})
👉 invite friends [https://t.me/HQ_courses]({invite_link})
#course #education"""

    async def post_to_telegram(self, course: Course):
        """Post a course to Telegram channel."""
        try:
            message = await self.format_message(course)
            
            if course.image_url:
                # Send image with caption
                await self.client.send_file(
                    CONFIG['channel_username'],
                    course.image_url,
                    caption=message,
                    parse_mode='markdown'
                )
            else:
                # Send text message without image
                await self.client.send_message(
                    CONFIG['channel_username'],
                    message,
                    parse_mode='markdown'
                )
            
            # Keep track of posted courses to avoid duplicates
            self.posted_courses.append(course.link)
            self._save_posted_courses()
            
            # Respect Telegram's rate limits
            time.sleep(15)
            
        except FloodWaitError as e:
            print(f"Rate limited. Waiting {e.seconds} seconds")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"Error posting to Telegram: {e}")

    async def run(self):
        """Main execution function."""
        print(f"Starting course scraper at {datetime.now()}")
        
        try:
            await self.client.start(bot_token=CONFIG['bot_token'])
            
            # Scrape the courses from the website
            courses = self.scrape_courses()
            
            # Filter out courses that have already been posted
            new_courses = [course for course in courses if course.link not in self.posted_courses]
            
            print(f"Found {len(new_courses)} new courses")
            
            for course in new_courses:
                await self.post_to_telegram(course)
                
        except Exception as e:
            print(f"Error in main execution: {e}")
        finally:
            await self.client.disconnect()

if __name__ == "__main__":
    import asyncio
    
    # Instantiate and run the bot
    bot = CourseScraperBot()
    asyncio.run(bot.run())
