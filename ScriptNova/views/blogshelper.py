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
    # Use a conservative per-request timeout to avoid blocking gunicorn workers.
    # Cap the timeout to 25s for the HTTP request (the function still accepts a larger timeout
    # value to indicate an overall operation budget but each HTTP call must be short).
    request_timeout = min(189, max(5, int(timeout)))

    last_error = None
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            r = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=request_timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout as e:
            last_error = e
            # brief backoff between attempts
            if attempt < max_attempts - 1:
                time.sleep(2 * (attempt + 1))
        except requests.exceptions.ConnectionError as e:
            last_error = e
            if attempt < max_attempts - 1:
                time.sleep(2 * (attempt + 1))
        except requests.exceptions.HTTPError as e:
            # Explicitly surface auth errors as runtime errors so callers can return friendly responses
            if e.response is not None and e.response.status_code == 401:
                raise RuntimeError(
                    "NVIDIA rejected the API key. Check NVIDIA_API_KEY in the environment and restart the backend."
                ) from e
            # For other HTTP errors, capture and break so we don't indefinitely retry
            last_error = e
            break
        except Exception as e:
            last_error = e
            break

    # Raise a controlled runtime error for the caller to handle (avoids leaking internal exceptions)
    raise RuntimeError(f"External model call failed: {last_error}") from last_error

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
    Rewrites AI-generated blog content so it sounds more natural and human.
    Uses NVIDIA NIM with the configured humanize model for the blog humanize path.
    """

    style_instructions = {
        "natural": (
            "Rewrite this article so it sounds like a knowledgeable person wrote it — "
            "casual, with natural sentence variety, occasional contractions, and some asides. "
            "Avoid formal AI phrasing, robotic transitions, and vocabulary that feels too polished. "
            "Keep the tone grounded and easy to read."
        ),
        "conversational": (
            "Rewrite this article in a warm, conversational tone — like you're explaining it to a smart friend over coffee. "
            "Use contractions freely, ask a rhetorical question now and then, and keep it feeling humane and easygoing."
        ),
        "storytelling": (
            "Rewrite this article using a storytelling approach. Open with a scene or real example, weave in the information naturally, "
            "and make the voice feel human, vivid, and readable."
        ),
        "professional": (
            "Rewrite this article so it sounds like a senior industry professional wrote it — clear, confident, and helpful, but still human. "
            "Avoid filler language and stiff AI phrasing; keep it grounded and humane."
        ),
    }

    instruction = style_instructions.get(style, style_instructions["natural"])

    prompt = (
        f"{instruction}\n\n"
        f"CRITICAL RULES:\n"
        f"- Rewrite the article to sound humane and written by a real person.\n"
        f"- Keep all existing information, structure, and markdown headings.\n"
        f"- Do not add new facts or remove existing points.\n"
        f"- Do not change the title.\n"
        f"- Use varied sentence lengths, simple words, and natural phrasing.\n"
        f"- Remove AI-like transitions such as 'Furthermore', 'Moreover', 'In conclusion'.\n"
        f"- Preserve the blog structure and the original meaning.\n"
        f"- Keep the rewritten output in the same format as the original article.\n\n"
        f"ARTICLE TO HUMANIZE:\n{content}"
    )

    return _nvidia_chat(
        prompt,
        model=HUMANIZE_MODEL,
        max_tokens=3800,
        temperature=0.75,
        timeout=360,
    )

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
