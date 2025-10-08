"""
Example demonstrating the sqltap.profiling module for performance profiling.

This example shows how to use sqltap_profiler to profile database queries
anywhere in your application - tests, development, or production debugging.
Includes examples of catching performance issues like N+1 queries.
"""

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from sqltap.profiling import sqltap_profiler


Base = declarative_base()


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    posts = relationship("Post", back_populates="author")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="posts")


def setup_database():
    """Create database and sample data."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create sample data
    for i in range(5):
        author = Author(name=f"Author {i}")
        session.add(author)
        for j in range(3):
            post = Post(title=f"Post {j} by Author {i}", author=author)
            session.add(post)
    
    session.commit()
    return session


def example_good_query(session):
    """Example of efficient query with eager loading."""
    print("\n=== Example 1: Good Query (with eager loading) ===")
    
    with sqltap_profiler("good-query", save_report=False) as stats:
        # Efficient: use joinedload to avoid N+1
        from sqlalchemy.orm import joinedload
        posts = session.query(Post).options(joinedload(Post.author)).all()
        
        # Access authors without triggering additional queries
        for post in posts:
            _ = post.author.name
    
    print(f"Total queries: {stats.query_count}")
    print(f"Unique queries: {stats.unique_queries}")
    print(f"Total time: {stats.total_time:.4f}s")
    
    # Verify efficiency
    assert stats.query_count <= 3, "Should use minimal queries with eager loading"


def example_n_plus_one(session):
    """Example of N+1 query problem (to be detected)."""
    print("\n=== Example 2: N+1 Query Problem (detected) ===")
    
    with sqltap_profiler("n-plus-one", save_report=False) as stats:
        # Inefficient: lazy loading causes N+1 queries
        posts = session.query(Post).all()
        
        # Each access to author triggers a separate query!
        for post in posts:
            _ = post.author.name
    
    print(f"Total queries: {stats.query_count}")
    print(f"Unique queries: {stats.unique_queries}")
    print(f"Total time: {stats.total_time:.4f}s")
    
    # Detect N+1 issue
    selects = stats.get_queries_by_type('SELECT')
    print(f"\nSELECT queries: {len(selects)}")
    for i, qg in enumerate(selects):
        print(f"  {i+1}. Executed {qg.query_count} times - {qg.sql_text[:80]}...")
    
    # This assertion would fail, alerting us to the N+1 problem
    try:
        assert stats.query_count <= 3, "N+1 query detected!"
    except AssertionError as e:
        print(f"\n Performance issue detected: {e}")


def example_detailed_analysis(session):
    """Example showing detailed query analysis."""
    print("\n=== Example 3: Detailed Query Analysis ===")
    
    with sqltap_profiler("detailed-analysis", save_report=False) as stats:
        # Mix of different query types
        authors = session.query(Author).filter(Author.id <= 3).all()
        posts = session.query(Post).filter(Post.author_id.in_([1, 2])).all()
        
        # Update query
        session.query(Post).filter(Post.id == 1).update({"title": "Updated Title"})
        session.commit()
    
    print(f"\nOverall Statistics:")
    print(f"  Total queries: {stats.query_count}")
    print(f"  Unique queries: {stats.unique_queries}")
    print(f"  Total time: {stats.total_time:.4f}s")
    print(f"  Mean time: {stats.mean_time:.4f}s")
    print(f"  Median time: {stats.median_time:.4f}s")
    
    print(f"\nQuery Breakdown by Type:")
    for query_type in ['SELECT', 'UPDATE', 'INSERT', 'DELETE']:
        queries = stats.get_queries_by_type(query_type)
        if queries:
            print(f"  {query_type}: {len(queries)} unique, "
                  f"total: {sum(q.query_count for q in queries)} executions")
    
    print(f"\nSlowest Query:")
    slowest = stats.get_slowest_query()
    if slowest:
        print(f"  Type: {slowest.first_word}")
        print(f"  Executed: {slowest.query_count} times")
        print(f"  Total time: {slowest.total_time:.4f}s")
        print(f"  Mean time: {slowest.mean_time:.4f}s")


def example_with_assertions(session):
    """Example showing how to use in actual tests."""
    print("\n=== Example 4: Test Assertions ===")
    
    with sqltap_profiler("test-assertions", save_report=False) as stats:
        # Query that should be efficient
        authors = session.query(Author).limit(10).all()
    
    # Performance assertions
    try:
        assert stats.query_count <= 5, f"Too many queries: {stats.query_count}"
        assert stats.total_time < 1.0, f"Queries too slow: {stats.total_time}s"
        assert stats.unique_queries <= 3, f"Too many unique queries: {stats.unique_queries}"
        print("✓ All performance assertions passed!")
    except AssertionError as e:
        print(f"✗ Performance assertion failed: {e}")


def example_summary_report(session):
    """Example showing the summary report."""
    print("\n=== Example 5: Summary Report ===")
    
    with sqltap_profiler("summary-report", save_report=False) as stats:
        session.query(Author).all()
        session.query(Post).filter(Post.author_id == 1).all()
    
    print(stats.summary())


def main():
    """Run all examples."""
    print("SQLTap Testing Module Examples")
    print("=" * 70)
    
    session = setup_database()
    
    try:
        example_good_query(session)
        example_n_plus_one(session)
        example_detailed_analysis(session)
        example_with_assertions(session)
        example_summary_report(session)
        
        print("\n" + "=" * 70)
        print("Examples completed! Check the output above to see how to use")
        print("sqltap_profiler for performance testing in your projects.")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

