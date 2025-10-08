import tempfile
import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqltap.profiling import sqltap_profiler, QueryGroupStats


Base = declarative_base()


class TestModel(Base):
    __tablename__ = "test_model"
    id = Column("id", Integer, primary_key=True)
    name = Column("name", String)


class TestSQLTapProfiling:
    """Test suite for sqltap.profiling utilities."""
    
    def setUp(self):
        """Set up test database."""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def test_basic_profiling(self):
        """Test basic profiling with sqltap_profiler."""
        self.setUp()
        
        with sqltap_profiler("test-basic", save_report=False) as stats:
            # Execute some queries
            self.session.add(TestModel(name="test1"))
            self.session.add(TestModel(name="test2"))
            self.session.commit()
            
            # Query
            self.session.query(TestModel).all()
        
        # Verify stats
        assert stats.query_count > 0
        assert isinstance(stats.total_time, float)
        assert stats.total_time >= 0
        assert stats.unique_queries > 0
    
    def test_query_count_assertion(self):
        """Test query count assertions."""
        self.setUp()
        
        with sqltap_profiler("test-count", save_report=False) as stats:
            self.session.add(TestModel(name="test"))
            self.session.commit()
        
        # Should have INSERT and some other queries
        assert stats.query_count >= 1
    
    def test_query_groups(self):
        """Test query group analysis."""
        self.setUp()
        
        with sqltap_profiler("test-groups", save_report=False) as stats:
            # Insert multiple records with same query
            for i in range(3):
                self.session.add(TestModel(name=f"test{i}"))
            self.session.commit()
        
        # Check query groups
        assert len(stats.query_groups) > 0
        for qg in stats.query_groups:
            assert isinstance(qg, QueryGroupStats)
            assert hasattr(qg, 'query_count')
            assert hasattr(qg, 'total_time')
            assert hasattr(qg, 'sql_text')
    
    def test_get_queries_by_type(self):
        """Test filtering queries by type."""
        self.setUp()
        
        with sqltap_profiler("test-filter", save_report=False) as stats:
            self.session.add(TestModel(name="test"))
            self.session.commit()
            self.session.query(TestModel).all()
        
        # Get SELECT queries
        selects = stats.get_queries_by_type('SELECT')
        assert len(selects) > 0
        for qg in selects:
            assert qg.first_word.upper() == 'SELECT'
    
    def test_get_slowest_query(self):
        """Test getting slowest query."""
        self.setUp()
        
        with sqltap_profiler("test-slowest", save_report=False) as stats:
            self.session.add(TestModel(name="test"))
            self.session.commit()
        
        slowest = stats.get_slowest_query()
        if slowest:  # Might be None if no queries
            assert isinstance(slowest, QueryGroupStats)
            assert slowest.total_time >= 0
    
    def test_summary(self):
        """Test summary generation."""
        self.setUp()
        
        with sqltap_profiler("test-summary", save_report=False) as stats:
            self.session.add(TestModel(name="test"))
            self.session.commit()
        
        summary = stats.summary()
        assert isinstance(summary, str)
        assert "Performance Summary" in summary
        assert "Total queries:" in summary
    
    def test_custom_report_dir(self):
        """Test saving report to custom directory."""
        self.setUp()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with sqltap_profiler("test-custom-dir", save_report=True, report_dir=tmpdir) as stats:
                self.session.add(TestModel(name="test"))
                self.session.commit()
            
            # Check that report was created
            files = os.listdir(tmpdir)
            assert len(files) > 0
            assert any(f.endswith('.html') for f in files)
    
    def test_no_report_generation(self):
        """Test disabling report generation."""
        self.setUp()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with sqltap_profiler("test-no-report", save_report=False, report_dir=tmpdir) as stats:
                self.session.add(TestModel(name="test"))
                self.session.commit()
            
            # Verify no report was created
            files = os.listdir(tmpdir)
            assert len([f for f in files if f.endswith('.html')]) == 0
    
    def test_performance_stats_properties(self):
        """Test PerformanceStats property access."""
        self.setUp()
        
        with sqltap_profiler("test-props", save_report=False) as stats:
            self.session.add(TestModel(name="test"))
            self.session.commit()
        
        assert isinstance(stats.query_count, int)
        assert isinstance(stats.unique_queries, int)
        assert isinstance(stats.total_time, float)
        assert isinstance(stats.mean_time, float)
        assert isinstance(stats.median_time, float)
        assert isinstance(stats.min_time, float)
        assert isinstance(stats.max_time, float)
        assert isinstance(stats.profiling_duration, float)
    
    def test_empty_stats(self):
        """Test stats with no queries."""
        with sqltap_profiler("test-empty", save_report=False) as stats:
            pass  # No queries
        
        assert stats.query_count == 0
        assert stats.total_time == 0
        assert stats.unique_queries == 0
        assert len(stats.query_groups) == 0
        assert stats.get_slowest_query() is None

