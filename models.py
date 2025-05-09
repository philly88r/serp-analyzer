import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class SearchQuery(Base):
    """Model for storing search queries and their metadata."""
    __tablename__ = 'search_queries'
    
    id = Column(Integer, primary_key=True)
    query = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(String(255), nullable=True)  # Optional user identifier
    
    # Relationships
    results = relationship("SearchResult", back_populates="query", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query='{self.query}')>"


class SearchResult(Base):
    """Model for storing search results for a query."""
    __tablename__ = 'search_results'
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('search_queries.id'), nullable=False)
    position = Column(Integer, nullable=False)
    title = Column(String(1024), nullable=True)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    query = relationship("SearchQuery", back_populates="results")
    page_analysis = relationship("PageAnalysis", back_populates="search_result", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SearchResult(id={self.id}, url='{self.url}', position={self.position})>"


class PageAnalysis(Base):
    """Model for storing detailed page analysis data."""
    __tablename__ = 'page_analyses'
    
    id = Column(Integer, primary_key=True)
    search_result_id = Column(Integer, ForeignKey('search_results.id'), nullable=False)
    word_count = Column(Integer, nullable=True)
    title_length = Column(Integer, nullable=True)
    meta_description_length = Column(Integer, nullable=True)
    has_schema_markup = Column(Boolean, nullable=True)
    schema_types = Column(JSON, nullable=True)
    h1_count = Column(Integer, nullable=True)
    h2_count = Column(Integer, nullable=True)
    h3_count = Column(Integer, nullable=True)
    internal_links_count = Column(Integer, nullable=True)
    external_links_count = Column(Integer, nullable=True)
    images_count = Column(Integer, nullable=True)
    images_with_alt_count = Column(Integer, nullable=True)
    page_size_kb = Column(Float, nullable=True)
    load_time_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    raw_data = Column(JSON, nullable=True)  # Store full analysis as JSON
    
    # Relationships
    search_result = relationship("SearchResult", back_populates="page_analysis")
    
    def __repr__(self):
        return f"<PageAnalysis(id={self.id}, word_count={self.word_count})>"


class CompetitorAnalysis(Base):
    """Model for storing competitor analysis data."""
    __tablename__ = 'competitor_analyses'
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('search_queries.id'), nullable=False)
    target_url = Column(String(2048), nullable=False)  # The user's URL being analyzed
    competitor_url = Column(String(2048), nullable=False)  # Competitor URL
    gap_score = Column(Float, nullable=True)  # Overall gap score
    content_gap = Column(JSON, nullable=True)  # Content gap analysis
    keyword_gap = Column(JSON, nullable=True)  # Keyword gap analysis
    technical_gap = Column(JSON, nullable=True)  # Technical SEO gap analysis
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<CompetitorAnalysis(id={self.id}, target='{self.target_url}', competitor='{self.competitor_url}')>"


class AIRecommendation(Base):
    """Model for storing AI-generated recommendations."""
    __tablename__ = 'ai_recommendations'
    
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('search_queries.id'), nullable=True)
    page_analysis_id = Column(Integer, ForeignKey('page_analyses.id'), nullable=True)
    url = Column(String(2048), nullable=False)
    recommendation_type = Column(String(255), nullable=False)  # content, technical, etc.
    recommendation = Column(Text, nullable=False)
    impact_score = Column(Float, nullable=True)  # 0-10 score of estimated impact
    difficulty = Column(String(50), nullable=True)  # easy, medium, hard
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<AIRecommendation(id={self.id}, type='{self.recommendation_type}', impact={self.impact_score})>"


class ProxyStatus(Base):
    """Model for tracking proxy health and performance."""
    __tablename__ = 'proxy_statuses'
    
    id = Column(Integer, primary_key=True)
    proxy_url = Column(String(2048), nullable=False)
    is_active = Column(Boolean, default=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    average_response_time_ms = Column(Float, nullable=True)
    last_check = Column(DateTime, default=datetime.datetime.utcnow)
    country_code = Column(String(10), nullable=True)
    region = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<ProxyStatus(id={self.id}, proxy='{self.proxy_url}', active={self.is_active})>"
