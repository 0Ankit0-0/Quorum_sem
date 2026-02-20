"""
Query Command
SQL query operations
"""
import click

from services.query_service import query_service
from cli.utils import (
    print_success, print_error, print_info, print_header,
    print_table
)
from config.logging_config import get_logger

logger = get_logger(__name__)


@click.group()
def query():
    """Execute SQL queries on log database"""
    pass


@query.command()
@click.argument('sql_query')
@click.option('--limit', '-l', type=int, default=100, help='Max results')
@click.option('--output', '-o', help='Export to file (CSV or JSON)')
def execute(sql_query, limit, output):
    """Execute a SQL query"""
    try:
        print_header("Executing Query")
        print_info(f"Query: {sql_query}")
        
        # Execute
        result = query_service.execute_query(sql_query, limit)
        
        # Display results
        if output:
            # Export to file
            import json
            from pathlib import Path
            
            output_path = Path(output)
            
            if output_path.suffix.lower() == '.json':
                with open(output_path, 'w') as f:
                    json.dump(result['rows'], f, indent=2, default=str)
            elif output_path.suffix.lower() == '.csv':
                import csv
                with open(output_path, 'w', newline='') as f:
                    if result['rows']:
                        writer = csv.DictWriter(f, fieldnames=result['columns'])
                        writer.writeheader()
                        writer.writerows(result['rows'])
            
            print_success(f"Results exported to {output_path}")
        
        else:
            # Display in terminal
            if result['rows']:
                print_table(result['rows'][:20])  # Show first 20
                
                if result['row_count'] > 20:
                    print_info(f"\nShowing 20 of {result['row_count']} results")
            else:
                print_info("No results")
        
        print_info(f"Execution time: {result['execution_time_ms']:.2f}ms")
    
    except Exception as e:
        print_error(f"Query failed: {e}")
        logger.error(f"Query error: {e}", exc_info=True)
        raise click.Abort()


@query.command()
def saved():
    """List saved queries"""
    try:
        print_header("Saved Queries")
        
        queries = query_service.get_saved_queries()
        
        for name, sql in queries.items():
            click.echo(f"\n{click.style(name, bold=True)}:")
            click.echo(f"  {sql.strip()}")
    
    except Exception as e:
        print_error(f"Failed to get saved queries: {e}")
        logger.error(f"Saved queries error: {e}", exc_info=True)
        raise click.Abort()


@query.command()
@click.option('--limit', '-l', type=int, default=10, help='Number to show')
def history(limit):
    """Show query history"""
    try:
        print_header("Query History")
        
        history = query_service.get_query_history(limit)
        
        if history:
            for i, item in enumerate(history, 1):
                click.echo(f"\n{i}. {item['query']}")
                click.echo(f"   Rows: {item['row_count']}, "
                         f"Time: {item['execution_time_ms']:.2f}ms")
        else:
            print_info("No query history")
    
    except Exception as e:
        print_error(f"Failed to get history: {e}")
        logger.error(f"History error: {e}", exc_info=True)
        raise click.Abort()