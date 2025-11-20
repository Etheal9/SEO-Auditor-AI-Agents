from pydantic import BaseModel, Field
from typing import List, Optional


class HeadingItem(BaseModel):
    tag: str = Field(..., description="Heading tag such as h1, h2, h3.")
    text: str = Field(..., description="Text content of the heading.")


class LinkCounts(BaseModel):
    internal: Optional[int] = Field(None, description="Number of internal links on the page.")
    external: Optional[int] = Field(None, description="Number of external links on the page.")
    broken: Optional[int] = Field(None, description="Number of broken links detected.")
    notes: Optional[str] = Field(
        None, description="Additional qualitative observations about linking."
    )


class AuditResults(BaseModel):
    title_tag: str = Field(..., description="Full title tag text.")
    meta_description: str = Field(..., description="Meta description text.")
    primary_heading: str = Field(..., description="Primary H1 heading on the page.")
    secondary_headings: List[HeadingItem] = Field(
        default_factory=list, description="Secondary headings (H2-H4) in reading order."
    )
    word_count: Optional[int] = Field(
        None, description="Approximate number of words in the main content."
    )
    content_summary: str = Field(
        ..., description="Summary of the main topics and structure of the content."
    )
    link_counts: LinkCounts = Field(
        ...,
        description="Quantitative snapshot of internal/external/broken links.",
    )
    technical_findings: List[str] = Field(
        default_factory=list,
        description="List of notable technical SEO issues (e.g., missing alt text, slow LCP).",
    )
    content_opportunities: List[str] = Field(
        default_factory=list,
        description="Observed content gaps or opportunities for improvement.",
    )


class TargetKeywords(BaseModel):
    primary_keyword: str = Field(..., description="Most likely primary keyword target.")
    secondary_keywords: List[str] = Field(
        default_factory=list, description="Related secondary or supporting keywords."
    )
    search_intent: str = Field(
        ...,
        description="Dominant search intent inferred from the page (informational, transactional, etc.).",
    )
    supporting_topics: List[str] = Field(
        default_factory=list,
        description="Cluster of supporting topics or entities that reinforce the keyword strategy.",
    )


class PageAuditOutput(BaseModel):
    audit_results: AuditResults = Field(..., description="Structured on-page audit findings.")
    target_keywords: TargetKeywords = Field(
        ..., description="Keyword focus derived from page content."
    )


class SerpResult(BaseModel):
    rank: int = Field(..., description="Organic ranking position.")
    title: str = Field(..., description="Title of the search result.")
    url: str = Field(..., description="Landing page URL.")
    snippet: str = Field(..., description="SERP snippet or summary.")
    content_type: str = Field(
        ..., description="Content format (blog post, landing page, tool, video, etc.)."
    )


class SerpAnalysis(BaseModel):
    primary_keyword: str = Field(..., description="Keyword used for SERP research.")
    top_10_results: List[SerpResult] = Field(
        ..., description="Top organic competitors for the keyword."
    )
    title_patterns: List[str] = Field(
        default_factory=list,
        description="Common patterns or phrases used in competitor titles.",
    )
    content_formats: List[str] = Field(
        default_factory=list,
        description="Typical content formats found (guides, listicles, comparison pages, etc.).",
    )
    people_also_ask: List[str] = Field(
        default_factory=list,
        description="Representative questions surfaced in People Also Ask.",
    )
    key_themes: List[str] = Field(
        default_factory=list,
        description="Notable recurring themes, features, or angles competitors emphasize.",
    )
    differentiation_opportunities: List[str] = Field(
        default_factory=list,
        description="Opportunities to stand out versus competitors.",
    )


class OptimizationRecommendation(BaseModel):
    priority: str = Field(..., description="Priority level (P0, P1, P2).")
    area: str = Field(..., description="Optimization focus area (content, technical, UX, etc.).")
    recommendation: str = Field(..., description="Recommended action.")
    rationale: str = Field(..., description="Why this change matters, referencing audit/SERP data.")
    expected_impact: str = Field(..., description="Anticipated impact on SEO or user metrics.")
    effort: str = Field(..., description="Relative effort required (low/medium/high).")