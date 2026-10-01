"""
Kid-friendly prompt definitions and guidelines for LLM script generation.
Adheres strictly to COPPA safety and child-appropriate language.
"""

KID_SYSTEM_PROMPT = """You are a world-class children's educational content creator, animator, and storyteller for US kids aged 3 to 8.
Your style is:
1. Warm, enthusiastic, cheerful, and encouraging (like Mr. Rogers meets modern fun animated shows).
2. Clean, safe, positive, and COPPA compliant (strictly NO violence, NO scary elements, NO sensitive topics).
3. Educational, sparking curiosity, kindness, and joyful wonder.
4. Uses simple words, expressive conversational beats, sound effects descriptions (e.g., [Roar!], [Chirp!], [Ding!]), and natural kid pauses.

You output ONLY valid, strictly parseable JSON conforming exactly to the requested schema.
"""

SHORTS_PROMPT_TEMPLATE = """Generate a high-energy, super-engaging YouTube Short script for US kids on the topic: "{topic_name}".
Educational Objective: {educational_goal}

CRITICAL RULES FOR SHORTS:
1. Length: MUST BE UNDER 60 SECONDS when spoken out loud (between 80 and 130 words maximum).
2. Hook: First 3 seconds MUST grab attention instantly (e.g., "Wait! Can you guess who has the biggest ears on Earth?", "Quick question! What shines brighter than a million diamonds?").
3. Middle (10-35s): 3-4 bite-sized, fascinating clues, rhymes, or fun facts.
4. Climax / Reveal (35-45s): Exciting answer or joyful celebration!
5. Call-To-Action (45-55s): Friendly kid CTA (e.g. "Did you guess right? Tell your parents or tap subscribe for more animal fun!").

Output JSON format:
{{
  "title": "Short, catchy title with kid emoji and #Shorts (under 60 chars)",
  "description": "2-3 kid-friendly sentences describing the short, with 3-4 safe hashtags (#KidsLearning #Shorts #FunFacts)",
  "tags": ["kid safe tag 1", "tag 2", "tag 3", "tag 4", "tag 5"],
  "target_duration_seconds": 45,
  "scenes": [
    {{
      "narration": "Exact words spoken by the voiceover.",
      "visual_description": "Clear visual cue for background and stickers (e.g., cute cartoon baby elephant drinking water).",
      "caption_text": "Punched-up, short caption text for auto-subtitles (3-6 words maximum).",
      "duration_seconds": 6
    }}
  ],
  "call_to_action": "Friendly outro line"
}}
"""

LONG_FORM_PROMPT_TEMPLATE = """Generate a full, joyful, interactive long-form YouTube episode script (3 to 8 minutes) for US kids on the topic: "{topic_name}".
Educational Objective: {educational_goal}

CRITICAL RULES FOR LONG-FORM EPISODES:
1. Length: Target 450 to 800 words (structured across 4-6 narrative segments / chapters).
2. Chapter 1: Cheerful Welcome, catchy intro hook, and hello song or greeting.
3. Chapter 2: The Core Discovery / Story Part 1 (fascinating, colorful details).
4. Chapter 3: Interactive Kid Challenge (riddle, count-along, find-the-hidden-object, or repeat-after-me).
5. Chapter 4: Story Part 2 / Wow-Factor Deep Dive.
6. Chapter 5: Helpful Summary Lesson, kindness/moral takeaway, and goodbye wave.
7. Include natural visual scene shifts every 15-30 seconds to keep young minds visually stimulated.

Output JSON format:
{{
  "title": "Engaging, parent-approved YouTube title with emoji (e.g., 'Amazing Space Secrets for Kids! 🚀 Explore Planets, Stars & The Moon!')",
  "description": "Engaging description with educational overview, timestamps (00:00 Welcome, etc.), COPPA statement, and hashtags.",
  "tags": ["kids education", "learning for toddlers", "fun kids video", "stem for kids", "storytime"],
  "target_duration_seconds": 240,
  "chapters": [
    {{"time": "00:00", "title": "Welcome Friends!"}},
    {{"time": "00:45", "title": "The Big Discovery"}},
    {{"time": "01:45", "title": "Interactive Play & Riddle"}},
    {{"time": "02:45", "title": "Secret Fun Facts"}},
    {{"time": "03:30", "title": "Recap & High Five!"}}
  ],
  "scenes": [
    {{
      "narration": "Spoken segment text for this chapter scene.",
      "visual_description": "Visual scene description for kid cartoon animations or stock footage.",
      "caption_text": "Key phrase highlight for auto-captions.",
      "duration_seconds": 20
    }}
  ],
  "call_to_action": "Warm goodbye, high-five, and invitation to subscribe with parents' permission."
}}
"""
