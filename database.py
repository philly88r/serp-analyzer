import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from models import Base, SearchQuery, SearchResult, PageAnalysis, CompetitorAnalysis, AIRecommendation, ProxyStatus

# Set up logging
logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'serp_analyzer.db')
DB_URL = f'sqlite:///{DB_PATH}'

# Create engine
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

# Create session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """Initialize the database, creating tables if they don't exist."""
    try:
        Base.metadata.create_all(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_session():
    """Get a database session."""
    return Session()

def close_session(session):
    """Close a database session."""
    session.close()

def save_search_query(query, user_id=None):
    """Save a search query to the database."""
    session = get_session()
    try:
        search_query = SearchQuery(query=query, user_id=user_id)
        session.add(search_query)
        session.commit()
        logger.info(f"Saved search query: {query}")
        return search_query.id
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving search query: {str(e)}")
        raise
    finally:
        close_session(session)

def save_search_results(query_id, results):
    """Save search results to the database."""
    session = get_session()
    try:
        for result in results:
            search_result = SearchResult(
                query_id=query_id,
                position=result.get('position', 0),
                title=result.get('title', ''),
                url=result.get('url', ''),
                description=result.get('description', '')
            )
            session.add(search_result)
        session.commit()
        logger.info(f"Saved {len(results)} search results for query ID {query_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving search results: {str(e)}")
        raise
    finally:
        close_session(session)

def save_page_analysis(search_result_id, analysis_data):
    """Save page analysis data to the database."""
    session = get_session()
    try:
        # Extract specific fields from analysis_data
        page_analysis = PageAnalysis(
            search_result_id=search_result_id,
            word_count=analysis_data.get('content', {}).get('word_count'),
            title_length=len(analysis_data.get('title', '')),
            meta_description_length=len(analysis_data.get('description', '')),
            has_schema_markup=analysis_data.get('schema_markup', {}).get('has_schema', False),
            schema_types=analysis_data.get('schema_markup', {}).get('schema_types', []),
            h1_count=len(analysis_data.get('headings', {}).get('h1', [])),
            h2_count=len(analysis_data.get('headings', {}).get('h2', [])),
            h3_count=len(analysis_data.get('headings', {}).get('h3', [])),
            internal_links_count=analysis_data.get('links', {}).get('internal', 0),
            external_links_count=analysis_data.get('links', {}).get('external', 0),
            images_count=analysis_data.get('images', {}).get('total', 0),
            images_with_alt_count=analysis_data.get('images', {}).get('with_alt', 0),
            page_size_kb=analysis_data.get('technical', {}).get('page_size_kb', 0),
            load_time_ms=analysis_data.get('technical', {}).get('load_time_ms', 0),
            raw_data=analysis_data  # Store the full analysis data
        )
        session.add(page_analysis)
        session.commit()
        logger.info(f"Saved page analysis for search result ID {search_result_id}")
        return page_analysis.id
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving page analysis: {str(e)}")
        raise
    finally:
        close_session(session)

def save_competitor_analysis(query_id, target_url, competitor_url, analysis_data):
    """Save competitor analysis data to the database."""
    session = get_session()
    try:
        competitor_analysis = CompetitorAnalysis(
            query_id=query_id,
            target_url=target_url,
            competitor_url=competitor_url,
            gap_score=analysis_data.get('gap_score'),
            content_gap=analysis_data.get('content_gap'),
            keyword_gap=analysis_data.get('keyword_gap'),
            technical_gap=analysis_data.get('technical_gap')
        )
        session.add(competitor_analysis)
        session.commit()
        logger.info(f"Saved competitor analysis for query ID {query_id}, target URL {target_url}, competitor URL {competitor_url}")
        return competitor_analysis.id
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving competitor analysis: {str(e)}")
        raise
    finally:
        close_session(session)

def save_ai_recommendation(url, recommendation_type, recommendation, impact_score, difficulty, query_id=None, page_analysis_id=None):
    """Save AI-generated recommendation to the database."""
    session = get_session()
    try:
        ai_recommendation = AIRecommendation(
            query_id=query_id,
            page_analysis_id=page_analysis_id,
            url=url,
            recommendation_type=recommendation_type,
            recommendation=recommendation,
            impact_score=impact_score,
            difficulty=difficulty
        )
        session.add(ai_recommendation)
        session.commit()
        logger.info(f"Saved AI recommendation for URL {url}, type {recommendation_type}")
        return ai_recommendation.id
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving AI recommendation: {str(e)}")
        raise
    finally:
        close_session(session)

def update_proxy_status(proxy_url, success=True, response_time_ms=None, country_code=None, region=None):
    """Update proxy status in the database."""
    session = get_session()
    try:
        proxy_status = session.query(ProxyStatus).filter_by(proxy_url=proxy_url).first()
        if not proxy_status:
            proxy_status = ProxyStatus(
                proxy_url=proxy_url,
                country_code=country_code,
                region=region
            )
            session.add(proxy_status)
        
        # Update fields
        if success:
            proxy_status.success_count += 1
        else:
            proxy_status.failure_count += 1
        
        if response_time_ms:
            if proxy_status.average_response_time_ms:
                # Calculate new average
                total_requests = proxy_status.success_count + proxy_status.failure_count
                proxy_status.average_response_time_ms = (
                    (proxy_status.average_response_time_ms * (total_requests - 1)) + response_time_ms
                ) / total_requests
            else:
                proxy_status.average_response_time_ms = response_time_ms
        
        session.commit()
        logger.info(f"Updated proxy status for {proxy_url}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating proxy status: {str(e)}")
        raise
    finally:
        close_session(session)

def get_historical_rankings(url, limit=10):
    """Get historical rankings for a URL."""
    session = get_session()
    try:
        results = session.query(
            SearchQuery.query,
            SearchResult.position,
            SearchResult.timestamp
        ).join(
            SearchResult, SearchQuery.id == SearchResult.query_id
        ).filter(
            SearchResult.url.like(f"%{url}%")
        ).order_by(
            SearchResult.timestamp.desc()
        ).limit(limit).all()
        
        return [
            {
                "query": r[0],
                "position": r[1],
                "timestamp": r[2].isoformat()
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error getting historical rankings: {str(e)}")
        return []
    finally:
        close_session(session)

def get_best_performing_proxies(limit=10):
    """Get the best performing proxies based on success rate and response time."""
    session = get_session()
    try:
        proxies = session.query(ProxyStatus).filter(
            ProxyStatus.is_active == True,
            ProxyStatus.success_count > 0
        ).all()
        
        # Calculate success rate and score
        for proxy in proxies:
            total_requests = proxy.success_count + proxy.failure_count
            proxy.success_rate = proxy.success_count / total_requests if total_requests > 0 else 0
            # Score = success_rate / response_time (higher is better)
            proxy.score = proxy.success_rate / proxy.average_response_time_ms if proxy.average_response_time_ms else 0
        
        # Sort by score (descending)
        proxies.sort(key=lambda p: p.score, reverse=True)
        
        return [
            {
                "proxy_url": p.proxy_url,
                "success_rate": p.success_rate,
                "avg_response_time_ms": p.average_response_time_ms,
                "country_code": p.country_code,
                "region": p.region
            }
            for p in proxies[:limit]
        ]
    except Exception as e:
        logger.error(f"Error getting best performing proxies: {str(e)}")
        return []
    finally:
        close_session(session)

# Initialize the database when this module is imported
init_db()
