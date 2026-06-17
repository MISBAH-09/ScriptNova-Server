# from rest_framework.views import APIView
# from rest_framework.response import Response
# from ScriptNova.middleware.auth import require_token
# from ScriptNova.models import Blog
# import os
# import time
# import requests

# NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
# INVOKE_URL     = "https://integrate.api.nvidia.com/v1/chat/completions"
# nvidia_headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}

# # ── Model routing ─────────────────────────────────────────────────────────────
# FAST_MODEL      = "meta/llama-3.1-8b-instruct"    # keywords, title
# QUALITY_MODEL   = "meta/llama-3.3-70b-instruct"   # blog generation, rephrase
# HUMANIZE_MODEL  = "meta/llama-3.3-70b-instruct"   # humanize layer

# LENGTH_MAP = {
#     "Short (500-800 words)":    {"min": 500,  "max": 800,  "max_tokens": 1200},
#     "Medium (1000-1500 words)": {"min": 1000, "max": 1500, "max_tokens": 2200},
#     "Long (2000+ words)":       {"min": 2000, "max": 2500, "max_tokens": 3800},
# }


# def _nvidia_chat(prompt_text, model=QUALITY_MODEL, max_tokens=300, temperature=0.6, timeout=300):
#     payload = {
#         "model": model,
#         "messages": [{"role": "user", "content": prompt_text}],
#         "max_tokens": max_tokens,
#         "temperature": temperature,
#         "stream": False,
#     }
#     last_error = None
#     for attempt in range(3):
#         try:
#             r = requests.post(INVOKE_URL, headers=nvidia_headers, json=payload, timeout=timeout)
#             r.raise_for_status()
#             return r.json()["choices"][0]["message"]["content"]
#         except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
#             last_error = e
#             if attempt < 2:
#                 time.sleep(3 * (attempt + 1))
#         except requests.exceptions.HTTPError:
#             raise
#     raise last_error


# def blog_to_dict(blog, include_content=True):
#     d = {
#         "id":                blog.id,
#         "prompt":            blog.prompt,
#         "title":             blog.title,
#         "keywords":          blog.keywords,
#         "tone":              blog.tone,
#         "length_preference": blog.length_preference,
#         "word_count":        blog.word_count,
#         "slug":              blog.slug,
#         "favourite":         blog.favourite,
#         "is_favourite":      blog.favourite == "favourite",
#         "is_humanized":      bool(blog.humanized_content),  # frontend knows if humanized exists
#         "created_at":        blog.created_at.isoformat() if blog.created_at else None,
#         "updated_at":        blog.updated_at.isoformat() if blog.updated_at else None,
#     }
#     if include_content:
#         d["content"]           = blog.content
#         d["humanized_content"] = blog.humanized_content
#     return d


# def generate_keywords(topic):
#     raw = _nvidia_chat(
#         f'Generate 8 SEO-friendly keywords for a blog about: "{topic}"\n'
#         f'Return ONLY a comma-separated list. No explanation, no numbering.',
#         model=FAST_MODEL, max_tokens=150, temperature=0.4, timeout=180
#     )
#     return [k.strip() for k in raw.split(",") if k.strip()]


# def suggest_title(topic, keywords=None):
#     kw = f"\nKeywords: {', '.join(keywords)}" if keywords else ""
#     raw = _nvidia_chat(
#         f"Suggest ONE catchy, SEO-friendly blog post title for this topic:\n"
#         f"Topic: {topic}{kw}\n\n"
#         f"Rules:\n- Return ONLY the title text. No quotes, no explanation, no numbering.\n"
#         f"- Make it engaging and click-worthy.\n- Between 6 and 12 words.",
#         model=FAST_MODEL, max_tokens=60, temperature=0.7, timeout=180
#     )
#     return raw.strip().strip('"').strip("'")


# def generate_blog_content(title, keywords, tone, length):
#     kw_str = ", ".join(keywords) if isinstance(keywords, list) else keywords
#     cfg    = LENGTH_MAP.get(length, LENGTH_MAP["Medium (1000-1500 words)"])
#     return _nvidia_chat(
#         f"You are an expert SEO blog writer.\n\n"
#         f"Write a blog post with EXACTLY between {cfg['min']} and {cfg['max']} words.\n\n"
#         f"Title: {title}\nKeywords: {kw_str}\nTone: {tone}\n\n"
#         f"STRUCTURE:\n- Introduction (no heading)\n- 3 to 4 sections each with a ## heading\n"
#         f"- Conclusion section with ## Conclusion heading\n\n"
#         f"FORMATTING RULES:\n- Use ## for section headings\n"
#         f"- Put a blank line before and after every ## heading\n"
#         f"- Use **bold** for important terms\n- Use bullet points with \"- \" where appropriate\n"
#         f"- Separate paragraphs with a blank line\n\nOUTPUT: blog content only, no extra commentary.",
#         model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.6, timeout=360
#     )


# def humanize_content(content, style="natural"):
#     """
#     Takes AI-generated content and rewrites it to sound genuinely human.
#     style options: natural | conversational | storytelling | professional
#     """
#     style_instructions = {
#         "natural": (
#             "Rewrite this article so it sounds like a real person wrote it — someone knowledgeable "
#             "but casual, who uses natural sentence variety, occasional contractions, and thinks out loud "
#             "a little. Avoid perfect parallel structure. Mix short and long sentences. Use first person "
#             "sparingly and naturally. Remove any phrasing that sounds like it was generated by AI "
#             "(e.g. 'In conclusion', 'It is worth noting', 'delve into', 'In today's world'). "
#             "No high level use of vocab use easy-normal words.so it must be detected ai less than 5%"
#         ),
#         "conversational": (
#             "Rewrite this article in a warm, conversational tone — like you're explaining it to a smart "
#             "friend over coffee. Use contractions freely. Ask rhetorical questions occasionally. "
#             "Keep it engaging and never stiff. Avoid robotic transitions and AI clichés."
#             "No high level use of vocab use easy-normal words.so it must be detected ai less than 5%"
#         ),
#         "storytelling": (
#             "Rewrite this article using a storytelling approach — open with a scene or scenario, "
#             "weave in the information through narrative flow rather than just listing facts. "
#             "Make the reader feel something. Keep it informative but human and engaging."
#             "No high level use of vocab use easy-normal words.so it must be detected ai less than 5%"
#         ),
#         "professional": (
#             "Rewrite this article so it sounds like a senior industry expert wrote it — authoritative "
#             "but not robotic. Use clear, confident language. Avoid filler phrases and AI-isms. "
#             "Every sentence should add value. Sound like a person with real experience, not a language model."
#             "No high level use of vocab use easy-normal words.so it must be detected ai less than 5%"
#         ),
#     }

#     instruction = style_instructions.get(style, style_instructions["natural"])

#     prompt = (
#         f"{instruction}\n\n"
#         f"CRITICAL RULES:\n"
#         f"- Keep ALL the same information, facts, and structure\n"
#         f"- Keep ALL markdown headings (##) and formatting\n"
#         f"- Do NOT add new facts or remove existing ones\n"
#         f"- Do NOT change the title\n"
#         f"- Output the rewritten article only — no explanations, no preamble\n\n"
#         f"ARTICLE TO HUMANIZE:\n{content}"
#     )

#     # Use a generous token budget — humanized output is same length as input
#     return _nvidia_chat(prompt, model=HUMANIZE_MODEL, max_tokens=3800, temperature=0.75, timeout=360)


# # ── AI Views ──────────────────────────────────────────────────────────────────

# class GenerateKeywords(APIView):
#     @require_token
#     def post(self, request):
#         title = request.data.get("title", "").strip()
#         if not title:
#             return Response({"success": False, "message": "Title is required"}, status=400)
#         try:
#             return Response({"success": True, "data": generate_keywords(title)})
#         except Exception as e:
#             return Response({"success": False, "message": str(e)}, status=500)


# class GenerateBlog(APIView):
#     @require_token
#     def post(self, request):
#         prompt   = request.data.get("prompt", "").strip()
#         keywords = request.data.get("keywords")
#         tone     = request.data.get("tone", "").strip()
#         length   = request.data.get("length", "").strip()
#         if not prompt or not tone or not length:
#             return Response({"success": False, "message": "prompt, tone, and length are required"}, status=400)
#         try:
#             if not keywords:
#                 keywords = generate_keywords(prompt)
#             suggested_title = suggest_title(prompt, keywords)
#             content         = generate_blog_content(suggested_title, keywords, tone, length)
#             return Response({"success": True, "data": {
#                 "prompt": prompt, "suggested_title": suggested_title,
#                 "keywords": keywords, "content": content,
#             }})
#         except Exception as e:
#             return Response({"success": False, "message": str(e)}, status=500)


# class RegenerateTitle(APIView):
#     @require_token
#     def post(self, request):
#         prompt          = request.data.get("prompt", "").strip()
#         article_content = request.data.get("article_content", "").strip()
#         keywords        = request.data.get("keywords")
#         if not prompt and not article_content:
#             return Response({"success": False, "message": "Either prompt or article_content is required"}, status=400)
#         try:
#             hint = prompt
#             if article_content:
#                 snippet = article_content[:400].replace("\n", " ")
#                 hint    = f"{prompt}\n\nArticle excerpt: {snippet}" if prompt else snippet
#             return Response({"success": True, "data": {"suggested_title": suggest_title(hint, keywords)}})
#         except Exception as e:
#             return Response({"success": False, "message": str(e)}, status=500)


# class RephraseBlog(APIView):
#     @require_token
#     def post(self, request):
#         article_content = request.data.get("article_content", "").strip()
#         mode            = request.data.get("mode", "rephrase")
#         if not article_content and mode != "regenerate":
#             return Response({"success": False, "message": "article_content is required"}, status=400)
#         try:
#             cfg = LENGTH_MAP["Medium (1000-1500 words)"]
#             if mode == "rephrase":
#                 content = _nvidia_chat(
#                     f"Rephrase the following blog article. Keep the same structure and all the main points, "
#                     f"but use completely different wording. Maintain the same tone and length.\n\n"
#                     f"ARTICLE:\n{article_content}\n\nOUTPUT: rephrased article only, same markdown formatting.",
#                     model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.65, timeout=360)
#             elif mode == "rearrange":
#                 content = _nvidia_chat(
#                     f"Rearrange and restructure the following blog article. Keep all the same information "
#                     f"but reorganise sections into a better logical flow. Rename headings if it improves clarity.\n\n"
#                     f"ARTICLE:\n{article_content}\n\nOUTPUT: rearranged article only, same markdown formatting.",
#                     model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.65, timeout=360)
#             elif mode == "regenerate":
#                 prompt_val = request.data.get("prompt", "").strip()
#                 keywords   = request.data.get("keywords", [])
#                 tone       = request.data.get("tone", "Informative & Friendly")
#                 length     = request.data.get("length", "Medium (1000-1500 words)")
#                 if not prompt_val:
#                     return Response({"success": False, "message": "prompt is required for regenerate mode"}, status=400)
#                 content = generate_blog_content(prompt_val, keywords, tone, length)
#             else:
#                 return Response({"success": False, "message": "mode must be rephrase, rearrange, or regenerate"}, status=400)
#             return Response({"success": True, "data": {"content": content}})
#         except Exception as e:
#             return Response({"success": False, "message": str(e)}, status=500)


# class HumanizeView(APIView):
#     """
#     POST /humanize/
#     Two modes:
#       1. Pass content directly (no blog_id) — humanize any custom text, don't save
#       2. Pass blog_id — humanize that blog's content and save to humanized_content field

#     Body: { content, style, blog_id? }
#     style: "natural" | "conversational" | "storytelling" | "professional"
#     """
#     @require_token
#     def post(self, request):
#         content = request.data.get("content", "").strip()
#         style   = request.data.get("style", "natural")
#         blog_id = request.data.get("blog_id")

#         if not content:
#             return Response({"success": False, "message": "content is required"}, status=400)

#         valid_styles = ["natural", "conversational", "storytelling", "professional"]
#         if style not in valid_styles:
#             style = "natural"

#         try:
#             humanized = humanize_content(content, style)

#             # If blog_id provided — save humanized_content to that blog
#             if blog_id:
#                 try:
#                     blog = Blog.objects.get(pk=blog_id, user=request.auth_user)
#                     blog.humanized_content = humanized
#                     blog.save(update_fields=["humanized_content", "updated_at"])
#                     return Response({
#                         "success":   True,
#                         "data":      {"humanized_content": humanized},
#                         "blog_id":   blog.id,
#                         "saved":     True,
#                     })
#                 except Blog.DoesNotExist:
#                     return Response({"success": False, "message": "Blog not found"}, status=404)

#             # No blog_id — just return humanized text, don't save
#             return Response({
#                 "success": True,
#                 "data":    {"humanized_content": humanized},
#                 "saved":   False,
#             })

#         except Exception as e:
#             return Response({"success": False, "message": str(e)}, status=500)


# # ── Blog CRUD ──────────────────────────────────────────────────────────────────

# class BlogListCreateView(APIView):
#     @require_token
#     def get(self, request):
#         user = request.auth_user
#         qs   = Blog.objects.filter(user=user)

#         fav = request.query_params.get("favourite")
#         if fav == "true":
#             qs = qs.filter(favourite="favourite")

#         limit = request.query_params.get("limit")
#         if limit:
#             try: qs = qs[:int(limit)]
#             except (ValueError, TypeError): pass

#         return Response({"success": True, "data": [blog_to_dict(b, include_content=False) for b in qs]})

#     @require_token
#     def post(self, request):
#         user              = request.auth_user
#         title             = request.data.get("title", "").strip()
#         prompt_val        = request.data.get("prompt", "").strip()
#         content           = request.data.get("content", "").strip()
#         keywords          = request.data.get("keywords", "")
#         tone              = request.data.get("tone", "")
#         length_preference = request.data.get("length_preference", "")
#         word_count        = request.data.get("word_count", 0)

#         if not title:
#             return Response({"success": False, "message": "Title is required"}, status=400)
#         if not word_count and content:
#             word_count = len(content.split())
#         if isinstance(keywords, list):
#             keywords = ", ".join(keywords)

#         blog = Blog.objects.create(
#             user=user, prompt=prompt_val, title=title, content=content,
#             keywords=keywords, tone=tone, length_preference=length_preference,
#             word_count=word_count,
#         )
#         return Response({"success": True, "data": blog_to_dict(blog)}, status=201)


# class BlogDetailView(APIView):
#     def _get_blog(self, request, pk):
#         try:    return Blog.objects.get(pk=pk, user=request.auth_user)
#         except: return None

#     @require_token
#     def get(self, request, pk):
#         blog = self._get_blog(request, pk)
#         if not blog:
#             return Response({"success": False, "message": "Blog not found"}, status=404)
#         return Response({"success": True, "data": blog_to_dict(blog)})

#     @require_token
#     def patch(self, request, pk):
#         blog = self._get_blog(request, pk)
#         if not blog:
#             return Response({"success": False, "message": "Blog not found"}, status=404)

#         updatable = ["prompt", "title", "content", "humanized_content", "keywords",
#                      "tone", "length_preference", "word_count", "favourite"]
#         for field in updatable:
#             if field in request.data:
#                 val = request.data[field]
#                 if field == "keywords" and isinstance(val, list):
#                     val = ", ".join(val)
#                 setattr(blog, field, val)

#         if "content" in request.data and not request.data.get("word_count"):
#             blog.word_count = len(blog.content.split())

#         if "title" in request.data:
#             blog.slug = ""

#         blog.save()
#         return Response({"success": True, "data": blog_to_dict(blog)})

#     @require_token
#     def delete(self, request, pk):
#         blog = self._get_blog(request, pk)
#         if not blog:
#             return Response({"success": False, "message": "Blog not found"}, status=404)
#         blog.delete()
#         return Response({"success": True, "message": "Deleted"}, status=204)


# class BlogBySlugView(APIView):
#     @require_token
#     def get(self, request, slug):
#         try:
#             blog = Blog.objects.get(slug=slug, user=request.auth_user)
#             return Response({"success": True, "data": blog_to_dict(blog)})
#         except Blog.DoesNotExist:
#             return Response({"success": False, "message": "Blog not found"}, status=404)


# class BlogFavouriteView(APIView):
#     @require_token
#     def post(self, request, pk):
#         try:
#             blog = Blog.objects.get(pk=pk, user=request.auth_user)
#         except Blog.DoesNotExist:
#             return Response({"success": False, "message": "Blog not found"}, status=404)

#         blog.favourite = "normal" if blog.favourite == "favourite" else "favourite"
#         blog.save(update_fields=["favourite", "updated_at"])
#         return Response({
#             "success":      True,
#             "id":           blog.id,
#             "favourite":    blog.favourite,
#             "is_favourite": blog.favourite == "favourite",
#         })


# class BlogStatsView(APIView):
#     @require_token
#     def get(self, request):
#         qs          = Blog.objects.filter(user=request.auth_user)
#         total_words = sum(qs.values_list("word_count", flat=True))
#         return Response({"success": True, "data": {
#             "total":       qs.count(),
#             "favourites":  qs.filter(favourite="favourite").count(),
#             "humanized":   qs.exclude(humanized_content="").count(),
#             "total_words": total_words,
#         }})



from rest_framework.views import APIView
from rest_framework.response import Response
from ScriptNova.middleware.auth import require_token
from ScriptNova.models import Blog, BlogComment, BlogReaction

# ✅ import helpers
from .blogshelper import (
    generate_keywords,
    suggest_title,
    generate_blog_content,
    humanize_content,
    blog_to_dict,
    _nvidia_chat,
    LENGTH_MAP,
    QUALITY_MODEL
)


def _display_name(user):
    return f"{user.first_name} {user.last_name}".strip() or user.username or user.email


def _reader_identity(request):
    user = getattr(request, "auth_user", None)
    if user:
        return {
            "user": user,
            "name": _display_name(user),
            "email": user.email.lower(),
            "error": None,
        }

    name = request.data.get("reader_name", "").strip()
    email = request.data.get("reader_email", "").strip().lower()
    if not name or not email:
        return {
            "user": None,
            "name": "",
            "email": "",
            "error": "Name and email are required",
        }

    return {
        "user": None,
        "name": name,
        "email": email,
        "error": None,
    }


def _request_reader_email(request):
    user = getattr(request, "auth_user", None)
    if user:
        return user.email.lower()
    return request.query_params.get("reader_email", "").strip().lower()


def comment_to_dict(comment):
    name = comment.reader_name or (_display_name(comment.user) if comment.user else "Reader")
    email = comment.reader_email or (comment.user.email if comment.user else "")
    return {
        "id": comment.id,
        "body": comment.body,
        "author": {
            "id": comment.user.id if comment.user else None,
            "username": comment.user.username if comment.user else "",
            "name": name,
            "email": email,
        },
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
    }


def discussion_to_dict(blog, user=None, reader_email=""):
    reactions = blog.reactions.all()
    user_reaction = None
    if user:
        match = reactions.filter(reader_email=user.email.lower()).first() or reactions.filter(user=user).first()
        user_reaction = match.reaction if match else None
    elif reader_email:
        match = reactions.filter(reader_email=reader_email.lower()).first()
        user_reaction = match.reaction if match else None

    return {
        "blog_id": blog.id,
        "likes": reactions.filter(reaction=BlogReaction.LIKE).count(),
        "dislikes": reactions.filter(reaction=BlogReaction.DISLIKE).count(),
        "user_reaction": user_reaction,
        "comments": [
            comment_to_dict(comment)
            for comment in blog.comments.select_related("user").all()
        ],
    }

# ── AI Views ──────────────────────────────────────────────────────────────────

class GenerateKeywords(APIView):
    @require_token
    def post(self, request):
        title = request.data.get("title", "").strip()
        if not title:
            return Response({"success": False, "message": "Title is required"}, status=400)
        try:
            return Response({"success": True, "data": generate_keywords(title)})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


class GenerateBlog(APIView):
    @require_token
    def post(self, request):
        prompt   = request.data.get("prompt", "").strip()
        keywords = request.data.get("keywords")
        tone     = request.data.get("tone", "").strip()
        length   = request.data.get("length", "").strip()
        if not prompt or not tone or not length:
            return Response({"success": False, "message": "prompt, tone, and length are required"}, status=400)
        try:
            if not keywords:
                keywords = generate_keywords(prompt)
            suggested_title = suggest_title(prompt, keywords)
            content         = generate_blog_content(suggested_title, keywords, tone, length)
            return Response({"success": True, "data": {
                "prompt":          prompt,
                "suggested_title": suggested_title,
                "keywords":        keywords,
                "content":         content,
            }})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


class RegenerateTitle(APIView):
    @require_token
    def post(self, request):
        prompt          = request.data.get("prompt", "").strip()
        article_content = request.data.get("article_content", "").strip()
        keywords        = request.data.get("keywords")
        if not prompt and not article_content:
            return Response({"success": False, "message": "Either prompt or article_content is required"}, status=400)
        try:
            hint = prompt
            if article_content:
                snippet = article_content[:400].replace("\n", " ")
                hint    = f"{prompt}\n\nArticle excerpt: {snippet}" if prompt else snippet
            return Response({"success": True, "data": {"suggested_title": suggest_title(hint, keywords)}})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


class RephraseBlog(APIView):
    @require_token
    def post(self, request):
        article_content = request.data.get("article_content", "").strip()
        mode            = request.data.get("mode", "rephrase")
        if not article_content and mode != "regenerate":
            return Response({"success": False, "message": "article_content is required"}, status=400)
        try:
            cfg = LENGTH_MAP["Medium (1000-1500 words)"]
            if mode == "rephrase":
                content = _nvidia_chat(
                    f"Rephrase the following blog article. Keep the same structure and all the main points, "
                    f"but use completely different wording. Maintain the same tone and length.\n\n"
                    f"ARTICLE:\n{article_content}\n\nOUTPUT: rephrased article only, same markdown formatting.",
                    model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.65, timeout=360)
            elif mode == "rearrange":
                content = _nvidia_chat(
                    f"Rearrange and restructure the following blog article. Keep all the same information "
                    f"but reorganise sections into a better logical flow. Rename headings if it improves clarity.\n\n"
                    f"ARTICLE:\n{article_content}\n\nOUTPUT: rearranged article only, same markdown formatting.",
                    model=QUALITY_MODEL, max_tokens=cfg["max_tokens"], temperature=0.65, timeout=360)
            elif mode == "regenerate":
                prompt_val = request.data.get("prompt", "").strip()
                keywords   = request.data.get("keywords", [])
                tone       = request.data.get("tone", "Informative & Friendly")
                length     = request.data.get("length", "Medium (1000-1500 words)")
                if not prompt_val:
                    return Response({"success": False, "message": "prompt is required for regenerate mode"}, status=400)
                content = generate_blog_content(prompt_val, keywords, tone, length)
            else:
                return Response({"success": False, "message": "mode must be rephrase, rearrange, or regenerate"}, status=400)
            return Response({"success": True, "data": {"content": content}})
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


class HumanizeView(APIView):
    """
    POST /humanize/

    Two modes:
      1. No blog_id  — humanize any content directly, return result, don't save
      2. With blog_id — humanize that blog's content and save to humanized_content field

    Body params:
      content     (str, required)  — the article text to humanize
      style       (str, optional)  — natural | conversational | storytelling | professional
      blog_id     (int, optional)  — if provided, saves result to that Blog record
      single_pass (bool, optional) — debug flag: skip pass 2 to test pass 1 output alone
    """
    @require_token
    def post(self, request):
        content     = request.data.get("content", "").strip()
        style       = request.data.get("style", "natural")
        blog_id     = request.data.get("blog_id")
        single_pass = request.data.get("single_pass", False)  # debug only

        if not content:
            return Response({"success": False, "message": "content is required"}, status=400)

        valid_styles = ["natural", "conversational", "storytelling", "professional"]
        if style not in valid_styles:
            style = "natural"

        try:
            if single_pass:
                # Debug mode: only run pass 1 so you can isolate which pass helps more
                humanized = _nvidia_chat(
                    content,
                    model=HUMANIZE_MODEL,
                    max_tokens=3800,
                    temperature=0.92,
                    timeout=360
                )
            else:
                humanized = humanize_content(content, style)

            if blog_id:
                try:
                    blog = Blog.objects.get(pk=blog_id, user=request.auth_user)
                    blog.humanized_content = humanized
                    blog.save(update_fields=["humanized_content", "updated_at"])
                    return Response({
                        "success": True,
                        "data":    {"humanized_content": humanized},
                        "blog_id": blog.id,
                        "saved":   True,
                    })
                except Blog.DoesNotExist:
                    return Response({"success": False, "message": "Blog not found"}, status=404)

            return Response({
                "success": True,
                "data":    {"humanized_content": humanized},
                "saved":   False,
            })

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


# ── Blog CRUD ──────────────────────────────────────────────────────────────────

class BlogListCreateView(APIView):
    @require_token
    def get(self, request):
        user = request.auth_user
        qs   = Blog.objects.filter(user=user)

        fav = request.query_params.get("favourite")
        if fav == "true":
            qs = qs.filter(favourite="favourite")

        limit = request.query_params.get("limit")
        if limit:
            try: qs = qs[:int(limit)]
            except (ValueError, TypeError): pass

        return Response({"success": True, "data": [blog_to_dict(b, include_content=False) for b in qs]})

    @require_token
    def post(self, request):
        user              = request.auth_user
        title             = request.data.get("title", "").strip()
        prompt_val        = request.data.get("prompt", "").strip()
        content           = request.data.get("content", "").strip()
        keywords          = request.data.get("keywords", "")
        tone              = request.data.get("tone", "")
        length_preference = request.data.get("length_preference", "")
        word_count        = request.data.get("word_count", 0)
        published         = bool(request.data.get("published", False))

        if not title:
            return Response({"success": False, "message": "Title is required"}, status=400)
        if not word_count and content:
            word_count = len(content.split())
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)

        blog = Blog.objects.create(
            user=user, prompt=prompt_val, title=title, content=content,
            keywords=keywords, tone=tone, length_preference=length_preference,
            word_count=word_count, published=published,
        )
        return Response({"success": True, "data": blog_to_dict(blog)}, status=201)


class BlogDetailView(APIView):
    def _get_blog(self, request, pk):
        try:    return Blog.objects.get(pk=pk, user=request.auth_user)
        except: return None

    @require_token
    def get(self, request, pk):
        blog = self._get_blog(request, pk)
        if not blog:
            return Response({"success": False, "message": "Blog not found"}, status=404)
        return Response({"success": True, "data": blog_to_dict(blog)})

    @require_token
    def patch(self, request, pk):
        blog = self._get_blog(request, pk)
        if not blog:
            return Response({"success": False, "message": "Blog not found"}, status=404)

        updatable = ["prompt", "title", "content", "humanized_content", "keywords",
                     "tone", "length_preference", "word_count", "favourite", "published"]
        for field in updatable:
            if field in request.data:
                val = request.data[field]
                if field == "keywords" and isinstance(val, list):
                    val = ", ".join(val)
                setattr(blog, field, val)

        if "content" in request.data and not request.data.get("word_count"):
            blog.word_count = len(blog.content.split())

        if "title" in request.data:
            blog.slug = ""

        blog.save()
        return Response({"success": True, "data": blog_to_dict(blog)})

    @require_token
    def delete(self, request, pk):
        blog = self._get_blog(request, pk)
        if not blog:
            return Response({"success": False, "message": "Blog not found"}, status=404)
        blog.delete()
        return Response({"success": True, "message": "Deleted"}, status=204)


class BlogBySlugView(APIView):
    def get(self, request, slug):
        try:
            blog = Blog.objects.get(slug=slug, published=True)
            return Response({"success": True, "data": blog_to_dict(blog)})
        except Blog.DoesNotExist:
            return Response({"success": False, "message": "Blog not found"}, status=404)


class BlogFavouriteView(APIView):
    @require_token
    def post(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk, user=request.auth_user)
        except Blog.DoesNotExist:
            return Response({"success": False, "message": "Blog not found"}, status=404)

        blog.favourite = "normal" if blog.favourite == "favourite" else "favourite"
        blog.save(update_fields=["favourite", "updated_at"])
        return Response({
            "success":      True,
            "id":           blog.id,
            "favourite":    blog.favourite,
            "is_favourite": blog.favourite == "favourite",
        })


class BlogDiscussionView(APIView):
    def get(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk, published=True)
        except Blog.DoesNotExist:
            return Response({"success": False, "message": "Blog not found"}, status=404)

        return Response({
            "success": True,
            "data": discussion_to_dict(
                blog,
                getattr(request, "auth_user", None),
                _request_reader_email(request),
            )
        })


class BlogCommentView(APIView):
    def post(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk, published=True)
        except Blog.DoesNotExist:
            return Response({"success": False, "message": "Blog not found"}, status=404)

        body = request.data.get("body", "").strip()
        if not body:
            return Response({"success": False, "message": "Comment is required"}, status=400)

        identity = _reader_identity(request)
        if identity["error"]:
            return Response({"success": False, "message": identity["error"]}, status=400)

        comment = BlogComment.objects.create(
            blog=blog,
            user=identity["user"],
            reader_name=identity["name"],
            reader_email=identity["email"],
            body=body,
        )
        return Response({"success": True, "data": comment_to_dict(comment)}, status=201)


class BlogReactionView(APIView):
    def post(self, request, pk):
        try:
            blog = Blog.objects.get(pk=pk, published=True)
        except Blog.DoesNotExist:
            return Response({"success": False, "message": "Blog not found"}, status=404)

        reaction = request.data.get("reaction")
        if reaction not in [BlogReaction.LIKE, BlogReaction.DISLIKE]:
            return Response({"success": False, "message": "Reaction must be like or dislike"}, status=400)

        identity = _reader_identity(request)
        if identity["error"]:
            return Response({"success": False, "message": identity["error"]}, status=400)

        existing = BlogReaction.objects.filter(blog=blog, reader_email=identity["email"]).first()
        if existing and existing.reaction == reaction:
            existing.delete()
        elif existing:
            existing.reaction = reaction
            existing.reader_name = identity["name"]
            existing.user = identity["user"]
            existing.save(update_fields=["reaction", "reader_name", "user", "updated_at"])
        else:
            BlogReaction.objects.create(
                blog=blog,
                user=identity["user"],
                reader_name=identity["name"],
                reader_email=identity["email"],
                reaction=reaction,
            )

        return Response({
            "success": True,
            "data": discussion_to_dict(blog, identity["user"], identity["email"]),
        })


class PublishedBlogListView(APIView):
    def get(self, request):
        qs = Blog.objects.filter(published=True).select_related("user")

        limit = request.query_params.get("limit")
        if limit:
            try:
                qs = qs[:int(limit)]
            except (ValueError, TypeError):
                pass

        return Response({"success": True, "data": [blog_to_dict(b, include_content=True) for b in qs]})


class BlogStatsView(APIView):
    @require_token
    def get(self, request):
        qs          = Blog.objects.filter(user=request.auth_user)
        total_words = sum(qs.values_list("word_count", flat=True))
        return Response({"success": True, "data": {
            "total":       qs.count(),
            "favourites":  qs.filter(favourite="favourite").count(),
            "humanized":   qs.exclude(humanized_content="").count(),
            "total_words": total_words,
        }})
