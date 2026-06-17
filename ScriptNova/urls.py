from django.urls import path
from ScriptNova.views import signupAPI, loginAPI, getByIdApi, updateAPI
from ScriptNova.views.Blogs import (
    GenerateBlog, GenerateKeywords, RegenerateTitle, RephraseBlog,
    HumanizeView,
    BlogListCreateView, BlogDetailView, BlogBySlugView,
    BlogFavouriteView, BlogStatsView, PublishedBlogListView,
    BlogDiscussionView, BlogCommentView, BlogReactionView,
)
from ScriptNova.views.Payments import CreateCheckoutSession, PaymentStatus, StripeWebhook

app_name = 'ScriptNova'

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('signup/',          signupAPI.as_view(),  name='signup'),
    path('login/',           loginAPI.as_view(),   name='login'),
    path('user/<int:id>/',   getByIdApi.as_view(), name='get-user'),
    path('user/update/',     updateAPI.as_view(),  name='update-user'),

    # ── AI Generation ─────────────────────────────────────────────────────────
    path('generate-blog/',      GenerateBlog.as_view(),     name='generate-blog'),
    path('generate-keywords/',  GenerateKeywords.as_view(), name='generate-keywords'),
    path('generate-title/',     RegenerateTitle.as_view(),  name='generate-title'),
    path('rephrase-blog/',      RephraseBlog.as_view(),     name='rephrase-blog'),
    path('humanize/',           HumanizeView.as_view(),     name='humanize'),

    # ── Blog CRUD ─────────────────────────────────────────────────────────────
    path('blogs/',                    BlogListCreateView.as_view(), name='blog-list-create'),
    path('blogs/published/',          PublishedBlogListView.as_view(), name='published-blogs'),
    path('blogs/stats/',              BlogStatsView.as_view(),      name='blog-stats'),
    path('blogs/slug/<slug:slug>/',   BlogBySlugView.as_view(),     name='blog-by-slug'),
    path('blogs/<int:pk>/',           BlogDetailView.as_view(),     name='blog-detail'),
    path('blogs/<int:pk>/favourite/', BlogFavouriteView.as_view(),  name='blog-favourite'),
    path('blogs/<int:pk>/discussion/', BlogDiscussionView.as_view(), name='blog-discussion'),
    path('blogs/<int:pk>/comments/', BlogCommentView.as_view(), name='blog-comment'),
    path('blogs/<int:pk>/reaction/', BlogReactionView.as_view(), name='blog-reaction'),

    # Payments
    path('payments/create-checkout-session/', CreateCheckoutSession.as_view(), name='create-checkout-session'),
    path('payments/status/',                  PaymentStatus.as_view(),         name='payment-status'),
    path('payments/stripe-webhook/',          StripeWebhook.as_view(),         name='stripe-webhook'),
]
