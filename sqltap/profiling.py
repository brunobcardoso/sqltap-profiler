"""
Profiling utilities for SQLTap with comprehensive statistics and reporting.

This module provides convenient wrappers and context managers for profiling
SQLAlchemy queries anywhere in your application - tests, development, staging,
or production. It offers comprehensive statistics and automatic HTML report
generation.

Use cases:
    - Performance testing in pytest/unittest
    - Debugging slow queries in development
    - Profiling endpoints in staging
    - Temporary production performance analysis
    - N+1 query detection
    - Performance benchmarking

Example:
    Basic usage (works anywhere)::

        from sqltap.profiling import sqltap_profiler

        def my_function():
            with sqltap_profiler("operation-name") as stats:
                result = expensive_operation()
            
            print(f"Executed {stats.query_count} queries in {stats.total_time:.3f}s")
            return result
    
    In tests with assertions::

        def test_performance():
            with sqltap_profiler("my-test") as stats:
                response = my_function()
            
            assert stats.query_count <= 5
            assert stats.total_time <= 1.0
            
            # Check for N+1 queries
            selects = stats.get_queries_by_type('SELECT')
            for qg in selects:
                assert qg.query_count <= 10, f"Potential N+1: {qg.sql_text[:100]}"

    Custom report location::

        with sqltap_profiler("debug", report_dir="/tmp/reports") as stats:
            response = my_function()

    Without saving reports::

        with sqltap_profiler("quick-check", save_report=False) as stats:
            response = my_function()
"""

import os
import collections
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone

from . import sqltap


class QueryGroupStats:
    """Wrapper around a SQLTap QueryGroup for convenient access to query statistics.
    
    This class provides a clean interface to access statistics about a group of
    similar queries (queries with the same SQL text but potentially different parameters).
    
    Attributes:
        index (int): The index of this query group in the sorted list
    """
    
    def __init__(self, query_group, group_index):
        self._group = query_group
        self.index = group_index
    
    @property
    def query_count(self):
        """Number of times this query was executed."""
        return len(self._group.queries)
    
    @property
    def total_time(self):
        """Total time for all executions of this query."""
        return self._group.sum
    
    @property
    def mean_time(self):
        """Mean execution time."""
        return self._group.mean
    
    @property
    def median_time(self):
        """Median execution time."""
        return self._group.median
    
    @property
    def min_time(self):
        """Minimum execution time."""
        return self._group.min
    
    @property
    def max_time(self):
        """Maximum execution time."""
        return self._group.max
    
    @property
    def rowcount(self):
        """Total rows returned/affected by all executions of this query."""
        return self._group.rowcounts
    
    @property
    def sql_text(self):
        """The SQL query text."""
        return self._group.text
    
    @property
    def formatted_sql(self):
        """Formatted SQL query text."""
        return self._group.formatted_text
    
    @property
    def first_word(self):
        """First word of SQL (SELECT, INSERT, UPDATE, DELETE, etc)."""
        return self._group.first_word
    
    @property
    def queries(self):
        """Access individual query executions (list of QueryStats)."""
        return self._group.queries
    
    def get_query_details(self):
        """Get details of each individual execution.
        
        Returns:
            list: List of dicts with duration, rowcount, params, and params_id for each execution
        """
        return [
            {
                'duration': q.duration,
                'rowcount': q.rowcount,
                'params': q.params,
                'params_id': q.params_id
            }
            for q in self._group.queries
        ]
    
    def __repr__(self):
        return (f"<QueryGroupStats {self.index}: {self.first_word} "
                f"count={self.query_count} total={self.total_time:.3f}s "
                f"mean={self.mean_time:.3f}s rows={self.rowcount}>")


class PerformanceStats:
    """Comprehensive SQLTap statistics for performance testing.
    
    This class provides a high-level interface to SQLTap profiling results with
    convenient properties for common statistics and query analysis.
    
    Example:
        >>> stats = PerformanceStats(raw_stats)
        >>> print(f"Total queries: {stats.query_count}")
        >>> print(f"Total time: {stats.total_time:.3f}s")
        >>> for qg in stats.query_groups:
        ...     print(f"{qg.first_word}: {qg.query_count} times")
    """
    
    def __init__(self, raw_stats):
        self.raw_stats = raw_stats
        self._processed = False
        self._query_groups_list = []
        self._all_group = None
        self._profiling_duration = 0
    
    def _ensure_processed(self):
        """Lazy processing of stats - only process when first accessed."""
        if self._processed or not self.raw_stats:
            return
        
        self._processed = True
        
        # Process stats using SQLTap's infrastructure
        query_groups_dict = collections.defaultdict(sqltap.QueryGroup)
        self._all_group = sqltap.QueryGroup()
        
        for stat in self.raw_stats:
            stat.stack_text = ''.join(traceback.format_list(stat.stack)).strip()
            
            group = query_groups_dict[str(stat.text)]
            group.add(stat)
            self._all_group.add(stat)
        
        # Sort by total time (most expensive first)
        self._query_groups_list = sorted(
            query_groups_dict.values(),
            key=lambda g: g.sum,
            reverse=True
        )
        
        # Calculate medians
        for g in self._query_groups_list:
            g.calc_median()
        
        self._all_group.calc_median()
        self._profiling_duration = (
            self.raw_stats[-1].end_time - self.raw_stats[0].start_time
        )
    
    @property
    def query_count(self):
        """Total number of queries executed."""
        return len(self.raw_stats)
    
    @property
    def unique_queries(self):
        """Number of unique SQL queries."""
        self._ensure_processed()
        return len(self._query_groups_list)
    
    @property
    def total_time(self):
        """Total database time in seconds."""
        self._ensure_processed()
        return self._all_group.sum if self._all_group else 0
    
    @property
    def mean_time(self):
        """Mean query time in seconds."""
        self._ensure_processed()
        return self._all_group.mean if self._all_group else 0
    
    @property
    def median_time(self):
        """Median query time in seconds."""
        self._ensure_processed()
        return self._all_group.median if self._all_group else 0
    
    @property
    def min_time(self):
        """Minimum query time in seconds."""
        self._ensure_processed()
        return self._all_group.min if self._all_group else 0
    
    @property
    def max_time(self):
        """Maximum query time in seconds."""
        self._ensure_processed()
        return self._all_group.max if self._all_group else 0
    
    @property
    def profiling_duration(self):
        """Total profiling duration in seconds."""
        self._ensure_processed()
        return self._profiling_duration
    
    @property
    def query_groups(self):
        """List of QueryGroupStats objects, sorted by total time (slowest first)."""
        self._ensure_processed()
        return [QueryGroupStats(g, i) for i, g in enumerate(self._query_groups_list)]
    
    def get_queries_by_type(self, sql_type):
        """Get query groups filtered by SQL type (SELECT, INSERT, UPDATE, DELETE).
        
        Args:
            sql_type (str): The SQL command type to filter by
            
        Returns:
            list: List of QueryGroupStats objects matching the type
            
        Example:
            >>> selects = stats.get_queries_by_type('SELECT')
            >>> print(f"Found {len(selects)} SELECT query groups")
        """
        self._ensure_processed()
        return [
            QueryGroupStats(g, i) 
            for i, g in enumerate(self._query_groups_list)
            if g.first_word.upper() == sql_type.upper()
        ]
    
    def get_slowest_query(self):
        """Get the slowest query group.
        
        Returns:
            QueryGroupStats: The query group with the highest total time, or None if no queries
        """
        self._ensure_processed()
        return QueryGroupStats(self._query_groups_list[0], 0) if self._query_groups_list else None
    
    def __len__(self):
        """Support len(stats) for backward compatibility."""
        return self.query_count
    
    def __iter__(self):
        """Support iteration over raw stats for backward compatibility."""
        return iter(self.raw_stats)
    
    def __repr__(self):
        return (f"<PerformanceStats queries={self.query_count} "
                f"unique={self.unique_queries} total={self.total_time:.3f}s "
                f"mean={self.mean_time:.3f}s>")
    
    def summary(self):
        """Return a text summary of performance stats.
        
        Returns:
            str: A formatted text summary of all statistics and query groups
        """
        lines = [
            "=" * 70,
            "Performance Summary",
            "=" * 70,
            f"Total queries: {self.query_count}",
            f"Unique queries: {self.unique_queries}",
            f"Total time: {self.total_time:.3f} second(s)",
            f"Mean time: {self.mean_time:.3f} second(s)",
            f"Median time: {self.median_time:.3f} second(s)",
            f"Total profiling time: {self.profiling_duration:.3f} second(s)",
            "",
            "Query Groups (by total time):",
            "-" * 70,
        ]
        
        for qg in self.query_groups:
            lines.extend([
                f"\nQueryGroup {qg.index}: {qg.first_word}",
                f"  Query count: {qg.query_count}",
                f"  Total time: {qg.total_time:.3f}s",
                f"  Mean time: {qg.mean_time:.3f}s",
                f"  Median time: {qg.median_time:.3f}s",
                f"  Min time: {qg.min_time:.3f}s",
                f"  Max time: {qg.max_time:.3f}s",
                f"  Rowcount: {qg.rowcount}",
            ])
        
        lines.append("=" * 70)
        return "\n".join(lines)


def _save_report_locally(html, key_hint, report_dir=None):
    """Save HTML report locally to specified directory.
    
    Args:
        html (str): The HTML report content
        key_hint (str): Hint for the filename (e.g., test name)
        report_dir (str, optional): Directory to save reports. Defaults to ./sqltap_reports
        
    Returns:
        str: Path to the saved report file
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    hint = (key_hint or "test").replace("/", "_")
    
    if report_dir is None:
        report_dir = os.path.join(os.getcwd(), "sqltap_reports")
    
    os.makedirs(report_dir, exist_ok=True)
    
    local_file = os.path.join(report_dir, f"{ts}_{hint}.html")
    
    with open(local_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return local_file


@contextmanager
def sqltap_profiler(key_hint="test", save_report=True, report_dir=None):
    """Context manager for SQLTap profiling with comprehensive statistics.

    This context manager simplifies SQLTap profiling for tests by providing:
    - Automatic profiler setup and teardown
    - Comprehensive statistics via PerformanceStats object
    - Optional HTML report generation with configurable location
    - Easy-to-use assertions on query counts and performance
    - Works with pytest fixtures (stats accessible during test execution)

    Args:
        key_hint (str, optional): Identifier for the test (used in report filename). Defaults to "test".
        save_report (bool, optional): Whether to save HTML report. Defaults to True.
        report_dir (str, optional): Directory to save reports. Defaults to ./sqltap_reports.

    Yields:
        PerformanceStats: Statistics object with query metrics and analysis methods.
                        Stats are lazily collected on first access, allowing usage
                        in pytest fixtures and nested contexts.

    Example:
        Basic usage::
        
            with sqltap_profiler("my-test") as stats:
                response = my_function()
            
            # Stats accessible inside or after the context
            assert stats.query_count <= 5
            assert stats.total_time <= 1.0
        
        With pytest fixtures::
        
            @pytest.fixture
            def profile_db(request):
                with sqltap_profiler(request.node.name, save_report=False) as stats:
                    yield stats
            
            def test_example(profile_db):
                response = my_function()
                # Stats accessible during test execution
                assert profile_db.query_count <= 5
                logger.info(profile_db.summary())
        
        Detailed analysis::
        
            with sqltap_profiler("my-test") as stats:
                response = my_function()
            
            # Check for N+1 queries
            selects = stats.get_queries_by_type('SELECT')
            for qg in selects:
                assert qg.query_count <= 10, f"Potential N+1: {qg.sql_text[:100]}"
            
            # Print summary
            print(stats.summary())
        
        Custom report location::
        
            with sqltap_profiler("my-test", report_dir="/tmp/reports") as stats:
                response = my_function()
        
        Without saving reports::
        
            with sqltap_profiler("my-test", save_report=False) as stats:
                response = my_function()

    Note:
        Statistics are collected lazily on first property access (e.g., query_count,
        summary()). This allows the profiler to capture all queries that occur during
        the context, making it compatible with pytest fixtures and nested usage patterns.
        Once collected, stats are cached and remain consistent across multiple accesses.
    """
    profiler = sqltap.start()
    
    # Create a stats object that will be populated later
    class LivePerformanceStats(PerformanceStats):
        def __init__(self):
            self._profiler = profiler
            self._collected = False
            super().__init__([])
        
        def _ensure_collected(self):
            """Collect stats from profiler if not already collected."""
            if not self._collected and self._profiler:
                self.raw_stats.extend(self._profiler.collect())
                self._collected = True
        
        def _ensure_processed(self):
            """Override to ensure stats are collected before processing."""
            self._ensure_collected()
            super()._ensure_processed()
        
        @property
        def query_count(self):
            """Total number of queries executed."""
            self._ensure_collected()
            return len(self.raw_stats)
    
    stats = LivePerformanceStats()
    
    try:
        yield stats
    finally:
        # Ensure collection happens
        stats._ensure_collected()
        
        if stats.raw_stats and save_report:
            try:
                html = sqltap.report(stats.raw_stats)
                report_file = _save_report_locally(html, key_hint, report_dir)
                print(
                    f"[sqltap] Generated report with "
                    f"{stats.query_count} queries "
                    f"({stats.unique_queries} unique), "
                    f"total time: {stats.total_time:.3f}s, "
                    f"mean: {stats.mean_time:.3f}s: {report_file}"
                )
            except Exception as e:
                print(f"[sqltap] Failed to generate report: {e}")
