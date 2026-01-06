# backend/app/db_utils.py
"""
Database utilities for handling concurrency, locking, and optimizations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import OperationalError, IntegrityError
from contextlib import contextmanager
from functools import wraps
import time
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

class LockTimeoutError(Exception):
    """Raised when unable to acquire lock within timeout"""
    pass

class ConcurrencyError(Exception):
    """Raised when concurrent modification detected"""
    pass

@contextmanager
def db_lock_row(db: Session, model, row_id: int, timeout: int = 10):
    """
    Context manager for row-level locking using SELECT FOR UPDATE.
    Prevents race conditions when multiple users try to modify the same row.
    
    Usage:
        with db_lock_row(db, Equipment, equipment_id):
            # Perform operations on locked row
            equipment = db.query(Equipment).get(equipment_id)
            equipment.status = 'IN_USE'
            db.commit()
    """
    start_time = time.time()
    max_retries = timeout
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Acquire lock using SELECT FOR UPDATE
            locked_row = db.query(model).filter(model.id == row_id).with_for_update(nowait=False).first()
            
            if locked_row is None:
                raise ValueError(f"Row with id {row_id} not found in {model.__tablename__}")
            
            logger.debug(f"Lock acquired for {model.__tablename__}.{row_id}")
            yield locked_row
            return
            
        except OperationalError as e:
            # Database is locked, retry
            retry_count += 1
            if retry_count >= max_retries:
                elapsed = time.time() - start_time
                logger.error(f"Failed to acquire lock on {model.__tablename__}.{row_id} after {elapsed:.2f}s")
                raise LockTimeoutError(
                    f"Could not acquire lock on {model.__tablename__} row {row_id}. "
                    f"Another user may be modifying this record. Please try again."
                )
            
            # Exponential backoff
            wait_time = min(0.1 * (2 ** retry_count), 1.0)
            logger.debug(f"Lock retry {retry_count}/{max_retries}, waiting {wait_time}s")
            time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"Unexpected error acquiring lock: {str(e)}")
            raise

def retry_on_lock_error(max_retries: int = 3, backoff: float = 0.1):
    """
    Decorator to retry database operations on lock errors.
    Handles transient database lock errors automatically.
    
    Usage:
        @retry_on_lock_error(max_retries=3)
        def my_db_operation(db: Session):
            # Database operations
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                    
                except (OperationalError, IntegrityError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a retryable error
                    if 'locked' in error_msg or 'busy' in error_msg or 'deadlock' in error_msg:
                        if attempt < max_retries - 1:
                            wait_time = backoff * (2 ** attempt)
                            logger.warning(
                                f"Database lock/busy error in {func.__name__}, "
                                f"retry {attempt + 1}/{max_retries} after {wait_time}s"
                            )
                            time.sleep(wait_time)
                            
                            # Rollback the session to clean state
                            if args and hasattr(args[0], 'rollback'):
                                args[0].rollback()
                            continue
                    
                    # Non-retryable error
                    raise
                    
                except Exception as e:
                    # Non-database errors should not be retried
                    raise
            
            # All retries exhausted
            logger.error(f"All {max_retries} retries exhausted for {func.__name__}")
            raise last_exception
            
        return wrapper
    return decorator

def optimistic_lock_update(
    db: Session,
    model,
    row_id: int,
    updates: dict,
    version_field: str = 'updated_at'
) -> Optional[Any]:
    """
    Optimistic locking: Update with version check.
    Detects concurrent modifications without explicit locks.
    
    Usage:
        result = optimistic_lock_update(
            db, Equipment, equipment_id,
            {'status': 'IN_USE'},
            version_field='updated_at'
        )
        if result is None:
            raise ConcurrencyError("Record was modified by another user")
    """
    from datetime import datetime, timezone
    from sqlalchemy import update
    
    # Get current version
    row = db.query(model).filter(model.id == row_id).first()
    if not row:
        return None
    
    old_version = getattr(row, version_field)
    new_version = datetime.now(timezone.utc)
    
    # Update with version check
    updates[version_field] = new_version
    
    stmt = (
        update(model)
        .where(and_(
            model.id == row_id,
            getattr(model, version_field) == old_version
        ))
        .values(**updates)
    )
    
    result = db.execute(stmt)
    db.commit()
    
    if result.rowcount == 0:
        # Version mismatch - concurrent update detected
        logger.warning(f"Optimistic lock failure for {model.__tablename__}.{row_id}")
        return None
    
    # Return updated row
    db.expire_all()
    return db.query(model).filter(model.id == row_id).first()

def batch_insert_optimized(db: Session, model, records: list, batch_size: int = 100):
    """
    Optimized batch insert with chunking.
    Reduces database round-trips for bulk operations.
    
    Usage:
        records = [Equipment(name=f"Eq{i}", equipment_id=f"ID{i}") for i in range(1000)]
        batch_insert_optimized(db, Equipment, records, batch_size=100)
    """
    total = len(records)
    inserted = 0
    
    try:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            db.bulk_save_objects(batch)
            db.commit()
            inserted += len(batch)
            logger.debug(f"Inserted batch {i//batch_size + 1}, total: {inserted}/{total}")
        
        logger.info(f"Successfully inserted {inserted} {model.__tablename__} records")
        return inserted
        
    except Exception as e:
        logger.error(f"Batch insert failed: {str(e)}")
        db.rollback()
        raise

def execute_with_isolation(
    db: Session,
    func: Callable,
    isolation_level: str = "SERIALIZABLE"
):
    """
    Execute function with specific isolation level.
    Use for critical sections requiring strong consistency.
    
    Isolation levels:
    - READ UNCOMMITTED: Lowest isolation, dirty reads possible
    - READ COMMITTED: No dirty reads (default for most databases)
    - REPEATABLE READ: No dirty or non-repeatable reads
    - SERIALIZABLE: Highest isolation, no anomalies
    
    Usage:
        def critical_operation(db):
            # Critical database operations
            pass
        
        result = execute_with_isolation(db, critical_operation, "SERIALIZABLE")
    """
    original_level = db.connection().connection.isolation_level
    
    try:
        # Set isolation level
        db.connection().connection.isolation_level = isolation_level
        logger.debug(f"Set isolation level to {isolation_level}")
        
        # Execute function
        result = func(db)
        db.commit()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in isolated transaction: {str(e)}")
        db.rollback()
        raise
        
    finally:
        # Restore original isolation level
        db.connection().connection.isolation_level = original_level

class QueryOptimizer:
    """Helper class for query optimization"""
    
    @staticmethod
    def paginate_query(query, page: int = 1, per_page: int = 50):
        """Efficient pagination"""
        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page)
    
    @staticmethod
    def add_eager_loading(query, *relationships):
        """Add eager loading for relationships to avoid N+1 queries"""
        from sqlalchemy.orm import joinedload
        
        for rel in relationships:
            query = query.options(joinedload(rel))
        return query
    
    @staticmethod
    def get_count_optimized(query) -> int:
        """Optimized count query"""
        from sqlalchemy import func, select
        
        # Use subquery for better performance on large tables
        count_query = select(func.count()).select_from(query.subquery())
        return query.session.execute(count_query).scalar()

# Connection pool health check
def check_connection_pool_health(engine) -> dict:
    """
    Check database connection pool health.
    Useful for monitoring and debugging.
    """
    pool = engine.pool
    
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.checkedin() + pool.checkedout(),
        "status": "healthy" if pool.checkedin() > 0 else "warning"
    }
