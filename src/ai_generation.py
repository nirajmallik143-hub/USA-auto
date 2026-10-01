import os
import json
import random
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Fallback Offline Database of Kids Content
OFFLINE_SCRIPTS = {
    "stories": [
        {
            "title": "The Little Bear's Big Adventure",
            "scenes": [
                {"title": "Meet Barnaby Bear", "text": "Once upon a time, in a bright green forest, lived a little fuzzy bear named Barnaby."},
                {"title": "A Shiny Object", "text": "One sunny morning, Barnaby saw a shiny gold key lying under a giant oak tree leaf."},
                {"title": "The Magic Chest", "text": "He followed a trail of tiny yellow flowers and found a wooden chest covered in moss."},
                {"title": "Unlocking the Mystery", "text": "Barnaby turned the key in the lock, click clack! The lid popped open!"},
                {"title": "Sweet Surprise!", "text": "Inside, there were no gold coins, but a heap of delicious sweet berries! The best treasure ever!"}
            ]
        },
        {
            "title": "The Star That Lost Its Sparkle",
            "scenes": [
                {"title": "Twinkle, the Tiny Star", "text": "High up in the midnight sky lived Twinkle, the smallest and friendliest little star."},
                {"title": "Twinkle Goes Dim", "text": "One night, Twinkle felt sad and lost her sparkly glow. She was totally dark!"},
                {"title": "Moon's Kind Words", "text": "The big round Moon smiled and said, 'Just remember what makes you happy, little star!'"},
                {"title": "Thinking of Friends", "text": "Twinkle thought about playing tag with the comets and tickling the fluffy clouds."},
                {"title": "Sparkling Once More!", "text": "Suddenly, she giggled and burst into a brilliant sparkle! Happiness makes us shine!"}
            ]
        },
        {
            "title": "The Friendly Dinosaur's First Day",
            "scenes": [
                {"title": "Danny the Dino", "text": "Danny was a cute green T-Rex who loved making friends and eating broccoli trees."},
                {"title": "Dino School!", "text": "Today was his very first day at Dino School, and his tummy had little butterflies."},
                {"title": "Meet the Teacher", "text": "His teacher, Mrs. Brontosaurus, gave him a warm smile and a big shiny star sticker."},
                {"title": "Sharing Toys", "text": "Danny shared his favorite colorful building blocks with a shy triceratops named Toby."},
                {"title": "Best Day Ever!", "text": "They giggled and built a giant sandcastle together. Danny loved school!"}
            ]
        }
    ],
    "trivia": [
        {
            "title": "Fun Dinosaur Trivia!",
            "scenes": [
                {"title": "Amazing Dinosaur Facts", "text": "Are you ready to explore the land of dinosaurs? Let's go!"},
                {"title": "The Giant Dino", "text": "Did you know Argentinosaurus was as heavy as seventeen African elephants combined?"},
                {"title": "T-Rex Teeth", "text": "The Tyrannosaurus Rex had teeth as long as large bananas! Imagine brushing those teeth!"},
                {"title": "Dino Feathers", "text": "Many dinosaurs, like the Velociraptor, actually had colorful feathers just like modern birds!"},
                {"title": "Fast Runners", "text": "Some small dinosaurs could run faster than a school bus! Beep beep, watch out!"}
            ]
        },
        {
            "title": "Unbelievable Space Facts!",
            "scenes": [
                {"title": "Space is Cool!", "text": "Let's zoom past the clouds and discover the secrets of outer space!"},
                {"title": "No Sound in Space", "text": "Space is completely silent! There is no air, so sound waves can't travel at all!"},
                {"title": "Hot Venus", "text": "Venus is the hottest planet, even hotter than a baking oven at four hundred degrees!"},
                {"title": "Diamond Rain", "text": "On Neptune and Saturn, it actually rains real diamonds! Talk about a sparkly shower!"},
                {"title": "Floating Astronauts", "text": "Astronauts grow taller in space because there is no gravity pulling them down!"}
            ]
        }
    ],
    "learning": [
        {
            "title": "Learn Colors with Fruits!",
            "scenes": [
                {"title": "Let's Learn Colors!", "text": "Hello friends! Today we are learning beautiful colors with tasty fruits!"},
                {"title": "Red Strawberry", "text": "First, we have red! This sweet strawberry is bright and red! Delicious!"},
                {"title": "Yellow Banana", "text": "Next is yellow! This curved banana is yellow and very rich in vitamins!"},
                {"title": "Green Apple", "text": "Here is green! A crispy green apple is sweet, tart, and super healthy!"},
                {"title": "Purple Grapes", "text": "Finally, we have purple! A juicy bunch of purple grapes to finish our rainbow feast!"}
            ]
        },
        {
            "title": "Counting Forest Animals 1 to 5!",
            "scenes": [
                {"title": "Let's Count Animals!", "text": "Let's visit the magic forest and count our friendly animal neighbors!"},
                {"title": "One Little Fox", "text": "Look! There is one clever orange fox taking a nap under the bush!"},
                {"title": "Two Friendly Deer", "text": "One, two! Two elegant deer eating sweet green grass together."},
                {"title": "Three Busy Squirrels", "text": "One, two, three! Three busy squirrels gathering brown acorns for winter."},
                {"title": "Four Happy Rabbits", "text": "One, two, three, four! Four fluffy rabbits hopping around the meadow!"},
                {"title": "Five Wise Owls", "text": "One, two, three, four, five! Five wise owls hooting in the tall trees!"}
            ]
        }
    ]
}


def generate_kids_script(category: str, is_short: bool = True, topic_detail: str = None) -> Dict[str, Any]:
    """
    Generates a structured kid-friendly script for video generation.
    Returns:
        dict: {
            "title": "Title of the video",
            "category": "stories" | "trivia" | "learning",
            "scenes": [
                {"title": "Scene Visual Cue/Title", "text": "Spoken voiceover text"},
                ...
            ]
        }
    """
    category = category.lower()
    if category not in ["stories", "trivia", "learning"]:
        category = random.choice(["stories", "trivia", "learning"])

    provider = os.getenv("AI_PROVIDER", "mock").lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            length_desc = "Short vertical video (approx 30-45 seconds, 4-5 quick simple scenes)" if is_short else "Long horizontal video (approx 2-3 minutes, 8-12 interactive educational scenes)"
            
            prompt = f"""
            Write a highly engaging, safe, educational, and fun kids video script.
            Target Audience: Toddlers & Young Kids (US-based)
            Category: {category}
            Topic / Specifics: {topic_detail or "Surprise us with a popular kid-friendly theme"}
            Video Format: {length_desc}
            
            IMPORTANT:
            1. Language must be extremely simple, clear, phonetic, energetic, and repetitive.
            2. Return ONLY a valid JSON object matching this schema:
            {{
                "title": "Engaging Catchy Kid-Friendly Title",
                "scenes": [
                    {{
                        "title": "Short Visual Title (e.g. Red Strawberry)",
                        "text": "Extremely simple, slow, clear spoken voiceover text (e.g. This is a bright red strawberry! It is sweet and yummy!)"
                    }}
                ]
            }}
            Do not include any other markdown formatting or text outside the JSON.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional kids' YouTube channel content scriptwriter."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8
            )
            
            result = json.loads(response.choices[0].message.content)
            result["category"] = category
            logger.info(f"Successfully generated script via OpenAI: {result['title']}")
            return result
        except Exception as e:
            logger.error(f"OpenAI script generation failed ({e}). Falling back to local script generator.")

    # Fallback/Mock Generator
    available_scripts = OFFLINE_SCRIPTS.get(category, OFFLINE_SCRIPTS["learning"])
    selected = random.choice(available_scripts)
    
    # If it's a Short, we keep only the first 3-4 scenes to keep it brief
    # If it's Long, we can use the full set of scenes, and maybe duplicate/extend or just keep as is
    scenes = selected["scenes"]
    if is_short and len(scenes) > 4:
        scenes = scenes[:4]
    elif not is_short and len(scenes) < 6:
        # For long form, let's make sure it has enough scenes, or use them as is
        pass
        
    script = {
        "title": selected["title"],
        "category": category,
        "scenes": [dict(s) for s in scenes]
    }
    
    # Let's customize it slightly if a topic_detail is specified in fallback mode
    if topic_detail:
        script["title"] = f"{topic_detail} ({category.capitalize()})"
        
    logger.info(f"Generated mock/local script: {script['title']}")
    return script
