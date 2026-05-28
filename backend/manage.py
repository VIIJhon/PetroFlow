"""
Database Management CLI
Command-line interface for database operations
"""

import click
import logging
import sys
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.db.init_db import init_db, create_tables, drop_tables, check_db_health
from app.db.seed_data import seed_all

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """PetroFlow Database Management CLI"""
    pass


@cli.command()
def init():
    """Initialize database with tables and initial admin user"""
    click.echo("Initializing database...")
    
    try:
        db = SessionLocal()
        init_db(db)
        db.close()
        click.echo(click.style("✓ Database initialized successfully!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Error initializing database: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def migrate(message):
    """Create a new migration"""
    click.echo(f"Creating migration: {message}")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'revision', '--autogenerate', '-m', message],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        click.echo(click.style("✓ Migration created successfully!", fg="green"))
        click.echo(result.stdout)
    else:
        click.echo(click.style(f"✗ Error creating migration: {result.stderr}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--revision', '-r', default='head', help='Target revision (default: head)')
def upgrade(revision):
    """Run database migrations"""
    click.echo(f"Running migrations to {revision}...")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'upgrade', revision],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        click.echo(click.style("✓ Migrations completed successfully!", fg="green"))
        click.echo(result.stdout)
    else:
        click.echo(click.style(f"✗ Error running migrations: {result.stderr}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--revision', '-r', default='-1', help='Target revision (default: -1)')
def downgrade(revision):
    """Rollback database migrations"""
    click.echo(f"Rolling back to {revision}...")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'downgrade', revision],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        click.echo(click.style("✓ Rollback completed successfully!", fg="green"))
        click.echo(result.stdout)
    else:
        click.echo(click.style(f"✗ Error rolling back: {result.stderr}", fg="red"))
        raise click.Abort()


@cli.command()
def seed():
    """Seed database with sample data"""
    click.echo("Seeding database with sample data...")
    
    try:
        db = SessionLocal()
        result = seed_all(db)
        db.close()
        
        click.echo(click.style("✓ Database seeded successfully!", fg="green"))
        click.echo(f"  Users: {result['users']}")
        click.echo(f"  Equipment: {result['equipment']}")
        click.echo(f"  Simulations: {result['simulations']}")
        click.echo(f"  Telemetry: {result['telemetry']}")
        click.echo(f"  Analysis: {result['analysis']}")
    except Exception as e:
        click.echo(click.style(f"✗ Error seeding database: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset the database? This will delete all data!')
def reset():
    """Reset database (drop all tables and recreate)"""
    click.echo(click.style("WARNING: Resetting database - all data will be lost!", fg="yellow"))
    
    try:
        # Drop all tables
        click.echo("Dropping all tables...")
        drop_tables()
        
        # Run migrations
        click.echo("Running migrations...")
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'upgrade', 'head'], capture_output=True)
        
        if result.returncode != 0:
            raise Exception("Migration failed")
        
        # Seed database
        click.echo("Seeding database...")
        db = SessionLocal()
        seed_result = seed_all(db)
        db.close()
        
        click.echo(click.style("✓ Database reset completed successfully!", fg="green"))
        click.echo(f"  Users: {seed_result['users']}")
        click.echo(f"  Equipment: {seed_result['equipment']}")
        click.echo(f"  Simulations: {seed_result['simulations']}")
        click.echo(f"  Telemetry: {seed_result['telemetry']}")
        click.echo(f"  Analysis: {seed_result['analysis']}")
    except Exception as e:
        click.echo(click.style(f"✗ Error resetting database: {e}", fg="red"))
        raise click.Abort()


@cli.command()
def status():
    """Check database status and health"""
    click.echo("Checking database status...")
    
    try:
        db = SessionLocal()
        health = check_db_health(db)
        db.close()
        
        if health['status'] == 'healthy':
            click.echo(click.style("✓ Database is healthy", fg="green"))
            click.echo(f"  Connected: {health['connected']}")
            click.echo(f"  Users: {health['users']}")
            click.echo(f"  Equipment: {health['equipment']}")
        else:
            click.echo(click.style("✗ Database is unhealthy", fg="red"))
            click.echo(f"  Error: {health.get('error', 'Unknown error')}")
            
        # Check migration status
        click.echo("\nMigration status:")
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'current'], capture_output=True, text=True)
        click.echo(result.stdout)
        
    except Exception as e:
        click.echo(click.style(f"✗ Error checking database status: {e}", fg="red"))
        raise click.Abort()


@cli.command()
def history():
    """Show migration history"""
    click.echo("Migration history:")
    
    import subprocess
    result = subprocess.run([sys.executable, '-m', 'alembic', '-c', 'petroflow/alembic.ini', 'history'], capture_output=True, text=True)
    
    if result.returncode == 0:
        click.echo(result.stdout)
    else:
        click.echo(click.style(f"✗ Error getting migration history: {result.stderr}", fg="red"))
        raise click.Abort()


@cli.command()
def create_tables():
    """Create all database tables"""
    click.echo("Creating database tables...")
    
    try:
        create_tables()
        click.echo(click.style("✓ Tables created successfully!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Error creating tables: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to drop all tables? This will delete all data!')
def drop_tables():
    """Drop all database tables"""
    click.echo(click.style("WARNING: Dropping all tables!", fg="yellow"))
    
    try:
        drop_tables()
        click.echo(click.style("✓ Tables dropped successfully!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Error dropping tables: {e}", fg="red"))
        raise click.Abort()


if __name__ == '__main__':
    cli()