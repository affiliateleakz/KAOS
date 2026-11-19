# TradingView Pine Script library

Member page: `/dashboard/pinescripts` (**TradingView Scripts** in the member menu).
Admin page: `/admin/pinescripts` (**TradingView Scripts** in the admin menu).
The previous bot Scripts page remains at `/dashboard/scripts`.

Members can upload .pine/.txt source, add a still PNG/JPEG/WebP thumbnail, title,
description/setup instructions, type, markets and timeframes. They can keep drafts,
submit for review, edit/resubmit and archive their own uploads. Published source is
available to signed-in members for viewing, copying and .pine download. There is
no paid-plan restriction on this library. Drafts/pending/rejected uploads are visible
only to the author and admins, not other members or moderators.

Admins/super-admins can upload official scripts, edit any listing/source/thumbnail,
publish/reject/archive, add author-visible moderation notes, mark official/featured,
and permanently delete a listing after confirmation. The normal member endpoints
cannot self-publish or set official/featured status. Editing a published member
submission resubmits it for review and removes any official/featured designation.
No script is published automatically just because its author has an admin role;
the separate authenticated admin endpoints govern administrative changes.

Source is plain text, limited to 128 KiB, with a Pine version 3–6 declaration.
That check is not a Pine compiler or a performance/security certification.
KAOS never executes uploaded code. The author confirms permission to share the
source and thumbnail and should include licensing/attribution in the source.
Descriptions render as plain text, not arbitrary HTML.

Thumbnails are limited to 2 MiB/16 megapixels and converted on upload to stripped
JPEG images no larger than 640×360. SVG, animated images, remote thumbnail URLs
and arbitrary executable files are not accepted. Source, metadata and normalized
thumbnails are stored in MongoDB; no public filesystem upload directory is needed.
Raw source is omitted from paginated listings; a member fetches it on detail/download.
Private pages/responses are no-store. Updates/deletions use revision matching to
prevent stale admin or member edits from overwriting newer changes. The latest 30
change metadata events are retained on each document; full source-version rollback
is not implemented. Member upload count is capped at 100 listings.

Deploy the matching website/backend cPanel packages and restart the Python app.
The Passenger wrapper explicitly admits only these Pine write paths; handlers
still enforce author/admin permissions. No database migration or preseed is needed;
an empty library invites member/admin uploads and contains no fabricated scripts.

Syntax/import/production-build/package checks are local checks. Regression source
is included; no new test suite is executed under the owner's prior instruction.
No live site was overwritten by preparing this feature.
