/**
 * Single source of truth for what is live and what is still a roadmap item.
 * The UI renders this registry so a not-yet-built phase is always shown as a
 * warning instead of a broken screen.
 */

export const PHASES = [
  {
    phase: 1,
    title: "Authentication & profiles",
    status: "done",
    blurb: "Accounts, JWT login, password changes and public/private profiles.",
    items: [
      { label: "Register, login, logout", done: true },
      { label: "Change password / deactivate", done: true },
      { label: "GET & PATCH /users/me", done: true },
      { label: "Public profile with live counts", done: true },
    ],
  },
  {
    phase: 2,
    title: "Social graph & posts",
    status: "done",
    blurb:
      "Follow relationships plus post creation, editing and soft delete, with a people search so the graph is easy to explore.",
    items: [
      { label: "Follow / unfollow", done: true },
      { label: "Followers & following lists", done: true },
      { label: "Create, edit, soft-delete posts", done: true },
      { label: "Personal posts (paginated)", done: true },
      { label: "People search (find someone to follow)", done: true },
    ],
  },
  {
    phase: 3,
    title: "Interactions",
    status: "todo",
    blurb: "Likes, reposts, comments and one-level replies.",
    items: [
      { label: "Likes", done: false, slug: "likes" },
      { label: "Reposts", done: false, slug: "reposts" },
      { label: "Comments & replies", done: false, slug: "comments" },
    ],
  },
  {
    phase: 4,
    title: "Feed, bookmarks & notifications",
    status: "todo",
    blurb: "Following feed, saved posts and the notification inbox.",
    items: [
      { label: "Following feed", done: false, slug: "feed" },
      { label: "Bookmarks", done: false, slug: "bookmarks" },
      { label: "Notifications", done: false, slug: "notifications" },
    ],
  },
  {
    phase: 5,
    title: "Discovery",
    status: "todo",
    blurb: "Search, hashtags and @mentions.",
    items: [
      { label: "Search", done: false, slug: "search" },
      { label: "Hashtags", done: false, slug: "hashtags" },
      { label: "Mentions", done: false, slug: "mentions" },
    ],
  },
  {
    phase: 6,
    title: "Safety & admin",
    status: "todo",
    blurb: "Blocking, reporting and the admin moderation tools.",
    items: [
      { label: "Blocking", done: false, slug: "blocking" },
      { label: "Reporting", done: false, slug: "reports" },
      { label: "Admin panel", done: false, slug: "admin" },
    ],
  },
];

export const FEATURES = {
  likes: {
    phase: 3,
    title: "Likes",
    blurb:
      "Liking and unliking posts, with duplicate prevention and live like counts.",
    endpoints: "POST /posts/{id}/like · DELETE /posts/{id}/like",
  },
  reposts: {
    phase: 3,
    title: "Reposts",
    blurb: "Sharing someone else's post, with optional quote text.",
    endpoints: "POST /posts/{id}/repost · DELETE /posts/{id}/repost",
  },
  comments: {
    phase: 3,
    title: "Comments & replies",
    blurb:
      "Threaded discussion on posts, limited to one level of replies, with edit and delete.",
    endpoints: "POST /posts/{id}/comments · GET /posts/{id}/comments",
  },
  feed: {
    phase: 4,
    title: "Following feed",
    blurb:
      "A single timeline of posts and reposts from the people you follow, newest first.",
    endpoints: "GET /feed?limit=&offset=",
  },
  bookmarks: {
    phase: 4,
    title: "Bookmarks",
    blurb: "Save posts for later and browse your saved collection.",
    endpoints: "POST /posts/{id}/bookmark · GET /bookmarks",
  },
  notifications: {
    phase: 4,
    title: "Notifications",
    blurb:
      "In-app alerts for follows, likes, comments and mentions, with an unread counter.",
    endpoints: "GET /notifications · PATCH /notifications/{id}/read",
  },
  search: {
    phase: 5,
    title: "Search",
    blurb:
      "Find posts, hashtags and mentions by text. People search is already live from Phase 2.",
    endpoints: "GET /search/users?q= · GET /search/posts?q=",
  },
  hashtags: {
    phase: 5,
    title: "Hashtags",
    blurb: "Extract #hashtags from posts and browse everything tagged with one.",
    endpoints: "GET /hashtags/{name}/posts · GET /hashtags/trending",
  },
  mentions: {
    phase: 5,
    title: "Mentions",
    blurb: "Link @usernames inside posts and notify the people mentioned.",
    endpoints: "Mention extraction on post create/edit",
  },
  blocking: {
    phase: 6,
    title: "Blocking",
    blurb:
      "Block an account to hide content both ways and remove existing follows.",
    endpoints: "POST /blocks/{user_id} · DELETE /blocks/{user_id} · GET /blocks",
  },
  reports: {
    phase: 6,
    title: "Reporting",
    blurb: "Report a user, post or comment for moderator review.",
    endpoints: "POST /reports",
  },
  admin: {
    phase: 6,
    title: "Admin panel",
    blurb:
      "Moderation queue, account deactivation and content removal for admins.",
    endpoints: "GET /admin/reports · PATCH /admin/reports/{id}",
  },
};
