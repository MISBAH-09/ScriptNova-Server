from django.db import models


class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=20)
    email = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    token = models.CharField(max_length=200, null=True, blank=True)
    profile = models.CharField(max_length=100, null=True, blank=True)
    plan = models.CharField(max_length=20, default='free')
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_subscription_status = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Blog(models.Model):
    FAVOURITE_CHOICES = [
        ('normal',    'Normal'),
        ('favourite', 'Favourite'),
    ]

    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    prompt            = models.CharField(max_length=500, blank=True, default='')
    title             = models.CharField(max_length=500)
    content           = models.TextField()
    humanized_content = models.TextField(blank=True, default='')  # stores humanized version
    keywords          = models.CharField(max_length=1000, blank=True, default='')
    tone              = models.CharField(max_length=100, blank=True, default='')
    length_preference = models.CharField(max_length=100, blank=True, default='')
    word_count        = models.PositiveIntegerField(default=0)
    slug              = models.SlugField(max_length=600, blank=True, unique=True)
    published         = models.BooleanField(default=False)
    favourite         = models.CharField(
                            max_length=20,
                            choices=FAVOURITE_CHOICES,
                            default='normal'
                        )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        star = '★' if self.favourite == 'favourite' else '☆'
        return f"{star} {self.title} — {self.user.username}"

    def save(self, *args, **kwargs):
        if self.content and not self.word_count:
            self.word_count = len(self.content.split())
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.title)[:550]
            self.slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
        super().save(*args, **kwargs)


class BlogComment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='blog_comments', null=True, blank=True)
    reader_name = models.CharField(max_length=100, blank=True, default='')
    reader_email = models.EmailField(max_length=100, blank=True, default='')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        name = self.reader_name or (self.user.username if self.user else 'Reader')
        return f"Comment by {name} on {self.blog.title}"


class BlogReaction(models.Model):
    LIKE = 'like'
    DISLIKE = 'dislike'
    REACTION_CHOICES = [
        (LIKE, 'Like'),
        (DISLIKE, 'Dislike'),
    ]

    blog = models.ForeignKey(Blog, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='blog_reactions', null=True, blank=True)
    reader_name = models.CharField(max_length=100, blank=True, default='')
    reader_email = models.EmailField(max_length=100, blank=True, default='')
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        name = self.reader_name or (self.user.username if self.user else 'Reader')
        return f"{name} {self.reaction}d {self.blog.title}"
