import os
import time
import requests
import random

# ── API KEYS ───────────────────────────────────────────────────────────────
INVOKE_URL = os.getenv("INVOKE_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
grok_headers = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# ── Models ────────────────────────────────────────────────────────────────
FAST_MODEL       = "meta/llama-3.1-8b-instruct"
QUALITY_MODEL    = "meta/llama-3.3-70b-instruct"
HUMANIZE_MODEL   = "meta/llama-3.1-70b-instruct"
ROUGHEN_MODEL    = "meta/llama-3.1-8b-instruct"
FINAL_TOUCH_MODEL= "meta/llama-3.1-8b-instruct"

LENGTH_MAP = {
    "Short (500-800 words)":    {"min": 500,  "max": 800,  "max_tokens": 1200},
    "Medium (1000-1500 words)": {"min": 1000, "max": 1500, "max_tokens": 2200},
    "Long (2000+ words)":       {"min": 2000, "max": 2500, "max_tokens": 3800},
}

# ── NVIDIA CHAT HELPER ────────────────────────────────────────────────────
def _nvidia_chat(prompt_text, model=QUALITY_MODEL, max_tokens=300, temperature=0.6, timeout=300):
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key or nvidia_api_key.strip().lower() in {"none", "null", "your-key", "nvapi-your-key"}:
        raise RuntimeError(
            "NVIDIA_API_KEY is missing. Add a valid NVIDIA NIM API key to "
            "Backend/ScriptNova-Backend/.env, then restart the backend server."
        )

    headers = {
        "Authorization": f"Bearer {nvidia_api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    last_error = None
    for attempt in range(3):
        try:
            r = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                raise RuntimeError(
                    "NVIDIA rejected the API key. Check NVIDIA_API_KEY in "
                    "Backend/ScriptNova-Backend/.env and restart the backend server."
                ) from e
            raise
    raise last_error

# ── GROK CHAT HELPER ──────────────────────────────────────────────────────
def _grok_chat(prompt_text, max_tokens=2500, temperature=1.18, model="llama-3.3-70b-versatile"):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_completion_tokens": max_tokens
    }
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        r = requests.post(GROK_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ GROK FAILED:", str(e))
        raise

# ── MERGED ULTIMATE HUMANIZER ─────────────────────────────────────────────
def humanize_content(content: str, style: str = "natural"):
    """
    Combines Perplexity/Burstiness (ZeroGPT) and Structural Flipping (Quillbot) 
    tactics into a single-pass deep humanizer.
    """
    
    # Personas that naturally write with 'messy' AI-resistant structures
    PERSONAS = [
        "A skeptical field expert who uses 'I' and 'me' and hates corporate jargon.",
        "A sharp-tongued blogger who writes in quick bursts and personal asides.",
        "A technical veteran explaining things to a friend with 'real-talk' honesty."
    ]
    
    selected_persona = random.choice(PERSONAS)
    
    # Randomly inject a 'Human Quirk' to break the AI's perfect logic flow
    quirks = [
        # "Use parentheses (like this) for a quick side-thought.",
        "Start a sentence with 'Look,' or 'Honestly,' to sound more conversational.",
        "Include a one-word sentence for emphasis.",
        "Use a contraction like 'wouldn't' or 'it's' in every second sentence."
    ]
    selected_quirk = random.choice(quirks)

    prompt = f"""
    [SYSTEM: ACT AS {selected_persona.upper()}]
    
    TASK: Rewrite the text below to be completely undetectable by AI classifiers. 
    You must destroy the 'AI footprint' by being statistically unpredictable.
    
    QUIRK TO INCLUDE: {selected_quirk}

    ANTI-DETECTION RULES (STRICT):
    1. BURSTINESS (ZeroGPT): Every paragraph must mix a very long, complex sentence (max 15 words) with a very short, punchy one (under 5 words).
    2. LOGIC FLIPPING (Quillbot): Do not follow the original sentence order. Explain the 'result' or 'impact' first, then the 'process'.
    3. NO SYNONYM SPINS: Don't just swap words. Rephrase the entire thought as if you're speaking out loud.
    4. DELETE TRANSITIONS: Kill all words like 'Furthermore', 'Moreover', 'In addition', 'In conclusion', and 'Notably'.
    5. I/ME PERSPECTIVE: Use first-person perspective or direct address ('you') to break formal AI neutrality.
    6. you can pharaphrase some sentence to make it more human like and less ai like
    7. Use simple, common words. If a simpler word exists, use it. Always.
    
    BANNED AI DNA: 
    delve, tapestry, leverage, unlock, comprehensive, multifaceted, dynamic, testament, navigate, realm.

    TEXT TO TRANSFORM:
    {content}
    """

    # We use 70b-versatile because 8b models can't handle these complex logic flips
    return _grok_chat(prompt, model="llama-3.3-70b-versatile")

# ── EXAMPLE USAGE ──────────────────────────────────────────────────────────
# result = humanize_content_v2("Your AI-generated text here")
# print(result)

# # ── GROK CHAT HELPER ──────────────────────────────────────────────────────
# def _grok_chat(prompt_text, max_tokens=1500, temperature=1.0, timeout=300, model="llama-3.3-70b-versatile", api_key=GROK_API_KEY):
#     payload = {
#         "model": model,
#         "messages": [{"role": "user", "content": prompt_text}],
#         "temperature": temperature,
#         "max_completion_tokens": max_tokens
#     }
#     try:
#         r = requests.post(GROK_URL, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
#                           json=payload, timeout=timeout)
#         r.raise_for_status()
#         return r.json()["choices"][0]["message"]["content"]
#     except Exception as e:
#         print("❌ GROK FAILED:", str(e))
#         raise
    

# import os
# import random
# import requests

# # Ensure these are set in your environment
# GROK_API_KEY = os.getenv("GROK_API_KEY")
# GROK_URL = "https://groq.com"

# def humanize_content(content: str):
#     """
#     Advanced humanizer designed to break ZeroGPT/Quillbot patterns.
#     Uses high temperature (1.1 - 1.2) and 'Burstiness' constraints.
#     """
    
#     # Anti-AI Personas: These are designed to be 'imperfect'
#     PERSONAS = [
#         "A skeptical veteran who hates corporate fluff and uses short, punchy sentences.",
#         "A tired freelancer who writes with messy, long run-on sentences mixed with tiny ones.",
#         "A direct practitioner who uses 'I' and 'me' and avoids all formal transitions."
#     ]
    
#     selected_persona = random.choice(PERSONAS)

#     # The Prompt: Focused on breaking 'predictability'
#     prompt = f"""
#     [SYSTEM: {selected_persona}]
    
#     REWRITE RULE #1 (BURSTINESS): You must vary sentence length wildly. Every paragraph must have one 30+ word sentence and one 3-5 word sentence.
#     REWRITE RULE #2 (PERPLEXITY): Use common, 'ugly' words. Replace 'utilize' with 'use', 'facilitate' with 'help', 'subsequent' with 'next'.
#     REWRITE RULE #3 (TRANSITIONS): Delete 'Furthermore', 'Moreover', 'In conclusion', and 'Notably'. They are AI tracking signals.
#     REWRITE RULE #4 (FLAWED LOGIC): It is okay to start a sentence with 'And' or 'But'. Use fragments like 'At least for now.' or 'Makes sense.'
    
#     STRICT BANNED WORDS: delve, tapestry, leverage, unlock, comprehensive, dynamic, multifaceted, fast-paced world, journey.

#     TEXT TO HUMANIZED:
#     {content}
#     """

#     payload = {
#         "model": "llama-3.3-70b-versatile", # Use 70B for high-quality reasoning
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 1.15,  # Higher temp = less predictable word choices
#         "max_tokens": 4096
#     }
    
#     headers = {
#         "Authorization": f"Bearer {GROK_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     try:
#         r = requests.post(GROK_URL, headers=headers, json=payload, timeout=120)
#         r.raise_for_status()
#         return r.json()["choices"][0]["message"]["content"]
#     except Exception as e:
#         return f"Error: {str(e)}"

# def deep_humanize(content: str):
#     """
#     Advanced humanizer that targets QuillBot's structural analysis.
#     Uses 'sentence flipping' and 'imperfection injection'.
#     """
#     # High-variability persona focused on informal, non-linear thought
#     prompt = f"""
#     [ACT AS A HUMAN WRITER IN A HURRY]
    
#     TASK: Completely re-organize the following text. 
    
#     ANTI-QUILLBOT RULES:
#     1. FLIP THE LOGIC: Do not follow the original sentence order. Start with the 'why' instead of the 'what'.
#     2. DELETE TRANSITIONS: Remove all words like 'Furthermore', 'Consequently', 'Moreover'. Real people use 'Also', 'So', or just start a new paragraph.
#     3. INJECT IMPERFECTIONS: Use a sentence fragment. Use a contraction (can't, won't) every single time. 
#     4. VARY RHYTHM: One sentence must be over 35 words. The very next must be 4 words or fewer.
#     5. NO SYNONYM SWAPPING: Don't just replace words. Change how the idea is explained. Explain it like you're talking to a friend at a loud bar.
    
#     BANNED PATTERNS (AI SIGNATURES):
#     - No "In conclusion" or "To summarize".
#     - No "Not only... but also..."
#     - No passive voice. Change 'The ball was hit' to 'I hit the ball'.

#     TEXT:
#     {content}
#     """

#     # We use a very high temperature (1.2) to maximize unpredictability
#     return _grok_chat(prompt, model="llama-3.3-70b-versatile", temperature=1.2, max_tokens=3500)


# --------------------------------------------------------------------------------
# import random

# PERSONAS = [
#     {
#         "name": "burnt-out journalist",
#         "voice": (
#             "You're a journalist who's been writing since 2003. You've covered everything. "
#             "You're a little tired of hype. You cut to what actually matters. "
#             "Your sentences are short when making a point. They get longer when explaining something complicated, "
#             "almost like you're thinking out loud. You occasionally catch yourself mid-thought and redirect. "
#             "You don't explain things twice. You trust your reader."
#         ),
#     },
#     {
#         "name": "curious generalist blogger",
#         "voice": (
#             "You run a blog that a few thousand people read. You're not an expert — you just research obsessively "
#             "and write about what you found in plain English. You get excited. You share the interesting bits. "
#             "You sometimes go on a tangent and pull yourself back. "
#             "You write like you talk — occasional run-ons, the odd half-finished thought. "
#             "You never use words like 'leverage' or 'delve' because that's not how you talk."
#         ),
#     },
#     {
#         "name": "no-nonsense practitioner",
#         "voice": (
#             "You've actually done this stuff. Not read about it — done it. "
#             "Zero patience for fluff. You say the thing directly. "
#             "Short sentences. Occasionally one that's just four words. Then you explain why. "
#             "You don't hedge. You don't say 'it's important to note.' You just note it."
#         ),
#     },
#     {
#         "name": "enthusiastic specialist",
#         "voice": (
#             "You genuinely love this topic. It shows. You find the surprising angles interesting. "
#             "You ask rhetorical questions because you want the reader to think. "
#             "Your paragraphs are uneven — sometimes two sentences, sometimes seven. "
#             "You throw in a personal observation here and there. "
#             "You don't wrap things up with fake conclusions. You end when you've said what you wanted."
#         ),
#     },
# ]

# STYLE_TONES = {
#     "natural":        "casual and genuine, like a real person wrote this on a Tuesday",
#     "conversational": "like you're texting a smart friend a really detailed message",
#     "storytelling":   "narrative-forward, scene-setting, emotionally grounded",
#     "professional":   "direct and confident, written by someone who has done the work",
# }

# def humanize_content(content: str, style: str = "natural") -> str:
#     persona = random.choice(PERSONAS)
#     tone_desc = STYLE_TONES.get(style, STYLE_TONES["natural"])
    
#     # Randomly pick a 'human quirk' to force the AI out of its comfort zone
#     quirks = [
#         "Start at least two sentences with 'Look,' or 'Honestly,' or 'See,'",
#         "Use a fragment sentence (no verb) for emphasis somewhere.",
#         "Use a set of parentheses (like this) to add a quick side-note.",
#         "Break a long sentence into two using a single coordinating conjunction like 'But' or 'Yet'."
#     ]
#     selected_quirk = random.choice(quirks)

#     prompt = f"""
# [SYSTEM: ACT AS A {persona['name'].upper()}. {persona['voice']}]

# TASK: Rewrite the provided text. You must destroy the 'AI look' by being statistically unpredictable.

# {selected_quirk}

# CORE RULES:
# 1. BURSTINESS: Every paragraph must have one very long sentence (30+ words) and one very short sentence (under 5 words). 
# 2. LOW PREDICTABILITY: Use 'mostly' instead of 'predominantly', 'use' instead of 'utilize', 'help' instead of 'facilitate'.
# 3. CONTRACTIONS: Use 'don't', 'can't', 'it's', 'won't' 100% of the time.
# 4. NO REPETITION: Never start two consecutive sentences with the same word.
# 5. NO LISTS: If the original has a bulleted list, turn it into a messy, conversational paragraph.

# BANNED LIST (Detection Triggers):
# - "Delve", "Leverage", "Tapestry", "Testament", "In the rapidly evolving", "Furthermore", "Moreover", "In conclusion".
# - No "Imagine a world where..." or "In today's digital age..."

# STYLE: {tone_desc}

# TEXT TO REWRITE:
# {content}
# """
#     # CRITICAL: Temperature must be high (1.0 - 1.2) to avoid "Top-K" word predictability
#     return _grok_chat(prompt, max_tokens=3800, temperature=1.1, model="llama-3.3-70b-versatile")


# def humanize_content(content: str, style: str = "natural") -> str:
#     """
#     Single-pass humanizer using Grok at high temperature.
#     Persona identity + pattern destruction + banned words all in one prompt.
#     No second pass — second passes re-sanitize back to AI-smooth.
#     """
#     persona   = random.choice(PERSONAS)
#     tone_desc = STYLE_TONES.get(style, STYLE_TONES["natural"])

#     prompt = f"""You are a {persona['name']}.

# {persona['voice']}

# Rewrite the article below completely in your voice. Tone: {tone_desc}.

# STRUCTURE RULES (non-negotiable):
# - Keep every ## heading exactly as written — word for word, do not rename or remove any.
# - Keep all facts, data, and key points. Do not invent new information.
# - Do NOT open your response with meta-text like "Here is the rewritten article" — just start writing.

# VOICE & STYLE RULES:
# - Contractions everywhere: don't, it's, you'll, can't, won't, that's, we're.
# - Sentence lengths must vary wildly and unpredictably. Some sentences: 4-6 words. Some: 20-28 words. No consistent rhythm — ever.
# - Paragraph lengths vary too. One paragraph: 2 sentences. Next one: 5-6 sentences. Don't be consistent.
# - Simple vocabulary only. If a shorter, plainer word exists — use it. Always.
# - Add one rhetorical question somewhere in the middle. Make it feel natural, not forced.
# - Add one very short punchy sentence (3-5 words max) somewhere it lands like a gut punch.
# - One sentence somewhere should trail off or end slightly abruptly, like the writer moved on mid-thought.
# - Occasionally start a sentence with "And", "But", or "So" — real writers do this.
# - One slight word repetition across paragraphs is fine. Real writers repeat themselves.

# BANNED WORDS & PHRASES — do not use any of these anywhere:
# leverage, delve, realm, game-changer, revolutionize, in today's world, it's worth noting,
# it is important to note, in conclusion, furthermore, nevertheless, to summarize,
# in this article, let's dive in, navigate, multifaceted, embark, robust, cutting-edge,
# it goes without saying, at the end of the day, having said that.

# BANNED PATTERNS:
# - Do NOT use em dashes (—) more than once total.
# - Do NOT write 3 sentences in a row starting with "The" or "This".
# - Do NOT write 3+ consecutive sentences of roughly the same length.
# - Do NOT use textbook definitions ("X is defined as...", "X refers to...", "X can be described as...") — turn them into human observations instead.
# - Do NOT end with a generic motivational conclusion. End naturally, like a real writer would.

# ARTICLE:
# {content}"""

#     return _grok_chat(prompt, max_tokens=3800, temperature=1.15, timeout=360)



# # ── HUMANIZER ─────────────────────────────────────────────────────────────
# STYLE_INSTRUCTIONS = {
#     "natural": (
#         "Write in a natural, human style. Mix short and long sentences, "
#         "use casual asides, avoid formal words, contractions everywhere."
#     ),
#     "conversational": (
#         "Write as if chatting with a smart friend. Loose, informal, rhetorical questions, "
#         "short paragraphs, natural sentence flow."
#     ),
#     "storytelling": (
#         "Rewrite as a story. Introduce scenes, use varied sentence lengths, "
#         "place reader inside situations, occasional 'I' statements."
#     ),
#     "professional": (
#         "Rewrite as a senior industry expert. Direct, confident, no fluff, "
#         "vary sentence openings, keep clarity and concise flow."
#     ),
# }

# def humanize_content(content, style="natural"):
#     """
#     Three-pass humanizer reducing AI detection.
#     Frontend can pass style: 'natural', 'conversational', 'storytelling', 'professional'
#     """

#     instruction = STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["natural"])

#     # ── PASS 1: GROK deep rewrite ───────────────────────────────
#     pass1_prompt = (
#         f"{instruction}\n\n"
#         "Rules:\n"
#         "- Keep all original facts and headings (## markdown).\n"
#         "- Vary sentence lengths (4-15 words).\n"
#         "- Avoid formal vocabulary, high-level words, excessive punctuation.\n"
#         "- Slight imperfections and casual tone to mimic human writing.\n"
#         "- AI detection should be below 5%.\n\n"
#         f"ARTICLE:\n{content}"
#     )

#     pass1 = _grok_chat(pass1_prompt, max_tokens=3800, temperature=1.1, timeout=360)

#     # ── PASS 2: NVIDIA roughen patterns ─────────────────────────
#     pass2_prompt = (
#         "Reduce AI patterns without changing meaning.\n"
#         "1. Break uniform sentence patterns.\n"
#         "2. Add one slightly awkward sentence.\n"
#         "3. Include one rhetorical question.\n"
#         "4. Replace formal words with simple ones.\n"
#         "5. Remove robotic transitions.\n\n"
#         f"TEXT:\n{pass1}"
#     )
#     pass2 = _nvidia_chat(pass2_prompt, model=ROUGHEN_MODEL, max_tokens=3800, temperature=0.9, timeout=300)

#     # ── PASS 3: Final human touch ───────────────────────────────
#     pass3_prompt = (
#         "Final humanization pass:\n"
#         "- Slight repetition of words.\n"
#         "- One very short sentence (3-5 words).\n"
#         "- Slight imperfection in flow.\n\n"
#         f"TEXT:\n{pass2}"
#     )
#     pass3 = _nvidia_chat(pass3_prompt, model=FINAL_TOUCH_MODEL, max_tokens=3800, temperature=0.95, timeout=300)

#     return pass3


# ── Serializer ────────────────────────────────────────────────────────────────

def blog_to_dict(blog, include_content=True):
    author_name = f"{blog.user.first_name} {blog.user.last_name}".strip() or blog.user.username
    d = {
        "id":                blog.id,
        "prompt":            blog.prompt,
        "title":             blog.title,
        "keywords":          blog.keywords,
        "tone":              blog.tone,
        "length_preference": blog.length_preference,
        "word_count":        blog.word_count,
        "slug":              blog.slug,
        "published":         blog.published,
        "favourite":         blog.favourite,
        "is_favourite":      blog.favourite == "favourite",
        "is_humanized":      bool(blog.humanized_content),
        "author":            {
            "id":       blog.user.id,
            "username": blog.user.username,
            "name":     author_name,
        },
        "author_name":       author_name,
        "created_at":        blog.created_at.isoformat() if blog.created_at else None,
        "updated_at":        blog.updated_at.isoformat() if blog.updated_at else None,
    }
    if include_content:
        d["content"]           = blog.content
        d["humanized_content"] = blog.humanized_content
    return d


# ── Generation helpers ────────────────────────────────────────────────────────

def generate_keywords(topic):
    raw = _nvidia_chat(
        f'Generate 8 SEO-friendly keywords for a blog about: "{topic}"\n'
        f'Return ONLY a comma-separated list. No explanation, no numbering.',
        model=FAST_MODEL, max_tokens=150, temperature=0.4, timeout=180
    )
    return [k.strip() for k in raw.split(",") if k.strip()]


def suggest_title(topic, keywords=None):
    kw = f"\nKeywords: {', '.join(keywords)}" if keywords else ""
    raw = _nvidia_chat(
        f"Suggest ONE catchy, SEO-friendly blog post title for this topic:\n"
        f"Topic: {topic}{kw}\n\n"
        f"Rules:\n- Return ONLY the title text. No quotes, no explanation, no numbering.\n"
        f"- Make it engaging and click-worthy.\n- Between 6 and 12 words.",
        model=FAST_MODEL, max_tokens=60, temperature=0.7, timeout=180
    )
    return raw.strip().strip('"').strip("'")


def generate_blog_content(title, keywords, tone, length):
    kw_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
    cfg    = LENGTH_MAP.get(length, LENGTH_MAP["Medium (1000-1500 words)"])
    return _nvidia_chat(
        f"You are an expert SEO blog writer.\n\n"
        f"Write a blog post with EXACTLY between {cfg['min']} and {cfg['max']} words.\n\n"
        f"Title: {title}\nKeywords: {kw_str}\nTone: {tone}\n\n"
        f"STRUCTURE:\n- Introduction (no heading)\n- 3 to 4 sections each with a ## heading\n"
        f"- Conclusion section with ## Conclusion heading\n\n"
        f"FORMATTING RULES:\n- Use ## for section headings\n"
        f"- Put a blank line before and after every ## heading\n"
        f"- Use **bold** for important terms\n- Use bullet points with \"- \" where appropriate\n"
        f"- Separate paragraphs with a blank line\n\nOUTPUT: blog content only, no extra commentary.",
        model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.6, timeout=360
    )


# # ── Humanizer (two-pass) ──────────────────────────────────────────────────────

# # def humanize_content(content, style="natural"):
# #     """
# #     Two-pass humanizer designed to reduce AI detection scores:

# #     Pass 1 — Rewrites with Mixtral (MoE architecture = higher natural perplexity,
# #               less uniform token distribution than pure RLHF models like Llama).
# #               Temperature 0.92 pushes output off modal/predictable paths.

# #     Pass 2 — Cheap roughen pass with the 8B model. Targets the exact structural
# #               patterns that ZeroGPT and similar detectors key on:
# #               uniform sentence length, filler transitions, repetitive openers.

# #     style options: natural | conversational | storytelling | professional
# #     """

# #     style_instructions = {
# #         "natural": (
# #             "You are a human blogger rewriting an article in your own voice. "
# #             "You write the way you think — not perfectly. "
# #             "Mix very short sentences with longer rambling ones. "
# #             "Start some sentences with 'And', 'But', 'So' — real writers do this. "
# #             "Use contractions everywhere: don't, it's, you'll, they're, can't, won't. "
# #             "Occasionally repeat a word or phrase for emphasis like real writers do. "
# #             "Drop filler transitions like 'Furthermore', 'In conclusion', 'It is worth noting', 'Delve into'. "
# #             "Replace high-vocabulary words with the simplest word that works. "
# #             "Add one small personal aside or casual opinion — just one, not preachy. "
# #             "No two consecutive paragraphs should have the same rhythm or length."
# #         ),
# #         "conversational": (
# #             "You are writing this as if messaging a smart friend a long detailed message about a topic you care about. "
# #             "Keep it loose and natural. Some sentences are half-finished thoughts. "
# #             "Ask a rhetorical question mid-article like 'Makes sense, right?' or 'Sound familiar?'. "
# #             "Use openers like 'Honestly,', 'Look,', 'Here's the thing —', 'The truth is,' to start paragraphs sometimes. "
# #             "Short paragraphs. Contractions always. Zero corporate language. "
# #             "If something is complicated, say so — then explain it simply."
# #         ),
# #         "storytelling": (
# #             "You are a blogger who always opens with a scene or moment — never a fact or statistic. "
# #             "Rewrite this article so the introduction puts the reader inside a specific situation. "
# #             "Weave the information into the narrative rather than listing it. "
# #             "Use 'I' once or twice naturally. "
# #             "Write at least one sentence that is only three to five words — a gut-punch moment. "
# #             "Write at least one sentence that runs long, building and building a point across multiple clauses "
# #             "because you want the reader to feel the weight of it before you land. "
# #             "Real writers have wildly uneven rhythms. Match that energy."
# #         ),
# #         "professional": (
# #             "You are a senior industry practitioner — not a content marketer, not a copywriter. "
# #             "Write with earned confidence and zero fluff. "
# #             "Cut any sentence that doesn't add concrete information or insight. "
# #             "Never hedge with phrases like 'It is important to note', 'One might argue', 'It goes without saying'. "
# #             "Just say the thing directly. "
# #             "Vary your sentence openings — no two consecutive sentences start the same way. "
# #             "One sentence per section should be unusually short. A single sharp point. Like this. "
# #             "Sound like a person who has done the work, not a model summarising a topic."
# #         ),
# #     }

# #     instruction = style_instructions.get(style, style_instructions["natural"])

# #     # ── Pass 1: Core rewrite — Mixtral for higher perplexity output ───────────
# #     pass1_prompt = (
# #         f"{instruction}\n\n"
# #         f"NON-NEGOTIABLE RULES:\n"
# #         f"- Keep ALL the same facts, data points, and information\n"
# #         f"- Keep ALL ## markdown section headings exactly as they are\n"
# #         f"- Keep **bold** formatting on important terms\n"
# #         f"- Do NOT add new information or remove existing points\n"
# #         f"- Do NOT write a meta-intro like 'Here is the rewritten article' — just start writing\n"
# #         f"- Use simple, everyday vocabulary. No SAT words, no jargon unless it's the topic itself\n"
# #         f"- Sentence lengths must vary wildly — mix 4-word sentences with 30-word sentences freely\n"
# #         f"- Output the rewritten article only. Nothing else.\n\n"
# #         f"ARTICLE TO REWRITE:\n{content}"
# #     )

# #     pass1_output = _nvidia_chat(
# #         pass1_prompt,
# #         model=HUMANIZE_MODEL,
# #         max_tokens=3800,
# #         temperature=0.92,   # high — push off modal token paths
# #         timeout=360
# #     )

# #     # ── Pass 2: Roughen pass — fast 8B model, targets detector patterns ───────
# #     pass2_prompt = (
# #         f"Read this article carefully and make the following specific edits. "
# #         f"Do not rewrite the whole thing — just apply these targeted fixes:\n\n"
# #         f"1. Find any paragraph where all sentences are roughly the same length. "
# #         f"   In that paragraph, split one sentence into two short ones, and merge two others into one longer run-on.\n\n"
# #         f"2. Scan every word that sounds formal, elevated, or textbook-ish. "
# #         f"   Replace it with the simplest everyday word that means the same thing.\n\n"
# #         f"3. If three or more consecutive sentences start with the same word or the same type of opening "
# #         f"   (like 'The', 'This', 'These' repeatedly), rewrite one of them to start differently.\n\n"
# #         f"4. Add exactly one very short punchy sentence (4 to 6 words maximum) somewhere in the middle of "
# #         f"   the article where the writing feels slow or dense.\n\n"
# #         f"5. Hunt down and remove or rephrase any of these AI clichés wherever they appear: "
# #         f"   'it's important to', 'in today's world', 'in this article', 'let's dive in', "
# #         f"   'to summarize', 'in conclusion', 'it is worth noting', 'delve into', "
# #         f"   'in the realm of', 'game-changer', 'revolutionize', 'leverage' (when used loosely).\n\n"
# #         f"STRICT RULES:\n"
# #         f"- Keep ALL ## markdown headings unchanged\n"
# #         f"- Keep ALL the same information — do not add or remove facts\n"
# #         f"- Don't use to much punctuation especially (—) this one \n"
# #         f"- Output the final article only. No explanation of what you changed.\n\n"
# #         f"- Not sound like an AI / agent/bot. must dteect ai less than 10% also ddont use high level vocabulary\n\n"
# #         f"ARTICLE:\n{pass1_output}"
# #     )

# #     pass2_output = _nvidia_chat(
# #         pass2_prompt,
# #         model=ROUGHEN_MODEL,    # fast + cheap — no need for 70B here
# #         max_tokens=3800,
# #         temperature=0.85,
# #         timeout=300
# #     )

# #     return pass2_output

# def humanize_content(content, style="natural"):
#     """
#     3-pass humanizer to reduce AI detection without touching original meaning.
#     """

#     # ── PASS 1: Deep rewrite (high variation) ───────────────────────
#     pass1_prompt = (
#         "Rewrite this article like a real human wrote it.\n\n"
#         "Rules:\n"
#         "You are a human blogger rewriting an article in your own voice. "
#         "Keep[ the length of the blog as it is -means in range of the article not too breif not too elaborate"
#         "You write the way you think  not perfectly. "
#         "Mix very short sentences with longer rambling ones. "
#         "Start some sentences with 'And', 'But', 'So' — real writers do this. "
#         "Use contractions everywhere: don't, it's, you'll, they're, can't, won't. "
#         "Occasionally repeat a word or phrase for emphasis like real writers do. "
#         "Drop filler transitions like 'Furthermore', 'In conclusion', 'It is worth noting', 'Delve into'. "
#         "Replace high-vocabulary words with the simplest word that works. "
#         "Add one small personal aside or casual opinion — just one, not preachy. "
#         "No two consecutive paragraphs should have the same rhythm or length."
#         "- Avoid perfect grammar \n"
#         "- Avoid formal vocabulary\n"
#         "- sounds like a human written\n\n"
#         "- keep in mind that AI detections hould less than 5%\n\n"
#         "- Dont use too much puntuation\n\n"
#         "- Dont sound robotic or agent\n\n"
#         "- Slight imperfection in flow\n\n"
#         "- Dont use high level vocabulary\n\n"
#         "Srict Rules:\n"
#         "- length of sentence = Small to medium sentences"
#         "- dont make a sentence more than 12-15 words!!!!!\n\n"
#         "Keep markdown headings (##) unchanged.\n\n"
#         f"ARTICLE:\n{content}"
#     )

#     pass1 = _grok_chat(
#         pass1_prompt,
#         max_tokens=3800,
#         temperature=1.1,
#         timeout=360
#     )

#     # ── PASS 2: Break AI patterns ───────────────────────────────────
#     pass2_prompt = (
#         "Make this text feel less like AI.\n\n"
#         "Do this:\n"
#         "1. Break uniform sentence patterns\n"
#         "2. Add 1 slightly awkward sentence\n"
#         "3. Add 1 rhetorical question\n"
#         "4. Replace formal words with simple ones\n"
#         "5. Remove robotic transitions\n\n"
#         "Keep meaning same. Keep headings.\n\n"
#         f"TEXT:\n{pass1}"
#     )

#     pass2 = _nvidia_chat(
#         pass2_prompt,
#         model=ROUGHEN_MODEL,
#         max_tokens=3800,
#         temperature=0.9,
#         timeout=300
#     )

#     # ── PASS 3: Human noise injection ───────────────────────────────
#     pass3_prompt = (
#         "Final pass to make it human-like.\n\n"
#         "Add:\n"
#         "- Slight repetition of words\n"
#         "- One very short sentence (3-5 words)\n"
#         "- Slight imperfection in flow\n\n"
#         "Do NOT change meaning.\n\n"
#         f"TEXT:\n{pass2}"
#     )

#     pass3 = _nvidia_chat(
#         pass3_prompt,
#         model=FINAL_TOUCH_MODEL,
#         max_tokens=3800,
#         temperature=0.95,
#         timeout=300
#     )

#     return pass1
