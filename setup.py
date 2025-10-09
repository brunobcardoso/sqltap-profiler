from setuptools import setup

long_description = """
sqltap-profiler is an enhanced version of sqltap that provides SQL profiling 
and introspection for applications using SQLAlchemy, with improved performance
and additional features for modern Python applications.

sqltap-profiler helps you quickly understand:

   * how many times a sql query is executed
   * how much time your sql queries take
   * where your application is issuing sql queries from

This enhanced version includes:
   * Better performance and memory usage
   * Improved AWS Lambda support
   * Enhanced reporting capabilities
   * Modern Python 3 support
   * NEW in v1.1.0: Comprehensive profiling utilities

Original sqltap: https://github.com/inconshreveable/sqltap
Enhanced version: https://github.com/brunobcardoso/sqltap-profiler
"""

setup(
    name="sqltap-profiler",
    version="1.1.0",
    description=("Enhanced SQL profiling and introspection for applications using "
                 "sqlalchemy with improved performance and modern features"),
    long_description=long_description,
    author="Bruno Cardoso",
    author_email="cardosobrunob@gmail.com",
    url="https://github.com/brunobcardoso/sqltap-profiler",
    packages=["sqltap"],
    package_data={"sqltap": ["templates/*.mako"]},
    install_requires=[
        "SQLAlchemy >= 1.4",
        "Mako >= 0.4.1",
        "Werkzeug >= 0.9.6",
        "sqlparse >= 0.1.15"
    ],
    python_requires=">=3.7",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Database',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Testing'
    ],
    keywords="sqlalchemy sql profiling debugging performance",
    project_urls={
        'Bug Reports': 'https://github.com/brunobcardoso/sqltap-profiler/issues',
        'Source': 'https://github.com/brunobcardoso/sqltap-profiler',
        'Documentation': 'https://github.com/brunobcardoso/sqltap-profiler#readme',
    }
)
