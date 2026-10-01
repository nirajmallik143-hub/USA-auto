"""
Dynamic script generation engine for US kids' content.
Supports OpenAI, Anthropic, and a rich kid-friendly procedural template engine.
"""

import json
import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import requests

from src.config import LLMProvider, VideoFormat, VideoTopic, settings
from src.content.prompts import (
    KID_SYSTEM_PROMPT,
    LONG_FORM_PROMPT_TEMPLATE,
    SHORTS_PROMPT_TEMPLATE,
)
from src.content.topics import get_topic_definition
from src.logger import logger


@dataclass
class Scene:
    narration: str
    visual_description: str
    caption_text: str
    duration_seconds: float = 6.0


@dataclass
class ScriptData:
    title: str
    description: str
    tags: List[str]
    video_format: str
    topic: str
    target_duration_seconds: float
    scenes: List[Scene]
    call_to_action: str
    chapters: Optional[List[Dict[str, str]]] = None

    @property
    def total_words(self) -> int:
        return sum(len(s.narration.split()) for s in self.scenes)

    @property
    def full_narration(self) -> str:
        return " ".join(s.narration.strip() for s in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "video_format": self.video_format,
            "topic": self.topic,
            "target_duration_seconds": self.target_duration_seconds,
            "scenes": [asdict(s) for s in self.scenes],
            "call_to_action": self.call_to_action,
            "chapters": self.chapters,
            "total_words": self.total_words,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScriptData":
        scenes = [
            Scene(
                narration=s["narration"],
                visual_description=s["visual_description"],
                caption_text=s["caption_text"],
                duration_seconds=float(s.get("duration_seconds", 6.0)),
            )
            for s in data.get("scenes", [])
        ]
        return cls(
            title=data["title"],
            description=data["description"],
            tags=data.get("tags", []),
            video_format=data["video_format"],
            topic=data["topic"],
            target_duration_seconds=float(data.get("target_duration_seconds", 45.0)),
            scenes=scenes,
            call_to_action=data.get("call_to_action", ""),
            chapters=data.get("chapters"),
        )


class ProceduralKidsTemplateEngine:
    """
    Generates rich, high-quality, diverse scripts for US kids
    without requiring external LLM API tokens. Used as default or fallback.
    """

    def generate_shorts_script(self, topic: str) -> ScriptData:
        topic_def = get_topic_definition(topic)

        if topic == VideoTopic.ANIMAL_RIDDLES.value:
            animals = [
                {
                    "name": "Lion",
                    "sound": "ROAAAR!",
                    "clue1": "I have a big golden mane like a royal crown!",
                    "clue2": "I love to take long sunny naps on the African savannah!",
                    "clue3": "When I speak, everyone hears my mighty ROAR!",
                    "reveal": "It's the mighty Lion, king of the animals!",
                    "visual": "cartoon king lion on golden rock",
                },
                {
                    "name": "Elephant",
                    "sound": "TRUUUMPET!",
                    "clue1": "I am the biggest walking giant in the entire wild world!",
                    "clue2": "I use my long super trunk like a giant straw to drink water!",
                    "clue3": "I have giant floppy ears that flap like wings to stay cool!",
                    "reveal": "It's the gentle giant Elephant!",
                    "visual": "cute baby elephant splashing water",
                },
                {
                    "name": "Dolphin",
                    "sound": "CLICK-CLICK-WHISTLE!",
                    "clue1": "I live in the sparkling blue ocean, but I breathe fresh air!",
                    "clue2": "I love jumping high through the waves and doing flips!",
                    "clue3": "I am super friendly and talk with clicks and whistles!",
                    "reveal": "It's a joyful, playful Dolphin!",
                    "visual": "happy cartoon dolphin jumping through rainbow wave",
                },
                {
                    "name": "Owl",
                    "sound": "HOOT-HOOT!",
                    "clue1": "I have huge golden eyes that see perfectly in the dark night!",
                    "clue2": "I can turn my head almost all the way around like magic!",
                    "clue3": "I sit in tall oak trees and softly sing: Hoot hoot!",
                    "reveal": "It's the wise, sleepy night Owl!",
                    "visual": "cute fluffy owl under starry moon",
                },
            ]
            chosen = random.choice(animals)
            scenes = [
                Scene(
                    narration="Quick! Can you guess this mystery animal before time runs out?",
                    visual_description="Bouncing mystery gift box with question marks and sparkles",
                    caption_text="Mystery Animal Riddle!",
                    duration_seconds=5.0,
                ),
                Scene(
                    narration=f"Clue number one! {chosen['clue1']}",
                    visual_description=f"Curious cartoon detective searching near {chosen['visual']}",
                    caption_text="Clue #1!",
                    duration_seconds=7.0,
                ),
                Scene(
                    narration=f"Clue number two! {chosen['clue2']}",
                    visual_description=f"Animated hints glowing: {chosen['sound']}",
                    caption_text="Clue #2: Listen closely!",
                    duration_seconds=7.0,
                ),
                Scene(
                    narration=f"Last clue! {chosen['clue3']} Three... two... one... do you know who it is?",
                    visual_description="Big colorful countdown clock: 3... 2... 1...",
                    caption_text="3... 2... 1... Guess!",
                    duration_seconds=8.0,
                ),
                Scene(
                    narration=f"YES! {chosen['reveal']} Give yourself a big happy high-five!",
                    visual_description=f"Celebratory confetti and happy {chosen['visual']}",
                    caption_text=f"It's the {chosen['name']}! 🎉",
                    duration_seconds=7.0,
                ),
                Scene(
                    narration="Did you guess it right? Tap subscribe and tell your friends for the next riddle!",
                    visual_description="Animated subscribe button with cheerful stars and bells",
                    caption_text="Subscribe for more fun! ⭐",
                    duration_seconds=6.0,
                ),
            ]
            title = f"Guess the Mystery Animal! 🦁 Can You Solve This? #Shorts"
            desc = (
                f"Can you guess the mystery animal in this fun kid riddle? "
                f"Test your animal superpowers! #KidsRiddles #Shorts #AnimalFun #KidsLearning"
            )

        elif topic == VideoTopic.SPACE_FACTS.value:
            space_facts = [
                {
                    "planet": "Saturn",
                    "hook": "Wait! Did you know Saturn's giant shiny rings are made of ice cubes?",
                    "detail": "It's true! Billions of pieces of glittering cosmic ice and rock spin around Saturn like a glowing cosmic race track!",
                    "mindblow": "And here is the craziest secret: if you had a gigantic bathtub, Saturn would actually float like a rubber ducky!",
                    "visual": "cartoon planet saturn floating in giant bubble bath",
                },
                {
                    "planet": "The Sun",
                    "hook": "Hold on to your space helmets! How big is our bright yellow Sun?",
                    "detail": "Our Sun is so gigantic that over ONE MILLION Earths could fit inside it! That is like one million bouncy balls in a giant toy chest!",
                    "mindblow": "It sends warm sunshine 93 million miles across space right to your nose in just 8 minutes!",
                    "visual": "cheerful smiling cartoon sun waving sunglasses",
                },
            ]
            chosen = random.choice(space_facts)
            scenes = [
                Scene(
                    narration=f"{chosen['hook']}",
                    visual_description="Zooming cartoon rocket ship flying past glittering stars",
                    caption_text="Space Mystery! 🚀",
                    duration_seconds=6.0,
                ),
                Scene(
                    narration=f"{chosen['detail']}",
                    visual_description="Whimsical space animation with floating planets and sparkles",
                    caption_text="Super Space Fact!",
                    duration_seconds=9.0,
                ),
                Scene(
                    narration=f"{chosen['mindblow']}",
                    visual_description=chosen["visual"],
                    caption_text="Mind Blown! 🌟",
                    duration_seconds=9.0,
                ),
                Scene(
                    narration="Space is full of magical surprises! Keep looking up at the stars and subscribe for your next cosmic adventure!",
                    visual_description="Cute astronaut waving goodbye from rocket cockpit",
                    caption_text="Explore Space With Us! 🪐",
                    duration_seconds=7.0,
                ),
            ]
            title = f"Mind-Blowing Space Secrets! 🚀 {chosen['planet']} Facts! #Shorts"
            desc = (
                f"Discover incredible space secrets about {chosen['planet']}! "
                f"Educational, safe, and fun for curious kids! #SpaceFacts #KidsShorts #AstronomyKids #Shorts"
            )

        elif topic == VideoTopic.KIDS_JOKES_PUZZLES.value:
            jokes = [
                {
                    "setup": "Why did the teddy bear say no to dessert?",
                    "punchline": "Because she was already STUFFED! Haha!",
                    "visual": "cute cartoon teddy bear with happy tummy",
                },
                {
                    "setup": "What do you call a sleeping dinosaur?",
                    "punchline": "A DINO-SNORE! Zzzzzz!",
                    "visual": "cute sleeping cartoon t-rex with snoring bubbles",
                },
                {
                    "setup": "Why do fish live in salt water?",
                    "punchline": "Because pepper makes them sneeze! Achoo!",
                    "visual": "funny cartoon fish sneezing bubbles underwater",
                },
            ]
            chosen = random.choice(jokes)
            scenes = [
                Scene(
                    narration="Ready for the silliest giggle challenge on Earth? Try not to laugh!",
                    visual_description="Bouncing funny emoji faces and colorful circus confetti",
                    caption_text="Try Not To Laugh! 😆",
                    duration_seconds=5.0,
                ),
                Scene(
                    narration=f"Here comes the joke: {chosen['setup']}",
                    visual_description=chosen["visual"],
                    caption_text=chosen["setup"],
                    duration_seconds=8.0,
                ),
                Scene(
                    narration=f"The answer is... {chosen['punchline']}",
                    visual_description="Party poppers exploding with smiley faces and stars",
                    caption_text=chosen["punchline"],
                    duration_seconds=8.0,
                ),
                Scene(
                    narration="Did you giggle? Hit that subscribe button and share a smile with your family today!",
                    visual_description="Smiling cartoon character waving thumbs up",
                    caption_text="Share a Smile! 👍",
                    duration_seconds=6.0,
                ),
            ]
            title = "Super Silly Kids Joke! 🤣 Can You Keep a Straight Face? #Shorts"
            desc = "A cheerful, kid-safe joke to brighten your day! Perfect for toddlers, preschoolers, and family laughs. #KidsJokes #FamilyFun #Shorts #Giggles"

        elif topic == VideoTopic.SCIENCE_CURIOSITIES.value:
            scenes = [
                Scene(
                    narration="Have you ever wondered where rainbows come from after the rain?",
                    visual_description="Cute cartoon rain clouds parting for a bright golden sun",
                    caption_text="Where Do Rainbows Come From? 🌈",
                    duration_seconds=6.0,
                ),
                Scene(
                    narration="When sunlight shines through raindrops, each tiny drop acts like a crystal prism!",
                    visual_description="Sunbeams splitting into red, orange, yellow, green, blue, and purple light",
                    caption_text="Raindrops Are Prisms!",
                    duration_seconds=8.0,
                ),
                Scene(
                    narration="It bends the light and paints seven gorgeous colors across the sky: Red, Orange, Yellow, Green, Blue, Indigo, and Violet!",
                    visual_description="Magnificent bright rainbow arching over cartoon green hills",
                    caption_text="7 Beautiful Colors!",
                    duration_seconds=9.0,
                ),
                Scene(
                    narration="You are a real science explorer! Subscribe to discover more wonderful secrets about our world!",
                    visual_description="Cartoon kid wearing fun scientist glasses and waving",
                    caption_text="Stay Curious! 🔬",
                    duration_seconds=7.0,
                ),
            ]
            title = "How Do Rainbows Actually Form? 🌈 Magic Science! #Shorts"
            desc = "Learn how sunlight and raindrops create magical rainbows in the sky! Fun science for kids. #ScienceKids #Shorts #RainbowMagic #Curiosity"

        else:
            # Default / Alphabet / Dinosaurs / Moral stories
            scenes = [
                Scene(
                    narration=f"Welcome friends! Today we have an exciting mystery in {topic_def.name}!",
                    visual_description="Colorful cartoon intro with stars, rainbow ribbons, and happy music",
                    caption_text="Let's Explore Together! ✨",
                    duration_seconds=6.0,
                ),
                Scene(
                    narration=f"Did you know learning new things makes your brain grow stronger like a superhero?",
                    visual_description="Cartoon superhero kid flexing with smiling star muscles",
                    caption_text="Brain Superpowers! 🦸",
                    duration_seconds=8.0,
                ),
                Scene(
                    narration="Always be kind, stay curious, and ask wonderful questions every single day!",
                    visual_description="Animals and kids holding hands around a glowing happy heart",
                    caption_text="Be Kind & Curious! ❤️",
                    duration_seconds=8.0,
                ),
                Scene(
                    narration="You are awesome! Tap subscribe for your daily dose of fun learning!",
                    visual_description="Sparkling subscribe button with cheerful bells ringing",
                    caption_text="You Are Amazing! ⭐",
                    duration_seconds=6.0,
                ),
            ]
            title = f"{topic_def.name} for Kids! 🌟 Super Fun Learning #Shorts"
            desc = f"Fun, safe educational short about {topic_def.name}! Designed for kids and families. #KidsLearning #Shorts #Educational #Preschool"

        return ScriptData(
            title=title,
            description=desc,
            tags=["kids learning", "educational shorts", "family safe", "toddler fun", topic],
            video_format=VideoFormat.SHORTS.value,
            topic=topic,
            target_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            call_to_action="Tap subscribe and smile today!",
        )

    def generate_long_script(self, topic: str) -> ScriptData:
        topic_def = get_topic_definition(topic)

        if topic == VideoTopic.MORAL_STORIES.value:
            scenes = [
                Scene(
                    narration="Hello best friends! Welcome to our magical story corner! Today, we are opening our big golden storybook to read 'The Kind Little Fox and the Lost Bird'. Put on your listening ears and let's jump right in!",
                    visual_description="Whimsical storybook opening with golden sparkles floating out in a sunny fairy-tale forest",
                    caption_text="Welcome to Storytime! 📖",
                    duration_seconds=22.0,
                ),
                Scene(
                    narration="Deep inside the Whispering Woods lived Barnaby, a cheerful little fox with a bright bushy tail. One sunny morning, while picking sweet blackberries, Barnaby heard a tiny sound: Peep! Peep! Near the mossy roots of an old oak tree was Pip, a tiny bluebird who had tumbled from his nest.",
                    visual_description="Cute cartoon fox with red fur and big kind eyes helping a tiny shivering bluebird",
                    caption_text="Meet Barnaby the Fox! 🦊",
                    duration_seconds=28.0,
                ),
                Scene(
                    narration="Pip was frightened and could not fly back up yet. Barnaby could have hurried home to play with his toys, but he remembered what his wise grandmother taught him: 'Whenever you see someone in need, kindness is the greatest superpower you can ever choose!'",
                    visual_description="Barnaby wrapping the little bird in a soft green leaf blanket with a warm smile",
                    caption_text="Kindness is a Superpower! 💖",
                    duration_seconds=26.0,
                ),
                Scene(
                    narration="Now friends, here is our interactive story puzzle! How can Barnaby reach the high nest? Should he ask Oliver the tall Owl, build a soft ladder with twigs, or call Mama Bird? What do you think? Say it out loud! ... Great idea! Barnaby let out a gentle whistle, and Oliver the Owl swooped down gracefully to lend a wing!",
                    visual_description="Wise smiling cartoon owl with reading glasses flying down to help Barnaby",
                    caption_text="Let's Solve the Puzzle! 🦉",
                    duration_seconds=30.0,
                ),
                Scene(
                    narration="Together, Oliver gently carried little Pip right back into the warm nest with Mama Bird! Pip chirped with joy, and Mama Bird sang the sweetest thank-you song that echoed through the trees. Barnaby felt a warm, glowing sunshine inside his heart.",
                    visual_description="Mama bird hugging her baby bird while Barnaby smiles happily below",
                    caption_text="Safe in the Nest! 🎵",
                    duration_seconds=28.0,
                ),
                Scene(
                    narration="Here is our golden lesson for today: Even the smallest act of kindness can make the biggest difference in someone's world. When you share a smile, help a friend, or say kind words, you make the whole world brighter!",
                    visual_description="Golden sun beaming down on all forest animals holding hands and smiling",
                    caption_text="Our Golden Lesson ⭐",
                    duration_seconds=25.0,
                ),
                Scene(
                    narration="Thank you for sharing this beautiful story journey with us today! Give yourself a giant high five! Be sure to subscribe with mom and dad's help, and we will see you on our next magical adventure. Bye-bye friends!",
                    visual_description="Barnaby waving a cheerful goodbye as colorful balloons float into the sky",
                    caption_text="See You Next Time! 👋",
                    duration_seconds=20.0,
                ),
            ]
            title = "The Kind Little Fox 🦊 Heartwarming Story on Sharing & Kindness for Kids"
            desc = (
                "A gentle, uplifting moral story for kids and families about empathy, helping others, and friendship.\n\n"
                "Chapters:\n"
                "00:00 Welcome to Storytime\n"
                "00:22 Barnaby Meets Pip the Bluebird\n"
                "00:50 The Superpower of Kindness\n"
                "01:16 Helping Hand Puzzle\n"
                "01:46 The Sweet Thank-You Song\n"
                "02:14 Golden Moral Lesson\n"
                "02:39 High-Five & Goodbye Wave\n\n"
                "Made for Kids. COPPA compliant, safe educational family entertainment."
            )
            chapters = [
                {"time": "00:00", "title": "Welcome to Storytime"},
                {"time": "00:22", "title": "Meet Barnaby the Fox"},
                {"time": "00:50", "title": "The Power of Kindness"},
                {"time": "01:16", "title": "Interactive Story Puzzle"},
                {"time": "01:46", "title": "Safe in the Nest"},
                {"time": "02:14", "title": "Our Golden Lesson"},
                {"time": "02:39", "title": "Goodbye Wave"},
            ]

        elif topic == VideoTopic.SPACE_FACTS.value:
            scenes = [
                Scene(
                    narration="Greetings Cosmic Explorers! Put on your shiny silver astronaut helmets, buckle your seatbelts, and get ready for blast-off! 3... 2... 1... WHOOSH! Today, we are blasting through our Solar System to discover the most incredible secrets of the planets!",
                    visual_description="Animated rocket ship shooting off from launchpad into deep blue space with colorful cosmic dust",
                    caption_text="Blast Off into Space! 🚀",
                    duration_seconds=24.0,
                ),
                Scene(
                    narration="Our first planetary stop is closest to the Sun: Mercury! Mercury zooms around the Sun faster than any other planet. But at night, without an atmosphere blanket, it gets colder than a freezer full of popsicles! Brrrr!",
                    visual_description="Small rocky cartoon planet shivering under starry sky with ice crystals",
                    caption_text="Stop 1: Speedy Mercury! 🪐",
                    duration_seconds=26.0,
                ),
                Scene(
                    narration="Next up is the sparkling Red Planet: Mars! Did you know Mars has the biggest volcano in our entire solar system? It's called Olympus Mons, and it is three times taller than Mount Everest! Robot rovers named Curiosity and Perseverance are driving across Mars right now taking pictures!",
                    visual_description="Cute cartoon Mars rover with friendly camera eyes beeping across red dusty dunes",
                    caption_text="Stop 2: Mighty Mars Rovers! 🤖",
                    duration_seconds=30.0,
                ),
                Scene(
                    narration="Now it's time for our Cosmic Kid Quiz! Can you guess which planet is the biggest giant of them all? It has a giant swirling red storm that has been spinning for hundreds of years! Is it Venus, Saturn, or Jupiter? ... That's right! It is gigantic Jupiter!",
                    visual_description="Giant cartoon Jupiter with swirling colorful stripes and famous red spot smiling",
                    caption_text="Cosmic Quiz: The King Planet! 👑",
                    duration_seconds=28.0,
                ),
                Scene(
                    narration="And finally, we fly back to the most special planet of all: our sweet home, Planet Earth! With sparkling blue oceans, lush green trees, fluffy white clouds, and all of us! Let's always take wonderful care of our beautiful home planet.",
                    visual_description="Vibrant cartoon Planet Earth wearing a cheerful flower crown and smiling warmly",
                    caption_text="Home Sweet Earth! 🌍",
                    duration_seconds=28.0,
                ),
                Scene(
                    narration="You did fantastic on our space flight today, Junior Astronauts! Touch your helmet and give a salute! Subscribe for more interstellar voyages, and keep shining like the brightest stars in the universe! See you on the next mission!",
                    visual_description="Astronaut kid floating peacefully while planets dance in background",
                    caption_text="Mission Accomplished! ⭐",
                    duration_seconds=22.0,
                ),
            ]
            title = "Solar System Adventure for Kids! 🚀 Explore Planets, Rovers & Secrets of Space"
            desc = (
                "Blast off into outer space with this fun, educational solar system tour for kids!\n\n"
                "Chapters:\n"
                "00:00 Blast Off into Space\n"
                "00:24 Speedy Mercury\n"
                "00:50 Mighty Mars & Robot Rovers\n"
                "01:20 Cosmic Planet Quiz (Jupiter)\n"
                "01:48 Home Sweet Earth\n"
                "02:16 Mission Accomplished\n\n"
                "Safe, wholesome science and astronomy education for kids. Made for Kids."
            )
            chapters = [
                {"time": "00:00", "title": "Blast Off into Space"},
                {"time": "00:24", "title": "Speedy Mercury"},
                {"time": "00:50", "title": "Mighty Mars & Rovers"},
                {"time": "01:20", "title": "Cosmic Planet Quiz"},
                {"time": "01:48", "title": "Home Sweet Earth"},
                {"time": "02:16", "title": "Mission Accomplished"},
            ]

        else:
            # General educational long episode
            scenes = [
                Scene(
                    narration=f"Hello wonderful learners! Welcome back to our learning clubhouse! Today, we are diving deep into the amazing world of {topic_def.name}! Are you ready for some big fun? Let's get started!",
                    visual_description="Cheerful clubhouse with colorful books, animated toys, and bouncing balloons",
                    caption_text=f"Welcome to {topic_def.name}! 🎉",
                    duration_seconds=20.0,
                ),
                Scene(
                    narration=f"Our topic today is all about {topic_def.description}. Every time we explore something new, our brain creates brand new pathways that make us sharper and more creative!",
                    visual_description="Cartoon brain glowing with lightbulbs and cheerful smiling gears turning",
                    caption_text="Smart Brain Superpowers! 💡",
                    duration_seconds=25.0,
                ),
                Scene(
                    narration="Let's do an interactive challenge together! I will say a fun word, and you repeat it after me as loud and proud as you can! Ready? Super... Explorer! ... Wow, you sounded amazing! Give yourself two big claps!",
                    visual_description="Clapping hands emoji with colorful stars and musical notes jumping",
                    caption_text="Repeat After Me! 👏",
                    duration_seconds=25.0,
                ),
                Scene(
                    narration="Here is a super cool fact that most people do not know: Curiosity is like a golden key that opens doors to every adventure in the world! When you ask questions and explore, you are a real-life scientist!",
                    visual_description="Golden key unlocking a magical glowing door full of rainbow wonders",
                    caption_text="Curiosity is the Key! 🔑",
                    duration_seconds=28.0,
                ),
                Scene(
                    narration="You did an incredible job learning with us today! Never stop wondering, never stop being kind to your family and friends, and remember that you are capable of doing great things!",
                    visual_description="Smiling cartoon teacher waving ribbons and giving high-fives",
                    caption_text="You Did Great Today! 🌟",
                    duration_seconds=24.0,
                ),
                Scene(
                    narration="Make sure to subscribe so you never miss another adventure with our clubhouse family! See you next time, super star! Goodbye!",
                    visual_description="Clubhouse waving banner with subscribe bell and confetti",
                    caption_text="Subscribe for More Fun! 👋",
                    duration_seconds=18.0,
                ),
            ]
            title = f"Exciting {topic_def.name} Adventure for Kids! 🌟 Fun Learning Episode"
            desc = (
                f"Explore {topic_def.name} in this full interactive educational video for children.\n\n"
                f"Educational Objective: {topic_def.educational_goal}\n"
                "Safe, wholesome, family-friendly learning. Made for Kids."
            )
            chapters = [
                {"time": "00:00", "title": "Welcome to Clubhouse"},
                {"time": "00:20", "title": "Discovery Time"},
                {"time": "00:45", "title": "Interactive Challenge"},
                {"time": "01:10", "title": "Super Cool Fact"},
                {"time": "01:38", "title": "Awesome Job Recap"},
                {"time": "02:02", "title": "Clubhouse Goodbye"},
            ]

        return ScriptData(
            title=title,
            description=desc,
            tags=["kids learning", "educational videos for kids", "storytime", "family safe", topic],
            video_format=VideoFormat.LONG.value,
            topic=topic,
            target_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            call_to_action="Subscribe for more fun episodes!",
            chapters=chapters,
        )


class ScriptGenerator:
    """Orchestrates script generation using LLM API with automated fallback."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or settings.llm_provider
        self.template_engine = ProceduralKidsTemplateEngine()

    def generate_script(self, video_format: str, topic: str) -> ScriptData:
        """
        Generate a script appropriate for format (Shorts < 60s vs Long 3-8m).
        Tries LLM if configured, falls back to ProceduralKidsTemplateEngine.
        """
        topic_def = get_topic_definition(topic)
        logger.info(f"Generating script: format={video_format}, topic={topic}, provider={self.provider}")

        if self.provider == LLMProvider.OPENAI and settings.openai_api_key:
            try:
                return self._generate_with_openai(video_format, topic_def)
            except Exception as e:
                logger.warning(f"OpenAI script generation failed ({e}), falling back to template engine")

        elif self.provider == LLMProvider.ANTHROPIC and settings.anthropic_api_key:
            try:
                return self._generate_with_anthropic(video_format, topic_def)
            except Exception as e:
                logger.warning(f"Anthropic script generation failed ({e}), falling back to template engine")

        # Default template engine
        if video_format == VideoFormat.SHORTS.value:
            script = self.template_engine.generate_shorts_script(topic)
        else:
            script = self.template_engine.generate_long_script(topic)

        logger.info(f"Generated script '{script.title}' with {len(script.scenes)} scenes, ~{script.total_words} words")
        return script

    def _generate_with_openai(self, video_format: str, topic_def: Any) -> ScriptData:
        prompt_tmpl = SHORTS_PROMPT_TEMPLATE if video_format == VideoFormat.SHORTS.value else LONG_FORM_PROMPT_TEMPLATE
        prompt = prompt_tmpl.format(
            topic_name=topic_def.name,
            educational_goal=topic_def.educational_goal,
        )

        auth_token = settings.openai_api_key
        headers = {
            "Authorization": "Bearer " + auth_token,
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": KID_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7,
        }

        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(data)
        parsed["video_format"] = video_format
        parsed["topic"] = topic_def.id
        return ScriptData.from_dict(parsed)

    def _generate_with_anthropic(self, video_format: str, topic_def: Any) -> ScriptData:
        prompt_tmpl = SHORTS_PROMPT_TEMPLATE if video_format == VideoFormat.SHORTS.value else LONG_FORM_PROMPT_TEMPLATE
        prompt = prompt_tmpl.format(
            topic_name=topic_def.name,
            educational_goal=topic_def.educational_goal,
        )

        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.anthropic_model,
            "max_tokens": 2048,
            "system": KID_SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": f"{prompt}\nReturn ONLY pure JSON without markdown backticks."}
            ],
        }

        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        # Strip potential markdown fences
        clean = re.sub(r"^```json\s*", "", text.strip())
        clean = re.sub(r"\s*```$", "", clean)
        parsed = json.loads(clean)
        parsed["video_format"] = video_format
        parsed["topic"] = topic_def.id
        return ScriptData.from_dict(parsed)


script_generator = ScriptGenerator()
