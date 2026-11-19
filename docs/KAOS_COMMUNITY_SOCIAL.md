# KAOS member community

Community is now a member social feed alongside the existing published strategy
library. The gold theme is used throughout the new workspace and member profiles.

## Member experience

- Feed: discussions, strategy posts, scripts and related HTTPS links. Plain text
  and script files (.py/.js/.pine/.json/.txt, up to 30 KB) can be shared. No binary
  attachments, direct messaging or live chat are included in this release.
- Following: posts by followed creators, using the same follow relationships as
  profiles and the existing strategy feed. Members can discover people by name,
  view profiles, and browse follower/following lists.
- Posts: likes, comments, replies, copied member-only permalinks, author edits and
  removal. Scripts are loaded on demand for review/download; they are never
  executed by the server, browser renderer, extension or trainer when shared.
- Strategies: attach published PUBLIC strategies with creator attribution. A
  withdrawn/private strategy is no longer exposed through the social attachment.
  The original catalog remains under Strategy library.
- Profiles: Posts, Strategies, Followers and Following. Profile information is
  edited through the existing Account page.

## Access and moderation

The social API lives under `/api/community/posts` and `/api/community/members`.
It requires a current authenticated account with the community entitlement;
community is currently included in the existing free and paid entitlements.
Feeds and connection directories return public profile projections, not account
email addresses, password hashes or authentication data.

Post authors can edit/remove their posts. Comment authors can remove their own
comments. Moderators can remove reported posts/comments through the existing
Admin reports workflow or the in-feed removal controls. Removed content is hidden
from feeds, direct links and comment endpoints. Account deletion hides that user's
social posts/comments and removes social reactions and follow edges.

New-post, comment, reaction, follow and report rates are bounded. Reactions and
follow insertion are idempotent; replies must belong to the same visible post.
Script HTML is rendered as escaped text, not HTML. Related links are HTTP(S) only,
with no embedded credentials and no server-side fetching.

## Hosting and release behavior

Feed pages load up to 20 posts, with cursor pagination. Member search is debounced
and paginated. Likes/comments and authors are enriched in batches. Scripts are
excluded from list payloads. There is no continuous feed polling or new worker.
New collections create their indexes lazily so Passenger need not run lifespan
hooks. No existing posts, strategies, scripts or follows are migrated or seeded.

The cPanel login-validation wrapper explicitly permits these member social
writes and role-protected report moderation while retaining payment/order
restrictions. Both the website and backend package must be installed together,
then the Python application restarted and browser refreshed. No provider API keys
or changes to Google sign-in are needed for this feature.

Validation includes isolated MongoDB tests for privacy, permissions, follows,
reactions, cross-post replies, rate limits, pagination, moderation and account
removal, plus the browser community workflow with fixture accounts. Production
availability still depends on the API host allowing browser requests.
