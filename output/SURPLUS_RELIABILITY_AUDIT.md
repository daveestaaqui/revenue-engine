# Surplus Docket reliability audit — September 11, 2026

All eight Revenue Engine workflows were inventoried. Recent Pages, revenue-pipeline, inbound-responder, weekly-report and syndication runs completed; subscriber-management and bug-resolver workflows have no recorded runs. The B2B marketing hub only shows older successful Pages deployments.

The latest form-outreach run (34526934032) launched Chromium successfully on Ubuntu but processed 0/12 targets while reporting workflow success. The unfinished local WebKit change and macOS permission commands have NOT been deployed. The original /Users/davidmahler/revenue-engine checkout is dirty/diverged and was preserved; fixes are isolated in /Users/davidmahler/src/.worktrees/surplus-reliability on astra/surplus-reliability.

Implemented: platform-specific browser selection, isolated preview logs/screenshots, owned browser fixtures, nonzero status for zero-success batches, explicit unconfirmed-delivery status with retry suppression, preserved failure logs, and serialized outreach runs. Form clicks alone no longer count as confirmed delivery. No law-firm forms were submitted during this work.

Syndication: latest registry reports IndexNow HTTP 200, Google ping 404 and Bing ping 410. Dev.to/Medium are simulated because keys are absent; the webhook is unconfigured. Retired search-engine pings were removed. Submission acceptance no longer claims proven indexing, only actual article successes count as publication, and dry runs no longer mutate the production registry. Historical registry counts were not rewritten.

Added a dependency-free site checker for all HTML internal links, sitemap destinations, robots discovery and live GET checks. Local validation passed for 56 HTML pages and 37 sitemap URLs. An Actions workflow checks live availability daily after merge; browser tests run on changes against an owned in-memory form with external requests blocked. These checks use no paid model API.

Remaining business-critical work: repository secrets contain only GMAIL_APP_PASS. Verify/provision the intended Stripe API credential and validate paid subscriber intake/fulfillment before claiming that payment-to-delivery works. Do not make a real purchase as a test. External publishing needs approved accounts/credentials and publication deduplication before enabling it. Generated packets are not earned backlinks. Search Console/Bing Webmaster verification and acquisition/conversion analytics were not accessible here. Existing legal/fee statements, public data accuracy and uptime claims were not independently certified. Browser fixtures validate the engine, not acceptance by every law firm's website; blocked/incompatible forms require approved manual review rather than anti-bot bypasses.

Sources: https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping and https://blogs.bing.com/webmaster/may-2022/Spring-cleaning-Removed-Bing-anonymous-sitemap-submission
