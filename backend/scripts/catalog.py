"""Hand-written catalog of mock Healthcheck checks (synthetic; modeled on the real audit's categories).

Tuple fields: category, name, description, recommendation, entity_type, severity, fail_prob
severity decides the bucket for a failed check: high -> Actions Required, low -> Areas of Opportunity.
"""

SECURITY = "Security"
MODELING = "Content Modeling"
CONTENT = "Content"
OTHER = "Other Configurations"

CHECKS = [
    # Security
    (SECURITY, "SSO Enabled", "Verifies that single sign-on is configured for the organization so user access is centrally managed.",
     "Configure SSO with your identity provider to enforce central authentication and simplify offboarding.", "organization", "high", 0.35),
    (SECURITY, "Two-Factor Authentication Enforced", "Checks whether two-factor authentication is required for all stack users.",
     "Enforce 2FA at the organization level so compromised passwords alone cannot grant access.", "user", "high", 0.4),
    (SECURITY, "Unused Management Tokens", "Finds management tokens that have not been used in the last 90 days.",
     "Revoke management tokens that are no longer needed; they grant broad write access to the stack.", "management_token", "high", 0.5),
    (SECURITY, "Unused Delivery Tokens", "Finds delivery tokens with no recorded usage in the last 90 days.",
     "Delete unused delivery tokens to reduce the surface for leaked credentials.", "delivery_token", "low", 0.55),
    (SECURITY, "Users With Excessive Roles", "Flags users assigned the Admin role when a narrower custom role would suffice.",
     "Apply least privilege: create custom roles scoped to the content types and environments users actually work with.", "user", "high", 0.45),
    (SECURITY, "Webhooks Without Secrets", "Detects webhooks that do not send a signed secret header to the receiver.",
     "Add a shared secret or signature header to each webhook and validate it on the receiving end.", "webhook", "low", 0.3),
    (SECURITY, "Inactive Users", "Lists users who have not logged in for more than 180 days.",
     "Remove or downgrade inactive accounts during regular access reviews.", "user", "low", 0.4),
    # Content Modeling
    (MODELING, "Unused Content Types", "Identifies content types that have no entries.",
     "Delete or archive content types with no entries to keep the model easy to understand.", "content_type", "low", 0.6),
    (MODELING, "Excessive Fields per Content Type", "Flags content types with more than 50 fields, which slows editing and API responses.",
     "Split large content types into smaller ones and use references or modular blocks.", "content_type", "high", 0.45),
    (MODELING, "Deeply Nested Groups", "Detects group fields nested more than three levels deep.",
     "Flatten nested groups; deep nesting makes entries hard to edit and queries expensive.", "content_type", "low", 0.35),
    (MODELING, "Missing Field Descriptions", "Finds fields without help text for content editors.",
     "Add instructions to fields so editors know what to enter and in what format.", "field", "low", 0.65),
    (MODELING, "Unvalidated Required Fields", "Checks that mandatory fields use validation such as regex or length limits.",
     "Add validation rules to required fields to prevent malformed content reaching production.", "field", "low", 0.5),
    (MODELING, "Circular References", "Detects reference fields that create circular dependencies between content types.",
     "Break circular references; they cause infinite include loops and hard-to-debug API responses.", "content_type", "high", 0.2),
    # Content
    (CONTENT, "Entries Missing Image Optimization", "Finds entries whose images are served without transformation or compression parameters.",
     "Use the Image Delivery API transformations (format, quality, width) to reduce page weight.", "entry", "high", 0.6),
    (CONTENT, "Unpublished Entries Older Than 1 Year", "Lists entries that have been in draft for more than a year.",
     "Publish or delete stale drafts to keep the stack clean and reduce editor confusion.", "entry", "low", 0.55),
    (CONTENT, "Entries Without Publish Rules", "Detects entries published outside any workflow or publish rule.",
     "Route publishing through workflows so every entry gets an approval step.", "entry", "high", 0.4),
    (CONTENT, "Unused Assets", "Finds assets not referenced by any entry.",
     "Delete or archive unreferenced assets to reduce storage and improve asset search.", "asset", "low", 0.7),
    (CONTENT, "Oversized Assets", "Flags assets larger than 5 MB.",
     "Compress large assets before upload or rely on image transformations for delivery.", "asset", "high", 0.5),
    (CONTENT, "Assets Missing Alt Text", "Finds image assets with no title or description usable as alt text.",
     "Add descriptive titles or descriptions to assets to meet accessibility requirements.", "asset", "low", 0.6),
    # Other Configurations
    (OTHER, "Multiple Environments Configured", "Checks that the stack has at least a development and production environment.",
     "Create separate environments so changes can be tested before reaching production.", "stack", "high", 0.15),
    (OTHER, "Workflows Defined", "Checks whether at least one publishing workflow exists.",
     "Define a workflow with review stages for content types that need editorial approval.", "stack", "high", 0.3),
    (OTHER, "Locales Without Fallback", "Finds non-master locales with no fallback locale configured.",
     "Set fallback locales so untranslated entries still return content to users.", "locale", "low", 0.4),
    (OTHER, "Extensions Not Version Controlled", "Detects custom extensions and apps with no linked source repository.",
     "Keep extension source in version control and record the repo URL in the extension metadata.", "extension", "low", 0.45),
    (OTHER, "Release Hygiene", "Finds releases that were created but never deployed.",
     "Deploy or delete abandoned releases to avoid confusion about what is live.", "release", "low", 0.35),
]

STACKS = [
    ("Acme Retail - Web", 8420, 5310),
    ("Acme Retail - Mobile App", 2150, 1890),
    ("Globex Corporate Site", 640, 720),
    ("Initech Support Portal", 15300, 4020),
]

ENTITY_WORDS = ["homepage", "pricing", "about-us", "product-detail", "blog-post", "faq", "landing", "footer",
                "header", "banner", "press-release", "case-study", "careers", "contact", "docs-index",
                "promo", "category", "campaign", "legal", "onboarding"]
